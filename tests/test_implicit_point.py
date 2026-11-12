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


def root(g, lo, hi, env=None):
    node = ast.parse(f"implicit(_root_x, {g}, {lo}, {hi})", mode="eval").body
    return C._implicit_iv(node, {k: (F(v), F(v)) for k, v in (env or {}).items()})


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
# a touching root (g >= 0, zero at 2): dg changes sign there — never cleared by monotony
a, b = root("(_root_x - 2)*(_root_x - 2)", "0", "3")
check(a <= 2 <= b, f"PLANTED a double root is kept ({float(a)}, {float(b)})")

# PLANTED — poles: monotony clears a piece only where the derivative is READ (a pole inside: it is not), so a root
# beside a pole is kept and the pole's neighbourhood is never cleared as "monotone"
for g_, lo_, hi_, x_ in [("1/(_root_x - 1) - 0.5", "0", "5", 3.0), ("(_root_x - 3)/(_root_x - 1)", "0", "5", 3.0),
                         ("tan(_root_x)", "1.5", "4", 3.141592653589793),
                         ("max(_root_x, 0)/(_root_x - 2) + 3", "0.5", "5", 1.5)]:
    a, b = root(g_, lo_, hi_)
    check(float(a) <= x_ <= float(b), f"PLANTED pole: {g_} on [{lo_}, {hi_}] keeps its root {x_} ({float(a)}, {float(b)})")
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
# KNOWN DEFECT, found by this planted case 2026-11-12 (older than the change tested here: the same on the checker
# before it). The kernel proves an ENCLOSURE of the roots ("every root lies in a kept piece") and never that a root
# EXISTS; the stand reads the enclosure as the quantity's range. Around a jump no piece can be excluded, so the
# stand says EARNED with x ~ 1 for a law that has no root at all. BRICKS.md promises OPEN ("no root in search").
# Not counted green; reported to the curator (the stand's claim boundary — his word). When fixed, make it a check.
KNOWN = []
if r4.get("verdict") == "EARNED":
    KNOWN.append("a law that jumps across zero with no root is EARNED (existence of the root is not shown)")
    print("KNOWN DEFECT:", KNOWN[-1], "| guaranteed", r4.get("guaranteed"))
else:
    print("NOTE: the jump case is no longer EARNED — turn the KNOWN DEFECT into a check:", r4.get("verdict"))

if FAILS:
    print(f"IMPLICIT POINT RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"IMPLICIT POINT GREEN ({CHECKS} checks)" + (f"; KNOWN DEFECTS {len(KNOWN)}: {KNOWN}" if KNOWN else ""))
