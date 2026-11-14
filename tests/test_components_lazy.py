# -*- coding: utf-8 -*-
"""A MODULE'S CONTRACT TIGHTENED ONLY WHERE THE SYSTEM NEEDS IT (BRICKS.md 7d, 2026-11-14). An output read through a
function or an implicit root has, at a point, the checker's proved INTERVAL: until 2026-11-14 the aid that tightens a
contract divided it as a number, failed silently, and such a module kept the stand's outer reading — a chiller's
rejected heat 297..728 kW where it is ~467 kW, and the system around it OPEN. Now the outer reading is where such an
output STARTS, and the system's judgement asks for one step more (within 1 %, 0.01 %, one millionth of the span past
the values attained) only while it is undecided. Small hand-checked modules, no task data.
Run: python3 tests/test_components_lazy.py"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import components as CM, stand as S   # noqa: E402

CHECKS, FAILS = 0, []


def check(c, what):
    global CHECKS
    CHECKS += 1
    if not c:
        FAILS.append(what)
        print("FAIL:", what)


# THE MODULES. A: y = exp(x) - exp(x)/2 - exp(x)/2 + 3, which is 3 for every x — but read term by term over x in
# [0, 1] it is [1.28, 4.72] (the stand's outer reading: exp(x) appears three times and does not cancel).
A = {"stand": "ztl-stand/1",
     "quantities": {"x": {"role": "given", "unit": "", "range": ["0", "1"], "ground": "test"},
                    "y": {"role": "derived", "unit": ""}},
     "laws": [{"zfl": "y == exp(x) - exp(x)/2 - exp(x)/2 + 3", "source": "test"}], "requirements": [],
     "interface": {"inputs": {"x": {"assume": ["0", "1"]}}, "outputs": ["y"]}}
# E: the same shape with exact values at its points (no function): y = 2x + 1
E = copy.deepcopy(A)
E["laws"] = [{"zfl": "y == 3*x - x + 1", "source": "test"}]


def B(assume, arriving=False):
    """downstream: z = 2u, proved for u in `assume` — as ONE band (its guarantee is then for the whole band, whatever
    arrives), or, with arriving, on the range that arrives itself"""
    return {"stand": "ztl-stand/1",
            "quantities": {"u": {"role": "given", "unit": "", "range": list(assume), "ground": "test"},
                           "z": {"role": "derived", "unit": ""}},
            "laws": [{"zfl": "z == 2*u", "source": "test"}], "requirements": [],
            "interface": {"inputs": {"u": dict({"assume": list(assume)}, **({"bands": "arriving"} if arriving else {}))},
                          "outputs": ["z"]}}


def system(assume, limit, first=A, arriving=False):
    return {"stand": "ztl-stand/1",
            "components": {"A": {"brick": copy.deepcopy(first)}, "B": {"brick": B(assume, arriving)}},
            "connect": {"A.x": "x0", "B.u": "A.y"},
            "quantities": {"x0": {"role": "given", "unit": "", "range": ["0", "1"], "ground": "test"},
                           "w": {"role": "derived", "unit": ""}},
            "laws": [{"zfl": "w == B.z"}],
            "requirements": [{"quantity": "w", "op": "<=", "value": limit, "why": "test"}]}


def run(b):
    """the stand's answer and how many bounds were proved on demand, per margin"""
    asked, real = [], CM._tighten

    def counted(sub, base, n, outer, attained, tries=None):
        if tries and len(tries) == 1 and tries[0] in CM.LAZY_STEPS:
            # (the remainder of the output's affine form, zres_y, takes the same steps: counted as the output's)
            asked.append((n[len("zres_"):] if n.startswith("zres_") else n, CM.LAZY_STEPS.index(tries[0]) + 1))
        return real(sub, base, n, outer, attained, tries=tries)
    CM._tighten = counted
    try:
        out = S.run(b)
    finally:
        CM._tighten = real
    out.pop("seconds", None)
    return out, asked


def fl(pair):
    return [float(eval(str(x).split(" ")[0].replace("~", ""), {"__builtins__": {}})) for x in pair]


