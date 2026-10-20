"""SEARCH for a certificate (here, outside ZTL); ZTL checks it (ZTL/zcertify.py).

The decision of 2026-10-09: ZTL's kernel takes no budgets. Splitting a box until
every piece is decided is a search, and a search may need a budget — so it lives
here, in the stand. What it brings to ZTL is a certificate: a bisection tree whose
leaves are "monotone" (the derivative's sign per quantity, so the extreme sits at
one corner) or "interval" (the reading settles the piece). ZTL rebuilds the
derivatives itself and checks every leaf exactly; this file is not trusted.

Used when a requirement on a quantity with an explicit expression is neither shown
by the interval reading nor violated at any corner: the extreme may sit INSIDE the
box (power into a load peaks at RL = Rs). The search either brings a proof, or
finds a point inside the box where the requirement fails (exact rational value;
the checker recomputes it from the laws), or gives up within its budget — then the
design stays OPEN, as before.
"""
from __future__ import annotations

import ast
import re
from fractions import Fraction as F
import numpy as np

from . import judge_ztl as J          # puts ZTL on the path
from .stopflag import check as _stop_check
from . import mode as MODE

import zcertify as ZC                 # noqa: E402
from znumjudge import _parse_arith, parse_quantities   # noqa: E402

MAX_PIECES = 4000      # the SEARCHER's budget (outside the kernel): past it, no certificate
WHOLE_AFTER_SPLIT = 200   # the whole's budget when its sum split, tried first, found no certificate (stand._certify)
MAX_DEPTH = 60         # and its depth: a derivative that reads across zero for ever (p0 - p0) stops here


def expression(q, explicit, derived):
    """The text of q in terms of non-derived quantities where possible: every derived
    name with an explicit law is replaced by its expression (in parentheses)."""
    text = ast.unparse(explicit[q])
    for _ in range(len(explicit) + 1):
        before = text
        for n, rhs in explicit.items():
            if n != q:
                text = re.sub(rf"\b{re.escape(n)}\b", f"({ast.unparse(rhs)})", text)
        if text == before:
            break
    left = {m for m in re.findall(r"[A-Za-z_]\w*", text) if m in derived}
    return text, left


MAX_SYSTEM = 6         # linear unknowns solved symbolically (search side; the checker re-derives its own)


def _sym_text(x):
    """A sympy expression as text ZTL's reader takes: + - * / and parentheses only."""
    import sympy as sp
    if isinstance(x, sp.Symbol):
        return x.name
    if isinstance(x, sp.Integer):
        return f"({int(x)})"
    if isinstance(x, sp.Rational):
        return f"({x.p}/{x.q})"
    if isinstance(x, sp.Add):
        return "(" + " + ".join(_sym_text(a) for a in x.args) + ")"
    if isinstance(x, sp.Mul):
        num, den = sp.fraction(x)
        if den != 1:
            return f"({_sym_text(num)}/{_sym_text(den)})"
        return "(" + "*".join(_sym_text(a) for a in x.args) + ")"
    if isinstance(x, sp.Pow) and x.exp.is_Integer:
        k = int(x.exp)
        body = "*".join([_sym_text(x.base)] * abs(k))
        return f"({body})" if k > 0 else f"(1/({body}))"
    # FUNCTIONS (2026-10-10): back into the reader's spelling
    if isinstance(x, sp.Pow) and x.exp == sp.Rational(1, 2):
        return f"sqrt({_sym_text(x.base)})"
    if isinstance(x, sp.Pow):
        return f"pow({_sym_text(x.base)}, {_sym_text(x.exp)})"
    if isinstance(x, sp.exp):
        return f"exp({_sym_text(x.args[0])})"
    if isinstance(x, sp.log):
        return f"ln({_sym_text(x.args[0])})"
    if isinstance(x, sp.atan):
        return f"atan({_sym_text(x.args[0])})"
    if isinstance(x, sp.tan):
        return f"tan({_sym_text(x.args[0])})"
    if isinstance(x, sp.sin):
        return f"sin({_sym_text(x.args[0])})"
    if isinstance(x, sp.cos):
        return f"cos({_sym_text(x.args[0])})"
    if isinstance(x, (sp.Min, sp.Max)) and len(x.args) == 2:
        return f"{'min' if isinstance(x, sp.Min) else 'max'}({_sym_text(x.args[0])}, {_sym_text(x.args[1])})"
    raise ValueError(f"not in the reader's arithmetic: {x}")


