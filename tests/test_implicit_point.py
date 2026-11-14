# -*- coding: utf-8 -*-
"""The checker's implicit root AT A POINT (2026-11-12): max/min have a derivative (the hull of both where the
arguments cross), a piece is cleared by MONOTONY (dg/dq strictly signed, the exact sign of g at one end), and an
enclosure that pruning left wide is LOCALISED. Measured cause: an EnergyPlus UA tower (72 KB of law) whose proved
outlet lay wholly past a bound came out OPEN — its root at the witness point stayed 4.5 K wide. The UA tower itself
is refuted in tests/test_hvac_plant.py ('ua-'); here the small cases and the PLANTED ones that must NOT be decided."""
import ast
import os
import sys
from fractions import Fraction as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import checker as C, stand as S          # noqa: E402

CHECKS, FAILS = 0, []


def check(c, what):
    global CHECKS
    CHECKS += 1
    if not c:
        FAILS.append(what)
        print("FAIL:", what)


def d_iv(text, x, lo, hi):
    return C._ivl(C._fold(C._d(ast.parse(text, mode="eval").body, x)), {x: (F(lo), F(hi))})


# 1. the derivative of max / min: the branch taken where it is decided, the hull of both where they cross
check(d_iv("max(x, 2)", "x", 3, 4) == (1, 1) and d_iv("max(x, 2)", "x", 0, 1) == (0, 0)
      and d_iv("max(x, 2)", "x", 1, 3) == (0, 1), "d max(x, 2)/dx: 1 above 2, 0 below, [0, 1] across")
check(d_iv("min(x*x, 3)", "x", 0, 1) == (0, 2) and d_iv("min(x*x, 3)", "x", 2, 3) == (0, 0)
      and d_iv("min(x*x, 3)", "x", 1, 2) == (0, 4), "d min(x^2, 3)/dx: 2x below, 0 above, the hull across")
# a kink keeps a STRICT sign when both sides do: max(x, 2x - 1) rises on both branches
check(C._sgn(C._fold(C._d(ast.parse("max(x, 2*x - 1)", mode="eval").body, "x")), {"x": (F(0), F(2))}) == 1,
      "a kink with both slopes positive is strictly rising (the hull [1, 2])")


REFUSED = (None, None)


def root(g, lo, hi, env=None):
    """the enclosure of the roots at a point — or REFUSED when no root is shown to exist there"""
    node = ast.parse(f"implicit(_root_x, {g}, {lo}, {hi})", mode="eval").body
    try:
        return C._implicit_iv(node, {k: (F(v), F(v)) for k, v in (env or {}).items()})
    except C.CheckError as e:
        if "SHOWN TO EXIST" not in str(e):
            raise
        return REFUSED


# 2. roots at a point, with max/min in the law — tight, and equal to the root
a, b = root("_root_x*_root_x*_root_x + max(_root_x, 1) - 3", "0", "3")
x0 = 1.2134116627622296                                       # x^3 + x = 3
check(b - a < F(1, 10 ** 9) and float(a) <= x0 <= float(b), f"x^3 + max(x, 1) = 3: one root, tight ({float(a)}, {float(b)})")
a, b = root("min(_root_x, 5)*exp(_root_x) - 7", "0", "4")
check(b - a < F(1, 10 ** 9) and abs(float(a) * 2.718281828459045 ** float(a) - 7) < 1e-6,
      f"min(x, 5)*exp(x) = 7: tight ({float(a)}, {float(b)})")

# 3. PLANTED — two roots: neither may be dropped (monotony clears a piece only where g is strictly monotone)
a, b = root("(_root_x - 1)*(_root_x - 2)", "0", "3")
check(a <= 1 and b >= 2, f"PLANTED two roots (x-1)(x-2): the enclosure keeps both ({float(a)}, {float(b)})")
a, b = root("max(_root_x - 1, 0)*(_root_x - 2)*(_root_x - 2.5)", "1.5", "3")
check(a <= 2 and b >= F(5, 2), f"PLANTED two roots behind a max: both kept ({float(a)}, {float(b)})")
# a touching root (g >= 0, zero at 2): no sign change anywhere — its existence is not shown, so no value is given
check(root("(_root_x - 2)*(_root_x - 2)", "0", "3") == REFUSED,
      "a root that only touches zero is REFUSED at a point (no sign change: existence not shown)")
