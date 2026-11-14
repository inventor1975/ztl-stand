# -*- coding: utf-8 -*-
"""THE STRUCTURE SECTION OF A BRICK (BRICKS.md 7j, 2026-11-14): `assembly` inside a brick - the stand chooses from a
catalogue THROUGH a structure whose parts act on one another, in every mode, with the objective; and the rule for a
refutation that leans on a proved range. Hand-solved models, no task data. Run: python3 tests/test_assembly_brick.py"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import bricks as B, stand as S   # noqa: E402

CHECKS, FAILS = 0, []


def check(c, what):
    global CHECKS
    CHECKS += 1
    if not c:
        FAILS.append(what)
        print("FAIL:", what)


def names(r):
    return {k: v.get("name") for k, v in (r.get("design") or {}).items()}


# ---- 1. ONE PANEL, the deck chosen for a drift limit. Hand: flow q = P / width = 24 / 4 = 6 kN/m whatever the deck;
# drift u = q / G' x height + chord stretch = 6 / G' x 2 + 24 x 4 / 4000: G' 12 -> 1.006 m, 24 -> 0.506 m, 48 -> 0.256 m
one = {"stand": "ztl-stand/1",
       "quantities": {"P": {"role": "given", "value": "24", "unit": "kN", "ground": "load case"},
                      "EAt": {"role": "given", "value": "4000", "unit": "kN", "ground": "chord"},
                      "Lc": {"role": "given", "value": "4", "unit": "m", "ground": "drawing"}},
       "slots": {"DECK": {"from": ["decks"]}}, "laws": [],
       "assembly": {"length_unit": "m",
                    "nodes": {"bl": [0, 0], "br": [4, 0], "tr": [4, 2], "tl": [0, 2]},
                    "fixed": [["bl", "X"], ["bl", "Y"], ["br", "X"], ["br", "Y"], ["tl", "Y"], ["tr", "Y"]],
                    "elements": [{"id": "p", "type": "panel", "nodes": ["bl", "br", "tr", "tl"], "g": "DECK.G"},
                                 {"id": "top", "type": "bar", "a": "tl", "b": "tr", "k": "EAt/Lc"}],
                    "loads": [["tr", "X", "P"]],
                    "outputs": {"q": {"flow": "p", "unit": "kN/m"}, "u": {"u": ["tr", "X"], "unit": "mm"}}},
       "requirements": [{"quantity": "u", "op": "<=", "value": "600", "why": "drift limit"},
                        {"quantity": "q", "op": "<=", "value": "DECK.cap", "why": "panel capacity"}],
       "objective": {"minimize": "DECK.price"},
       "catalog": {"decks": {"ground": "catalogue",
                             "items": [{"name": "D12", "G": "12", "cap": "8", "price": "10"},
                                       {"name": "D24", "G": "24", "cap": "8", "price": "15"},
                                       {"name": "D48", "G": "48", "cap": "8", "price": "22"}],
                             "fields": {"G": {"unit": "kN/m"}, "cap": {"unit": "kN/m"}, "price": {"unit": "USD"}}}}}
r = S.run(one)
check(r["verdict"] == "EARNED" and names(r) == {"DECK": "D24"} and r["objective"]["optimal"] is True
      and r["guaranteed"] == {"u_req": ["506", "506"], "q_req": ["6", "6"]}
      and [d["verdict"] for d in r["designs"]] == ["REFUTED", "EARNED"] and r["designs"][0]["by_at_witness"] == "406",
      f"one panel: the stand solves the structure for each deck, refutes D12 by 406 mm, earns D24 at exactly 506 mm and 6 kN/m ({r.get('verdict')}, {r.get('guaranteed')})")
check(r["units"].startswith("checked"), f"the section's units are checked with the brick's ({r.get('units')})")

# ---- 2. TWO ZONES UNDER ONE COLLECTOR: the load splits by stiffness, so one zone's demand depends on the OTHER's
# choice. Hand (rigid collector): qA + qB = P / 4, qA / qB = GA / GB. P = 40: (soft, soft) 5 | 5 > 4; (soft, mid)
# 3.33 | 6.67 > 6; (mid, mid) 5 | 5 <= 6 -> the cheapest pair that holds, 28.
decks = [{"name": "soft", "G": "10", "cap": "4", "price": "10"}, {"name": "mid", "G": "20", "cap": "6", "price": "14"},
         {"name": "stiff", "G": "40", "cap": "9", "price": "20"}]
reqs2 = [{"quantity": "qA", "op": "<=", "value": "ZA.cap", "why": "capacity, zone A"},
         {"quantity": "qB", "op": "<=", "value": "ZB.cap", "why": "capacity, zone B"}]
two = {"stand": "ztl-stand/1",
       "quantities": {"P": {"role": "given", "value": "40", "unit": "kN", "ground": "load case"},
                      "kc": {"role": "given", "value": "1000000000", "unit": "kN/m", "ground": "collector, nearly rigid"}},
       "slots": {"ZA": {"from": ["decks"]}, "ZB": {"from": ["decks"]}}, "laws": [],
       "assembly": {"length_unit": "m",
                    "nodes": {"a0": [0, 0], "a1": [4, 0], "a2": [8, 0], "t0": [0, 2], "t1": [4, 2], "t2": [8, 2]},
                    "fixed": [["a0", "X"], ["a0", "Y"], ["a1", "X"], ["a1", "Y"], ["a2", "X"], ["a2", "Y"],
                              ["t0", "Y"], ["t1", "Y"], ["t2", "Y"]],
                    "elements": [{"id": "pA", "type": "panel", "nodes": ["a0", "a1", "t1", "t0"], "g": "ZA.G"},
                                 {"id": "pB", "type": "panel", "nodes": ["a1", "a2", "t2", "t1"], "g": "ZB.G"},
                                 {"id": "c1", "type": "bar", "a": "t0", "b": "t1", "k": "kc"},
                                 {"id": "c2", "type": "bar", "a": "t1", "b": "t2", "k": "kc"}],
                    "loads": [["t1", "X", "P"]],
                    "outputs": {"qA": {"flow": "pA", "unit": "kN/m"}, "qB": {"flow": "pB", "unit": "kN/m"}}},
       "requirements": copy.deepcopy(reqs2), "objective": {"minimize": "ZA.price + ZB.price"}, "report": "all",
       "catalog": {"decks": {"ground": "catalogue", "items": decks,
                             "fields": {"G": {"unit": "kN/m"}, "cap": {"unit": "kN/m"}, "price": {"unit": "USD"}}}}}
r = S.run(two)
by = {tuple(d["design"].split("name=")[i].split(",")[0] for i in (1, 2)): d for d in r["designs"]}
check(r["verdict"] == "EARNED" and names(r) == {"ZA": "mid", "ZB": "mid"} and r["objective"]["value"] == "28" and r["objective"]["optimal"] is True,
      f"two coupled zones: the cheapest pair that holds is (mid, mid) at 28, proved optimal ({names(r)}, {r.get('objective')})")
check(by[("soft", "mid")]["verdict"] == "REFUTED" and by[("soft", "mid")]["fails"] == "capacity, zone B"
      and by[("soft", "stiff")]["verdict"] == "EARNED" and by[("mid", "mid")]["guaranteed"] == {"qA_req": ["5", "5"], "qB_req": ["5", "5"]},
      "the coupling is real: a soft zone A sends zone B past a mid deck's capacity (6.67 > 6) and is carried by a stiff one")

# ---- 3. MODES: two load cases, the design must hold in both. Seismic P = 56 -> 14 kN/m in all: (mid, mid) 7 | 7 > 6,
# (mid, stiff) 4.67 | 9.33 > 9, (stiff, stiff) 7 | 7 <= 9 -> 40.
modes = copy.deepcopy(two)
modes.pop("report")
modes["requirements"] = []
modes["modes"] = {"wind": {"quantities": {"P": {"value": "40"}}, "requirements": copy.deepcopy(reqs2)},
                  "seismic": {"quantities": {"P": {"value": "56"}}, "requirements": copy.deepcopy(reqs2)}}
r = S.run(modes)
check(r["verdict"] == "EARNED" and names(r) == {"ZA": "stiff", "ZB": "stiff"} and r["objective"]["value"] == "40"
      and r["per_mode"]["seismic"]["guaranteed"] == {"qA_req": ["7", "7"], "qB_req": ["7", "7"]}
      and r["per_mode"]["wind"]["guaranteed"] == {"qA_req": ["5", "5"], "qB_req": ["5", "5"]},
      f"load cases as modes: the structure is solved in each, (stiff, stiff) is the cheapest that holds in both ({names(r)}, {r.get('per_mode', {}).keys()})")

# ---- 4. A STRUCTURE ABOVE THE EXACT SIZE: its results are PROVED RANGES (one value, about 1e-25 wide), and a
# refutation that leans on one must hold over the WHOLE range.


def grid(limit_mm, items, nx=8, ny=6):
    a = b = 6
    el = [{"id": f"p{i}_{j}", "type": "panel", "nodes": [f"n{i}_{j}", f"n{i+1}_{j}", f"n{i+1}_{j+1}", f"n{i}_{j+1}"], "g": "DECK.G"}
          for i in range(nx) for j in range(ny)]
    el += [{"id": f"bx{i}_{j}", "type": "bar", "a": f"n{i}_{j}", "b": f"n{i+1}_{j}", "k": "kbar"} for j in range(ny + 1) for i in range(nx)]
    el += [{"id": f"by{i}_{j}", "type": "bar", "a": f"n{i}_{j}", "b": f"n{i}_{j+1}", "k": "kbar"} for i in range(nx + 1) for j in range(ny)]
    el += [{"id": f"s{d}{i}_{j}", "type": "spring", "node": f"n{i}_{j}", "dir": d, "k": "kfr"} for j in (0, ny) for i in (0, nx) for d in "XY"]
    return {"stand": "ztl-stand/1",
            "quantities": {"kbar": {"role": "given", "value": "700", "unit": "kN/m", "ground": "members"},
                           "kfr": {"role": "given", "value": "9", "unit": "kN/m", "ground": "frames"},
                           "w": {"role": "given", "value": "2", "unit": "kN", "ground": "load case"}},
            "slots": {"DECK": {"from": ["decks"]}}, "laws": [],
            "assembly": {"length_unit": "m", "nodes": {f"n{i}_{j}": [i * a, j * b] for i in range(nx + 1) for j in range(ny + 1)},
                         "fixed": [], "elements": el, "loads": [[f"n{i}_{ny}", "X", "w"] for i in range(nx + 1)],
                         "outputs": {"umid": {"u": [f"n{nx // 2}_{ny}", "X"], "unit": "mm"}}},
            "requirements": [{"quantity": "umid", "op": "<=", "value": limit_mm, "why": "drift limit"}],
            "objective": {"minimize": "DECK.price"},
            "catalog": {"decks": {"ground": "catalogue", "items": items, "fields": {"G": {"unit": "kN/m"}, "price": {"unit": "USD"}}}}}


three = [{"name": "D12", "G": "12", "price": "10"}, {"name": "D24", "G": "24", "price": "15"}, {"name": "D48", "G": "48", "price": "22"}]
lb = B.load(grid("1e9", three))
d12 = next(iter(S.designs(lb)))
fx, bx, _dv, _gr = S.frame(lb, d12)
check("umid" in bx and "umid" not in fx and 0 < bx["umid"][1] - bx["umid"][0] < 1e-20 and S._enclosed(lb, bx) == ["umid"],
      f"126 unknowns: the result is a proved range, not a point, and the stand knows it is an enclosure (width {float(bx['umid'][1] - bx['umid'][0]):.1e})")
r = S.run(grid("760", three))          # D12 780.36 mm, D24 743.69 mm
check(r["verdict"] == "EARNED" and names(r) == {"DECK": "D24"} and r["designs"][0]["verdict"] == "REFUTED" and r["objective"]["optimal"] is True,
      f"a limit clear of every range: the refutation is confirmed and stands, the next deck is earned and optimal ({[d['verdict'] for d in r['designs']]})")
mid = (bx["umid"][0] + bx["umid"][1]) / 2 * 1000        # mm, strictly inside D12's proved range
edge = grid(f"{mid.numerator}/{mid.denominator}", three)
r = S.run(edge)
check(r["verdict"] == "EARNED" and names(r) == {"DECK": "D24"} and r["designs"][0]["verdict"] == "OPEN"
      and "does not separate" in r["designs"][0]["why"] and r["objective"]["optimal"] is False and "undecided" in r["objective"]["note"],
      f"THE KNIFE EDGE - the limit inside D12's proved range: D12 is OPEN, not refuted, and the dearer deck is NOT called optimal ({r['designs'][0]}, {r['objective']})")
keep = S._refutation_stands
S._refutation_stands = lambda *a, **k: True            # the rule switched off: what the stand said without it
r_off = S.run(edge)
S._refutation_stands = keep
check(r_off["designs"][0]["verdict"] == "REFUTED" and r_off["objective"]["optimal"] is True,
      "PLANTED the rule switched off: the same brick refutes D12 at an end of its range and calls the dearer deck optimal - the fault the rule closes")
r = S.run(grid(f"{mid.numerator}/{mid.denominator}", three[:1]))
check(r["verdict"] == "OPEN", f"a knife-edge design alone: OPEN, never REFUTED ({r.get('verdict')}, {r.get('why')})")
r = S.run(grid("700", three))
check(r["verdict"] == "REFUTED" and [d["verdict"] for d in r["designs"]] == ["REFUTED"] * 3,
      f"a limit below every range: every design refuted, each confirmed over its range ({r.get('verdict')})")

# ---- 5. REFUSALS, each by name
for word, edit in (("a bare number", lambda x: x["assembly"]["elements"][2].update(k="1000")),
                   ("a flow is", lambda x: x["assembly"]["outputs"]["qA"].update(unit="mm")),
                   ("has no exact value", lambda x: x["quantities"]["P"].update(tolerance="0.1")),
                   ("mechanism", lambda x: x["assembly"].update(fixed=[])),
                   ("a quantity of that name exists", lambda x: x["quantities"].update(qA={"role": "given", "value": "1", "unit": "kN/m"})),
                   ("a mode overrides what the world gives", lambda x: x.update(modes={"m": {"quantities": {"qA": {"value": "1"}}, "requirements": []}}))):
    bad = copy.deepcopy(two)
    edit(bad)
    r = S.run(bad)
    check(r["verdict"] == "BRICK ERROR" and word in str(r.get("why")), f"PLANTED a wrong structure section is refused with its reason: {word!r} ({str(r.get('why'))[:110]})")

# ---- 6. A brick WITHOUT the section is judged as before (the rule does not touch it)
plain = {"stand": "ztl-stand/1",
         "quantities": {"y": {"role": "given", "range": ["0.9999999", "1.0000001"], "unit": "mm"}, "d": {"role": "derived", "unit": "mm"}},
         "slots": {}, "catalog": {}, "laws": [{"zfl": "d == y", "source": "itself"}],
         "requirements": [{"quantity": "d", "op": "<=", "value": "1", "why": "limit"}]}
r = S.run(plain)
check(r["verdict"] == "REFUTED", f"a TOLERANCE past its limit at one end is refuted as before: every point of a tolerance is a state of the world ({r.get('verdict')})")

if FAILS:
    print(f"ASSEMBLY BRICK RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"ASSEMBLY BRICK GREEN ({CHECKS} checks)")