def solve_linear(linear_laws, unknowns):
    """{u: text} — the linear unknowns in terms of the other quantities (sympy, untrusted:
    ZTL checks the certificate built on it, and the checker re-derives its own by Cramer)."""
    import sympy as sp
    unknowns = sorted(unknowns)
    if len(unknowns) > MAX_SYSTEM:
        return None
    eqs, names = [], set()
    fns = {"exp": sp.exp, "ln": sp.log, "log10": lambda u: sp.log(u, 10), "atan": sp.atan, "tan": sp.tan, "sin": sp.sin, "cos": sp.cos,
           "sqrt": sp.sqrt, "pow": sp.Pow, "min": sp.Min, "max": sp.Max}
    for law in linear_laws:
        names |= set(re.findall(r"[A-Za-z_]\w*", law)) - set(fns)
    syms = dict({n: sp.Symbol(n) for n in names}, **fns)
    for law in linear_laws:
        l, r = law.split("==")
        eqs.append(sp.sympify(l, locals=syms, rational=True) - sp.sympify(r, locals=syms, rational=True))
    sol = sp.solve(eqs, [syms[u] for u in unknowns], dict=True)
    if len(sol) != 1 or set(sol[0]) != {syms[u] for u in unknowns}:
        return None                                  # not determined uniquely: no expression
    try:
        return {u: _sym_text(sp.factor(sp.together(sol[0][syms[u]]))) for u in unknowns}
    except ValueError:
        return None


def fold_zeros(text, zeros):
    """Each name in `zeros` replaced by 0 and the zeros folded (0*x -> 0, x + 0 -> x, x - 0 -> x, 0 - x -> -x,
    0/x -> 0) — and NOTHING else: the rest keeps the author's factored form. (2026-10-16, the 28-datum motor: the
    fold went through simplify, whose one-fraction-factored form EXPANDED (Dt + dDt)^2 into terms of 5e8 that cancel
    — an interval reading 1e6 wide where the value moves by 1 %, and no certificate in hours.)"""
    tree = ast.parse(text, mode="eval")

    def zero(n):
        return isinstance(n, ast.Constant) and n.value == 0

    class _Z(ast.NodeTransformer):
        def visit_Name(self, node):
            return ast.Constant(0) if node.id in zeros else node

        def visit_BinOp(self, node):
            self.generic_visit(node)
            l, r = node.left, node.right
            if isinstance(node.op, ast.Mult) and (zero(l) or zero(r)):
                return ast.Constant(0)
            if isinstance(node.op, ast.Div) and zero(l):
                return ast.Constant(0)
            if isinstance(node.op, ast.Add):
                if zero(l):
                    return r
                if zero(r):
                    return l
            if isinstance(node.op, ast.Sub):
                if zero(r):
                    return l
                if zero(l):
                    return ast.UnaryOp(op=ast.USub(), operand=r)
            return node
    return ast.unparse(_Z().visit(tree))


def simplify(text):
    """One fraction, factored (V*V*RL/((Rs+RL)*(Rs+RL)) rather than a product of two
    fractions over the same denominator): the readings, and so the search, are tighter.
    Untrusted like the rest of this file: ZTL checks the certificate on THIS text, the
    checker on its own expression from the laws."""
    import sympy as sp
    fns = {"exp": sp.exp, "ln": sp.log, "log10": lambda u: sp.log(u, 10), "atan": sp.atan, "tan": sp.tan, "sin": sp.sin, "cos": sp.cos,
           "sqrt": sp.sqrt, "pow": sp.Pow, "min": sp.Min, "max": sp.Max}
    names = set(re.findall(r"[A-Za-z_]\w*", text)) - set(fns)
    syms = dict({n: sp.Symbol(n) for n in names}, **fns)
    try:
        return _sym_text(sp.factor(sp.together(sp.sympify(text, locals=syms, rational=True))))
    except (ValueError, TypeError, sp.SympifyError):
        return text              # a form sympy cannot give back in the reader's spelling: search the original


BRACKET_STEPS = 12     # bisections for an implicit root's bracket on a piece, inside the parent's bracket
POINT_STEPS = 34       # and at a point (a corner): tight, the corner's value is read with it
# (MEASURED 2026-10-11, c02 Esd >= 0.85: 40 steps from U's whole range on every piece were 52 of 60 s)


