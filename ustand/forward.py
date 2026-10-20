"""The stand's FORWARD step: what ZTL does not bound today, bounded here — and labelled.

ZTL (as of 62b71ea) solves the linear system exactly but leaves a nonlinear
definition such as P1 == I*I*R1 unbounded (-inf, inf), and marks the linear
unknowns "over the linear rows" when such a row sits in the claim. So the stand
sends ZTL the linear laws only, and bounds each definition here by plain
interval arithmetic over ZTL's ranges and the tolerance boxes: sound (never too
narrow), possibly too wide. Every value from here is labelled "outside ZTL".
When ZTL learns this mathematics, this step moves into the judge.

Written separately from checker.py on purpose (the checker must not share code
with what it checks); both read the same ZFL equalities.
"""
from __future__ import annotations

import ast
from fractions import Fraction as F


class ForwardError(ValueError):
    pass


def _names_in(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _is_nonlinear(node, derived):
    """True when the expression multiplies or divides by a derived quantity product."""
    for n in ast.walk(node):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult):
            if _names_in(n.left) & derived and _names_in(n.right) & derived:
                return True
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
            if _names_in(n.right) & derived:
                return True
    return False


def _has_call(node):
    return any(isinstance(n, ast.Call) for n in ast.walk(node))


_SPLIT = {}


def split(laws, derived):
    """Memoized _split (the same laws are split again for every design — MEASURED 2026-10-10, blind test 2
    c10: 1.8 s of 6.7 under the profiler); each caller gets its own list and dict."""
    key = (tuple(laws), frozenset(derived))
    hit = _SPLIT.get(key)
    if hit is None:
        hit = _split(laws, derived)
        if len(_SPLIT) > 4096:
            _SPLIT.clear()
        _SPLIT[key] = hit
    return list(hit[0]), dict(hit[1])


def _split(laws, derived):
    """(linear laws for the judge, definitions {name: rhs ast}).

    A DEFINITION is a law `X == expression` (X derived, not in the expression) that is nonlinear,
    or holds a FUNCTION, or leans on another definition — found to a fixed point, so a CHAIN of
    definitions works (2026-10-10: Dveff == Dv - g0*tb with Dv == Isp*g0*ln(m0/mf); gap G14).
    Every other law must be linear in the derived quantities and free of definitions."""
    derived = set(derived)
    parsed = []
    for law in laws:
        tree = ast.parse(law, mode="eval").body
        if not (isinstance(tree, ast.Compare) and len(tree.ops) == 1 and isinstance(tree.ops[0], ast.Eq)):
            raise ForwardError(f"a law must be one equality: {law!r}")
        parsed.append((law, tree.left, tree.comparators[0]))
    defs, def_law = {}, {}

    def explicit_form(lhs, rhs):
        return isinstance(lhs, ast.Name) and lhs.id in derived and lhs.id not in _names_in(rhs)

    grew = True
    while grew:
        grew = False
        for law, lhs, rhs in parsed:
            if law in def_law:
                continue
            special = (_is_nonlinear(lhs, derived) or _is_nonlinear(rhs, derived) or _has_call(lhs) or _has_call(rhs)
                       or ((_names_in(lhs) | _names_in(rhs)) & set(defs)))
            if not special:
                continue
            if explicit_form(lhs, rhs):
                if lhs.id in defs:      # the second silently replaced the first (blind test b02, 2026-10-10)
                    raise ForwardError(f"{lhs.id} is defined by two nonlinear laws: keep one")
                defs[lhs.id], def_law[law] = rhs, lhs.id
                grew = True
    linear = []
    for law, lhs, rhs in parsed:
        if law in def_law:
            continue
        if _is_nonlinear(lhs, derived) or _is_nonlinear(rhs, derived) or _has_call(lhs) or _has_call(rhs):
            raise ForwardError(f"a nonlinear law, or one with a function, must define one derived quantity "
                               f"(X == expression): {law!r}")
        linear.append(law)
    return linear, defs


