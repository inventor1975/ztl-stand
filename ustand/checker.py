"""Independent checker: shares NO code with the judge (ZTL) or the stand's forward step.

It reads each law with its own small parser (Python's ast, a closed list of node
kinds). Laws are of two kinds:
  * LINEAR rows — linear in the derived quantities, with exact numbers for every
    given, toleranced or chosen quantity — solved together, exactly;
  * DEFINITIONS — `X == expression`, where the expression may multiply derived
    quantities (power, energy); evaluated after the linear rows.

What it can confirm, stated plainly:
  * a WITNESS — every derived value at one concrete point — always, exactly
    (rational arithmetic, no rounding);
  * the RANGE of a linear unknown by enumerating the box's corners — the true
    range when each linear unknown is monotone in each single toleranced quantity
    (linear-fractional per parameter: the judge's own exact class);
  * an OUTER BOUND of a definition by its own interval arithmetic over those
    ranges and the box — sound (never too narrow), possibly too wide.
Corner enumeration is 2^n: a checker for small cases, not a solver.
"""
from __future__ import annotations

import ast
import math
import copy
import itertools
from fractions import Fraction as F

MAX_CORNER_PARAMS = 16


from .stopflag import check as _stop_check   # noqa: E402

class CheckError(ValueError):
    pass


class NonLinear(CheckError):
    pass