def _dyadic(lo, hi):
    """A point strictly inside (lo, hi) with a short denominator (the midpoint's grows every step)."""
    m = (lo + hi) / 2
    k = 2 ** 40
    c = F(int(m * k), k)
    return c if lo < c < hi else m


def _brackets(implicit, qs, piece, parent=None):
    """{U: (a, b)} — for every x of the piece the root of U's law lies in [a, b] — or None. Search side:
    bisection on U toward the root from both ends of the parent piece's bracket (a part of a piece keeps
    its bracket) or of U's range; ZTL re-reads every bracket."""
    out = {}
    point = all(lo == hi for lo, hi in piece.values())
    for u, g in implicit.items():
        rlo, rhi = qs[u]["lo"], qs[u]["hi"]
        a0, b0 = (parent or {}).get(u, (rlo, rhi))
        try:
            r = ZC._reading(ZC.derivative(g, u), qs, dict(piece, **{u: (rlo, rhi)}))
        except ZC.NoDerivative:
            return None
        if r is None or (r[0] <= 0 <= r[1]):
            return None
        s = 1 if r[0] > 0 else -1

        def side(v):
            """-1: g below 0 for the whole piece (times s), +1: above, 0: undecided."""
            rr = ZC._reading(g, qs, dict(piece, **{u: (v, v)}))
            if rr is None:
                return 0
            if (rr[1] <= 0) if s > 0 else (rr[0] >= 0):
                return -1
            if (rr[0] >= 0) if s > 0 else (rr[1] <= 0):
                return 1
            return 0
        if parent is None and (side(a0) != -1 or side(b0) != 1):
            return None
        steps = POINT_STEPS if point else BRACKET_STEPS
        lo, hi = a0, b0                         # a: the highest point still on the low side
        for _ in range(steps):
            m = _dyadic(lo, hi)
            lo, hi = (m, hi) if side(m) == -1 else (lo, m)
        a = lo
        lo, hi = a, b0                          # b: the lowest point already on the high side
        for _ in range(steps):
            m = _dyadic(lo, hi)
            lo, hi = (lo, m) if side(m) == 1 else (m, hi)
        out[u] = (a, hi)
    return out


def _corner_value(e, qs, corner, implicit=None):
    pt = {n: (v, v) for n, v in corner.items()}
    if implicit:
        br = _brackets(implicit, qs, pt)
        if br is None:
            return None
        pt.update(br)
    r = ZC._reading(e, qs, pt)
    return None if r is None else r[0]


def search(text, fixed, boxes, op, bound, implicit=None, budget=None):
    """{"cert", "pieces"} | {"witness": point, "value"} | {"gave_up": why}.
    implicit = {U: law text g (U a root of g == 0)}: U's range is its box in `boxes`."""
    qs = parse_quantities(J.sheet(fixed, boxes, [], {}))[0]
    imp = {u: _parse_arith(g, qs) for u, g in (implicit or {}).items()}
    return _search_node(_parse_arith(text, qs), qs, fixed, boxes, op, bound, imp,
                        both=None if implicit or not MODE.DEV[0] else _checker_reads(text, fixed, op, bound),
                        budget=budget)


def _checker_reads(text, fixed, op, bound):
    """For the search only: does the CHECKER's own reading (with its cases) settle the piece too? An interval leaf
    ZTL can read and the checker cannot is cut further instead (blind test 5, c09: ZTL's affine reading held a 0.76 %
    margin the checker's interval-and-sympy reading could not, and the certificate came back unconfirmed). The
    search is untrusted: it may use either judge's reading to choose its leaves; each judge still checks alone."""
    import ast as _ast
    from . import checker as C
    try:
        node = C._fold(_ast.parse(text, mode="eval").body)
    except SyntaxError:
        return None
    base = {n: (v, v) for n, v in fixed.items()}

    def reads(piece):
        try:
            lo, hi = C._ivl_cases(node, dict(base, **piece))
        except (C.CheckError, ZeroDivisionError, ValueError, ArithmeticError):
            return False
        return hi <= bound if op == "<=" else lo >= bound
    return reads


