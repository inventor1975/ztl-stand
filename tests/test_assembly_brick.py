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

# ---- 5b. THE SAME SECTION BY RULES ON A GRID: cells by box, bars along lines, loads spread, the largest over a zone
by_rules = copy.deepcopy(one)
by_rules["assembly"] = {"length_unit": "m", "grid": {"x": [0, 4], "y": [0, 2]},
                        "panels": [{"g": "DECK.G"}],
                        "bars": [{"along": "x", "lines": [2], "EA": "EAt"}],
                        "fixed": [{"at": [0, 0], "dir": "X"}, {"at": [0, 0], "dir": "Y"}, {"at": [4, 0], "dir": "X"},
                                  {"at": [4, 0], "dir": "Y"}, {"at": [0, 2], "dir": "Y"}, {"at": [4, 2], "dir": "Y"}],
                        "loads": [{"at": [4, 2], "dir": "X", "P": "P"}],
                        "outputs": {"q": {"what": "flow", "at": [2, 1], "unit": "kN/m"},
                                    "u": {"what": "max_u", "dir": "X", "unit": "mm"}}}
by_rules["quantities"].pop("Lc")
r = S.run(by_rules)
check(r["verdict"] == "EARNED" and names(r) == {"DECK": "D24"} and r["guaranteed"] == {"u_req": ["506", "506"], "q_req": ["6", "6"]},
      f"the one-panel brick stated by grid rules gives the element-by-element answer exactly: a bar is EA over its segment ({r.get('guaranteed')})")


def roof(seismic, drift):
    """a plan 48 x 36 on a 6-grid: end zones and a middle zone of deck, a hole, chords, frames as springs, two load cases"""
    reqs = lambda u: [{"quantity": "qEnd", "op": "<=", "value": "END.cap", "why": "end zone capacity"},      # noqa: E731
                      {"quantity": "qMid", "op": "<=", "value": "MID.cap", "why": "middle zone capacity"},
                      {"quantity": u, "op": "<=", "value": drift, "why": "drift limit"}]
    return {"stand": "ztl-stand/1",
            "quantities": {"EAc": {"role": "given", "value": "200000", "unit": "kN", "ground": "chords"},
                           "KF": {"role": "given", "value": "30", "unit": "kN/mm", "ground": "frames"},
                           "WX": {"role": "given", "value": "0", "unit": "kN", "ground": "load case"},
                           "WY": {"role": "given", "value": "0", "unit": "kN", "ground": "load case"},
                           "Aend": {"role": "given", "value": "864", "unit": "m^2"}, "Amid": {"role": "given", "value": "828", "unit": "m^2"}},
            "slots": {"END": {"from": ["decks"]}, "MID": {"from": ["decks"]}}, "laws": [],
            "assembly": {"length_unit": "m", "grid": {"x": {"from": 0, "to": 48, "step": 6}, "y": {"from": 0, "to": 36, "step": 6}},
                         "panels": [{"g": "MID.G"}, {"g": "END.G", "box": [0, 0, 12, 36]}, {"g": "END.G", "box": [36, 0, 48, 36]}],
                         "holes": [[18, 12, 24, 18]],
                         "bars": [{"along": "x", "lines": "all", "EA": "EAc"}, {"along": "y", "lines": "all", "EA": "EAc"}],
                         "springs": [{"at": [x, y], "dir": d, "k": "KF"} for x in (0, 48) for y in (0, 36) for d in "XY"],
                         "loads": [{"on": "area", "dir": "X", "total": "WX"}, {"on": "area", "dir": "Y", "total": "WY"}],
                         "outputs": {"qEnd": {"what": "max_flow", "box": [0, 0, 12, 36], "unit": "kN/m"},
                                     "qMid": {"what": "max_flow", "box": [12, 0, 36, 36], "unit": "kN/m"},
                                     "ux": {"what": "max_u", "dir": "X", "unit": "mm"}, "uy": {"what": "max_u", "dir": "Y", "unit": "mm"}}},
            "requirements": [],
            "modes": {"wind X": {"quantities": {"WX": {"value": "300"}}, "requirements": reqs("ux")},
                      "seismic Y": {"quantities": {"WY": {"value": seismic}}, "requirements": reqs("uy")}},
            "objective": {"minimize": "Aend*END.price + Amid*MID.price"},
            "catalog": {"decks": {"ground": "catalogue",
                                  "items": [{"name": "light", "G": "2000", "cap": "3", "price": "20"},
                                            {"name": "medium", "G": "4000", "cap": "5", "price": "24"},
                                            {"name": "heavy", "G": "9000", "cap": "9", "price": "31"}],
                                  "fields": {"G": {"unit": "kN/m"}, "cap": {"unit": "kN/m"}, "price": {"unit": "USD/m^2"}}}}}