# ── exact linear forms ────────────────────────────────────────────────────
def _lin(node, env, unknowns):
    """Expression -> {unknown or 1: coefficient}, linear in the unknowns."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return {1: F(str(node.value))}
    if isinstance(node, ast.Name):
        if node.id in env:
            return {1: env[node.id]}
        if node.id in unknowns:
            return {node.id: F(1)}
        raise CheckError(f"unknown name {node.id!r}")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        e = _lin(node.operand, env, unknowns)
        return {k: -v for k, v in e.items()} if isinstance(node.op, ast.USub) else e
    if isinstance(node, ast.BinOp):
        a, b = _lin(node.left, env, unknowns), _lin(node.right, env, unknowns)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            s = 1 if isinstance(node.op, ast.Add) else -1
            out = dict(a)
            for k, v in b.items():
                out[k] = out.get(k, 0) + s * v
            return out
        if isinstance(node.op, ast.Mult):
            if set(a) <= {1}:
                return {k: a.get(1, 0) * v for k, v in b.items()}
            if set(b) <= {1}:
                return {k: b.get(1, 0) * v for k, v in a.items()}
            raise NonLinear("product of two unknowns")
        if isinstance(node.op, ast.Div):
            if set(b) <= {1} and b.get(1, 0) != 0:
                return {k: v / b[1] for k, v in a.items()}
            raise NonLinear("division by an unknown")
    raise CheckError(f"unsupported expression: {ast.dump(node)[:60]}")


def _eq(law):
    return _eq_parsed(law)


@__import__("functools").lru_cache(maxsize=8192)
def _eq_parsed(law):
    """A law parsed once (2026-10-20: re-parsed at every exact solution, 7-13 % of the bridge girder's time). The
    trees are read, never changed, by the callers."""
    tree = ast.parse(law, mode="eval").body
    if not (isinstance(tree, ast.Compare) and len(tree.ops) == 1 and isinstance(tree.ops[0], ast.Eq)):
        raise CheckError(f"a law must be one equality 'lhs == rhs': {law!r}")
    return tree.left, tree.comparators[0]


_CLASSIFY = {}


def classify(laws, names, unknowns):
    """Memoized _classify: the same laws are classified again at every point (MEASURED 2026-10-10, blind
    test 2 c10: 3.5 s of 9.8). The result is read, never changed, by its callers."""
    key = (tuple(laws), frozenset(names), tuple(unknowns))
    hit = _CLASSIFY.get(key)
    if hit is None:
        hit = _classify(laws, names, unknowns)
        if len(_CLASSIFY) > 4096:
            _CLASSIFY.clear()
        _CLASSIFY[key] = hit
    return hit


def _classify(laws, names, unknowns):
    """(linear laws, definitions [(name, rhs ast)]). names: every non-derived name.

    The checker's own reading of which laws are definitions (it shares no code with forward.split):
    a law is a definition when it is nonlinear in the unknowns, holds a function call, or uses a
    quantity already found to be a definition — repeated until nothing changes (a chain)."""
    env = {n: F(1) for n in names}
    unknowns = set(unknowns)
    eqs = [(law,) + _eq(law) for law in laws]
    defined, defs = set(), []

    def is_def_form(l, r):
        return isinstance(l, ast.Name) and l.id in unknowns and l.id not in _names_of(r)

    changed = True
    while changed:
        changed = False
        for law, l, r in eqs:
            if is_def_form(l, r) and l.id in defined:
                continue
            calls = any(isinstance(n, ast.Call) for n in ast.walk(l)) or any(isinstance(n, ast.Call) for n in ast.walk(r))
            leans = bool((_names_of(l) | _names_of(r)) & defined)
            nonlinear = False
            if not calls and not leans:
                try:
                    _lin(l, env, unknowns); _lin(r, env, unknowns)
                except NonLinear:
                    nonlinear = True
            if (calls or leans or nonlinear) and is_def_form(l, r) and l.id not in defined:
                defined.add(l.id)
                defs.append((l.id, r))
                changed = True
    linear = []
    for law, l, r in eqs:
        if is_def_form(l, r) and any(d == l.id and rr is r for d, rr in defs):
            continue
        if any(isinstance(n, ast.Call) for n in ast.walk(l)) or any(isinstance(n, ast.Call) for n in ast.walk(r)) \
                or ((_names_of(l) | _names_of(r)) & defined):
            raise CheckError(f"a law with a function or a defined quantity must define one derived quantity: {law!r}")
        try:
            _lin(l, env, unknowns); _lin(r, env, unknowns)
        except NonLinear:
            raise CheckError(f"a nonlinear law must define one derived quantity: {law!r}")
        linear.append(law)
    return linear, defs


# ── functions: the CHECKER'S OWN brackets (mpmath interval arithmetic, 200 bits) ───────────
# ZTL reads exp/ln/... with its own series (zfunc.py); the checker must not share that code,
# so it uses a different library: mpmath's interval arithmetic, outward-rounded, whose ends are
# converted to fractions EXACTLY (the raw mantissa and exponent, never through a float).
class NeedsInterval(CheckError):
    """A value at a point that is irrational (a function of exact numbers): an interval, not a number."""


def _mp_frac(raw):
    sign, man, exp, _bc = raw
    v = F(man) * (F(2) ** exp) if exp >= 0 else F(man, 2 ** (-exp))
    return -v if sign else v


def _call_iv(name, args):
    import mpmath
    ivc = mpmath.iv
    ivc.prec = 200

    def to_iv(a):
        lo = ivc.mpf(a[0].numerator) / ivc.mpf(a[0].denominator)
        hi = ivc.mpf(a[1].numerator) / ivc.mpf(a[1].denominator)
        return ivc.mpf([lo.a, hi.b])

    def back(x):
        lo, hi = x._mpi_
        return _mp_frac(lo), _mp_frac(hi)

    if name in ("min", "max"):
        (a, b), (c, d) = args
        return (min(a, c), min(b, d)) if name == "min" else (max(a, c), max(b, d))
    if name == "pow":
        (a, b), (c, d) = args
        if c == d and c.denominator == 1:                   # an integer power: exact, by hand
            n = int(c)
            if n == 0:
                return F(1), F(1)
            if n < 0 and a <= 0 <= b:
                raise CheckError("pow: a negative power of a range containing zero")
            ends = [a ** n, b ** n] if n > 0 else [F(1) / a ** -n, F(1) / b ** -n]
            if n > 0 and n % 2 == 0 and a < 0 < b:
                return F(0), max(ends)
            return min(ends), max(ends)
        if a <= 0:
            raise CheckError("pow: a non-integer power of a range reaching zero or below")
        return back(ivc.exp(to_iv((c, d)) * ivc.log(to_iv((a, b)))))
    (a, b), = args
    if name in ("ln", "log10", "sqrt") and a < 0 or (name in ("ln", "log10") and a == 0):
        raise CheckError(f"{name} of a range reaching below its domain")
    if name == "tan" and not (-F(3, 2) <= a and b <= F(3, 2)):
        raise CheckError("tan read only on |x| <= 1.5")
    x = to_iv((a, b))
    if name == "exp":
        return back(ivc.exp(x))
    if name == "ln":
        return back(ivc.log(x))
    if name == "log10":
        return back(ivc.log(x) / ivc.log(ivc.mpf(10)))
    if name == "atan":
        return back(ivc.atan2(x, ivc.mpf(1)))
    if name == "tan":
        return back(ivc.tan(x))
    if name == "sin":
        return back(ivc.sin(x))
    if name == "cos":
        return back(ivc.cos(x))
    if name == "sqrt":
        return back(ivc.sqrt(x))
    raise CheckError(f"unknown function {name}")


# ── exact evaluation at a point ──────────────────────────────────────────
def _val(node, env):
    if isinstance(node, ast.Constant):
        return F(str(node.value))
    if isinstance(node, ast.Call):
        raise NeedsInterval(f"{node.func.id}(...) is irrational at a point: read as an interval")
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise CheckError(f"no value for {node.id!r}")
        if isinstance(env[node.id], tuple):
            raise NeedsInterval(f"{node.id} is an interval at this point")
        return env[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _val(node.operand, env)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.BinOp):
        a, b = _val(node.left, env), _val(node.right, env)
        if isinstance(node.op, ast.Add): return a + b
        if isinstance(node.op, ast.Sub): return a - b
        if isinstance(node.op, ast.Mult): return a * b
        if isinstance(node.op, ast.Div):
            if b == 0:
                raise CheckError("division by zero")
            return a / b
    raise CheckError(f"unsupported expression: {ast.dump(node)[:60]}")


_ELIM = {}          # coefficient matrix -> (reduced matrix, the row operations T, rank, pivots); see solve_at


def solve_at(laws, env, unknowns):
    """Exact values of every derived quantity at one point (env: name -> Fraction)."""
    unknowns = list(unknowns)
    linear, defs = classify(laws, set(env), unknowns)
    defined = {n for n, _ in defs}
    lin_unknowns = [u for u in unknowns if u not in defined]
    rows = []
    for law in linear:
        l, r = _eq(law)
        a, b = _lin(l, env, set(lin_unknowns)), _lin(r, env, set(lin_unknowns))
        row = dict(a)
        for k, v in b.items():
            row[k] = row.get(k, 0) - v
        rows.append(row)
    n = len(lin_unknowns)
    M = tuple(tuple(row.get(u, F(0)) for u in lin_unknowns) for row in rows)
    rhs = [-row.get(1, F(0)) for row in rows]
    # THE ELIMINATION IS CACHED PER MATRIX (2026-10-20, the bridge girder: a 93-unknown truss whose matrix is the same
    # at every point — only the loads, on the right, move — was 1080 fresh Gauss-Jordan eliminations, 136 of 156 s).
    # The same row operations are recorded once as T (T·M = the reduced matrix) and applied to each right-hand side:
    # exactly the arithmetic the elimination would do on that column, O(n^2) instead of O(n^3).
    hit = _ELIM.get(M)
    if hit is None:
        m_ = len(M)
        A = [list(M[i]) + [F(int(i == j)) for j in range(m_)] for i in range(m_)]
        r, piv = 0, []
        for c in range(n):
            p = next((i for i in range(r, m_) if A[i][c] != 0), None)
            if p is None:
                continue
            A[r], A[p] = A[p], A[r]
            for i in range(m_):
                if i != r and A[i][c] != 0:
                    f = A[i][c] / A[r][c]
                    A[i] = [x - f * y for x, y in zip(A[i], A[r])]
            piv.append(c); r += 1
        hit = ([row[:n] for row in A], [row[n:] for row in A], r, piv)
        if len(_ELIM) >= 16:
            _ELIM.pop(next(iter(_ELIM)))
        _ELIM[M] = hit
    R, Tm, r, piv = hit
    tb = [sum((t * b for t, b in zip(trow, rhs) if t and b), F(0)) for trow in Tm]
    A = [list(R[i]) + [tb[i]] for i in range(len(R))]
    # a SINGULAR point named (J11, blind test 4, c06, 2026-10-11: with purge p = 0 an impurity has no way out, no
    # steady state — the stand said only "the laws do not determine every derived quantity")
    free = [lin_unknowns[c] for c in range(n) if c not in piv]

    def _point():
        # the point, named only when an error is raised (2026-10-12: built at EVERY solve, with the laws' names
        # re-parsed once per environment entry, it was 89 of 125 s of the feed brick t24 under a profiler)
        named = {x for l in linear for x in _names_of(_eq(l)[0]) | _names_of(_eq(l)[1])}
        return ", ".join(f"{k.replace('__', '.')} = {v}" for k, v in sorted(env.items())
                         if not isinstance(v, tuple) and k in named)
    if any(all(x == 0 for x in row[:-1]) and row[-1] != 0 for row in A[r:]):
        raise CheckError(f"at {_point()[:200]} the linear laws have NO solution"
                         + (f" ({', '.join(free)} cannot be fixed)" if free else "")
                         + " — e.g. a balance with no way out (no steady state). If that case means failure, keep it "
                           "out with `where` or bound the given away from it")
    if r < n:
        raise CheckError(f"at {_point()[:200]} the linear laws do not fix {', '.join(free)} (a singular system: many "
                         "solutions) — the laws do not determine every derived quantity there")
    out = {lin_unknowns[c]: A[i][-1] / A[i][c] for i, c in enumerate(piv)}
    full = dict(env, **out)
    pending = list(defs)
    while pending:
        progress = False
        for item in list(pending):
            name, rhs = item
            try:
                try:
                    full[name] = out[name] = _val(rhs, full)
                except NeedsInterval:
                    # a FUNCTION in the definition (2026-10-10): the value at this point is a proved
                    # interval (lo, hi) of the checker's own; a requirement is violated only when
                    # the whole interval is past its bound
                    rng = {k: (v if isinstance(v, tuple) else (v, v)) for k, v in full.items()}
                    full[name] = out[name] = _ivl(rhs, rng)
                pending.remove(item); progress = True
            except CheckError:
                pass
        if not progress:
            raise CheckError("definitions depend on each other in a cycle or on an unknown")
    return out


def _groups(laws, boxes, unknowns, couple=()):
    """The laws split into INDEPENDENT groups (no derived quantity shared); each group's toleranced names.
    couple: more name sets that bind their names together like a law — a requirement's quantity with the names in
    its bound (real round 2, s02: F >= Fneed with Fneed in no law sat at its low end, so no corner showed the
    failure at mu high AND Fneed high), and the objective's names."""
    unknowns = set(unknowns)
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    law_names = []
    sets = []
    for law in laws:
        l, r = _eq(law)
        sets.append(_names_of(l) | _names_of(r))
    sets.extend(set(c) for c in couple)
    for ns in sets:
        law_names.append(ns)
        ds = sorted(ns & unknowns)
        for d in ds[1:]:
            parent[find(ds[0])] = find(d)
        if ds:
            find(ds[0])
    groups = {}
    for ns in law_names:
        ds = ns & unknowns
        key = find(sorted(ds)[0]) if ds else None
        groups.setdefault(key, set()).update(n for n in ns if n in boxes)
    return list(groups.values())


def corners(laws, fixed, boxes, unknowns, couple=()):
    """Corners of the tolerance box: [(point, values)] — every corner of each INDEPENDENT group of laws, the
    other groups held at their low corner (blind test 3, c12: 31 toleranced quantities over independent
    nutrient laws were 2^31 corners and the checker refused; per group they are a few each). Every listed
    point is a true corner of the whole box, and every quantity sees all the corners of its own group."""
    names = sorted(boxes)
    groups = [sorted(g) for g in _groups(laws, boxes, unknowns, couple) if g]
    covered = set().union(*groups) if groups else set()
    for g in groups:
        if len(g) > MAX_CORNER_PARAMS:
            raise CheckError(f"{len(g)} toleranced quantities in one group of coupled laws: 2^n corners too "
                             "many for the checker")
    base = {nm: boxes[nm][0] for nm in names}
    seen, out = set(), []
    for g in groups or [[]]:
        for ends in itertools.product((0, 1), repeat=len(g)):
            point = dict(base, **{nm: boxes[nm][e] for nm, e in zip(g, ends)})
            key = tuple(point[nm] for nm in names)
            if key in seen:
                continue
            seen.add(key)
            out.append((point, solve_at(laws, dict(fixed, **point), unknowns)))
    return out


# ── its own interval arithmetic (independent of the stand's forward step) ──
def _branch_side(x):
    return 1 if x[0] > 0 else (-1 if x[1] <= 0 else 0)


def _ivl(node, rng):
    if isinstance(node, ast.Call) and node.func.id == "implicit":
        return _implicit_iv(node, rng)
    if isinstance(node, ast.Call) and node.func.id in ("ifpos", "ifpos_d"):
        # a branch, read by the checker's own rule: decided -> that branch; not decided -> the hull of both
        # (ifpos) or no reading at all (ifpos_d, a derivative: across a jump its sign says nothing)
        side = _branch_side(_ivl(node.args[0], rng))
        if side:
            return _ivl(node.args[1] if side == 1 else node.args[2], rng)
        if node.func.id == "ifpos_d":
            raise CheckError("the derivative of a branch is not read where the branch is undecided")
        a, b = _ivl(node.args[1], rng), _ivl(node.args[2], rng)
        return min(a[0], b[0]), max(a[1], b[1])
    if isinstance(node, ast.Call):
        return _call_iv(node.func.id, [_ivl(a, rng) for a in node.args])
    if isinstance(node, ast.Constant):
        v = F(str(node.value)); return (v, v)
    if isinstance(node, ast.Name):
        if node.id not in rng:
            raise CheckError(f"no range for {node.id!r}")
        return rng[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        lo, hi = _ivl(node.operand, rng); return (-hi, -lo)
    if isinstance(node, ast.BinOp):
        (a, b), (c, d) = _ivl(node.left, rng), _ivl(node.right, rng)
        if isinstance(node.op, ast.Add): return (a + c, b + d)
        if isinstance(node.op, ast.Sub): return (a - d, b - c)
        if isinstance(node.op, ast.Mult):
            p = [a * c, a * d, b * c, b * d]; return (min(p), max(p))
        if isinstance(node.op, ast.Div):
            if c <= 0 <= d:
                raise CheckError("interval division by a range containing zero")
            p = [a / c, a / d, b / c, b / d]; return (min(p), max(p))
    raise CheckError(f"unsupported expression: {ast.dump(node)[:60]}")


# ── an IMPLICIT law, read with the checker's own means (gap G6, 2026-10-10) ──
# Q == implicit(_root_Q, g, lo, hi): Q is a root of g in [lo, hi]. ZTL checks a certificate
# brought by the stand (ZTL/zimplicit.py); here the checker finds its OWN enclosure, with its own
# interval arithmetic (mpmath for functions) and its own derivative, sharing no code with either:
#   1. exclusion: a piece of [lo, hi] whose reading of g (over the piece and the whole range of
#      everything else) keeps one strict sign holds no root; the pieces at the edges of what is
#      left are halved again, IMPLICIT_DEPTH times — every root lies in what is left (sound);
#   2. over a BOX, tightening: when dg/dQ keeps one strict sign over that hull and the box, and so
#      does dg/dp for every parameter p (or reads exactly 0), the root is monotone in each p, so its
#      extremes sit at two corners — those two corners are read as points (step 1 again).
# A range with no root left raises CheckError: the checker says it cannot evaluate, never guesses.
IMPLICIT_DEPTH = 48
BOX_COARSE = 14


# ── the FAST reading for implicit laws: the whole expression in mpmath interval arithmetic (200 bits,
# outward rounding) — the checker's own and sound, without the exact fractions growing on every step
# (MEASURED 2026-10-10: the pump, 513 corners, 72 s in Fraction arithmetic). A sign is read from it.
_IVC = []


def _mpiv():
    # the precision set ONCE (MEASURED 2026-10-11, blind test 4 c04: setting it on every node was 46 M calls,
    # ~10 % of a 191 s design); any precision keeps the reading sound, 200 bits keeps it tight
    if not _IVC:
        import mpmath
        mpmath.iv.prec = 200
        _IVC.append(mpmath.iv)
    return _IVC[0]


_LEAF = {}


def _leaf(x):
    v = _LEAF.get(x)
    if v is None:
        ivc = _mpiv()
        v = ivc.mpf(x.numerator) / ivc.mpf(x.denominator)
        if len(_LEAF) < 200000:
            _LEAF[x] = v
    return v


def _ivm(node, rng):
    """The fast reading of `node` over `rng` (names -> exact ranges). The ranges become mpmath intervals ONCE per
    reading, and the expression is compiled ONCE into closures (MEASURED 2026-10-11, blind test 4 c04 P2+G3:
    re-dispatching every node and re-converting every constant on each of 46 M visits took most of 191 s)."""
    _stop_check()                   # a stop asked from outside, seen here at a safe point (stopflag.py)
    ivc = _mpiv()
    env = {}
    for n, (a, b) in rng.items():
        env[n] = _leaf(a) if a == b else ivc.mpf([_leaf(a).a, _leaf(b).b])
    return _compiled(node)(env)


_CC = {}


def _compiled(node):
    hit = _CC.get(id(node))
    if hit is None or hit[0] is not node:
        hit = _CC[id(node)] = (node, _compile(node))
    return hit[1]


def _compile(node):
    ivc = _mpiv()
    if isinstance(node, ast.Constant):
        c = _leaf(F(str(node.value)))
        return lambda env: c
    if isinstance(node, ast.Name):
        name = node.id

        def leaf(env):
            try:
                return env[name]
            except KeyError:
                raise CheckError(f"no range for {name!r}")
        return leaf
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        f = _compile(node.operand)
        return lambda env: -f(env)
    if isinstance(node, ast.BinOp):
        fl, fr = _compile(node.left), _compile(node.right)
        if isinstance(node.op, ast.Add):
            return lambda env: fl(env) + fr(env)
        if isinstance(node.op, ast.Sub):
            return lambda env: fl(env) - fr(env)
        if isinstance(node.op, ast.Mult):
            return lambda env: fl(env) * fr(env)
        if isinstance(node.op, ast.Div):
            def div(env):
                x, y = fl(env), fr(env)
                try:
                    straddles = y.a <= 0 <= y.b
                except TypeError:       # mpmath refused the comparison (its bare `except:` returns NotImplemented on
                    # ANY exception inside — 2026-10-12: a test's alarm signal, not a NaN as first written)
                    raise CheckError("interval division by an undefined range")
                if straddles:
                    raise CheckError("interval division by a range containing zero")
                return x / y
            return div
    if isinstance(node, ast.Call) and node.func.id in ("ifpos", "ifpos_d"):
        fc, fa, fb = (_compile(x) for x in node.args)
        deriv = node.func.id == "ifpos_d"

        def branch(env):
            x = fc(env)
            if x.a > 0:
                return fa(env)
            if x.b <= 0:
                return fb(env)
            if deriv:
                raise CheckError("the derivative of a branch is not read where the branch is undecided")
            a, b = fa(env), fb(env)
            return ivc.mpf([min(a.a, b.a), max(a.b, b.b)])
        return branch
    if isinstance(node, ast.Call) and node.func.id != "implicit":
        name = node.func.id
        fs = [_compile(x) for x in node.args]
        if name in ("min", "max"):
            f1, f2 = fs
            if name == "min":
                return lambda env: (lambda a, b: ivc.mpf([min(a.a, b.a), min(a.b, b.b)]))(f1(env), f2(env))
            return lambda env: (lambda a, b: ivc.mpf([max(a.a, b.a), max(a.b, b.b)]))(f1(env), f2(env))
        if name == "pow":
            fa_, fe = fs

            def pw(env):
                a, e = fa_(env), fe(env)
                n = None
                if e.a == e.b and int(e.a) == e.a:
                    n = int(e.a)
                if n is not None:
                    if n == 0:
                        return ivc.mpf(1)
                    if n < 0 and a.a <= 0 <= a.b:
                        raise CheckError("pow: a negative power of a range containing zero")
                    if n > 0 and n % 2 == 0 and a.a < 0 < a.b:
                        m = max(abs(a.a), abs(a.b)) ** n
                        return ivc.mpf([0, ivc.mpf(m).b])
                    return a ** n
                if a.a <= 0:
                    raise CheckError("pow: a non-integer power of a range reaching zero or below")
                return ivc.exp(e * ivc.log(a))
            return pw
        if len(fs) != 1:
            raise CheckError(f"unsupported expression: {ast.dump(node)[:60]}")
        (f1,) = fs

        def fn(env):
            a = f1(env)
            if name in ("ln", "log10") and a.a <= 0 or name == "sqrt" and a.a < 0:
                raise CheckError(f"{name} of a range reaching below its domain")
            if name == "tan" and not (-1.5 <= a.a and a.b <= 1.5):
                raise CheckError("tan read only on |x| <= 1.5")
            if name == "exp": return ivc.exp(a)
            if name == "ln": return ivc.log(a)
            if name == "log10": return ivc.log(a) / ivc.log(ivc.mpf(10))
            if name == "atan": return ivc.atan2(a, ivc.mpf(1))
            if name == "tan": return ivc.tan(a)
            if name == "sin": return ivc.sin(a)
            if name == "cos": return ivc.cos(a)
            if name == "sqrt": return ivc.sqrt(a)
            raise CheckError(f"unsupported expression: {ast.dump(node)[:60]}")
        return fn
    raise CheckError(f"unsupported expression: {ast.dump(node)[:60]}")


def _sgn(node, rng):
    """1 / -1 when the fast reading keeps one strict sign, 0 when it does not, None when undefined."""
    try:
        r = _ivm(node, rng)
    except (CheckError, ValueError, ZeroDivisionError):
        return None
    if r.a > 0:
        return 1
    if r.b < 0:
        return -1
    return 0


_DCACHE = {}


def _dg(g, p):
    """The checker's derivative of g by p, folded — built once per law (the readings repeat it)."""
    hit = _DCACHE.get((id(g), p))
    if hit is None or hit[0] is not g:
        hit = _DCACHE[(id(g), p)] = (g, _fold(_d(g, p)))
    return hit[1]


def _g_excludes(g, ph, rng, a, b, splits=6):
    """No root of g for q in [a, b] and every point of rng — the checker's reading: plain first;
    then MONOTONE per variable (its own derivative): a variable whose dg/dv keeps one sign over the
    piece goes to the end where g is lowest (resp. highest), the others stay intervals; q itself
    too, so a range ending AT a root is excluded beyond it (2026-10-10, the pump's P3). A variable
    whose sign the reading cannot fix is halved, up to `splits` times (sound: both halves must
    exclude) — the checker's derivative reading is looser than ZTL's (pump P3: dg/dD read
    [-61, 934] here, [282, 933] by ZTL)."""
    box = dict(rng, **{ph: (a, b)})
    s0 = _sgn(g, box)
    if s0 is None:
        return False
    if s0:
        return True
    names = [n for n in _names_of(g) if n in box and box[n][0] != box[n][1]]
    if not names:
        return False
    low, high = dict(box), dict(box)
    unsigned = []
    for v in names:
        try:
            sv = _sgn(_dg(g, v), box)
        except CheckError:                   # min/max: no derivative — that variable stays an interval
            sv = 0
        if sv == 1:
            low[v], high[v] = (box[v][0],) * 2, (box[v][1],) * 2
        elif sv == -1:
            low[v], high[v] = (box[v][1],) * 2, (box[v][0],) * 2
        else:
            unsigned.append(v)
    try:
        lo_r, hi_r = _ivm(g, low), _ivm(g, high)
    except (CheckError, ValueError, ZeroDivisionError):
        return False
    if lo_r.a > 0 or hi_r.b < 0:
        return True
    if splits <= 0 or (lo_r.b < 0 < hi_r.a and not unsigned):
        return False              # every variable signed and the corners straddle 0: a root is real
    cands = [u for u in unsigned if u != ph]
    if not cands:
        return False
    # the WIDEST unsigned variable, relative to its size (it was the first in the list)
    v = max(cands, key=lambda u: (box[u][1] - box[u][0]) / (abs(box[u][0]) + abs(box[u][1]) or 1))
    m = (box[v][0] + box[v][1]) / 2
    return all(_g_excludes(g, ph, dict(rng, **{v: half}), a, b, splits - 1)
               for half in ((box[v][0], m), (m, box[v][1])))


_HINTS = {}        # law text -> [(box, hull)]: the checker's OWN enclosures over boxes, proved for every point


def _hint(key, g, ph, rng, lo, hi):
    """A narrower start for [lo, hi]: a hull the checker proved over a box that holds this rng."""
    for box, hull in _HINTS.get(key, ()):
        if all(n in rng and box[n][0] <= rng[n][0] and rng[n][1] <= box[n][1]
               for n in box):
            return max(lo, hull[0]), min(hi, hull[1])
    return lo, hi


def prime_implicit(laws, fixed, boxes):
    """Enclose every implicit quantity over the whole box ONCE, before the corners: each corner then
    starts its root search from that proved hull, not from the whole search range (G10, MEASURED
    2026-10-10: the pump's 513 corners). Sound: the hull holds every root at every point of the box."""
    rng = {n: (v, v) for n, v in fixed.items()}
    rng.update(boxes)
    for law in laws:
        try:
            l, r = _eq(law)
        except CheckError:
            continue
        if isinstance(r, ast.Call) and getattr(r.func, "id", "") == "implicit":
            try:
                _ivl(r, rng)
            except CheckError:
                pass


def _implicit_iv(node, rng):
    ph, g = node.args[0].id, node.args[1]
    lo, hi = _ivl(node.args[2], {})[0], _ivl(node.args[3], {})[0]
    key = ast.unparse(node)
    target = (hi - lo) / 2 ** IMPLICIT_DEPTH          # the precision is the SEARCH range's, hint or not
    here = {n: rng[n] for n in _names_of(g) if n != ph and n in rng}
    for box, hull in _HINTS.get(key, ()):
        if box == here:
            return hull                                  # this very box, already enclosed
    lo, hi = _hint(key, g, ph, rng, lo, hi)
    out = _implicit_core(node, rng, ph, g, lo, hi, target)
    params = [n for n in _names_of(g) if n != ph and n in rng and rng[n][0] != rng[n][1]]
    if params:
        hints = _HINTS.setdefault(key, [])
        if len(hints) < 64:
            hints.append((here, out))
    return out


def _implicit_core(node, rng, ph, g, lo, hi, target):

    def rootless(a, b):
        return _g_excludes(g, ph, rng, a, b)

    params = sorted(n for n in _names_of(g) if n != ph and n in rng and rng[n][0] != rng[n][1])

    def read_at(x):
        try:
            r = _ivm(g, dict(rng, **{ph: (x, x)}))
        except (CheckError, ValueError, ZeroDivisionError):
            return 0, None
        return (1 if r.a > 0 else (-1 if r.b < 0 else 0)), float(r.mid)

    def one_root(a, b):
        """At a POINT: [a, b] holds exactly one root when dg/dq keeps one strict sign there."""
        try:
            return _sgn(_dg(g, ph), dict(rng, **{ph: (a, b)})) in (1, -1)
        except CheckError:
            return False

    live = [(lo, hi)] if not rootless(lo, hi) else []
    def prune(live, levels):
        idle = 0
        for level in range(levels):
            if not live or live[-1][1] - live[0][0] <= target:
                break
            if not params and len(live) == 1 and one_root(*live[0]):
                # at a POINT, one piece with ONE root (dg/dq strictly signed: a piece with three roots
                # would otherwise lose two — caught 2026-10-10 before it shipped): the secant step from
                # the float readings, each step CHECKED by the exact sign at c - eps and c + eps; the
                # bracket shrinks by ~2^20 a step (MEASURED: the pump's 513 corners, 58 s by pruning)
                a, b = live[0]
                (sa, fa), (sb, fb) = read_at(a), read_at(b)
                for _ in range(80):
                    if b - a <= target or not (sa and sb and sa != sb):
                        break
                    eps = max(target / 2, (b - a) / 2 ** 20)
                    try:
                        c = a + (b - a) * F(fa / (fa - fb)) if fa is not None and fb is not None and fa != fb \
                            else (a + b) / 2
                    except (OverflowError, ValueError, ZeroDivisionError):
                        c = (a + b) / 2
                    c1, c2 = max(a, c - eps), min(b, c + eps)
                    (s1, f1), (s2, f2) = read_at(c1), read_at(c2)
                    if s1 == 0 or s2 == 0:                    # no exact sign there: halve instead
                        m = (a + b) / 2
                        sm, fm = read_at(m)
                        if sm == 0:
                            break
                        a, b, sa, sb, fa, fb = (m, b, sm, sb, fm, fb) if sm == sa else (a, m, sa, sm, fa, fm)
                    elif s1 != s2:
                        a, b, sa, sb, fa, fb = c1, c2, s1, s2, f1, f2
                    elif s1 == sa:
                        a, sa, fa = c2, s2, f2
                    else:
                        b, sb, fb = c1, s1, f1
                live = [(a, b)]
                break
            nxt = []
            for i, (a, b) in enumerate(live):
                at_edge = i == 0 or i == len(live) - 1 or live[i - 1][1] != a or live[i + 1][0] != b
                if not at_edge:
                    nxt.append((a, b))
                    continue
                m = (a + b) / 2
                nxt += [p for p in ((a, m), (m, b)) if not rootless(*p)]
            if params and nxt and live and (nxt[0][0], nxt[-1][1]) == (live[0][0], live[-1][1]):
                idle += 1         # over a box, levels that exclude nothing: the reading's floor
                if idle >= 3:     # (one empty level stopped it early: hull 7% wider, 2026-10-10)
                    return nxt
            else:
                idle = 0
            live = nxt
        return live

    def tighten(hull):
        """Monotone in every parameter -> the extremes sit at two corners, read as points."""
        try:
            box = dict(rng, **{ph: hull})
            dq = _ivl(_dg(g, ph), box)
            if not (dq[0] > 0 or dq[1] < 0):
                return None
            sq = 1 if dq[0] > 0 else -1
            ends = {"min": {}, "max": {}}
            for p in params:
                dp = _ivl(_dg(g, p), box)
                if dp == (0, 0):
                    sp = 0
                elif dp[0] > 0 or dp[1] < 0:
                    sp = 1 if dp[0] > 0 else -1
                else:
                    return None                   # not monotone in p: the plain enclosure
                up = -sp * sq                     # the sign of dQ/dp
                ends["min"][p] = rng[p][1] if up < 0 else rng[p][0]
                ends["max"][p] = rng[p][1] if up > 0 else rng[p][0]
            a = _implicit_iv(node, dict(rng, **{p: (v, v) for p, v in ends["min"].items()}))
            b = _implicit_iv(node, dict(rng, **{p: (v, v) for p, v in ends["max"].items()}))
        except CheckError:
            return None
        return max(hull[0], a[0]), min(hull[1], b[1])

    def none_left():
        return CheckError(f"the implicit law of {ph[len('_root_'):]} has no root in [{lo}, {hi}] here")

    if not params:
        live = prune(live, IMPLICIT_DEPTH)
        if not live:
            raise none_left()
        return live[0][0], live[-1][1]
    # over a BOX: a coarse enclosure first, then the corners; the fine pruning only when the corners
    # cannot be used (MEASURED 2026-10-10: the pump's box enclosure took 13 s at full depth, and the
    # corners made it tight anyway)
    live = prune(live, BOX_COARSE)
    if not live:
        raise none_left()
    t = tighten((live[0][0], live[-1][1]))
    if t is not None:
        return t
    live = prune(live, IMPLICIT_DEPTH - BOX_COARSE)
    if not live:
        raise none_left()
    hull = (live[0][0], live[-1][1])
    return tighten(hull) or hull


def implicit_excludes(law_rhs, rng, zlo, zhi, depth=60, splits=14):
    """True when the checker, with its OWN readings, shows no root of the implicit law in
    [lo, zlo) or (zhi, hi] over rng — i.e. confirms ZTL's range [zlo, zhi] encloses every root,
    without needing its own enclosure to be as tight (2026-10-10: the pump's P3, the checker's
    enclosure was 0.08% wider than ZTL's and an inclusion test called a sound range unconfirmed)."""
    node = ast.parse(law_rhs, mode="eval").body if isinstance(law_rhs, str) else law_rhs
    ph, g = node.args[0].id, node.args[1]
    lo, hi = _ivl(node.args[2], {})[0], _ivl(node.args[3], {})[0]

    def clear(a, b, d):
        if a >= b or _g_excludes(g, ph, rng, a, b, splits):
            return True
        if d >= depth:
            return False
        m = (a + b) / 2
        return clear(a, m, d + 1) and clear(m, b, d + 1)

    # the open ends: a root exactly AT zlo or zhi is inside the range, so the outer pieces stop there
    return clear(lo, zlo, 0) and clear(zhi, hi, 0)


def implicit_root_outside(law_rhs, point, zlo, zhi, grid=512):
    """A root of the implicit law at ONE point, outside [zlo, zhi], PROVED: two grid points with strict
    opposite signs (exact readings at points) and, between them, a defined reading of g (no pole) and no
    branch in g (a branch may jump). Then g is continuous there and changes sign: a root (intermediate value
    theorem). Returns the bracket or None — the witness that turns "could not confirm" into a STAND FAULT."""
    node = ast.parse(law_rhs, mode="eval").body if isinstance(law_rhs, str) else law_rhs
    ph, g = node.args[0].id, node.args[1]
    if any(isinstance(n, ast.Call) and getattr(n.func, "id", "") in ("ifpos", "ifpos_d", "min", "max")
           for n in ast.walk(g)):
        return None
    lo, hi = _ivl(node.args[2], {})[0], _ivl(node.args[3], {})[0]
    env = {k: (v, v) for k, v in point.items()}

    def sign_at(x):
        try:
            r = _ivl(g, dict(env, **{ph: (x, x)}))
        except CheckError:
            return 0
        return 1 if r[0] > 0 else (-1 if r[1] < 0 else 0)
    for a0, b0 in ((lo, zlo), (zhi, hi)):
        if b0 <= a0:
            continue
        xs = [a0 + (b0 - a0) * i / grid for i in range(grid + 1)]
        ss = [sign_at(x) for x in xs]
        for (x1, s1), (x2, s2) in zip(zip(xs, ss), zip(xs[1:], ss[1:])):
            if s1 and s2 and s1 != s2:
                try:
                    _ivl(g, dict(env, **{ph: (x1, x2)}))          # defined between: no pole
                except CheckError:
                    continue
                if (x2 <= zlo or x1 >= zhi):
                    return (x1, x2)
    return None


def bound_definitions(laws, fixed, boxes, unknowns, implicit_ranges=None, lazy=False, couple=()):
    """Outer bounds of every definition: corner ranges of the linear unknowns
    (exact in the monotone class), then interval arithmetic.
    lazy: when every unknown has a definition the bounds need no corners — they are NOT computed (cs is None)
    and the caller asks for them only if it needs them (blind test 5, c03: 4016 corners x 4 implicit roots,
    ~110 s per design, for bounds that did not use them)."""
    names = set(fixed) | set(boxes)
    _, defs = classify(laws, names, list(unknowns))
    prime_implicit(laws, fixed, boxes)
    defined = {n for n, _ in defs}
    cs = None if lazy and set(unknowns) <= defined else corners(laws, fixed, boxes, unknowns, couple)
    rng = {n: (v, v) for n, v in fixed.items()}
    rng.update(boxes)
    for u in unknowns:
        if u not in defined:
            vals = [v[u] for _, v in cs]
            rng[u] = (min(vals), max(vals))
    out = {}
    # implicit ranges the caller had the checker CONFIRM by its own exclusion (implicit_excludes) stand in
    # for its own, looser enclosure
    for name, r in (implicit_ranges or {}).items():
        rng[name] = out[name] = r
    pending = [d for d in defs if d[0] not in (implicit_ranges or {})]
    while pending:
        progress = False
        for item in list(pending):
            name, rhs = item
            try:
                rng[name] = out[name] = _ivl(rhs, rng)
                pending.remove(item); progress = True
            except CheckError:
                pass
        if not progress:
            raise CheckError("definitions could not be bounded")
    return out, cs


# ── a brought certificate, re-checked with this file's own means (gap J9) ──
# ZTL checks the stand's certificate (ZTL/zcertify.py). Here it is checked AGAIN from
# the laws themselves: the checker finds q's expression in the laws, differentiates it
# itself (ast), reads it with its own interval arithmetic and evaluates corners exactly.
# Its interval reading may be looser than ZTL's; a leaf it cannot settle is split
# further (sound: a statement true on every sub-piece is true on the piece), at most
# REFINE_DEPTH times. The checker then confirms or reports that it could not.
REFINE_DEPTH = 8


def _names_of(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def explicit_expression(laws, unknowns, q):
    """q in terms of non-derived quantities: its law `q == rhs`, with every other derived
    quantity that has such a law substituted in. CheckError when one is left."""
    unknowns = set(unknowns)
    rhs_of, src_of = {}, {}
    for law in laws:
        l, r = _eq(law)
        if isinstance(l, ast.Name) and l.id in unknowns and l.id not in _names_of(r):
            if l.id not in rhs_of:
                rhs_of[l.id], src_of[l.id] = r, law
    if q not in rhs_of and q not in _linear_unknowns(laws, unknowns):
        raise CheckError(f"no law of the form {q} == expression")

    class Sub(ast.NodeTransformer):
        def __init__(self, depth):
            self.depth = depth

        def visit_Name(self, node):
            if node.id in rhs_of and node.id in unknowns:
                if self.depth > len(rhs_of):
                    raise CheckError("explicit laws refer to each other in a cycle")
                return Sub(self.depth + 1).visit(ast.parse(ast.unparse(rhs_of[node.id]), mode="eval").body)
            return node

    e = (Sub(1).visit(ast.parse(ast.unparse(rhs_of[q]), mode="eval").body) if q in rhs_of
         else ast.Name(id=q, ctx=ast.Load()))       # a linear unknown of the core: Cramer gives it
    left = _names_of(e) & unknowns
    if left:
        # gap Z6: linear unknowns left — the checker solves the linear laws ITSELF, by
        # Cramer's rule on its own symbolic coefficients (no polynomial arithmetic: the
        # determinants stay as cofactor-expansion trees)
        # the CORE only: laws that are not explicit definitions, with those substituted in
        core = []
        for law in laws:
            l, r = _eq(law)
            if isinstance(l, ast.Name) and src_of.get(l.id) == law:
                continue
            both = ast.Compare(left=Sub(1).visit(copy.deepcopy(l)), ops=[ast.Eq()],
                               comparators=[Sub(1).visit(copy.deepcopy(r))])
            core.append(ast.unparse(both))
        core_unknowns = [u for u in unknowns if u not in rhs_of]
        sol = _cramer(core, core_unknowns, set())

        class Lin(ast.NodeTransformer):
            def visit_Name(self, node):
                return copy.deepcopy(sol[node.id]) if node.id in sol else node

        e = Lin().visit(e)
        left = _names_of(e) & unknowns
        if left:
            raise CheckError(f"{q} still depends on derived {sorted(left)}")
    return e


MAX_CRAMER = 5          # n! cofactor terms: 120 at five unknowns


def _lin_ast(node, unknowns):
    """Expression -> {unknown or 1: coefficient ast}, linear in the unknowns."""
    if isinstance(node, ast.Call):
        if _names_of(node) & set(unknowns):
            raise NonLinear(f"an unknown inside {node.func.id}(...)")
        return {1: node}
    if isinstance(node, ast.Constant):
        return {1: node}
    if isinstance(node, ast.Name):
        return {node.id: _c(1)} if node.id in unknowns else {1: node}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        e = _lin_ast(node.operand, unknowns)
        if isinstance(node.op, ast.UAdd):
            return e
        return {k: ast.UnaryOp(op=ast.USub(), operand=v) for k, v in e.items()}
    if isinstance(node, ast.BinOp):
        a, b = _lin_ast(node.left, unknowns), _lin_ast(node.right, unknowns)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            out = dict(a)
            for k, v in b.items():
                out[k] = ast.BinOp(left=out[k], op=node.op, right=v) if k in out else \
                    (v if isinstance(node.op, ast.Add) else ast.UnaryOp(op=ast.USub(), operand=v))
            return out
        if isinstance(node.op, ast.Mult):
            if set(a) <= {1}:
                return {k: ast.BinOp(left=a[1], op=ast.Mult(), right=v) for k, v in b.items()}
            if set(b) <= {1}:
                return {k: ast.BinOp(left=v, op=ast.Mult(), right=b[1]) for k, v in a.items()}
            raise NonLinear("product of two unknowns")
        if isinstance(node.op, ast.Div):
            if set(b) <= {1}:
                return {k: ast.BinOp(left=v, op=ast.Div(), right=b[1]) for k, v in a.items()}
            raise NonLinear("division by an unknown")
    raise CheckError(f"unsupported expression: {ast.dump(node)[:60]}")


def _linear_unknowns(laws, unknowns):
    """The unknowns no nonlinear definition defines."""
    out = set(unknowns)
    for law in laws:
        l, r = _eq(law)
        try:
            _lin_ast(l, unknowns); _lin_ast(r, unknowns)
        except NonLinear:
            if isinstance(l, ast.Name):
                out.discard(l.id)
    return out


def _det(M):
    """Cofactor expansion along the first row, as an ast (no expansion of products)."""
    n = len(M)
    if n == 1:
        return M[0][0]
    out = None
    for j in range(n):
        minor = [row[:j] + row[j + 1:] for row in M[1:]]
        term = ast.BinOp(left=M[0][j], op=ast.Mult(), right=_det(minor))
        if out is None:
            out = term if j % 2 == 0 else ast.UnaryOp(op=ast.USub(), operand=term)
        else:
            out = ast.BinOp(left=out, op=ast.Add() if j % 2 == 0 else ast.Sub(), right=term)
    return out


def _cramer(laws, unknowns, _defined):
    """{linear unknown: ast} by Cramer's rule over the square linear system."""
    lin_u = sorted(_linear_unknowns(laws, unknowns))
    rows = []
    for law in laws:
        l, r = _eq(law)
        try:
            a, b = _lin_ast(l, set(unknowns)), _lin_ast(r, set(unknowns))
        except NonLinear:
            continue
        if (set(a) | set(b)) - {1} - set(lin_u):
            continue                           # mentions a defined (nonlinear) quantity: not a row
        row = {}
        for k, v in a.items():
            row[k] = v
        for k, v in b.items():
            row[k] = ast.BinOp(left=row[k], op=ast.Sub(), right=v) if k in row else ast.UnaryOp(op=ast.USub(), operand=v)
        rows.append(row)
    n = len(lin_u)
    if n > MAX_CRAMER:
        raise CheckError(f"{n} linear unknowns: Cramer's n! terms too many for the checker")
    if len(rows) != n:
        raise CheckError(f"{len(rows)} linear laws for {n} linear unknowns: not a square system")
    A = [[_fold(row.get(u, _c(0))) for u in lin_u] for row in rows]
    rhs = [_fold(ast.UnaryOp(op=ast.USub(), operand=row.get(1, _c(0)))) for row in rows]
    D = _det(A)
    out = {}
    for i, u in enumerate(lin_u):
        Ai = [r[:i] + [rhs[k]] + r[i + 1:] for k, r in enumerate(A)]
        out[u] = ast.BinOp(left=_det(Ai), op=ast.Div(), right=D)
    return out


def _c(v):
    return ast.Constant(value=v)


def _call(name, *args):
    return ast.Call(func=ast.Name(id=name, ctx=ast.Load()), args=list(args), keywords=[])


def _bin(a, op, b):
    return ast.BinOp(left=a, op=op, right=b)


def _d(node, x):
    """d node / d x, as an ast."""
    if isinstance(node, ast.Call):                         # the checker's OWN chain rules (2026-10-10)
        name, args = node.func.id, node.args
        if name == "implicit":
            raise CheckError("an implicit quantity has no derivative here")
        if name in ("ifpos", "ifpos_d"):
            return _call("ifpos_d", args[0], _d(args[1], x), _d(args[2], x))
        if name in ("min", "max"):
            if x in _names_of(node):
                raise CheckError(f"{name} has no derivative where its arguments cross")
            return _c(0)
        if name == "pow":
            u, v = args
            du, dv = _d(u, x), _d(v, x)
            if x not in _names_of(v):                      # v * u^(v-1) * u'
                return _bin(_bin(v, ast.Mult(), _call("pow", u, _bin(v, ast.Sub(), _c(1)))), ast.Mult(), du)
            return _bin(node, ast.Mult(), _bin(_bin(dv, ast.Mult(), _call("ln", u)), ast.Add(),
                                               _bin(_bin(v, ast.Mult(), du), ast.Div(), u)))
        u = args[0]
        du = _d(u, x)
        if name == "exp":
            return _bin(node, ast.Mult(), du)
        if name == "ln":
            return _bin(du, ast.Div(), u)
        if name == "log10":
            return _bin(du, ast.Div(), _bin(u, ast.Mult(), _call("ln", _c(10))))
        if name == "atan":
            return _bin(du, ast.Div(), _bin(_c(1), ast.Add(), _bin(u, ast.Mult(), u)))
        if name == "tan":
            return _bin(du, ast.Mult(), _bin(_c(1), ast.Add(), _bin(node, ast.Mult(), node)))
        if name == "sin":
            return _bin(du, ast.Mult(), _call("cos", u))
        if name == "cos":
            return _bin(_c(0), ast.Sub(), _bin(du, ast.Mult(), _call("sin", u)))
        if name == "sqrt":
            return _bin(du, ast.Div(), _bin(_c(2), ast.Mult(), node))
        raise CheckError(f"no derivative for {name}")
    if isinstance(node, ast.Constant):
        return _c(0)
    if isinstance(node, ast.Name):
        return _c(1 if node.id == x else 0)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return ast.UnaryOp(op=ast.USub(), operand=_d(node.operand, x))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return _d(node.operand, x)
    if isinstance(node, ast.BinOp):
        a, b = node.left, node.right
        da, db = _d(a, x), _d(b, x)
        if isinstance(node.op, ast.Add):
            return ast.BinOp(left=da, op=ast.Add(), right=db)
        if isinstance(node.op, ast.Sub):
            return ast.BinOp(left=da, op=ast.Sub(), right=db)
        if isinstance(node.op, ast.Mult):
            return ast.BinOp(left=ast.BinOp(left=da, op=ast.Mult(), right=b), op=ast.Add(),
                             right=ast.BinOp(left=a, op=ast.Mult(), right=db))
        if isinstance(node.op, ast.Div):
            top = ast.BinOp(left=ast.BinOp(left=da, op=ast.Mult(), right=b), op=ast.Sub(),
                            right=ast.BinOp(left=a, op=ast.Mult(), right=db))
            return ast.BinOp(left=top, op=ast.Div(), right=ast.BinOp(left=b, op=ast.Mult(), right=b))
    raise CheckError(f"cannot differentiate: {ast.dump(node)[:60]}")


def _fold(node):
    """Constant folding with the zeros and ones a derivative leaves (keeps readings tighter)."""
    if isinstance(node, ast.UnaryOp):
        o = _fold(node.operand)
        if isinstance(o, ast.Constant):
            return _c(-F(str(o.value)) if isinstance(node.op, ast.USub) else F(str(o.value)))
        return ast.UnaryOp(op=node.op, operand=o)
    if not isinstance(node, ast.BinOp):
        return node
    a, b = _fold(node.left), _fold(node.right)
    za = isinstance(a, ast.Constant) and F(str(a.value)) == 0
    zb = isinstance(b, ast.Constant) and F(str(b.value)) == 0
    oa = isinstance(a, ast.Constant) and F(str(a.value)) == 1
    ob = isinstance(b, ast.Constant) and F(str(b.value)) == 1
    if isinstance(node.op, ast.Add):
        if za: return b
        if zb: return a
    if isinstance(node.op, ast.Sub) and zb:
        return a
    if isinstance(node.op, ast.Sub) and ast.dump(a) == ast.dump(b):
        return _c(0)                                # x - x: the reading would not cancel it
    if isinstance(node.op, ast.Mult):
        if za or zb: return _c(0)
        if oa: return b
        if ob: return a
    if isinstance(node.op, ast.Div):
        if za: return _c(0)
        if ob: return a
    if isinstance(a, ast.Constant) and isinstance(b, ast.Constant) and not isinstance(node.op, ast.Div):
        return _c(_val(ast.BinOp(left=a, op=node.op, right=b), {}))
    return ast.BinOp(left=a, op=node.op, right=b)


# ── CASES, re-read with the checker's own means (2026-10-11; ZTL's zcertify reads them affinely) ──
# On a piece, a min / max / ifpos the checker's reading decides is replaced by its branch; up to CASE_BITS undecided
# ones are tried both ways. Each combination is simplified by sympy (not ZTL); when it and its own conditions
# (g <= 0) are LINEAR in the names, its bound over the piece under those conditions is exact weak duality in
# fractions — min over the box of f + sum lam_j g_j, any lam >= 0 sound — and a combination the conditions rule
# out is skipped; otherwise the combination is read plainly over the whole piece (sound, looser). The hull of the
# combinations is met with the plain reading.
CASE_BITS = 6
_SYM = {}


def _sym_of(node):
    import sympy as sp
    key = ast.dump(node)
    hit = _SYM.get(key)
    if hit is None:
        names = _names_of(node)
        loc = {n: sp.Symbol(n) for n in names}
        loc.update({"exp": sp.exp, "ln": sp.log, "log10": lambda u: sp.log(u, 10), "sqrt": sp.sqrt,
                    "pow": sp.Pow, "atan": sp.atan, "tan": sp.tan, "sin": sp.sin, "cos": sp.cos})
        try:
            hit = sp.expand(sp.sympify(ast.unparse(node), locals=loc, rational=True))
        except (sp.SympifyError, TypeError, ValueError):
            hit = False
        if len(_SYM) < 20000:
            _SYM[key] = hit
    return hit


def _sym_to_ast(x):
    """A sympy expression back into the ast the checker reads (+ - * /, pow, its functions)."""
    import sympy as sp
    if isinstance(x, sp.Symbol):
        return ast.Name(id=x.name, ctx=ast.Load())
    if isinstance(x, sp.Rational):
        return ast.Constant(value=F(int(x.p), int(x.q))) if x.q != 1 else ast.Constant(value=int(x.p))
    if isinstance(x, sp.Add):
        out = _sym_to_ast(x.args[0])
        for a in x.args[1:]:
            out = ast.BinOp(left=out, op=ast.Add(), right=_sym_to_ast(a))
        return out
    if isinstance(x, sp.Mul):
        out = _sym_to_ast(x.args[0])
        for a in x.args[1:]:
            out = ast.BinOp(left=out, op=ast.Mult(), right=_sym_to_ast(a))
        return out
    if isinstance(x, sp.Pow):
        b, e = x.args
        if e == -1:
            return ast.BinOp(left=ast.Constant(value=1), op=ast.Div(), right=_sym_to_ast(b))
        if e == sp.Rational(1, 2):
            return ast.Call(func=ast.Name(id="sqrt", ctx=ast.Load()), args=[_sym_to_ast(b)], keywords=[])
        return ast.Call(func=ast.Name(id="pow", ctx=ast.Load()), args=[_sym_to_ast(b), _sym_to_ast(e)], keywords=[])
    fn = {sp.exp: "exp", sp.log: "ln", sp.atan: "atan", sp.tan: "tan", sp.sin: "sin", sp.cos: "cos"}.get(type(x))
    if fn:
        return ast.Call(func=ast.Name(id=fn, ctx=ast.Load()), args=[_sym_to_ast(x.args[0])], keywords=[])
    raise CheckError(f"no reading for {x}")


def _linear_coefs(expr, rng):
    """expr as c + sum k_a * a over ATOMS a — a name, or a nonlinear monomial read as one quantity (I1/u, x*y):
    ({atom key: k}, c, {atom key: its range}); None when a coefficient is not rational. The same monomial in two
    expressions is the same atom — so B - I1/u and I1/u - B cancel exactly under weak duality."""
    import sympy as sp
    if expr is False:
        return None
    coefs, c, ranges = {}, F(0), {}
    for mono, k in expr.as_coefficients_dict().items():
        if not k.is_Rational:
            return None
        kf = F(int(k.p), int(k.q))
        if mono == 1:
            c += kf
            continue
        key = sp.srepr(mono)
        if isinstance(mono, sp.Symbol):
            if mono.name not in rng:
                return None
            ranges[key] = rng[mono.name]
        else:
            try:
                ranges[key] = _ivl(_sym_to_ast(mono), rng)
            except (CheckError, ZeroDivisionError):
                return None
        coefs[key] = coefs.get(key, F(0)) + kf
    return coefs, c, ranges


def _dual_bound(f, gs, rng):
    """min over the box rng of the linear f where every linear g in gs is <= 0 — (bound, impossible). For any
    lam >= 0, min over the box of f + sum lam_j g_j is a lower bound (and > 0 with f = 0 proves the conditions
    cannot hold together); lam sought coordinate by coordinate among the breakpoints."""
    names = set(f[0])
    for g in gs:
        names |= set(g[0])
    names = sorted(names)

    def low(lam, with_f):
        c = f[1] if with_f else F(0)
        tot = 0
        for nm in names:
            k = (f[0].get(nm, F(0)) if with_f else F(0)) + sum((l * g[0].get(nm, F(0)) for l, g in zip(lam, gs)), F(0))
            lo_, hi_ = rng[nm]
            tot += min(k * lo_, k * hi_)
        return c + sum((l * g[1] for l, g in zip(lam, gs)), F(0)) + tot

    def ascend(with_f):
        lam = [F(0)] * len(gs)
        best = low(lam, with_f)
        for _ in range(3):
            for j, g in enumerate(gs):
                cands = {F(0), F(1)}
                for nm in names:
                    b = g[0].get(nm, F(0))
                    if b:
                        a = (f[0].get(nm, F(0)) if with_f else F(0)) + \
                            sum((l * h[0].get(nm, F(0)) for i, (l, h) in enumerate(zip(lam, gs)) if i != j), F(0))
                        if -a / b > 0:
                            cands.add(-a / b)
                for x in cands:
                    trial = lam[:j] + [x] + lam[j + 1:]
                    v = low(trial, with_f)
                    if v > best:
                        best, lam = v, trial
        return best
    if gs and ascend(False) > 0:
        return None, True
    return ascend(True), False


CASE_LEAVES = 256


class _TooManyCases(Exception):
    pass


def _branches_of(n):
    out, seen = [], set()
    for x in ast.walk(n):
        if isinstance(x, ast.Call) and getattr(x.func, "id", "") in ("min", "max", "ifpos"):
            k = ast.dump(x)
            if k not in seen:               # one choice per STRUCTURE (the same subtree, the same value)
                seen.add(k)
                out.append(x)
    return out


def _cond_of(n):
    if n.func.id == "ifpos":
        return n.args[0]
    return ast.BinOp(left=n.args[0], op=ast.Sub(), right=n.args[1])


def _neg(x):
    return ast.BinOp(left=ast.Constant(value=0), op=ast.Sub(), right=x)


def _side(n, rng):
    try:
        lo_, hi_ = _ivl(_cond_of(n), rng)
    except CheckError:
        return 0
    if n.func.id == "ifpos":
        return 1 if lo_ > 0 else (-1 if hi_ <= 0 else 0)
    if n.func.id == "min":
        return 1 if hi_ <= 0 else (-1 if lo_ >= 0 else 0)
    return 1 if lo_ >= 0 else (-1 if hi_ <= 0 else 0)


def _g_of(n, side):
    """The condition under which `side` of branch n is taken, as g <= 0 (closed)."""
    c = _cond_of(n)
    if n.func.id == "ifpos":
        return _neg(c) if side == 1 else c
    if n.func.id == "min":
        return c if side == 1 else _neg(c)
    return _neg(c) if side == 1 else c


def _resolve_ast(n, sd):
    if isinstance(n, ast.Call) and getattr(n.func, "id", "") in ("min", "max", "ifpos") and ast.dump(n) in sd:
        k = ast.dump(n)
        pick = (n.args[1] if sd[k] == 1 else n.args[2]) if n.func.id == "ifpos" else \
            (n.args[0] if sd[k] == 1 else n.args[1])
        return _resolve_ast(pick, sd)
    if isinstance(n, ast.BinOp):
        return ast.BinOp(left=_resolve_ast(n.left, sd), op=n.op, right=_resolve_ast(n.right, sd))
    if isinstance(n, ast.UnaryOp):
        return ast.UnaryOp(op=n.op, operand=_resolve_ast(n.operand, sd))
    if isinstance(n, ast.Call):
        return ast.Call(func=n.func, args=[_resolve_ast(a, sd) for a in n.args], keywords=[])
    return n


def _ivl_cases(e, rng):
    _stop_check()                   # a stop asked from outside (blind test 5: c09 literal ran past its limit here)
    base = _ivl(e, rng)
    if isinstance(e, ast.Call) and getattr(e.func, "id", "") in ("min", "max"):
        # an OUTER min / max: the min / max of its arguments' bounds, each read by cases on its own
        ra, rb = _ivl_cases(e.args[0], rng), _ivl_cases(e.args[1], rng)
        r = (min(ra[0], rb[0]), min(ra[1], rb[1])) if e.func.id == "min" else (max(ra[0], rb[0]), max(ra[1], rb[1]))
        lo, hi = max(r[0], base[0]), min(r[1], base[1])
        return (lo, hi) if lo <= hi else base
    if not _branches_of(e):
        return base
    leaves = []

    def settle(f, gs):
        while True:
            sd = {}
            for n in _branches_of(f):
                s_ = _side(n, rng)
                if s_:
                    sd[ast.dump(n)] = s_
            if not sd:
                return f, gs
            f = _resolve_ast(f, sd)
            gs = [_resolve_ast(g, sd) for g in gs]

    def go(f, gs):
        # a TREE of choices, as ZTL's zcertify does it (here with this file's own reading and sympy)
        f, gs = settle(f, gs)
        open_ = _branches_of(f)
        if not open_:
            leaves.append((f, gs))
            if len(leaves) > CASE_LEAVES:
                raise _TooManyCases()
            return
        n = min(open_, key=lambda x: len(ast.dump(x)))
        for side in (1, -1):
            sub = {ast.dump(n): side}
            go(_resolve_ast(f, sub), [_resolve_ast(g, sub) for g in gs] + [_resolve_ast(_g_of(n, side), sub)])
    try:
        go(e, [])
    except _TooManyCases:
        return base
    lo = hi = None
    for fe, gs in leaves:
        try:
            r = list(_ivl(fe, rng))
        except CheckError:
            return base
        sym = _sym_of(fe)
        if sym is not False:
            # the SIMPLIFIED form read as well (N - B - (N - B) is 0 there), met with the plain one: both enclose
            try:
                r2 = _ivl(_sym_to_ast(sym), rng)
                r = [max(r[0], r2[0]), min(r[1], r2[1])]
            except (CheckError, ZeroDivisionError):
                pass
        fl = _linear_coefs(sym, rng)
        gl = [_linear_coefs(_sym_of(g), rng) for g in gs]
        if fl is not None and all(g is not None for g in gl):
            arng = dict(fl[2])
            for g in gl:
                arng.update(g[2])
            fl2, gl2 = (fl[0], fl[1]), [(g[0], g[1]) for g in gl]
            low_, impossible = _dual_bound(fl2, gl2, arng)
            if impossible:
                continue
            up_, _ = _dual_bound(({k: -v for k, v in fl2[0].items()}, -fl2[1]), gl2, arng)
            r = [max(r[0], low_), min(r[1], -up_)]
        if r[0] > r[1]:
            continue
        lo = r[0] if lo is None else min(lo, r[0])
        hi = r[1] if hi is None else max(hi, r[1])
    if lo is None:
        return base
    lo, hi = max(lo, base[0]), min(hi, base[1])
    return (lo, hi) if lo <= hi else base


def check_certificate(laws, fixed, boxes, unknowns, q, op, bound, cert, implicit=None):
    """(True, leaves) when the certificate shows `q op bound` over the box, by this file's
    own reading; (False, reason) otherwise. Never consults the judge.

    implicit = {U: g (ast)}: U is the root of g == 0 in its box (J6, 2026-10-11) — the leaves'
    brackets "roots" / "corner_roots" re-checked here with this file's own derivative and reading:
    dg/dU one strict sign over the piece × U's box, g on the two sides of 0 at the bracket's ends;
    a monotone leaf's derivative is the total one, dE/dx + dE/dU * (-g_x / g_U)."""
    if op not in ("<=", ">="):
        return False, f"op {op!r}"
    implicit = implicit or {}
    try:
        e = explicit_expression(laws, unknowns, q)
    except CheckError as err:
        return False, str(err)
    used = _names_of(e)
    for g in implicit.values():
        used = used | _names_of(g)
    names = sorted((used & set(boxes)) - set(implicit))     # before folding: the searcher splits on these
    e = _fold(e)
    derivs = {}

    def total_d(n):
        d = _d(e, n)
        for u, g in implicit.items():
            gn = _fold(_d(g, n))
            if isinstance(gn, ast.Constant) and F(str(gn.value)) == 0:
                continue
            d = _bin(d, ast.Add(), _bin(_d(e, u), ast.Mult(),
                                        _bin(ast.UnaryOp(op=ast.USub(), operand=gn), ast.Div(), _d(g, u))))
        return _fold(d)

    def brackets(given, piece):
        """{U: (a, b)} checked over the piece (a point for a corner); U's whole box where none is given.
        CheckError when a given bracket does not check."""
        out = {}
        for u, g in implicit.items():
            rlo, rhi = boxes[u]
            if not given or u not in given:
                out[u] = (rlo, rhi)
                continue
            a, b = (F(str(x)) for x in given[u])
            if not (rlo <= a <= b <= rhi):
                raise CheckError(f"the bracket of {u} leaves its box")
            base = {n: (v, v) for n, v in fixed.items()}
            base.update(piece)
            dlo, dhi = _ivl(_fold(_d(g, u)), dict(base, **{u: (rlo, rhi)}))
            if dlo <= 0 <= dhi:
                raise CheckError(f"d/d{u} of its law keeps no strict sign")
            ga = _ivl(g, dict(base, **{u: (a, a)}))
            gb = _ivl(g, dict(base, **{u: (b, b)}))
            if not ((ga[1] <= 0 <= gb[0]) if dlo > 0 else (ga[0] >= 0 >= gb[1])):
                raise CheckError(f"the law of {u} does not change sign across its bracket")
            out[u] = (a, b)
        return out
    good = (lambda v: v <= bound) if op == "<=" else (lambda v: v >= bound)
    count = [0]

    def _corner_good(corner):
        """The value at the corner: exact, or — with a function in it — the checker's own interval,
        whose worse end must satisfy the bound."""
        try:
            return good(_val(e, dict(fixed, **corner)))
        except NeedsInterval:
            env = {k: (v, v) for k, v in dict(fixed, **corner).items()}
            lo, hi = _ivl(e, env)
            return good(hi if op == "<=" else lo)

    def rng_of(piece):
        r = {n: (v, v) for n, v in fixed.items()}
        r.update(boxes)
        r.update(piece)
        return r

    leaf_roots = [None]         # the bracket of the leaf being re-checked (valid on every part of its piece)

    def own_bracket(pt):
        """The checker's OWN bracket of every implicit root at a point (a corner of a part it cut itself,
        where the certificate brings none): bisection with its own reading, from the leaf's bracket."""
        out = {}
        base = {n: (v, v) for n, v in fixed.items()}
        base.update(pt)
        for u, g in implicit.items():
            lo, hi = (F(str(x)) for x in (leaf_roots[0] or {}).get(u, boxes[u]))
            sg = _ivl(_fold(_d(g, u)), dict(base, **{u: boxes[u]}))
            if sg[0] <= 0 <= sg[1]:
                raise CheckError(f"d/d{u} of its law keeps no strict sign")
            up = sg[0] > 0

            def side(v):
                r = _ivl(g, dict(base, **{u: (v, v)}))
                return (-1 if r[1] <= 0 else 1 if r[0] >= 0 else 0) * (1 if up else -1)
            if side(lo) != -1 or side(hi) != 1:
                raise CheckError(f"no sign change of {u}'s law across the leaf's bracket at the corner")
            a, b = lo, hi
            for _ in range(36):
                m = (a + b) / 2
                k = F(int(m * 2 ** 40), 2 ** 40)
                m = k if a < k < b else m
                sm = side(m)
                if sm == 0:
                    break
                a, b = (m, b) if sm == -1 else (a, m)
            out[u] = (a, b)
        return out

    def corner_with_roots(corner):
        """A monotone corner's value with implicit quantities: their brackets at the corner (the certificate's,
        re-checked, or the checker's own), read."""
        pt = {n: (v, v) for n, v in corner.items()}
        try:
            br = brackets(cur_corner_roots[0], pt)
            if any(br[u] == boxes[u] for u in implicit if boxes[u][0] < boxes[u][1]):
                raise CheckError("no bracket at the corner")
        except CheckError:
            br = own_bracket(pt)
        lo, hi = _ivl(e, rng_of(dict(pt, **br)))
        return good(hi if op == "<=" else lo)

    cur_corner_roots = [None]

    def leaf_holds(kind, signs, piece, depth):
        # the leaf's kind is the searcher's hint; the checker's reading is cruder than ZTL's
        # (it does not cancel p0 - p0), so on a piece it also tries the other kind — either,
        # when it holds, shows the statement on that piece
        if one_leaf("interval" if kind == "monotone" else "monotone", signs, piece):
            return True
        return _leaf(kind, signs, piece, depth)

    def one_leaf(kind, signs, piece):
        try:
            if implicit:
                piece = dict(piece, **brackets(leaf_roots[0], piece))
            if kind == "interval":
                lo, hi = _ivl_cases(e, rng_of(piece))
                return good(hi if op == "<=" else lo)
            if implicit and not leaf_roots[0]:
                return False
            corner = {}
            for n in names:
                lo, hi = piece[n]
                if lo == hi:
                    corner[n] = lo
                    continue
                s = signs.get(n)
                if s not in ("+", "-"):
                    return False
                if n not in derivs:
                    derivs[n] = total_d(n)
                dlo, dhi = _ivl(derivs[n], rng_of(piece))
                if (s == "+" and dlo < 0) or (s == "-" and dhi > 0):
                    return False
                corner[n] = hi if (s == "+") == (op == "<=") else lo
            return corner_with_roots(corner) if implicit else _corner_good(corner)
        except CheckError:
            return False

    def _leaf(kind, signs, piece, depth):
        try:
            if implicit:
                piece = dict(piece, **brackets(leaf_roots[0], piece))
            if kind == "interval":
                lo, hi = _ivl_cases(e, rng_of(piece))
                if good(hi if op == "<=" else lo):
                    return True
            elif kind == "monotone":
                if implicit and not leaf_roots[0]:
                    raise CheckError("a monotone leaf with an implicit quantity and no bracket")
                corner = {}
                for n in names:
                    lo, hi = piece[n]
                    if lo == hi:
                        corner[n] = lo
                        continue
                    s = signs.get(n)
                    if s not in ("+", "-"):
                        return False
                    if n not in derivs:
                        derivs[n] = total_d(n)
                    dlo, dhi = _ivl(derivs[n], rng_of(piece))
                    if (s == "+" and dlo < 0) or (s == "-" and dhi > 0):
                        raise CheckError("sign not shown here")
                    corner[n] = hi if (s == "+") == (op == "<=") else lo
                # a part's corner other than the leaf's has no bracket: CheckError, the part is not shown
                return corner_with_roots(corner) if implicit else _corner_good(corner)
        except CheckError:
            pass
        if depth == 0:
            return False
        n = max(names, key=lambda k: (piece[k][1] - piece[k][0]) / ((boxes[k][1] - boxes[k][0]) or 1))
        lo, hi = piece[n]
        if lo == hi:
            return False
        m = (lo + hi) / 2
        return (leaf_holds(kind, signs, dict(piece, **{n: (lo, m)}), depth - 1) and
                leaf_holds(kind, signs, dict(piece, **{n: (m, hi)}), depth - 1))

    def walk(node, piece):
        _stop_check()               # a stop asked from outside (a 900 s limit unheard in a long re-check, 2026-10-11)
        if not isinstance(node, dict):
            return False, "not a tree node"
        if "split" in node:
            n = node["split"]
            if n not in piece:
                return False, f"split on {n!r}, not a quantity of {q}"
            at = F(str(node["at"]))
            lo, hi = piece[n]
            if not (lo < at < hi):
                return False, f"split {n} at {at} outside [{lo}, {hi}]"
            ok, why = walk(node.get("lo"), dict(piece, **{n: (lo, at)}))
            return (ok, why) if not ok else walk(node.get("hi"), dict(piece, **{n: (at, hi)}))
        count[0] += 1
        kind = node.get("leaf")
        if kind not in ("interval", "monotone"):
            return False, f"unknown leaf {kind!r}"
        leaf_roots[0], cur_corner_roots[0] = node.get("roots"), node.get("corner_roots")
        if leaf_holds(kind, node.get("signs") or {}, piece, REFINE_DEPTH):
            return True, None
        return False, f"a {kind} leaf at {piece} is not shown by the checker"

    ok, why = walk(cert, {n: boxes[n] for n in names})
    return (True, count[0]) if ok else (False, why)


# ── LARGE LINEAR SYSTEMS, re-checked with the checker's own means (2026-10-15) ──
# ZTL's zlin.py checks a certificate for x_k <= U over a box (A(p) x = b(p) of any size). Here the SAME certificate is
# checked again, sharing no code with zlin: the system from the checker's own linear reading (_lin_ast), coefficients
# by its own interval arithmetic (_ivl), derivatives by its own rules (_d), Python fractions rounded outward to the
# certificate's grid (zlin works in integers), its own float candidates and its own exact solve at a point
# (solve_at). The rules are the same theorems: the verified enclosure (beta = |I - R[A]| < 1), the parametric form,
# a verified u >= |z| + |C| u, one verified y for the signs, pins at the favourable end, an exact leaf at a point.

def _lin_system(laws, unknowns):
    rows = []
    for law in laws:
        l, r = _eq(law)
        a, b = _lin_ast(l, unknowns), _lin_ast(r, unknowns)
        row = dict(a)
        for k, v in b.items():
            row[k] = ast.BinOp(left=row[k], op=ast.Sub(), right=v) if k in row else ast.UnaryOp(op=ast.USub(), operand=v)
        rows.append(row)
    if len(rows) != len(unknowns):
        raise CheckError("not a square linear system")
    A = [[row.get(u) for u in unknowns] for row in rows]
    b = [ast.UnaryOp(op=ast.USub(), operand=row[1]) if 1 in row else None for row in rows]
    return A, b


def _lc_out(iv, g):
    lo, hi = iv
    return (F(math.floor(lo * g), g), F(math.ceil(hi * g), g))


def _lc_fsolve(M, rhs):
    n = len(M)
    a = [list(map(float, row)) + [float(rhs[i])] for i, row in enumerate(M)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c]))
        if a[p][c] == 0:
            return None
        a[c], a[p] = a[p], a[c]
        for r in range(c + 1, n):
            f = a[r][c] / a[c][c]
            for j in range(c, n + 1):
                a[r][j] -= f * a[c][j]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (a[i][n] - sum(a[i][j] * x[j] for j in range(i + 1, n))) / a[i][i]
    return x


def _lc_vec(zm, Cm, transpose, g):
    """A verified u >= zm + |C| u (or the transposed), or None (then the caller uses the norm bound)."""
    n = len(zm)
    M = [[(1.0 if i == j else 0.0) - float(Cm[j][i] if transpose else Cm[i][j]) for j in range(n)] for i in range(n)]
    cand = _lc_fsolve(M, [float(v) for v in zm])
    if cand is None or any(v != v or v < 0 for v in cand):
        return None
    for infl in (1e-9, 1e-6, 1e-3):
        u = [F(math.ceil(v * (1 + infl) * g) + 1, g) for v in cand]
        if all(u[i] >= zm[i] + sum((Cm[m][i] if transpose else Cm[i][m]) * u[m] for m in range(n)) for i in range(n)):
            return u
    return None


# step 6 (one layer), with the checker's own means: its own degree bound on the ast, its own exact value (_val) on the
# grid (the combinatorial Nullstellensatz), its own derivatives (_d)

def _ast_deg(node, x):
    if isinstance(node, ast.Constant):
        return (0, 0)
    if isinstance(node, ast.Name):
        return (1, 0) if node.id == x else (0, 0)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _ast_deg(node.operand, x)
    if isinstance(node, ast.BinOp):
        a, c = _ast_deg(node.left, x), _ast_deg(node.right, x)
        if a is None or c is None:
            return None
        if isinstance(node.op, (ast.Add, ast.Sub)):
            return (max(a[0] + c[1], c[0] + a[1]), a[1] + c[1])
        if isinstance(node.op, ast.Mult):
            return (a[0] + c[0], a[1] + c[1])
        if isinstance(node.op, ast.Div):
            return (a[0] + c[1], a[1] + c[0])
    return None


def _ast_is_zero(node, limit=4096):
    names = sorted(_names_of(node))
    degs = {}
    for x in names:
        d = _ast_deg(node, x)
        if d is None:
            return False
        degs[x] = d[0]
    size = 1
    for x in names:
        size *= degs[x] + 1
    if size > limit:
        return False
    pts = {x: [F(11 + 13 * i, 7) for i in range(degs[x] + 1)] for x in names}
    for combo in itertools.product(*[pts[x] for x in names]):
        v = None
        for shift in range(9):
            env = {x: c + F(shift, 101) * (1 + names.index(x)) for x, c in zip(names, combo)}
            try:
                v = _val(node, env)
                break
            except (CheckError, ZeroDivisionError):
                continue
        if v is None or v != 0:
            return False
    return True


def _lc_structure(A, b, x, centre):
    """The checker's own proof that x enters by one layer: {"g", "u", "v", "kappa"} / {"g": None, "h", "u"} / None."""
    n = len(A)
    sub = lambda p_, q_: ast.BinOp(left=p_, op=ast.Sub(), right=q_)
    mul = lambda c, e: ast.BinOp(left=_c(c), op=ast.Mult(), right=e)
    try:
        # folded: a derivative carries 0*G0 - 1*0 terms that only inflate the degree bounds (the grid)
        dA = {(i, j): _fold(_d(A[i][j], x)) for i in range(n) for j in range(n)
              if A[i][j] is not None and x in _names_of(A[i][j])}
        db = {i: _fold(_d(b[i], x)) for i in range(n) if b[i] is not None and x in _names_of(b[i])}
    except CheckError:
        return None
    val = lambda e: _val(e, centre)
    try:
        dA = {kk: e for kk, e in dA.items() if not _ast_is_zero(e)}
        db = {kk: e for kk, e in db.items() if not _ast_is_zero(e)}
        if not dA:
            if not db:
                return None
            i0 = min(db)
            h = db[i0]
            hv = val(h)
            if hv == 0:
                return None
            u = {i: val(e) / hv for i, e in db.items()}
            if not all(_ast_is_zero(sub(e, mul(u[i], h))) for i, e in db.items()):
                return None
            return {"g": None, "h": h, "u": {i: c for i, c in u.items() if c}}
        a0, c0 = min(dA)
        g = dA[(a0, c0)]
        gv = val(g)
        if gv == 0:
            return None
        rows = sorted({i for i, _ in dA} | set(db))
        cols = sorted({j for _, j in dA})
        u = {i: (val(dA[(i, c0)]) / gv if (i, c0) in dA else F(0)) for i in rows}
        v = {j: (val(dA[(a0, j)]) / gv if (a0, j) in dA else F(0)) for j in cols}
        for i in rows:
            for j in cols:
                e = dA.get((i, j))
                if e is None:
                    if u[i] * v[j] != 0:
                        return None
                elif not _ast_is_zero(sub(e, mul(u[i] * v[j], g))):
                    return None
        kappa = F(0)
        if db:
            i0 = next((i for i in rows if u[i] and i in db), None)
            if i0 is None:
                return None
            kappa = ast.BinOp(left=db[i0], op=ast.Div(), right=mul(u[i0], g))
            if not _ast_is_zero(_fold(_d(kappa, x))):
                return None
            for i in rows:
                e = db.get(i)
                if e is None:
                    if u[i] != 0:
                        return None
                elif not _ast_is_zero(sub(mul(u[i0], e), mul(u[i], db[i0]))):
                    return None
        return {"g": g, "u": {i: c for i, c in u.items() if c}, "v": {j: c for j, c in v.items() if c}, "kappa": kappa}
    except (CheckError, ZeroDivisionError, NeedsInterval):
        return None


def check_linear_certificate(laws, fixed, boxes, unknowns, q, op, bound, cert):
    """(True, pieces) or (False, why): zlin's certificate for `q op bound`, checked independently."""
    if op not in ("<=", ">="):
        return False, "only <= and >="
    unknowns = list(unknowns)
    try:
        A, b = _lin_system(laws, unknowns)
    except (NonLinear, CheckError) as e:
        return False, f"the checker's reading: {e}"
    n, k = len(unknowns), unknowns.index(q)
    names = sorted({x for row in A for e in row if e is not None for x in _names_of(e)}
                   | {x for e in b if e is not None for x in _names_of(e)})
    bits, tree = (cert.get("grid", 64), cert["tree"]) if isinstance(cert, dict) and "tree" in cert else (64, cert)
    if not isinstance(bits, int) or not 64 <= bits <= 1024:
        return False, "grid out of range"
    g = 1 << bits
    base = {x: (v, v) for x, v in fixed.items()}
    zero = (F(0), F(0))
    rd = lambda e, rng: zero if e is None else _lc_out(_ivl(e, rng), g)
    dnode = {}

    def dread(e, x, rng):
        if e is None or x not in _names_of(e):
            return zero
        key = (id(e), x)
        if key not in dnode:
            dnode[key] = _d(e, x)
        return _lc_out(_ivl(dnode[key], rng), g)

    imul = lambda a, c: (min(a[0] * c[0], a[0] * c[1], a[1] * c[0], a[1] * c[1]),
                         max(a[0] * c[0], a[0] * c[1], a[1] * c[0], a[1] * c[1]))
    smul = lambda s, a: (s * a[0], s * a[1]) if s >= 0 else (s * a[1], s * a[0])
    mag = lambda a: max(abs(a[0]), abs(a[1]))

    def derivs(piece, rng, AA=None, bb=None):
        """{x: ({(m, j): iv}, {m: iv})} over the piece — each derivative read once."""
        AA, bb = (A if AA is None else AA), (b if bb is None else bb)
        out = {}
        for x, (lo, hi) in piece.items():
            if lo == hi:
                continue
            dA = {(m, j): dread(AA[m][j], x, rng) for m in range(n) for j in range(n)
                  if AA[m][j] is not None and x in _names_of(AA[m][j])}
            db = {m: dread(bb[m], x, rng) for m in range(n) if bb[m] is not None and x in _names_of(bb[m])}
            out[x] = ({kk: v for kk, v in dA.items() if v != zero}, {kk: v for kk, v in db.items() if v != zero})
        return out

    def rmul(R, vec):
        """R vec for a sparse interval vector {m: iv}."""
        return [(sum(min(smul(R[i][m], t)) for m, t in vec.items()), sum(max(smul(R[i][m], t)) for m, t in vec.items()))
                for i in range(n)]

    def enclosure(piece, R, xt, AA=None, bb=None):
        AA, bb = (A if AA is None else AA), (b if bb is None else bb)
        rng = dict(base, **piece)
        Ai = [[rd(e, rng) for e in row] for row in AA]
        bi = [rd(e, rng) for e in bb]
        mid = dict(base, **{x: ((lo + hi) / 2, (lo + hi) / 2) for x, (lo, hi) in piece.items()})
        A0 = [[rd(e, mid) for e in row] for row in AA]
        b0 = [rd(e, mid) for e in bb]
        D = derivs(piece, rng, AA, bb)
        w = {x: (hi - lo) / 2 for x, (lo, hi) in piece.items() if lo != hi}
        radC = [[F(0)] * n for _ in range(n)]
        radz = [F(0)] * n
        for x, (dA, db) in D.items():
            cols = {}
            for (m, j), iv in dA.items():
                cols.setdefault(j, {})[m] = iv
            for j, vec in cols.items():
                for i, t in enumerate(rmul(R, vec)):
                    radC[i][j] += w[x] * mag(t)
            v = dict(db)
            for (m, j), iv in dA.items():
                if xt[j]:
                    t = smul(xt[j], iv)
                    o = v.get(m, zero)
                    v[m] = (o[0] - t[1], o[1] - t[0])
            for i, t in enumerate(rmul(R, v)):
                radz[i] += w[x] * mag(t)
        C = []
        for i in range(n):
            row = []
            for j in range(n):
                acc = (sum(min(smul(R[i][m], Ai[m][j])) for m in range(n) if Ai[m][j] != zero),
                       sum(max(smul(R[i][m], Ai[m][j])) for m in range(n) if Ai[m][j] != zero))
                acc0 = (sum(min(smul(R[i][m], A0[m][j])) for m in range(n) if A0[m][j] != zero),
                        sum(max(smul(R[i][m], A0[m][j])) for m in range(n) if A0[m][j] != zero))
                one = F(1) if i == j else F(0)
                c1 = (one - acc[1], one - acc[0])
                c2 = (one - acc0[1] - radC[i][j], one - acc0[0] + radC[i][j])
                row.append(_lc_out((max(c1[0], c2[0]), min(c1[1], c2[1])), g))
            C.append(row)
        Cm = [[mag(c) for c in row] for row in C]
        beta = max(sum(row) for row in Cm)
        if beta >= 1:
            raise CheckError(f"beta {float(beta):.4g} >= 1")
        res = {m: (bi[m][0] - sum(max(smul(xt[j], Ai[m][j])) for j in range(n)),
                   bi[m][1] - sum(min(smul(xt[j], Ai[m][j])) for j in range(n))) for m in range(n)}
        res0 = {m: (b0[m][0] - sum(max(smul(xt[j], A0[m][j])) for j in range(n)),
                    b0[m][1] - sum(min(smul(xt[j], A0[m][j])) for j in range(n))) for m in range(n)}
        z1, z0 = rmul(R, res), rmul(R, res0)
        z = [_lc_out((max(z1[i][0], z0[i][0] - radz[i]), min(z1[i][1], z0[i][1] + radz[i])), g) for i in range(n)]
        return rng, C, Cm, beta, z, D

    def ebox(z, Cm, beta):
        zm = [mag(v) for v in z]
        delta = max(zm) / (1 - beta)
        E = [(-zm[i] - sum(Cm[i]) * delta, zm[i] + sum(Cm[i]) * delta) for i in range(n)]
        u = _lc_vec(zm, Cm, False, g)
        if u is not None:
            E = [(max(E[i][0], z[i][0] - sum(Cm[i][j] * u[j] for j in range(n))),
                  min(E[i][1], z[i][1] + sum(Cm[i][j] * u[j] for j in range(n)))) for i in range(n)]
        return E

    pieces = [0]
    centre = dict(fixed, **{x: (lo + hi) / 2 for x, (lo, hi) in boxes.items()})
    sts = {}

    def struct(x):
        if x not in sts:
            sts[x] = _lc_structure(A, b, x, centre)
        return sts[x]

    AT = [list(col) for col in zip(*A)]

    def lead_sign(st, piece):
        iv = _ivl(st["g"] if st["g"] is not None else st["h"], dict(base, **piece))
        return 1 if iv[0] > 0 else (-1 if iv[1] < 0 else 0)

    def solve_const(piece, R, AA, rhs, comp=None):
        """The enclosure of A y = rhs (constant) over the piece — y_comp, or every component."""
        bb = [_c(rhs[i]) if rhs.get(i) else None for i in range(n)]
        yt = [F(math.floor((sum((R[i][m] * c for m, c in rhs.items()), F(0))) * g + F(1, 2)), g) for i in range(n)]
        _rng, _C, Cm_, beta_, z_, _D = enclosure(piece, R, yt, AA, bb)
        E_ = ebox(z_, Cm_, beta_)
        Y = [(yt[i] + E_[i][0], yt[i] + E_[i][1]) for i in range(n)]
        return Y if comp is None else Y[comp]

    def factor_sign(x, piece, R):
        st = struct(x)
        if st is None:
            return None
        ls = lead_sign(st, piece)
        if not ls:
            return None
        Y = solve_const(piece, R, A, st["u"], k)
        if not (Y[0] > 0 or Y[1] < 0):
            return None
        sg = ls * (1 if Y[0] > 0 else -1)
        if st["g"] is None:
            return "+" if sg > 0 else "-"
        RT = [list(col) for col in zip(*R)]
        Mu = solve_const(piece, RT, AT, st["v"])
        rng = dict(base, **piece)
        ka = st["kappa"]
        kap = (ka, ka) if isinstance(ka, F) else _ivl(ka, rng)
        s_lo, s_hi = -kap[1], -kap[0]
        for i in range(n):
            if b[i] is not None:
                bi_ = _ivl(b[i], rng)
                ps = (Mu[i][0] * bi_[0], Mu[i][0] * bi_[1], Mu[i][1] * bi_[0], Mu[i][1] * bi_[1])
                s_lo += min(ps)
                s_hi += max(ps)
        if not (s_lo > 0 or s_hi < 0):
            return None
        sg = -sg * (1 if s_lo > 0 else -1)
        return "+" if sg > 0 else "-"

    def walk(node, piece, depth):
        if depth > 400 or not isinstance(node, dict):
            return "a malformed tree"
        if "vertex" in node:
            x = node["vertex"]
            if x not in piece or piece[x][0] == piece[x][1]:
                return f"vertex on {x!r}: not a wide quantity of the piece"
            st = struct(x)
            if st is None or not lead_sign(st, piece):
                return f"vertex on {x!r}: the checker could not prove it enters by one layer, monotone"
            try:
                R = [[F(math.floor(F(v) * g + F(1, 2)), g) for v in row] for row in node["R"]]
                xt = [F(math.floor(F(v) * g + F(1, 2)), g) for v in node["x"]]
                enclosure(piece, R, xt)                  # beta < 1: nonsingular over the piece
            except (CheckError, KeyError, TypeError, ValueError, ZeroDivisionError) as e:
                return f"vertex on {x!r}: {e}"
            lo, hi = piece[x]
            return walk(node["lo"], dict(piece, **{x: (lo, lo)}), depth + 1) or \
                walk(node["hi"], dict(piece, **{x: (hi, hi)}), depth + 1)
        if "split" in node:
            x, at = node["split"], F(node["at"])
            if x not in piece or not piece[x][0] < at < piece[x][1]:
                return f"split {x} at {at} is not inside its piece"
            return walk(node["lo"], dict(piece, **{x: (piece[x][0], at)}), depth + 1) or \
                walk(node["hi"], dict(piece, **{x: (at, piece[x][1])}), depth + 1)
        kind = node.get("leaf")
        if kind == "exact":
            if any(lo != hi for lo, hi in piece.values()):
                return "an exact leaf on a piece that is not a point"
            v = solve_at(laws, dict(fixed, **{x: lo for x, (lo, _h) in piece.items()}), unknowns)[q]
            if op == "<=" and v > bound or op == ">=" and v < bound:
                return f"{q} = {v} at the point"
            pieces[0] += 1
            return None
        try:
            R = [[F(math.floor(F(v) * g + F(1, 2)), g) for v in row] for row in node["R"]]
            xt = [F(math.floor(F(v) * g + F(1, 2)), g) for v in node["x"]]
            rng, C, Cm, beta, z, D = enclosure(piece, R, xt)
            E = ebox(z, Cm, beta)
            X = [(xt[i] + E[i][0], xt[i] + E[i][1]) for i in range(n)]
            if kind == "enclose":
                if op == "<=" and X[k][1] > bound or op == ">=" and X[k][0] < bound:
                    return f"the checker's enclosure of {q} is [{float(X[k][0]):.6g}, {float(X[k][1]):.6g}]"
                pieces[0] += 1
                return None
            if kind != "pin" or not node.get("signs"):
                return f"unknown or empty leaf {kind!r}"
            y = _lc_vec(Cm[k], Cm, True, g)
            for x, sg in node["signs"].items():
                dA, db = D.get(x, ({}, {}))
                r = {m: (-v[1], -v[0]) for m, v in db.items()}
                for (i, j), iv in dA.items():
                    t = imul(iv, X[j])
                    o = r.get(i, zero)
                    r[i] = (o[0] + t[0], o[1] + t[1])
                zd = [(-hi_, -lo_) for lo_, hi_ in rmul(R, r)]
                if y is not None:
                    cy = sum(y[m] * mag(zd[m]) for m in range(n))
                    lo, hi = zd[k][0] - cy, zd[k][1] + cy
                else:
                    lo, hi = ebox(zd, Cm, beta)[k]
                if sg == "+" and lo < 0 or sg == "-" and hi > 0:
                    if factor_sign(x, piece, R) == sg:
                        continue                         # step 6, by the checker's own means
                    return f"d{q}/d{x} reads [{float(lo):.4g}, {float(hi):.4g}] on the piece, not {sg}"
            to = {x: (piece[x][1] if (s == "+") == (op == "<=") else piece[x][0]) for x, s in node["signs"].items()}
            return walk(node.get("then"), dict(piece, **{x: (v, v) for x, v in to.items()}), depth + 1)
        except (CheckError, KeyError, TypeError, ValueError, ZeroDivisionError) as e:
            return f"the checker could not read the leaf: {e}"

    piece0 = {x: boxes[x] for x in names if x in boxes}
    why = walk(tree, piece0, 0)
    return (False, why) if why else (True, pieces[0])