# 1. the contract alone: the function module starts at its outer reading; the exact one is tight at once, as before
_i, _o, rows = CM.contract(A, ".")
got = rows[0][1]
lo, hi = (float(v) for v in got["outputs"]["y"])
check(got["earned"] and 1.2 < lo < 1.3 and 4.7 < hi < 4.8 and "y" in (got.get("lazy") or {}),
      f"a module whose output is read through a function: its contract starts as the outer reading [1.28, 4.72] and can "
      f"be tightened ({lo:.4g}, {hi:.4g})")
_i, _o, rows = CM.contract(E, ".")
gote = rows[0][1]
check(gote["earned"] and [float(v) for v in gote["outputs"]["y"]] == [1.0, 3.0] and not gote.get("lazy"),
      f"a module with exact values at its points is tightened at once, as before: y = 2x + 1 in [1, 3] "
      f"({[float(v) for v in gote['outputs']['y']]})")
steps = [tuple(float(v) for v in CM._at_level(got, "y", k)) for k in (1, 2, 3)]
check(all(a <= 3 <= b for a, b in steps) and steps[0][1] - steps[0][0] > steps[1][1] - steps[1][0] >= steps[2][1] - steps[2][0]
      and abs(steps[0][0] - 2.97) < 1e-9 and abs(steps[0][1] - 3.03) < 1e-9,
      f"each step on demand is a proved range around the true value 3, narrower every time: {steps}")

# 2. the outer reading is enough: no bound is proved on demand
CM._CACHE.clear()
r, asked = run(system(["0", "5"], "10"))
check(r.get("verdict") == "EARNED" and asked == [] and "tightened_on_demand" not in r["components"]["A"],
      f"a system the outer reading earns (w <= 10, outer 9.44): EARNED with NO bound proved on demand "
      f"({r.get('verdict')}, {asked})")

# 3. the arriving range leaves the next module's assume: only that output takes a step, and the system is earned
CM._CACHE.clear()
r, asked = run(system(["2.5", "3.5"], "10"))
check(r.get("verdict") == "EARNED" and sorted(set(asked)) == [("y", 1)] and "y" in r["components"]["A"].get("tightened_on_demand", {})
      and r["components"]["B"]["inputs"]["u"]["inside"],
      f"the outer range [1.28, 4.72] leaves the next module's assume [2.5, 3.5]: its ONE step (within 1 %) brings "
      f"[2.97, 3.03] inside, EARNED — before 2026-11-14 this was OPEN ({r.get('verdict')}, {asked})")
r3 = r

# 4. the system's own requirement needs it (the next module follows what ARRIVES): one step, then two
CM._CACHE.clear()
r, asked = run(system(["0", "5"], "6.1", arriving=True))
check(r.get("verdict") == "EARNED" and sorted(set(asked)) == [("y", 1)] and fl(r["guaranteed"]["w"])[1] <= 6.1,
      f"w <= 6.1 against an outer 9.44: one step (w <= 6.06) earns it ({r.get('verdict')}, {asked}, "
      f"{r.get('guaranteed')})")
CM._CACHE.clear()
r, asked = run(system(["0", "5"], "6.001", arriving=True))
check(r.get("verdict") == "EARNED" and sorted(set(asked)) == [("y", 1), ("y", 2)],
      f"w <= 6.001: the step of 1 % (w <= 6.06) does not reach it, the step of 0.01 % (w <= 6.0006) does — two "
      f"steps, EARNED ({r.get('verdict')}, {sorted(set(asked))})")

# 5. PLANTED — the true value 6 is past the limit: never EARNED, and refuted where the proved range lies wholly past it
CM._CACHE.clear()
r, asked = run(system(["0", "5"], "5.9", arriving=True))
check(r.get("verdict") == "REFUTED" and "EVERY point" in str(r.get("why")),
      f"PLANTED w <= 5.9 where w is 6: not EARNED at any step; REFUTED once the proved range [5.94, 6.06] lies wholly "
      f"past the limit ({r.get('verdict')}: {str(r.get('why'))[:90]})")

# 6. what one system needed does not leak into another: the same system gives the same answer after a hungrier one ran
r_again, _ = run(system(["2.5", "3.5"], "10"))
check(json.dumps(r_again, sort_keys=True, default=str) == json.dumps(r3, sort_keys=True, default=str),
      "a system's answer does not depend on what an earlier system asked of the same module (the steps are kept per "
      "module, each system takes only the steps it needs)")

if FAILS:
    print(f"COMPONENTS LAZY RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"COMPONENTS LAZY GREEN ({CHECKS} checks)")
