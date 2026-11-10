# -*- coding: utf-8 -*-
"""ustand.cadstiff: the four outcomes of a stiffness requirement on a proved bracket. Run: python3 -m tests.test_cadstiff"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import cadstiff as CS          # noqa: E402

CHECKS, FAILS = 0, []


def check(cond, what):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(what)
        print(f"FAIL: {what}")


# a bracket [1.0, 1.1] mm at E = 110000, E in [105000, 115000]: over E, d in [0.9565, 1.1524]
kw = dict(d_lo=1.0, d_hi=1.1, E_deck=110000, E_range=(105000, 115000))
r = CS.judge(**kw, E_ground="earned", d_max=1.2)
check(r["verdicts"]["d_max"]["disposition"] == "EARNED", f"d <= 1.2, E earned: EARNED ({r['verdicts']})")
r = CS.judge(**kw, E_ground="earned", d_max=0.9)
check(r["verdicts"]["d_max"]["disposition"] == "REFUTED", f"d <= 0.9: REFUTED — too soft at every E ({r['verdicts']})")
r = CS.judge(**kw, E_ground="earned", d_max=1.05)
check(r["verdicts"]["d_max"]["disposition"] not in ("EARNED", "REFUTED"), f"d <= 1.05 inside the bracket: not decided ({r['verdicts']})")
r = CS.judge(**kw, E_ground="credit", d_max=1.2)
v = r["verdicts"]["d_max"]
check(v["disposition"] == "ON CREDIT" and v["polarity"] == "toward T" and v["next_check"] == ["document E"],
      f"E on credit: ON CREDIT toward T, check E ({v})")
check(abs(r["d_bracket_over_E"][0] - 1.0 * 110000 / 115000) < 1e-12 and abs(r["d_bracket_over_E"][1] - 1.1 * 110000 / 105000) < 1e-12,
      "the bracket over E scales as 1/E")
try:
    CS.judge(d_lo=2, d_hi=1, E_deck=1, E_range=(1, 1))
    check(False, "a reversed bracket must be refused")
except ValueError:
    check(True, "a reversed bracket is refused")

if FAILS:
    print(f"CADSTIFF RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"CADSTIFF GREEN ({CHECKS} checks)")