def explicit(laws, names):
    """{X: rhs} for laws of the form `X == expression` with X in names — the laws the
    stand may bound itself when ZTL left X unbounded (gap Z2: ZTL 62b71ea gives
    (-inf, inf) for tau == R*C, a product of two toleranced quantities)."""
    out = {}
    for law in laws:
        tree = ast.parse(law, mode="eval").body
        if isinstance(tree, ast.Compare) and isinstance(tree.left, ast.Name) and tree.left.id in names \
                and tree.left.id not in _names_in(tree.comparators[0]):
            out[tree.left.id] = tree.comparators[0]
    return out


def _iv(node, r):
    if isinstance(node, ast.Constant):
        x = F(str(node.value)); return x, x
    if isinstance(node, ast.Name):
        if node.id not in r:
            raise ForwardError(node.id)
        return r[node.id]
    if isinstance(node, ast.Call) and node.func.id == "implicit":
        raise ForwardError("an implicit quantity is ZTL's to bound (judge_ztl.implicit)")
    if isinstance(node, ast.Call) and node.func.id in ("ifpos", "ifpos_d"):
        import zfunc
        x = _iv(node.args[0], r)
        side = zfunc._side(x)
        a = _iv(node.args[1], r) if side >= 0 else None
        b = _iv(node.args[2], r) if side <= 0 else None
        out = zfunc.TERNARY[node.func.id](x, a, b)
        if out is None:
            raise ForwardError("a branch whose derivative is read across its switch")
        return out
    if isinstance(node, ast.Call):                 # functions (2026-10-10): ZTL's proved brackets
        from . import judge_ztl  # noqa: F401
        import zfunc
        import znum
        args = [_iv(a, r) for a in node.args]
        name = node.func.id
        try:
            out = znum._iv_sqrt(args[0]) if name == "sqrt" else \
                (zfunc.UNARY[name](args[0]) if name in zfunc.UNARY else zfunc.BINARY[name](*args))
        except (zfunc.NoReadings, znum._NoReadings) as why:
            raise ForwardError(f"{name}: {why}")
        if out is None:
            raise ForwardError(f"{name} undefined somewhere on its range")
        return out
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        lo, hi = _iv(node.operand, r); return -hi, -lo
    if isinstance(node, ast.BinOp):
        x, y = _iv(node.left, r), _iv(node.right, r)
        if isinstance(node.op, ast.Add):
            return x[0] + y[0], x[1] + y[1]
        if isinstance(node.op, ast.Sub):
            return x[0] - y[1], x[1] - y[0]
        if isinstance(node.op, ast.Mult):
            ps = [a * b for a in x for b in y]; return min(ps), max(ps)
        if isinstance(node.op, ast.Div):
            if y[0] <= 0 <= y[1]:
                raise ForwardError("division by a range containing zero")
            ps = [a / b for a in x for b in y]; return min(ps), max(ps)
    raise ForwardError(f"unsupported: {ast.dump(node)[:50]}")


def bound(defs, ranges):
    """Outer ranges of the definitions, given ranges of everything else."""
    r = dict(ranges)
    out = {}
    todo = dict(defs)
    why = {}
    while todo:
        done = []
        for name, rhs in todo.items():
            try:
                r[name] = out[name] = _iv(rhs, r)
                done.append(name)
            except ForwardError as e:
                why[name] = str(e)
        if not done:
            # the reason and the usual cause said (blind test 4, c08: "cannot bound ['thold']" alone, for a sqrt
            # whose argument looked negative because a toleranced quantity was read twice, independently)
            first = sorted(todo)[0]
            raise ForwardError(f"cannot bound {sorted(todo)}: {why.get(first, 'a quantity it needs is unbounded')}"
                               " — an interval reading treats each occurrence of a toleranced quantity as "
                               "independent; writing the law so each appears once often helps")
        for n in done:
            del todo[n]
    return out