rb = B.load(roof("400", "40"))
check(len(S.frame(rb, next(iter(S.designs(rb))))[1]) >= 4, "the grid roof is above the exact size: its results are enclosures")
r = S.run(roof("400", "40"))
got = {k: {q: float(str(v[0]).lstrip("~").split(" ")[0]) for q, v in m["guaranteed"].items()} for k, m in (r.get("per_mode") or {}).items()}
check(r["verdict"] == "EARNED" and r["objective"]["optimal"] is True and r["designs_count"].get("REFUTED", 0) >= 1
      and all(got[m]["qEnd_req"] <= {"light": 3, "medium": 5, "heavy": 9}[names(r)["END"]] and got[m]["qMid_req"] <= {"light": 3, "medium": 5, "heavy": 9}[names(r)["MID"]] for m in got),
      f"a roof by rules, two zones, two load cases: cheaper pairs refuted, the chosen pair holds in both and is optimal ({names(r)}, {r.get('designs_count')}, {got})")
r_far = S.run(roof("400", "2"))
mc = (r_far.get("minimal_conflicts") or {}).get("sets") or []
check(r_far["verdict"] == "REFUTED" and any(len(s_) == 1 and "drift limit" in s_[0] for s_ in mc),
      f"a drift limit no deck of the catalogue reaches: REFUTED, and the stand names the drift requirement as the one that cannot be met ({r_far.get('verdict')}, {mc})")
for word, edit in (("is not a crossing", lambda x: x["assembly"]["springs"].append({"at": [5, 5], "dir": "X", "k": "KF"})),
                   ("no panel lies inside", lambda x: x["assembly"]["outputs"]["qEnd"].update(box=[18, 12, 24, 18])),
                   ("a bare number", lambda x: x["assembly"]["bars"][0].update(EA="200000")),
                   ("what is one of", lambda x: x["assembly"]["outputs"]["ux"].update(what="largest"))):
    bad = roof("400", "40")
    edit(bad)
    r = S.run(bad)
    check(r["verdict"] == "BRICK ERROR" and word in str(r.get("why")), f"PLANTED a wrong grid rule is refused with its reason: {word!r} ({str(r.get('why'))[:110]})")

# ---- 5b. THE PLATE'S OWN DEFLECTION (`sag`): along a grid line between two nodes, each node's displacement minus the
# straight line through the two ends' displacements; the largest size of it. Checked against the same roof's node
# displacements asked one by one: the sag's enclosure holds the value computed from them, and is not wider than theirs.
sg = roof("400", "40")
sg["catalog"]["decks"]["items"] = [sg["catalog"]["decks"]["items"][1]]
line = [x for x in range(0, 49, 6)]
sg["assembly"]["outputs"] = {"bow": {"what": "sag", "dir": "Y", "between": [[0, 18], [48, 18]], "unit": "mm"},
                             **{f"v{x}": {"what": "u", "at": [x, 18], "dir": "Y", "unit": "mm"} for x in line}}
sg["modes"] = {"seismic Y": {"quantities": {"WY": {"value": "400"}},
                             "requirements": [{"quantity": q, "op": ">=", "value": "-1000000", "why": "(read)"} for q in sg["assembly"]["outputs"]]}}