def _search_node(e, qs, fixed, boxes, op, bound, implicit=None, both=None, budget=None):
    implicit = implicit or {}
    budget = budget or MAX_PIECES
    used = set(ZC._names(e))
    for g in implicit.values():
        used |= ZC._names(g)
    names = sorted(n for n in used if n in boxes and n not in implicit)
    width0 = {n: boxes[n][1] - boxes[n][0] for n in names}
    # a HAIR-WIDE box (pi given as 3.141592653589793..4: 1e-16 wide) is never cut — cutting it doubled the
    # pieces for nothing (MEASURED 2026-10-11, c02); it still needs its sign in a monotone leaf
    hair = {n for n in names if width0[n] <= F(1, 10 ** 12) * max(abs(boxes[n][0]), abs(boxes[n][1]))}
    derivs = {}

    def deriv(n):
        """the symbolic dE/dn, built on demand (the graph's derivatives are read first, ZTL _graph_grad)"""
        if n not in derivs:
            try:
                derivs[n] = ZC._total_derivative(e, n, implicit)
            except ZC.NoDerivative:
                derivs[n] = None    # min/max in e (blind test 3, c09: it raised): that name never gets a sign,
                                    # so its pieces end in interval leaves — the kernel's own rule
        return derivs[n]
    bad = (lambda v: v > bound) if op == "<=" else (lambda v: v < bound)
    count = [0]

    class Found(Exception):
        pass

    def go(piece, depth=0, parent=None):
        _stop_check()               # a stop asked from outside (blind test 5, c12 literal: 21 min past a 900 s limit)
        count[0] += 1
        if count[0] > budget:
            raise Found({"gave_up": f"more than {budget} pieces"})
        if depth > MAX_DEPTH:
            raise Found({"gave_up": f"deeper than {MAX_DEPTH} splits"})
        signs, straddle = {}, []
        br = _brackets(implicit, qs, piece, parent) if implicit else None
        rp = dict(piece, **(br or {u: (qs[u]["lo"], qs[u]["hi"]) for u in implicit}))
        roots = {"roots": {u: [_fr(a), _fr(b)] for u, (a, b) in br.items()}} if br else {}
        gg = {} if implicit and br is None else ZC._graph_grad(
            e, qs, rp, [n for n in names if piece[n][0] != piece[n][1]], implicit)
        for n in names:
            lo, hi = piece[n]
            if lo == hi:
                continue
            if implicit and br is None:
                straddle.append(n)          # no bracket: no monotone leaf on this piece
                continue
            r = gg.get(n)                   # along the graph first (2026-10-16), the symbolic tree if undecided
            if r is None or not (r[0] >= 0 or r[1] <= 0):
                r = ZC._reading(deriv(n), qs, rp) if deriv(n) is not None else None
            if r is None:
                straddle.append(n)
            elif r[0] >= 0:
                signs[n] = "+"
            elif r[1] <= 0:
                signs[n] = "-"
            else:
                straddle.append(n)
        if not straddle:
            corner = {n: (piece[n][1] if (signs.get(n) == "+") == (op == "<=") else piece[n][0])
                      for n in names}
            if implicit:
                cpt = {n: (v, v) for n, v in corner.items()}
                cbr = _brackets(implicit, qs, cpt)
                r = ZC._reading(e, qs, dict(cpt, **cbr)) if cbr is not None else None
                if r is not None and (r[1] <= bound if op == "<=" else r[0] >= bound):
                    return {"leaf": "monotone", "signs": signs, **roots,
                            "corner_roots": {u: [_fr(a), _fr(b)] for u, (a, b) in cbr.items()}}
                if r is not None and bad(r[0] if op == ">=" else r[1]) and bad(r[1] if op == ">=" else r[0]):
                    raise Found({"witness": corner, "value": r[0]})
                straddle = list(names)      # the corner's reading undecided: cut further
            else:
                v = _corner_value(e, qs, corner)
                if v is not None and bad(v):
                    raise Found({"witness": corner, "value": v})     # the piece's true extreme fails
                return {"leaf": "monotone", "signs": signs}
        r = ZC._reading(e, qs, rp if implicit else piece)
        if r is not None and (r[1] <= bound if op == "<=" else r[0] >= bound) and (both is None or both(piece)):
            return {"leaf": "interval", **roots}
        if not implicit or depth % 4 == 0:     # a root's point bracket costs: the middle tried every 4th cut
            mid = {n: (lo + hi) / 2 for n, (lo, hi) in piece.items()}
            v = _corner_value(e, qs, mid, implicit)
            if v is not None and bad(v):
                raise Found({"witness": mid, "value": v})
        # PIN (2026-10-16, the curator's "б"): the quantities whose sign IS shown go to their extreme end, the rest
        # is searched in fewer dimensions — splitting all of them kept every signed one at full width, and its
        # spread kept the others' derivatives unreadable (the 28-datum motor: 16 of 18 signs at once, never a
        # monotone leaf in 18 dimensions). ZTL checks each pin's sign itself (zcertify, "pin").
        pinnable = {k: s_ for k, s_ in signs.items() if piece[k][0] < piece[k][1]}
        if pinnable and not MODE.DEV[0]:
            child = dict(piece)
            for k, s_ in pinnable.items():
                up_ = (s_ == "+") == (op == "<=")
                child[k] = (piece[k][1], piece[k][1]) if up_ else (piece[k][0], piece[k][0])
            return {"pin": pinnable, "then": go(child, depth + 1, br), **roots}
        # split a quantity whose sign is not shown (the widest of them, relative to its box) —
        # unless another side is far wider: the reading's dependency may come from IT
        rel = lambda k: (piece[k][1] - piece[k][0]) / (width0[k] or 1)
        cuttable = [k for k in names if piece[k][0] < piece[k][1] and k not in hair]
        straddle = [k for k in straddle if k in cuttable] or cuttable
        if not straddle:
            raise Found({"gave_up": "a point piece undecided"})
        n = max(straddle, key=rel)
        other = max(cuttable, key=rel)
        if rel(other) > 8 * rel(n):
            n = other
        lo, hi = piece[n]
        at = _dyadic(lo, hi)
        return {"split": n, "at": f"{at.numerator}/{at.denominator}",
                "lo": go(dict(piece, **{n: (lo, at)}), depth + 1, br),
                "hi": go(dict(piece, **{n: (at, hi)}), depth + 1, br)}

    try:
        cert = go({n: boxes[n] for n in names})
    except Found as f:
        return f.args[0]
    return {"cert": cert, "pieces": count[0], "expr": e, "qs": qs}