# NO ROOT AT ALL — a jump across zero, poles with a sign change, a capped pole: every one refused, none enclosed
for g_, lo_, hi_ in [("ifpos(_root_x - 1, _root_x + 5, _root_x - 3)", "0", "3"), ("1/(_root_x - 1)", "0", "2"),
                     ("1/(_root_x - 1) + 0.5", "0", "3"), ("tan(_root_x)", "1.5", "1.6"),
                     ("min(1/(_root_x - 1), 5) - 6", "0", "3")]:
    check(root(g_, lo_, hi_) == REFUSED, f"PLANTED no root: {g_} on [{lo_}, {hi_}] gives no value (not an enclosure of nothing)")

# PLANTED — poles: monotony clears a piece only where the derivative is READ (a pole inside: it is not), so a root
# beside a pole is kept and the pole's neighbourhood is never cleared as "monotone"
for g_, lo_, hi_, x_ in [("1/(_root_x - 1) - 0.5", "0", "5", 3.0), ("(_root_x - 3)/(_root_x - 1)", "0", "5", 3.0),
                         ("tan(_root_x)", "1.5", "4", 3.141592653589793),
                         ("max(_root_x, 0)/(_root_x - 2) + 3", "0.5", "5", 1.5)]:
    a, b = root(g_, lo_, hi_)
    check((a, b) == REFUSED or float(a) <= x_ <= float(b),
          f"PLANTED pole: {g_} on [{lo_}, {hi_}] keeps its root {x_} or gives no value — never an enclosure without it "
          f"({(a, b) if (a, b) == REFUSED else (float(a), float(b))})")
a, b = root("ln(_root_x) + 1", "0.01", "3")
check(b - a < F(1, 10 ** 9) and abs(float(a) - 0.36787944117144233) < 1e-9, f"ln(x) = -1: tight at 1/e ({float(a)})")


def brick(law, search, req):
    return {"stand": "ztl-stand/1",
            "quantities": {"c": {"role": "given", "value": "3"}, "x": {"role": "derived", "search": search}},
            "laws": [{"zfl": law, "source": "test"}],
            "requirements": [dict(req, quantity="x", why="test")]}


# 4. the stand: a violated bound on an implicit quantity with max in its law is REFUTED at a point; a true one EARNED
r1 = S.run(brick("x*x*x + max(x, 1) == c", ["0", "3"], {"op": "<=", "value": "1.1"}))
r2 = S.run(brick("x*x*x + max(x, 1) == c", ["0", "3"], {"op": "<=", "value": "1.3"}))
check(r1.get("verdict") == "REFUTED" and r2.get("verdict") == "EARNED",
      f"stand: x^3 + max(x, 1) = 3 — x <= 1.1 REFUTED, x <= 1.3 EARNED ({r1.get('verdict')}, {r2.get('verdict')})")
# PLANTED — two roots (1 and 2), a bound between them: never EARNED (the root 2 violates it)
r3 = S.run(brick("(x - 1)*(x - 2) == c - 3", ["0", "3"], {"op": "<=", "value": "1.5"}))
check(r3.get("verdict") != "EARNED", f"PLANTED stand: roots 1 and 2, x <= 1.5 is not EARNED ({r3.get('verdict')})")
# PLANTED — a branch that JUMPS across zero with no root: no root may be invented from the sign change
r4 = S.run(brick("if(x > 1, x + 5, x - 3) == c - 3", ["0", "3"], {"op": "<=", "value": "2"}))
# THE ROOT MUST EXIST (the curator, 2026-11-12: "OPEN — honesty above all"). Found by this planted case: the kernel
# proves an ENCLOSURE of the roots and the stand read it as the quantity's range — this law, with no root at all, was
# EARNED with x ~ 1, and REFUTED "at a concrete point" for x >= 2. Now the stand shows a root exists (a strict sign
# change, the law continuous between: checker.implicit_exists) or the design is OPEN.
check(r4.get("verdict") == "OPEN", f"PLANTED stand: a jump from -2 to 6 with no root, x <= 2 -> OPEN ({r4.get('verdict')})")
r5 = S.run(brick("if(x > 1, x + 5, x - 3) == c - 3", ["0", "3"], {"op": ">=", "value": "2"}))
r6 = S.run(brick("if(x > 1, x + 5, x - 3) == c - 3", ["0", "3"], {"op": "within", "value": ["0.9", "1.1"]}))
check(r5.get("verdict") == "OPEN" and r6.get("verdict") == "OPEN",
      f"PLANTED stand: the same law is neither REFUTED at a point that has no root nor EARNED around the jump "
      f"({r5.get('verdict')}, {r6.get('verdict')})")