r = S.run(sg)
g = ((r.get("per_mode") or {}).get("seismic Y") or {}).get("guaranteed") or {}
num = lambda v: float(str(v).lstrip("~").split(" ")[0])      # noqa: E731
try:
    u = {x: (num(g[f"v{x}_req"][0]), num(g[f"v{x}_req"][1])) for x in line}
    own = max(abs((u[x][0] + u[x][1]) / 2 - ((u[0][0] + u[0][1]) / 2 * (1 - x / 48) + (u[48][0] + u[48][1]) / 2 * (x / 48))) for x in line)
    width = max(b_ - a_ for a_, b_ in u.values())
    bow = (num(g["bow_req"][0]), num(g["bow_req"][1]))
    ok = r["verdict"] == "EARNED" and own > 0.01 and bow[0] - 1e-9 <= own <= bow[1] + 1e-9 and (bow[1] - bow[0]) <= 4 * width + 1e-9
except Exception as e:                                       # noqa: BLE001
    own, bow, ok = None, str(e), False
check(ok, f"a sag output: the largest bow of the line between its ends, equal to what the node displacements give ({bow}, own {own}, {r.get('verdict')} {str(r.get('why'))[:80]})")
for word, edit in (("on one grid line", lambda x: x["assembly"]["outputs"]["bow"].update(between=[[0, 18], [48, 24]])),
                   ("no grid node lies between", lambda x: x["assembly"]["outputs"]["bow"].update(between=[[0, 18], [6, 18]])),
                   ("is held in", lambda x: x["assembly"].setdefault("fixed", []).append({"at": [24, 18], "dir": "Y"}))):
    bad = copy.deepcopy(sg)
    edit(bad)
    r = S.run(bad)
    check(r["verdict"] == "BRICK ERROR" and word in str(r.get("why")), f"PLANTED a wrong sag line is refused with its reason: {word!r} ({str(r.get('why'))[:110]})")

# ---- 6. A brick WITHOUT the section is judged as before (the rule does not touch it)
plain = {"stand": "ztl-stand/1",
         "quantities": {"y": {"role": "given", "range": ["0.9999999", "1.0000001"], "unit": "mm"}, "d": {"role": "derived", "unit": "mm"}},
         "slots": {}, "catalog": {}, "laws": [{"zfl": "d == y", "source": "itself"}],
         "requirements": [{"quantity": "d", "op": "<=", "value": "1", "why": "limit"}]}
r = S.run(plain)
check(r["verdict"] == "REFUTED", f"a TOLERANCE past its limit at one end is refuted as before: every point of a tolerance is a state of the world ({r.get('verdict')})")

# ---- A MODE'S OWN LOADS AND SUPPORTS OF THE STRUCTURE (2026-11-14): a load case is not only other numbers - another
# load pattern, other frames holding it. The one-panel wall again: the mode "half" gives its own `loads` (12 kN in
# place of 24) - the structure is linear, so drift and flow are exactly half: 253 mm and 3 kN/m beside 506 and 6.
half = copy.deepcopy(one)
half["quantities"]["Ph"] = {"role": "given", "value": "12", "unit": "kN", "ground": "load case"}
half["modes"] = {"push": {}, "half": {"assembly": {"loads": [["tr", "X", "Ph"]]}}}
r = S.run(half)
pm = {m: {k: [str(x).split(" ")[0] for x in v] for k, v in (g.get("guaranteed") or {}).items()} for m, g in (r.get("per_mode") or {}).items()}
check(r.get("verdict") == "EARNED" and names(r) == {"DECK": "D24"}
      and pm.get("push") == {"u_req": ["506", "506"], "q_req": ["6", "6"]} and pm.get("half") == {"u_req": ["253", "253"], "q_req": ["3", "3"]},
      f"a mode with its own loads of the structure: half the load gives exactly half the drift and the flow (253 mm, "
      f"3 kN/m beside 506 and 6), the deck chosen for both ({r.get('verdict')}, {pm})")
bad = copy.deepcopy(half)
bad["modes"]["half"]["assembly"]["panels"] = []
r = S.run(bad)
check(r.get("verdict") == "BRICK ERROR" and "the same in every mode" in str(r.get("why")),
      f"a mode that tries to change the structure itself (its panels) is refused: only springs, supports, loads and "
      f"outputs are a mode's ({r.get('verdict')}: {str(r.get('why'))[:80]})")

if FAILS:
    print(f"ASSEMBLY BRICK RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"ASSEMBLY BRICK GREEN ({CHECKS} checks)")