def _fr(x):
    return f"{x.numerator}/{x.denominator}"


def prove(text, fixed, boxes, op, bound, system=None, implicit=None, budget=None):
    """Search, then let ZTL check. {"proved": pieces} | {"witness", "value"} | {"open": why}.

    system = (target, linear laws, unknowns): the quantity depends on unknowns solved from
    a linear system. The search runs on the stand's own solved `text`; ZTL is NOT given
    that text — it solves the system itself (zcertify.check_system) and checks the same
    certificate on its own solution. If ZTL's form reads too crudely for the tree, the
    search is run once more on ZTL's own form."""
    # the SEARCH builds its leaves on the plain reading (2026-10-10): with ZTL's affine reading on, it made
    # leaves so coarse that only the kernel could read them and the independent checker could not confirm
    # (t9: Rs = 11 OPEN). The kernel still checks with every reading it has.
    affine_was = ZC.AFFINE
    ZC.AFFINE = False
    try:
        got = search(text, fixed, boxes, op, bound, implicit, budget)
    finally:
        ZC.AFFINE = affine_was
    if "cert" not in got:
        return got if "witness" in got else {"open": got["gave_up"]}
    if implicit:
        if system is not None:
            return {"open": "an implicit quantity and a linear system together: not certified"}
        qs = got["qs"]
        ok, info = ZC.check(got["expr"], qs, op, bound, got["cert"],
                            implicit={u: _parse_arith(g, qs) for u, g in implicit.items()})
    elif system is None:
        ok, info = ZC.check(got["expr"], got["qs"], op, bound, got["cert"])
    else:
        target, laws, unknowns = system
        qs = parse_quantities(J.sheet(fixed, boxes, unknowns, {}))[0]
        ok, info = ZC.check_system(target, laws, unknowns, qs, op, bound, got["cert"])
        if not ok and not info.startswith("system:"):
            kform = ZC._subst(_parse_arith(target, qs), ZC.solve_system(laws, unknowns, qs))
            again = _search_node(kform, qs, fixed, boxes, op, bound, budget=budget)
            if "cert" in again:
                got = again
                ok, info = ZC.check_system(target, laws, unknowns, qs, op, bound, got["cert"])
    if not ok:
        return {"open": f"ZTL refused the stand's certificate: {info}"}   # the searcher was wrong
    return {"proved": info, "cert": got["cert"]}