r7 = S.run(brick("1/(x - 1) == c - 3", ["0", "2"], {"op": "<=", "value": "1.5"}))
check(r7.get("verdict") == "OPEN", f"PLANTED stand: a pole with a sign change and no root -> OPEN ({r7.get('verdict')})")
# two roots (x^2 = c): the root set exists (a sign change between an end and the middle) and both branches are judged
r8 = S.run(brick("x*x == c", ["-3", "3"], {"op": "within", "value": ["-1.8", "1.8"]}))
r9 = S.run(brick("x*x == c", ["-3", "3"], {"op": "<=", "value": "1"}))
check(r8.get("verdict") == "EARNED" and r9.get("verdict") != "EARNED",
      f"stand: x^2 = 3 on [-3, 3] — within [-1.8, 1.8] EARNED (both roots), x <= 1 not EARNED ({r8.get('verdict')}, {r9.get('verdict')})")
KNOWN = []

# ---- OPERATIONAL vs FORMAL (2026-11-12, the curator: "we keep operationality"; ZTL v2.1.6 §25 — "the q such that the
# law holds" is a definite description: it denotes only a grounded satisfier; ZRootPar.par_root builds one from a sign
# change AND a slope bounded away from zero). The intermediate value theorem alone says "exists" and builds nothing.
def level(g, lo, hi, zlo, zhi):
    node = ast.parse(f"implicit(_root_x, {g}, {lo}, {hi})", mode="eval").body
    return C.implicit_exists(node, {}, F(zlo), F(zhi))[0]


check(level("_root_x*_root_x*_root_x + _root_x - 3", "0", "3", "1.2", "1.3") == C.OPERATIONAL,
      "x^3 + x = 3: a sign change with a strict slope — the root is built (OPERATIONAL)")
check(level("(_root_x*_root_x - 2)*(_root_x*_root_x - 2)*(_root_x*_root_x - 2)", "0", "3", "1.4", "1.5") == C.FORMAL,
      "PLANTED (x^2 - 2)^3 = 0: the sign changes at sqrt 2 and the law is continuous, but the slope is 0 at the root — "
      "FORMAL only, the root is not built")
check(level("ifpos(_root_x - 1, _root_x + 5, _root_x - 3)", "0", "3", "0.9", "1.1") == C.NOT_SHOWN,
      "a jump across zero: NOT_SHOWN (not even formally)")
check(root("(_root_x*_root_x - 2)*(_root_x*_root_x - 2)*(_root_x*_root_x - 2)", "0", "3") == REFUSED,
      "a formally existing root gives NO VALUE at a point (no witness, no REFUTED, from an object that is not built)")
r10 = S.run(brick("(x*x - 2)*(x*x - 2)*(x*x - 2) == c - 3", ["0", "3"], {"op": "<=", "value": "2"}))
w10 = str((r10.get("designs") or [{}])[0].get("why") or r10.get("why"))
check(r10.get("verdict") == "OPEN" and "FORMALLY" in w10 and "ZTL's judge" in w10 and "to be verified" in w10,
      f"stand: the formal root is OPEN by ZTL's judge, the dirty atom named, the formal existence said ({r10.get('verdict')}; {w10[:140]})")
h2 = str((r2.get("how") or {}).get("x"))
check("ZRootPar.par_root" in h2 and "ZTL's judge on the claim about the quantity: EARNED" in h2,
      f"stand: an EARNED implicit quantity says its root was BUILT, by which rule, and that the judge granted it ({h2[-150:]})")
# over a BOX of a parameter: the root is built on every part of a partition, or it is not built
def level_box(g, lo, hi, zlo, zhi, p_lo, p_hi):
    node = ast.parse(f"implicit(_root_x, {g}, {lo}, {hi})", mode="eval").body
    return C.implicit_exists(node, {"p": (F(p_lo), F(p_hi))}, F(zlo), F(zhi))[0]


check(level_box("_root_x*_root_x*_root_x + _root_x - p", "0", "5", "0.6", "1.3", 1, 3) == C.OPERATIONAL,
      "x^3 + x = p for p in [1, 3]: built for every p (a strict slope on each part's own bracket)")
