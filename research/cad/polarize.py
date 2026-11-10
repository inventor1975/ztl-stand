# -*- coding: utf-8 -*-
"""
Level 3a: a CROSS quantity certified by polarization from two compliance brackets (2026-11-10, PLAN-level3.md).

For loads f, g on the same part, with solutions u (for f) and w (for g): l = a(u, w) = g(u) = f(w), and

    l = [ C(f + s g) - C(f - s g) ] / (4 s)

so from proved brackets C(f+sg) in [P_lo, P_hi] and C(f-sg) in [M_lo, M_hi]:

    l in [ (P_lo - M_hi) / 4s , (P_hi - M_lo) / 4s ]          (exact rational arithmetic on the binary64 inputs)

and dividing by |g| gives the work-conjugate displacement of g's application under f.

    python3 -I polarize.py plus.json minus.json --s 1 --g=gx,gy,gz      (--g= : a leading minus is not an option)
"""
import argparse
import json
import math
from fractions import Fraction as Fr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plus")
    ap.add_argument("minus")
    ap.add_argument("--s", default="1")
    ap.add_argument("--g", required=True, help="the force g of the test load, 'gx,gy,gz'")
    a = ap.parse_args()
    P = json.load(open(a.plus))
    M = json.load(open(a.minus))
    s = Fr(a.s)
    plo, phi = (Fr(x) for x in P["compliance"])
    mlo, mhi = (Fr(x) for x in M["compliance"])
    lo, hi = (plo - mhi) / (4 * s), (phi - mlo) / (4 * s)
    gn = math.sqrt(sum(float(x) ** 2 for x in a.g.split(",")))
    print(f"C(f+sg) in [{float(plo):.6f}, {float(phi):.6f}]   C(f-sg) in [{float(mlo):.6f}, {float(mhi):.6f}]")
    mid = abs((hi + lo) / 2)
    rel = f"{100 * float((hi - lo) / mid):.1f} % of the midpoint" if mid else "midpoint 0"
    print(f"l = a(u, w) in [{float(lo):.6f}, {float(hi):.6f}]   width {float(hi - lo):.3f} ({rel})")
    sign = "POSITIVE (proved)" if lo > 0 else "NEGATIVE (proved)" if hi < 0 else "OPEN"
    print(f"sign of l: {sign}")
    # the displacement of g's application point along g, under f (|g| in binary64; rounding below the printed digits)
    print(f"displacement along g under f: [{float(lo) / gn:.5f}, {float(hi) / gn:.5f}] mm")
    print(json.dumps({"l": [float(lo), float(hi)], "s": str(s), "g": a.g, "sign": sign,
                      "plus": a.plus, "minus": a.minus}))


if __name__ == "__main__":
    main()