# ── A SUM, term by term (2026-10-12, the curator's "да"; blind test 5 c11: A = P1 + P2 + P3 + P4 over five data —
# no certificate in 25 min — while each quarter over its own two is 4 pieces in 0.05 s; the author proved it by
# hand that way). min over the box of a sum >= the sum of each term's min over the box: SOUND, every term proved by
# its own certificate over its own (small) box; a datum shared by two terms is free in each, so the bound may be
# wider, never wrong.

def _term_extreme(text, fixed, boxes, op):
    """An approximate extreme (min for ">=", max for "<=") of the term over the box — SEARCH side: corners (up to
    2^8), then coordinate sweeps with golden refinement. The certificate decides; this only aims it."""
    import itertools
    qs = parse_quantities(J.sheet(fixed, boxes, [], {}))[0]
    node = _parse_arith(text, qs)
    names = sorted(n for n in ZC._names(node) if n in boxes and boxes[n][0] != boxes[n][1])
    sign = 1 if op == ">=" else -1

    def val(pt):
        r = ZC._reading(node, qs, {n: (v, v) for n, v in pt.items()}, cases=False, affine=False)
        return None if r is None else sign * (r[0] + r[1]) / 2
    best_pt = {n: (boxes[n][0] + boxes[n][1]) / 2 for n in names}
    best = val(best_pt)
    if len(names) <= 8:
        for ends in itertools.product(*[(boxes[n][0], boxes[n][1]) for n in names]):
            pt = dict(zip(names, ends))
            v = val(pt)
            if v is not None and (best is None or v < best):
                best, best_pt = v, pt
    if best is None:
        return None, {}
    for _ in range(2):
        for n in names:
            lo, hi = boxes[n]
            for k in range(17):
                c = lo + (hi - lo) * F(k, 16)
                v = val(dict(best_pt, **{n: c}))
                if v is not None and v < best:
                    best, best_pt = v, dict(best_pt, **{n: c})
            fa, fb = float(max(lo, best_pt[n] - (hi - lo) / 16)), float(min(hi, best_pt[n] + (hi - lo) / 16))
            g = 0.6180339887498949
            for _ in range(30):
                c1, c2 = fb - g * (fb - fa), fa + g * (fb - fa)
                v1 = val(dict(best_pt, **{n: F(c1).limit_denominator(10 ** 9)}))
                v2 = val(dict(best_pt, **{n: F(c2).limit_denominator(10 ** 9)}))
                if v1 is None or v2 is None:
                    break
                if v1 < v2:
                    fb = c2
                else:
                    fa = c1
            c = min(max(F((fa + fb) / 2).limit_denominator(10 ** 9), lo), hi)
            v = val(dict(best_pt, **{n: c}))
            if v is not None and v < best:
                best, best_pt = v, dict(best_pt, **{n: c})
    return sign * best, best_pt


SCALE_FROM = 0.9      # the plain beta (centre estimate) from which the unknowns are rescaled


def _perron_pow2(M):
    """M's Perron vector (M >= 0), normalised, floored at 1e-12, rounded to powers of two (exact and short)."""
    import math
    w, V = np.linalg.eig(M)
    p = np.abs(V[:, int(np.argmax(np.abs(w)))].real)
    if not np.isfinite(p).all() or p.max() <= 0:
        return None
    # the floor: Muhanna's benchmark 2 (U_42_Y, MEASURED 2026-10-16): 2^-8, 2^-12 left a beta >= 1 in the sign
    # proofs; 2^-16 .. 2^-24 a certificate in 3 pieces (94 signs proved); 2^-32 lost the grid's precision (beta 8)
    p = np.maximum(p / p.max(), 2.0 ** -20)
    return [F(2) ** int(round(math.log2(x))) for x in p]