check(level_box("_root_x*_root_x - p", "-3", "3", "-2", "2", 1, 4) == C.OPERATIONAL,
      "x^2 = p for p in [1, 4], TWO roots: one of them is built (the bracket is aimed at ONE root, not at the hull of "
      "both — aimed at the hull, the slope cannot be strict and the law came out OPEN, 2026-11-13)")
check(level_box("(_root_x - p)*(_root_x - p)*(_root_x - p)", "0", "5", "1", "2", 1, 2) == C.FORMAL,
      "PLANTED (x - p)^3 = 0 for p in [1, 2]: a sign change for every p, the slope 0 at the root — FORMAL, never built")
# a branch whose condition cancels (a*(x/a) - x is identically 0): decided by the mean value form, so the slope reads
gb = ast.parse("ifpos(1 - (a*(x/a) - x), x*x, 0 - 100)", mode="eval").body
check(C._sgn(C._dg(gb, "x"), {"x": (F(3), F(5)), "a": (F(7), F(7))}) == 1
      and C._sgn(C._dg(ast.parse("ifpos(x - 4, x, 0 - x)", mode="eval").body, "x"), {"x": (F(3), F(5))}) is None,
      "a branch whose condition cancels is decided by the mean value form; a real switch inside the box stays undecided")

# ZTL'S KERNEL BUILDS THE ROOT TOO (2026-11-13: zimplicit.check_exists, the same rule checked on a brought cover)
# The section needs a ZTL that has check_exists; on an older clone it is skipped, and said (the stand itself then
# uses the checker's route alone — the fourth check below plants exactly that).
import zimplicit as _ZI                                # noqa: E402

if not hasattr(_ZI, "check_exists"):
    print("SKIPPED: this ZTL has no zimplicit.check_exists — the kernel's existence route is not tested here")
else:
    def box_brick(law, search, req):
        b = brick(law, search, req)
        b["quantities"]["c"] = {"role": "given", "range": ["2.9", "3.1"]}
        return b


    def how_x(r):
        return str((r.get("how") or {}).get("x"))


    rk1 = S.run(box_brick("x*x*x + x == c", ["0", "3"], {"op": "<=", "value": "1.5"}))
    check(rk1.get("verdict") == "EARNED" and "ZTL's kernel; the checker built it by its own route too" in how_x(rk1)
          and "_root_" not in how_x(rk1),
          f"stand: a smooth law over a box — the root is built by ZTL's kernel AND by the checker, and the note says so "
          f"({rk1.get('verdict')}: {how_x(rk1)[-200:]})")
    rk2 = S.run(box_brick("x*x*x + max(x, 1) == c", ["0", "3"], {"op": "<=", "value": "1.5"}))
    check(rk2.get("verdict") == "EARNED" and "the checker's route; ZTL's kernel did not build it" in how_x(rk2),
          f"stand: a law with max — the kernel has no slope to read, the checker builds the root, and the note says who "
          f"({rk2.get('verdict')}: {how_x(rk2)[-200:]})")
    rk3 = S.run(box_brick("if(x > 1, x + 5, x - 3) == c - 3", ["0", "3"], {"op": "<=", "value": "2"}))
    check(rk3.get("verdict") == "OPEN" and "s kernel: the search built no existence certificate" in str(rk3),
          f"PLANTED a jump over a box: neither the kernel nor the checker builds a root — OPEN ({rk3.get('verdict')})")
    # an OLDER ZTL (no check_exists): the stand says so and the checker's route still earns the atom
    _keep = _ZI.check_exists
    del _ZI.check_exists
    try:
        rk4 = S.run(box_brick("x*x*x + x == c", ["0", "3"], {"op": "<=", "value": "1.5"}))
    finally:
        _ZI.check_exists = _keep
    check(rk4.get("verdict") == "EARNED" and "has no existence check" in how_x(rk4),
          f"stand on an older ZTL (no check_exists): the checker's route alone, said in the note ({rk4.get('verdict')})")
    # the kernel builds where the checker's own route does not: then the atom is the kernel's, and the note says so
    _keep_c = C.implicit_exists
    C.implicit_exists = lambda *a, **k: (C.NOT_SHOWN, "the checker was silenced for this test")
    try:
        rk5 = S.run(box_brick("x*x*x + x == c", ["0", "3"], {"op": "<=", "value": "1.5"}))
        rk6 = S.run(box_brick("if(x > 1, x + 5, x - 3) == c - 3", ["0", "3"], {"op": "<=", "value": "2"}))
    finally:
        C.implicit_exists = _keep_c
    check(rk5.get("verdict") == "EARNED" and "ZTL's kernel; the checker alone did not build it" in how_x(rk5)
          and rk6.get("verdict") == "OPEN",
          f"stand with the checker's existence route silenced: the kernel alone builds the smooth root (EARNED) and "
          f"builds nothing on the jump (OPEN) ({rk5.get('verdict')}, {rk6.get('verdict')})")

