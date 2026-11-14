# -*- coding: utf-8 -*-
"""THE CLIMB (ustand/climb.py, BRICKS.md 7k, 2026-11-14): a search for design spaces too large to judge one by one —
raise the slot a refutation points at, then try each slot one step cheaper. What must hold: every design it proposes
is judged by the stand as usual; the design found is EARNED; of the optimum only what was judged is claimed; a climb
that finds nothing is OPEN, never a refutation of the catalogue. Small hand-checked bricks, no task data.
Run: python3 tests/test_climb.py"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import climb as CL, stand as S   # noqa: E402

CHECKS, FAILS = 0, []


def check(c, what):
    global CHECKS
    CHECKS += 1
    if not c:
        FAILS.append(what)
        print("FAIL:", what)


def names(r):
    return {k: v.get("name") for k, v in (r.get("design") or {}).items()}


PARTS = ((3, 1), (6, 2), (10, 4), (20, 9))            # (capacity, price)


def three(demand=("5", "9", "2"), parts=PARTS):
    """three slots, each part must carry its own demand: the cheapest that holds is, slot by slot, the first part
    whose capacity reaches the demand — 6, 10, 3 -> 2 + 4 + 1 = 7"""
    return {"stand": "ztl-stand/1",
            "quantities": dict({f"d{i + 1}": {"role": "given", "value": d, "unit": "N", "ground": "test"} for i, d in enumerate(demand)},
                               **{f"m{i + 1}": {"role": "derived", "unit": "N"} for i in range(3)}),
            "slots": {s: {"from": ["parts"]} for s in "ABC"},
            "catalog": {"parts": {"ground": "test", "items": [{"name": f"p{c}", "cap": str(c), "price": str(p)} for c, p in parts],
                                  "fields": {"cap": {"unit": "N"}, "price": {"unit": "USD"}}}},
            "laws": [{"zfl": f"m{i + 1} == {s}.cap - d{i + 1}"} for i, s in enumerate("ABC")],
            "requirements": [{"quantity": f"m{i + 1}", "op": ">=", "value": "0", "why": f"{s} holds"} for i, s in enumerate("ABC")],
            "objective": {"minimize": "A.price + B.price + C.price", "unit": "USD"}}


def run(b, how):
    return S.run(dict(copy.deepcopy(b), search=how))


# 1. the same design as judging every design, with fewer judgements — and the optimum is not claimed
a, c = run(three(), "all"), run(three(), "climb")
check(a["verdict"] == c["verdict"] == "EARNED" and names(a) == names(c) == {"A": "p6", "B": "p10", "C": "p3"}
      and a["objective"]["value"] == c["objective"]["value"] == "7" and c["designs_tried"] < a["designs_tried"],
      f"three slots, each with its own demand: the climb takes the design that judging all 64 takes (p6, p10, p3 = 7 USD) "
      f"in {c['designs_tried']} judgements against {a['designs_tried']} ({names(c)})")
s = c.get("search") or {}
check(a["objective"]["optimal"] is True and c["objective"]["optimal"] is False and s.get("mode") == "climb"
      and s.get("judged") == c["designs_tried"] and s.get("not_judged") == 64 - c["designs_tried"]
      and [x.get("verdict", "bottom") for x in s.get("one_step_cheaper", [])] == ["REFUTED", "REFUTED", "bottom"],
      f"what the climb claims: optimal false, the designs never judged counted ({s.get('not_judged')}), and each slot "
      f"one step cheaper REFUTED (C holds its cheapest part) — {[x.get('verdict', 'bottom') for x in s.get('one_step_cheaper', [])]}")

# 2. with modes (load cases): the design must hold in every one
m = three()
m["modes"] = {"normal": {}, "storm": {"quantities": {"d1": {"value": "8"}}}}
a, c = run(m, "all"), run(m, "climb")
check(a["verdict"] == c["verdict"] == "EARNED" and names(a) == names(c) == {"A": "p10", "B": "p10", "C": "p3"}
      and c["designs_tried"] < a["designs_tried"] and c["objective"]["optimal"] is False and "search" in c
      # a design passed by is judged until its first failing mode; the design found - in every mode
      and set(c.get("per_mode") or {}) == {"normal", "storm"} and "first failing mode" in c["search"].get("modes", "")
      and all(len(o.get("failing_modes", [1])) == 1 for o in c.get("designs", []) if o.get("verdict") == "REFUTED"),
      f"with two load cases (A carries 8 in the storm): the same design either way (p10, p10, p3), "
      f"{c['designs_tried']} judgements against {a['designs_tried']} ({names(c)})")

# 3. nothing in the catalogue holds: the climb says it FOUND nothing — it has not refuted the catalogue
for label, b in (("plain", three(("5", "25", "2"))), ("modes", dict(three(("5", "25", "2")), modes={"n": {}, "s": {"quantities": {"d1": {"value": "8"}}}}))):
    a, c = run(b, "all"), run(b, "climb")
    check(a["verdict"] == "REFUTED" and c["verdict"] == "OPEN" and "not a refutation" in str(c.get("why"))
          and (c.get("search") or {}).get("found", "").startswith("no earned design"),
          f"no part carries 25 ({label}): judging all refutes the catalogue, the climb answers OPEN and says it judged "
          f"{(c.get('search') or {}).get('judged')} of 64 ({a['verdict']}, {c['verdict']})")

# 4. PLANTED — a catalogue where the climb's answer is NOT the cheapest: two slots, A.cap + B.cap >= 16, parts
#    (6, 10 USD) (7, 12) (8, 15) (13, 19). The climb ends at 8 + 8 = 30 USD (each slot one step cheaper gives 15: fails);
#    6 + 13 = 19 holds at 29 USD. The stand must not call 30 the optimum, and "all" must find 29.
trap = {"stand": "ztl-stand/1",
        "quantities": {"need": {"role": "given", "value": "16", "unit": "N", "ground": "test"}, "m": {"role": "derived", "unit": "N"}},
        "slots": {"A": {"from": ["parts"]}, "B": {"from": ["parts"]}},
        "catalog": {"parts": {"ground": "test", "items": [{"name": f"p{c}", "cap": str(c), "price": str(p)}
                                                         for c, p in ((6, 10), (7, 12), (8, 15), (13, 19))],
                              "fields": {"cap": {"unit": "N"}, "price": {"unit": "USD"}}}},
        "laws": [{"zfl": "m == A.cap + B.cap - need"}],
        "requirements": [{"quantity": "m", "op": ">=", "value": "0", "why": "the pair holds"}],
        "objective": {"minimize": "A.price + B.price", "unit": "USD"}}
a, c = run(trap, "all"), run(trap, "climb")
check(a["verdict"] == c["verdict"] == "EARNED" and a["objective"]["value"] == "29" and a["objective"]["optimal"] is True
      and c["objective"]["value"] == "30" and c["objective"]["optimal"] is False
      and "cheaper combination may exist" in c["objective"]["note"],
      f"PLANTED a catalogue where the climb stops at 30 USD and 29 exists: the climb's design is EARNED and NOT called "
      f"optimal; judging all finds 29 and proves it ({c['objective']['value']} optimal {c['objective']['optimal']}; "
      f"{a['objective']['value']} optimal {a['objective']['optimal']})")

# 5. which slot a failed requirement names
check(CL.blamed(three(), {"quantity": "m2", "op": ">=", "value": "0"}) == ["B"]
      and CL.blamed(trap, {"quantity": "m", "op": ">=", "value": "0"}) == ["A", "B"]
      and CL.blamed(three(), {"quantity": "q", "op": "<=", "value": "C.cap"}) == ["C"]
      and CL.blamed(three(), {"quantity": "d1", "op": "<=", "value": "100"}) == [],
      "the slot a failed requirement names: through the law that defines its quantity (m2 -> B), both of a shared "
      "law, the slot in its bound (<= C.cap), none when it reads no slot")

# 6. when it runs: asked for, or by itself for a structure with more than CLIMB_ABOVE designs; and what it refuses
check(not CL.wanted(three()) and CL.wanted(dict(three(), search="climb")) and not CL.wanted(dict(three(), search="all"))
      and CL.size(three()) == 64,
      "a small brick without a structure is judged design by design unless it asks for the climb")
bad = [run(three(), "sideways"), S.run(dict(three(), search="climb", where=['A.name == "p6"'])),
       S.run({k: v for k, v in dict(three(), search="climb").items() if k != "objective"})]
check(all(r["verdict"] == "BRICK ERROR" for r in bad) and "version 1" in str(bad[1].get("why")) and "objective" in str(bad[2].get("why")),
      f"refused, said plainly: an unknown search; a climb with `where` (version 1); a climb without an objective "
      f"({[r['verdict'] for r in bad]})")

# 7. THROUGH A STRUCTURE, by itself: eight shear panels along a wall, each its own zone choosing a deck from three,
#    all held by one top chord and loaded at every panel — the panels act on one another through the chord (a stiffer
#    deck draws more of the load), so no zone's demand is its own. 3^8 = 6561 designs: climbed without being asked.
#    Checked without a hand value: the design found is EARNED when judged again on its own, every zone one step
#    cheaper is judged and not earned, and the judgements are a handful.
N = 8
wall = {"stand": "ztl-stand/1",
        "quantities": {"P": {"role": "given", "value": "24", "unit": "kN", "ground": "test"},
                       "EAt": {"role": "given", "value": "4000", "unit": "kN", "ground": "test"}},
        "slots": {f"Z{i}": {"from": ["decks"]} for i in range(N)},
        "catalog": {"decks": {"ground": "test", "items": [{"name": "D4", "G": "12", "cap": "4", "price": "10"},
                                                          {"name": "D8", "G": "24", "cap": "8", "price": "15"},
                                                          {"name": "D12", "G": "48", "cap": "12", "price": "22"}],
                              "fields": {"G": {"unit": "kN/m"}, "cap": {"unit": "kN/m"}, "price": {"unit": "USD"}}}},
        "laws": [],
        "assembly": {"length_unit": "m",
                     "grid": {"x": [4 * i for i in range(N + 1)], "y": [0, 2]},
                     "panels": [{"g": f"Z{i}.G", "box": [4 * i, 0, 4 * i + 4, 2]} for i in range(N)],
                     "bars": [{"along": "x", "lines": [2], "EA": "EAt"}],
                     "fixed": [{"at": [4 * i, 0], "dir": d} for i in range(N + 1) for d in ("X", "Y")]
                              + [{"at": [4 * i, 2], "dir": "Y"} for i in range(N + 1)],
                     "loads": [{"at": [4 * i + 4, 2], "dir": "X", "P": "P"} for i in range(N)],
                     "outputs": {f"q{i}": {"what": "max_flow", "box": [4 * i, 0, 4 * i + 4, 2], "unit": "kN/m"} for i in range(N)}},
        "requirements": [{"quantity": f"q{i}", "op": "<=", "value": f"Z{i}.cap", "why": f"panel {i}"} for i in range(N)],
        "objective": {"minimize": " + ".join(f"Z{i}.price" for i in range(N)), "unit": "USD"}}
r = S.run(wall)
s = r.get("search") or {}
again = S.run(dict(copy.deepcopy(wall), search="all",
                   where=[" and ".join(f'{z}.name == "{n}"' for z, n in names(r).items())])) if r.get("design") else {}
check(r.get("verdict") == "EARNED" and again.get("verdict") == "EARNED" and again.get("designs_tried") == 1
      and s.get("mode") == "climb" and s.get("designs_in_the_catalogue") == 3 ** N and s.get("judged", 10 ** 9) <= 4 * N
      and r["objective"]["optimal"] is False
      and all(x.get("verdict", "bottom") in ("REFUTED", "OPEN", "bottom") for x in s.get("one_step_cheaper", [])),
      f"through a structure, unasked: eight coupled zones x three decks (6561 designs) climbed in {s.get('judged')} "
      f"judgements; the design found is EARNED again when judged alone, and every zone one step cheaper is not earned "
      f"({r.get('verdict')}, again {again.get('verdict')}, {names(r)}, {str(r.get('why') or '')[:120]})")

# 6. A REQUIREMENT THAT NAMES NO SLOT (a drift of a whole structure): the step is found by TRYING every single step.
# A small roof - two zones of deck from a catalogue of three, two load cases, a drift limit; with the limit at 20 the
# cheapest design that holds is (heavy, medium): shear names the end zone, the drift names nobody. The climb reaches
# the design that judging all nine takes, says a step was found by trying, and a limit nothing meets ends OPEN.
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


ra, rc = S.run(dict(roof("400", "20"), search="all")), S.run(dict(roof("400", "20"), search="climb"))
sc = rc.get("search") or {}
check(ra["verdict"] == rc["verdict"] == "EARNED" and names(ra) == names(rc) == {"END": "heavy", "MID": "medium"}
      and sc.get("steps_found_by_trying", 0) >= 1 and rc["objective"]["optimal"] is False,
      f"a drift limit that names no slot: the climb finds its step by trying and reaches the design that judging all "
      f"nine takes ({names(rc)}, tried {rc.get('designs_tried')}, by trying {sc.get('steps_found_by_trying')})")
rn = S.run(dict(roof("400", "5"), search="climb"))
check(rn["verdict"] == "OPEN" and "no earned design" in str((rn.get("search") or {}).get("found")),
      f"PLANTED a drift limit no design meets: the climb ends OPEN and says so, never REFUTED ({rn.get('verdict')}, {(rn.get('search') or {}).get('found')})")
if FAILS:
    print(f"CLIMB RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"CLIMB GREEN ({CHECKS} checks)")