def _scaling(laws, unknowns, qs):
    """UNITS FOR THE UNKNOWNS AND THE EQUATIONS (2026-10-16, Muhanna's truss benchmark 2): the kernel's contraction is
    the max row sum of |C| = sum_p halfwidth_p |R dA/dp| — a SUFFICIENT test; a 20-floor cantilever's top displacements
    are 1e4 x its bottom ones, and the row sums gave beta = 3.2 where rho(|C|) = 0.028 (MEASURED). x_j = v_j y_j, v the
    Perron vector of |C| (powers of two), makes the new row sums ~ rho: 0.04 at 20 floors. The sign proofs (zlin step 6)
    solve the TRANSPOSED system too, whose contraction depends on the EQUATIONS' scale, not the unknowns' (I - R'A' =
    D^-1 (I - RA) D, but I - R'^T A'^T = W^-1 (I - R^T A^T) W): each law i multiplied by w_i, w the Perron vector of
    sum_p halfwidth_p |dA/dp R|^T — without it all 101 sign proofs of the benchmark failed (beta 3.2) and the search
    branched exponentially (MEASURED). Exact changes only: the kernel checks the rescaled system as any other. Floats,
    trusted for nothing. -> {"v": {unknown: v_j}, "w": [w_i]} or None (not needed: both betas < SCALE_FROM)."""
    from . import linsearch as LS
    import zlin as ZL
    try:
        A, b = ZL.system(laws, unknowns, qs)
        mid = {n: (q["lo"] + q["hi"]) / 2 for n, q in qs.items() if q.get("lo") is not None}
        n = len(unknowns)
        Am = np.array([[LS._at(e, qs, mid) for e in row] for row in A])
        Rm = np.linalg.inv(Am)
        per = {}
        for i, row in enumerate(A):
            for j, e in enumerate(row):
                for nm in ZC._names(e):
                    if qs[nm].get("lo") is not None and qs[nm]["hi"] != qs[nm]["lo"]:
                        d = LS._at(ZC.derivative(e, nm), qs, mid) * float(qs[nm]["hi"] - qs[nm]["lo"]) / 2
                        per.setdefault(nm, np.zeros((n, n)))[i, j] += d
        S = sum((np.abs(Rm @ M) for M in per.values()), np.zeros((n, n)))      # forward: I - R A
        T = sum((np.abs(M @ Rm).T for M in per.values()), np.zeros((n, n)))    # transposed: I - R^T A^T
    except (ZL.LinError, ZC.NoDerivative, np.linalg.LinAlgError, KeyError, TypeError, ValueError):
        return None
    out = {}
    for key, M in (("v", S), ("w", T)):
        beta = M.sum(1).max()
        if not np.isfinite(beta) or beta < SCALE_FROM:
            continue
        p = _perron_pow2(M)
        if p is None:
            continue
        pf = np.array([float(x) for x in p])
        if ((M @ pf) / pf).max() < beta:
            out[key] = p
    if not out:
        return None
    return {"v": dict(zip(unknowns, out.get("v") or [F(1)] * len(unknowns))), "w": out.get("w") or [F(1)] * len(laws)}


def _rescale(laws, scale):
    """Every unknown x_j written (v_j*x_j) — the same name now holds x_j / v_j — and law i multiplied by w_i."""
    import re
    v = {u: c for u, c in scale["v"].items() if c != 1}
    out = []
    pat = re.compile(r"(?<![A-Za-z0-9_.])(" + "|".join(re.escape(u) for u in sorted(v, key=len, reverse=True))
                     + r")(?![A-Za-z0-9_])") if v else None
    for law, w in zip(laws, scale["w"]):
        if pat is not None:
            law = pat.sub(lambda m: f"(({v[m.group(1)]})*{m.group(1)})", law)
        if w != 1:
            lhs, rhs = law.split("==")
            law = f"({w})*({lhs}) == ({w})*({rhs})"
        out.append(law)
    return out


def prove_linear(laws, unknowns, target, fixed, boxes, op, bound, budget=None):
    """A bound on one unknown of a linear system too large to solve symbolically (more than MAX_SYSTEM unknowns,
    2026-10-15): ustand/linsearch.py searches, ZTL's zlin.py — a kernel module, exact — checks.
    {"proved": pieces, "cert": tree[, "checked_as": (laws, bound)]} | {"witness": {name: value}} | {"open": why}.
    checked_as: the RESCALED system and bound the certificate is for (see _scaling) — the checker re-checks THAT."""
    from . import linsearch as LS
    import zlin as ZL                   # ZTL's kernel module
    qs = parse_quantities(J.sheet(fixed, boxes, unknowns, {}))[0]
    scale = _scaling(laws, unknowns, qs)
    if scale:
        laws, bound = _rescale(laws, scale), F(bound) / scale["v"][target]
    got = LS.search(laws, unknowns, qs, target, op, bound, budget)
    if "witness" in got:
        return {"witness": got["witness"]}
    if "cert" not in got:
        return {"open": got["gave_up"]}
    ok, info = ZL.check(laws, unknowns, qs, target, op, bound, got["cert"])
    if not ok:
        return {"open": f"the kernel refused the stand's linear certificate: {info}"}   # the searcher was wrong
    out = {"proved": info, "cert": got["cert"]}
    if scale:
        out["checked_as"] = (laws, bound)
    return out