# ---- THE JUDGE FIRST (2026-11-14): where the floats say the nominal point holds, ZTL's judge is asked before the
# checker's exact solution of that point (dear with an implicit law), and the point is read exactly only if the judge
# did not show the design. The floats only ORDER the two: the verdict and everything said must be the same either way.
from ustand import fwitness as FW, mode as MODE     # noqa: E402


def run_counting(b, hint=None):
    """The stand's answer, and how many exact solutions the checker made; hint: what the floats are MADE to say."""
    calls, real_solve, real_hint = [0], C.solve_at, FW.holds_at_centre

    def counted(*a, **k):
        calls[0] += 1
        return real_solve(*a, **k)
    C.solve_at = counted
    if hint is not None:
        FW.holds_at_centre = lambda *a, **k: hint[0]
    try:
        out = S.run(b)
    finally:
        C.solve_at, FW.holds_at_centre = real_solve, real_hint
    out.pop("seconds", None)
    return out, calls[0]


earn = brick("x*x*x + max(x, 1) == c", ["0", "3"], {"op": "<=", "value": "1.3"})
fail = brick("x*x*x + max(x, 1) == c", ["0", "3"], {"op": "<=", "value": "1.1"})
e_new, e_calls = run_counting(earn)
e_old, e_old_calls = run_counting(earn, hint=[None])          # the floats silent: the order as it was
check(e_new.get("verdict") == "EARNED" and e_calls == 0 and e_old_calls >= 1 and e_new == e_old,
      f"judge first: an EARNED design with an implicit law makes NO exact solution of the nominal point ({e_calls}; "
      f"in the old order {e_old_calls}), and the stand's whole answer is the same ({e_new.get('verdict')}, "
      f"same: {e_new == e_old})")
f_new, f_calls = run_counting(fail)                           # the floats see the failure: the checker first, as before
f_old, _ = run_counting(fail, hint=[None])
f_lie, f_lie_calls = run_counting(fail, hint=[True])          # PLANTED: the floats say "holds" of a point that fails
check(f_new.get("verdict") == "REFUTED" and f_new == f_old and f_new == f_lie and f_lie_calls >= 1
      and f_lie.get("failed_at_nominal") == 1 and f_lie.get("judged") == 0,
      f"judge first, PLANTED floats that call a failing point fine: still REFUTED at the nominal point, read exactly "
      f"after the judge; the answer is the same in all three orders ({f_new.get('verdict')}, {f_lie.get('verdict')}, "
      f"same: {f_new == f_old}, {f_new == f_lie}; failed_at_nominal {f_lie.get('failed_at_nominal')})")
two_new, _ = run_counting(brick("(x - 1)*(x - 2) == c - 3", ["0", "3"], {"op": "<=", "value": "1.5"}))
two_old, _ = run_counting(brick("(x - 1)*(x - 2) == c - 3", ["0", "3"], {"op": "<=", "value": "1.5"}), hint=[None])
check(two_new.get("verdict") != "EARNED" and two_new == two_old,
      f"judge first, PLANTED two roots with the bound between them (the floats find the first root only and say "
      f"'holds'): not EARNED, the same answer as in the old order ({two_new.get('verdict')}, same: {two_new == two_old})")
MODE.DEV[0] = True
try:
    d_out, d_calls = run_counting(earn)
finally:
    MODE.DEV[0] = False
check(d_out.get("verdict") == "EARNED" and d_calls >= 1,
      f"judge first is WORK mode only: in dev mode the checker still solves the nominal point ({d_calls} solution(s))")

if FAILS:
    print(f"IMPLICIT POINT RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"IMPLICIT POINT GREEN ({CHECKS} checks)" + (f"; KNOWN DEFECTS {len(KNOWN)}: {KNOWN}" if KNOWN else ""))