def prove_linear_range(laws, unknowns, u, fixed, boxes, steps=30):
    """A PROVED range of one unknown of a large linear system (2026-10-15): each end by descent — the search's witness,
    solved exactly, is the next bound, until zlin's certificate is accepted for it. -> {"range": (lo, hi), "certs":
    [(op, bound, cert)], "pieces": n} | {"open": why}. The range then enters another certificate as a BOX (sound: the
    unknown's true value at every point of the tolerance box lies in it — the implicit quantities' rule, G6)."""
    from . import linsearch as LS
    import zlin as ZL
    qs = parse_quantities(J.sheet(fixed, boxes, unknowns, {}))[0]
    A, b = ZL.system(laws, unknowns, qs)
    k = list(unknowns).index(u)
    mid = {n: ((lo + hi) / 2, (lo + hi) / 2) for n, (lo, hi) in boxes.items()}
    names = {n for row in A for e in row for n in ZC._names(e)} | {n for e in b for n in ZC._names(e)}
    centre = dict({n: (qs[n]["lo"], qs[n]["hi"]) for n in names}, **{n: v for n, v in mid.items() if n in names})
    out, certs, pieces = [], [], 0
    for op in (">=", "<="):
        # the start: the greedy vertex's exact value (the extreme on every case measured), not the centre
        gv = LS.greedy_vertex(A, b, qs, k, op == "<=", {n: (qs[n]["lo"], qs[n]["hi"]) for n in names})
        bound = ZL._solve_point(A, b, qs, dict(centre, **{n: (v, v) for n, v in gv.items()}), k)
        for _ in range(steps):
            got = LS.search(laws, unknowns, qs, u, op, bound)
            if "witness" in got:
                pt = dict(centre, **{n: (v, v) for n, v in got["witness"].items()})
                bound = ZL._solve_point(A, b, qs, pt, k)
                continue
            if "cert" not in got:
                return {"open": f"{u}: {got.get('gave_up')}"}
            ok, info = ZL.check(laws, unknowns, qs, u, op, bound, got["cert"])
            if not ok:
                return {"open": f"{u}: the kernel refused the search's certificate: {info}"}
            certs.append((op, bound, got["cert"]))
            pieces += info
            out.append(bound)
            break
        else:
            return {"open": f"{u}: no certificate within {steps} descent steps"}
    return {"range": (out[0], out[1]), "certs": certs, "pieces": pieces}


def prove_sum(terms, fixed, boxes, op, bound):
    """Prove `Σ terms op bound` term by term: each term's approximate extreme m_i, the slack Σ m_i − bound shared
    equally, each term proved `op m_i ∓ share` by its own certificate (search + ZTL check, over the box — the
    term reads only its own data). -> {"proved": pieces, "terms": [(text, bound_i, pieces, cert)]} or None."""
    ms, at = [], {}
    for t in terms:
        m, pt = _term_extreme(t, fixed, boxes, op)
        if m is None:
            return None
        ms.append(m)
        for n, v in pt.items():
            at.setdefault(n, v)         # a datum two terms share: the first term's extreme point (a candidate only)
    slack = (sum(ms) - bound) if op == ">=" else (bound - sum(ms))
    if slack < 0:
        # the terms' approximate extremes already miss the bound: nothing to prove this way; their points together
        # are a CANDIDATE witness (the caller lets the checker decide it exactly)
        return {"miss": at}
    share = slack / len(terms)
    out, pieces = [], 0
    for t, m in zip(terms, ms):
        b_i = m - share if op == ">=" else m + share
        got = prove(t, fixed, boxes, op, b_i)
        if "proved" not in got:
            return None
        pieces += got["proved"]
        out.append((t, b_i, got["proved"], got["cert"]))
    return {"proved": pieces, "terms": out}

