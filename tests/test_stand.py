"""Stand: ztl-stand (formerly universal-stand) — the three verdicts, the checker, and lies caught.

Run: python3 -m tests.test_stand   (from the repo root)
"""
import json
import sys
import os
import re
import pathlib
from fractions import Fraction as F

from ustand import bricks as B, checker as C, judge_ztl as J, stand as S
from ustand import mode as _MODE   # the stand's tests run in DEV mode: the independent checker on every design
_MODE.DEV[0] = True

ok = fail = 0
EX = pathlib.Path(__file__).resolve().parent.parent / "examples"


def check(name, cond, why=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  OK   {name}")
    else:
        fail += 1; print(f"  FAIL {name} — {why}")


def ex(name):
    return json.load(open(EX / f"{name}.json", encoding="utf-8"))


# 1. the three outcomes on the divider
r = S.run(ex("divider-1pct-req-1pct"))
check("+-1% from 1% parts: EARNED, 1k/1k, guaranteed exactly [99/40, 101/40]",
      r["verdict"] == "EARNED" and r["guaranteed"]["Vout"][0].startswith("99/40")
      and r["guaranteed"]["Vout"][1].startswith("101/40"), json.dumps(r)[:300])
r = S.run(ex("divider-1pct-req-0.5pct"))
check("+-0.5% from 1% parts: REFUTED, with a violating point recomputed",
      r["verdict"] == "REFUTED" and r["value_there"]["Vout"].startswith("101/40"), json.dumps(r)[:300])
r = S.run(ex("divider-both-req-0.5pct"))
check("+-0.5% with 0.1% parts in the catalog: EARNED on the 0.1% parts",
      r["verdict"] == "EARNED" and r["design"]["R1"]["catalog"] == "res_0.1pct_quarterW", json.dumps(r)[:300])

# 1b. items with several fields: a power rating as a requirement bound
r = S.run(ex("power-16thW-only"))
check("power, 1/16 W parts only: REFUTED at a real corner where P1 exceeds the rating",
      r["verdict"] == "REFUTED" and r["value_there"].get("P1", "").startswith("25/396")
      and r["requirement"]["value"] == "R1.P", json.dumps(r)[:300])
r = S.run(ex("power-16thW-or-quarterW"))
check("power, 1/16 or 1/4 W: EARNED on 1/4 W parts, power bounded BY ZTL (interval reading, Z1 in ZTL 3a296b5)",
      r["verdict"] == "EARNED" and r["design"]["R1"]["catalog"] == "res_1pct_quarterW"
      and r["how"]["P1"].startswith("ZTL, interval reading"), json.dumps(r)[:300])

# 2. the checker on its own: exact values, its refusals
v = C.solve_at(["Vin - Vout == I*R1", "Vout == I*R2", "P1 == I*I*R1"],
               {"Vin": F(5), "R1": F(990), "R2": F(1010)}, ["I", "Vout", "P1"])
check("checker: divider at (990, 1010) is exactly 101/40, and P1 = (1/400)^2*990 exactly",
      v["Vout"] == F(101, 40) and v["P1"] == F(1, 400) ** 2 * 990, str(v))
try:
    C.solve_at(["Vout*I == I*I"], {}, ["I", "Vout"]); refused = False
except C.CheckError:
    refused = True
check("checker refuses a nonlinear law that defines nothing (outside its class) aloud", refused)

# 3. lies told by the judge must be caught
real = J.judge


def lying_narrow(laws, fixed, boxes, derived, grounds):
    out, log, d = real(laws, fixed, boxes, derived, grounds)
    out["Vout"] = (F(2499, 1000), F(2501, 1000), "corners")  # claims a range far tighter than true
    return out, log, d


J.judge = lying_narrow
r = S.run(ex("divider-1pct-req-0.5pct"))
J.judge = real
check("MUTATION: a judge claiming a too-narrow exact range is caught (STAND FAULT, not EARNED)",
      r["verdict"] == "STAND FAULT", json.dumps(r)[:200])


def lying_wide(laws, fixed, boxes, derived, grounds):
    out, log, d = real(laws, fixed, boxes, derived, grounds)
    out["Vout"] = (F(2), F(3), "corners")                     # claims a violation that no corner shows
    return out, log, d


J.judge = lying_wide
r = S.run(ex("divider-both-req-0.5pct"))
J.judge = real
check("MUTATION: a judge claiming a violation no corner shows is caught (STAND FAULT)",
      r["verdict"] == "STAND FAULT", json.dumps(r)[:200])


def unsure(laws, fixed, boxes, derived, grounds):
    out, log, d = real(laws, fixed, boxes, derived, grounds)
    return {k: (lo, hi, False) for k, (lo, hi, _) in out.items()}, log, d


J.judge = unsure
r = S.run(ex("divider-1pct-req-1pct"))
J.judge = real
check("a sound but not-exact range inside the requirement still EARNS (exactness is needed only to refute)",
      r["verdict"] == "EARNED" and r["how"]["Vout"] == "ZTL, outer range", json.dumps(r)[:200])


def silent(laws, fixed, boxes, derived, grounds):
    out, log, d = real(laws, fixed, boxes, derived, grounds)
    return {}, log, d


J.judge = silent
r = S.run(ex("divider-1pct-req-1pct"))
check("a judge whose solver bounds nothing: EARNED only through ZTL's OTHER instrument, the certificate check "
      "(since 2026-10-10 a refused range goes to certificates) — never by the stand alone",
      r["verdict"] == "EARNED" and all("certificate checked exactly" in h for h in r["how"].values()), json.dumps(r)[:200])
from ustand import certify as _K0          # noqa: E402
import zlin as _ZL0                        # noqa: E402 — ZTL's third instrument (linear systems, 2026-10-15)
_rc, _rs, _rz = _K0.ZC.check, _K0.ZC.check_system, _ZL0.check
_K0.ZC.check = _K0.ZC.check_system = _ZL0.check = lambda *a, **k: (False, "silent")
r = S.run(ex("divider-1pct-req-1pct"))
_K0.ZC.check, _K0.ZC.check_system, _ZL0.check = _rc, _rs, _rz
J.judge = real
check("a judge silent in ALL its instruments (solver, certificate check, linear certificate check) yields OPEN, "
      "never EARNED", r["verdict"] == "OPEN", json.dumps(r)[:200])

# 3b. lies about a DEFINITION (power) must be caught by the checker's own bound
def lying_defs(laws, fixed, boxes, derived, grounds):
    out, log, d = real(laws, fixed, boxes, derived, grounds)
    # the definitions calls: claim zero power (since 2026-10-11 the stand sends ONE definition per call — J2 —
    # so the lie must cover each of them, not only a call naming P1)
    if set(derived) & {"P1", "P2"}:
        out = {k: (F(0), F(0), False) for k in derived}
    return out, log, d


J.judge = lying_defs
r = S.run(ex("power-16thW-only"))
J.judge = real
check("MUTATION: ZTL claiming zero power for a definition is caught (STAND FAULT, not EARNED)",
      r["verdict"] == "STAND FAULT", json.dumps(r)[:200])


def silent_defs(laws, fixed, boxes, derived, grounds):
    out, log, d = real(laws, fixed, boxes, derived, grounds)
    return ({} if set(derived) & {"P1", "P2"} else out), log, d


from ustand import forward as W
real_bound = W.bound
W.bound = lambda defs, known: {k: (F(0), F(0)) for k in defs}
J.judge = silent_defs
r = S.run(ex("power-16thW-only"))
J.judge = real; W.bound = real_bound
check("MUTATION: when ZTL is silent, a fallback claiming zero power is caught too (STAND FAULT)",
      r["verdict"] == "STAND FAULT", json.dumps(r)[:200])
J.judge = silent_defs
r = S.run(ex("power-16thW-or-quarterW"))
J.judge = real
check("when ZTL is silent on a definition, the stand's fallback bounds it and labels it 'outside ZTL'",
      r["verdict"] == "EARNED" and r["how"]["P1"].startswith("outside ZTL"), json.dumps(r)[:200])

# 5. the five probe tasks (2026-10-09), held as regression — their verdicts and how they were reached
T = EX / "tasks"
def task(n): return S.run(json.load(open(T / f"{n}.json", encoding="utf-8")))
r = task("t1-thermal-heatsink")
check("t1 thermal: EARNED (2 C/W heatsink, 0.5 pad), Tj <= 599/5, now bounded BY ZTL exactly (Z2 closed in ZTL)",
      r["verdict"] == "EARNED" and r["guaranteed"]["Tj"][1].startswith("599/5") and r["how"]["Tj"] == "ZTL, exact at the corners",
      json.dumps(r)[:200])
r = task("t2-gap-stackup")
check("t2 gap stack-up: EARNED, gap in [11/100, 69/100]",
      r["verdict"] == "EARNED" and r["guaranteed"]["gap"] == ["11/100 (~0.11)", "69/100 (~0.69)"], json.dumps(r)[:200])
r = task("t3-rc-cutoff")
check("t3 RC cutoff: REFUTED with a real violating point (f below 950 Hz), in nF/ohm/Hz with units checked",
      r["verdict"] == "REFUTED" and "f" in r["value_there"] and r["units"].startswith("checked"), json.dumps(r)[:200])
check("t3 reasons (J7): the spread is wider than the window, and the capacitor's tolerance moves it most",
      "verdict_on_window" in r["reasons"] and r["reasons"]["largest_contributors"][0]["quantity"] == "C.C",
      json.dumps(r.get("reasons"))[:300])
r = task("t1-thermal-heatsink")
check("t1 objective (J2): the cheapest design that holds Tj (4.1), proven optimal (every cheaper one refuted)",
      r["objective"]["value"].startswith("41/10") and r["objective"]["optimal"] is True, json.dumps(r.get("objective")))
bad = json.load(open(T / "t1-thermal-heatsink.json", encoding="utf-8"))
bad["laws"][0]["zfl"] = "Tj == Ta + P*(Rjc + PAD.R + HS.R) + P"      # adds watts to degrees
r = S.run(bad)
check("units (J5): a law adding watts to degrees is refused as a BRICK ERROR",
      r["verdict"] == "BRICK ERROR" and "adding" in r["why"], json.dumps(r)[:200])
r = task("t4-battery-cells")
check("t4 battery: EARNED with 7 cells, the count given as an integer range (J6), V bounded by ZTL exactly",
      r["verdict"] == "EARNED" and r["design"]["PACK"]["N"]["nominal"] == "7" and r["how"]["V"] == "ZTL, exact at the corners",
      json.dumps(r)[:200])
r = task("t5-divider-tcr")
check("t5 divider over 0..85 C: EARNED on 25 ppm parts, exact through ZTL",
      r["verdict"] == "EARNED" and r["design"]["R1"]["catalog"] == "res_25ppm"
      and r["how"]["Vout"] == "ZTL, exact at the corners", json.dumps(r)[:200])

bad = json.load(open(T / "t1-thermal-heatsink.json", encoding="utf-8"))
bad["laws"].append({"zfl": "Tj*Tj == Ta*Tj", "source": "nonsense"})
r = S.run(bad)
check("a nonlinear law that defines nothing is refused as a BRICK ERROR (not a crash)",
      r["verdict"] == "BRICK ERROR" and r["why"].startswith("laws:"), json.dumps(r)[:200])

# 6. another domain: a truss (same A^T*G*A class as a circuit), and a correlated tolerance
r = task("t6-truss-three-bars")
check("t6 truss, independent E per bar: EARNED, lightest sections 150/150/100 proven optimal, all ranges by ZTL exactly",
      r["verdict"] == "EARNED" and r["objective"]["optimal"] is True
      and [r["design"][b]["A"]["nominal"] for b in ("B1", "B2", "B3")] == ["150", "150", "100"]
      and all(h == "ZTL, exact at the corners" for h in r["how"].values()), json.dumps(r)[:300])
r = task("t7-truss-one-batch")
check("t7 truss, ONE E for all bars (correlated): EARNED directly now (ZTL _solve_rank_many), same numbers as the rewrite t7b",
      r["verdict"] == "EARNED" and r["guaranteed"]["s2"][1].startswith("65560/557"), json.dumps(r)[:300])
r = task("t7b-truss-one-batch-rewritten")
check("t7b the same, rewritten with the scaled displacement v = E*u: EARNED, stresses independent of E (narrower than t6)",
      r["verdict"] == "EARNED" and r["guaranteed"]["s2"][1].startswith("65560/557"), json.dumps(r)[:300])

# 7. minimal conflicts (J7): the antichain of requirement sets the catalog cannot satisfy together
r = task("t3-rc-cutoff")
check("t3 minimal conflicts: the 1 kHz +-5% window alone", r["minimal_conflicts"]["sets"] == [["1 kHz +-5%"]],
      json.dumps(r.get("minimal_conflicts"))[:300])
r = S.run(ex("power-16thW-only"))
sets = {frozenset(x) for x in r["minimal_conflicts"]["sets"]}
want = {frozenset({"2.5 V +-1%", "the load needs at least 24 mA through the divider", "R1 within its power rating"}),
        frozenset({"2.5 V +-1%", "the load needs at least 24 mA through the divider", "R2 within its power rating"}),
        frozenset({"the load needs at least 24 mA through the divider", "R1 within its power rating", "R2 within its power rating"})}
check("power on 1/16 W parts: exactly three minimal conflicts, none containing another (an antichain)",
      sets == want and not any(a < b for a in sets for b in sets), json.dumps(r.get("minimal_conflicts"))[:400])
check("minimal conflicts on a small brick are still COMPLETE (4 requirements: every subset fits the default budget)",
      r["minimal_conflicts"].get("complete") is True, json.dumps(r.get("minimal_conflicts"))[:300])
# MORE THAN 8 REQUIREMENTS (2026-10-13, lever 3): the deletion pass finds a minimal conflict for any n (blind 6 c07,
# 10 requirements, was "skipped"); 8 harmless requirements added to the power brick — 12 in all
_p12 = ex("power-16thW-only")
_p12["requirements"] = _p12["requirements"] + [
    {"quantity": "Vin", "op": ">=", "value": str(-k - 1), "why": f"harmless {k}"} for k in range(8)]
r = S.run(_p12)
_mc12 = r.get("minimal_conflicts") or {}
_s12 = {frozenset(x) for x in _mc12.get("sets", [])}
check("minimal conflicts over 12 requirements: within the budget (4 per requirement since 2026-10-18, with monotone "
      "inference and complement probes) ALL THREE true ones, no harmless requirement in any, the listing marked "
      "incomplete (the harmless ones leave subsets unjudged)",
      _s12 == want and _mc12.get("complete") is False and _mc12.get("subset_runs") <= 48,
      json.dumps(_mc12)[:400])
_PLc = __import__("ustand.parallel", fromlist=["JOBS"])
_PLc.JOBS[0] = 3
r3 = S.run(_p12)
_PLc.JOBS[0] = 1
check("minimal conflicts with --jobs 3: the same listing as one process", r3.get("minimal_conflicts") == _mc12,
      json.dumps(r3.get("minimal_conflicts"))[:300])
r2 = S.run(dict(ex("power-16thW-only"), requirements=[q for q in ex("power-16thW-only")["requirements"]
                                                       if q["quantity"] != "I"]))
check("dropping the one requirement every conflict shares (>= 24 mA) makes it EARNED",
      r2["verdict"] == "EARNED", json.dumps(r2)[:200])

# 8. the extreme INSIDE the box: the stand searches a certificate, ZTL checks it (zcertify)
r = task("t8-load-power-peak-inside")
check("t8 load power (peak at RL = Rs, inside 1..100 ohm) <= 0.6 W: Rs = 10 refuted at an interior point, "
      "Rs = 11 EARNED by a certificate ZTL checked (before: 20 designs OPEN, earned only at 68)",
      r["verdict"] == "EARNED" and r["design"]["Rs"]["R"]["nominal"] == "11" and r["undecided"] == 0
      and "certificate checked exactly" in r["how"]["P"] and r["guaranteed"]["P"][1].startswith("3/5"),
      json.dumps(r)[:400])
r = task("t8b-load-power-refuted-inside")
pt = r.get("its_violating_point", {})
check("t8b 0.05 W over 1..1000 ohm: nominal and every corner pass, REFUTED at an interior point the checker "
      "recomputed (before: 16 designs OPEN)",
      r["verdict"] == "REFUTED" and r["failed_at_nominal"] == 0 and r["undecided"] == 0
      and pt.get("RL") not in (None, "1", "1000"), json.dumps(r)[:400])
from ustand import certify as K          # noqa: E402
real_search = K.search


def lying_search(*a, **k):
    got = real_search(*a, **k)
    if "cert" in got:                    # every monotone leaf's signs flipped: a false certificate
        def flip(n):
            if "split" in n:
                flip(n["lo"]); flip(n["hi"])
            elif n.get("leaf") == "monotone":
                n["signs"] = {q: ("-" if s == "+" else "+") for q, s in n["signs"].items()}
        flip(got["cert"])
    return got


real_check = K.ZC.check
seen = []


def watching_check(e, qs, op, bound, cert):
    got = real_check(e, qs, op, bound, cert)
    seen.append(("monotone" in json.dumps(cert), got[0]))
    return got


K.search, K.ZC.check = lying_search, watching_check
r = task("t8-load-power-peak-inside")
K.search, K.ZC.check = real_search, real_check
flipped = [acc for mono, acc in seen if mono]
check(f"MUTATION: a searcher flipping every monotone sign — ZTL refused all {len(flipped)} such certificates "
      f"(certificates of interval leaves only stay true and may pass); Rs = 10, which truly fails, is not earned",
      flipped and not any(flipped) and r["design"]["Rs"]["R"]["nominal"] != "10", json.dumps(r)[:300])

# 8b. J9: the checker re-checks the certificate from the laws, with its own means
r = task("t8-load-power-peak-inside")
check("t8: the checker re-checked the certificate itself (its own derivative and interval arithmetic)",
      "the checker re-checked the same certificate" in r["how"]["P"], json.dumps(r.get("how")))
real_cc = C.check_certificate
C.check_certificate = lambda *a, **k: (False, "mutated checker")
r = task("t8-load-power-peak-inside")
C.check_certificate = real_cc
check("MUTATION: a checker that confirms nothing — no design is EARNED on a certificate, and the refusal is reported",
      "certificate" not in json.dumps(r.get("how", {})) and r.get("certificates_unconfirmed"),
      json.dumps(r)[:300])
laws = ["P == V*V*RL/((Rs__R + RL)*(Rs__R + RL))"]
fx, bx = {"V": F(5)}, {"RL": (F(1), F(100)), "Rs__R": (F(1089, 100), F(1111, 100))}
cert = {"leaf": "monotone", "signs": {"RL": "+", "Rs__R": "-"}}
check("the checker refuses a false monotone certificate (P is not increasing in RL past RL = Rs)",
      not C.check_certificate(laws, fx, bx, ["P"], "P", "<=", F(3, 5), cert)[0])
check("the checker refuses a true certificate for a FALSE bound (0.57 W; the peak is 0.5739)",
      not C.check_certificate(laws, fx, bx, ["P"], "P", "<=", F(57, 100),
                              {"split": "RL", "at": "10", "lo": cert, "hi": {"leaf": "interval"}})[0])

# 8c. J9 at random: ZTL and the checker on the same certificates (rational shapes, no sqrt)
import random as _random                  # noqa: E402
from ustand import certify as _K          # noqa: E402
_rng = _random.Random(41)
_SH = ["{a}*{b} - {c}", "{a}/({b} + {c})", "{a}*{a} - {b}*{c}", "({a} - {b})*({b} - {c})",
       "{a}*{b}/{c} - {a}", "1/{a} + 1/{b} - {c}*{a}", "({a} + {b})*({a} - {c})*{b}"]
both = ztl_only = false_ok = tried = 0
for _ in range(150):
    names = [f"p{i}" for i in range(_rng.randint(1, 3))]
    bxs = {}
    for n in names:
        a = F(_rng.randint(1, 30), _rng.randint(1, 4))
        bxs[n] = (a, a + F(_rng.randint(1, 20), _rng.randint(1, 4)))
    text = _rng.choice(_SH).format(a=_rng.choice(names), b=_rng.choice(names), c=_rng.choice(names))
    law = [f"y == {text}"]
    pts = [dict(zip(names, c)) for c in __import__("itertools").product(*[bxs[n] for n in names])]
    pts += [{n: a + (b - a) * F(_rng.randint(0, 100), 100) for n, (a, b) in bxs.items()} for _ in range(20)]
    top = max(C._val(C._eq(law[0])[1], p) for p in pts)
    bound = top + (abs(top) + 1) / 50
    got = _K.prove(text, {}, bxs, "<=", bound)
    if "proved" not in got:
        continue
    tried += 1
    agree = C.check_certificate(law, {}, bxs, ["y"], "y", "<=", bound, got["cert"])[0]
    both += agree; ztl_only += not agree
    false_ok += C.check_certificate(law, {}, bxs, ["y"], "y", "<=", top - (abs(top) + 1) / 50, got["cert"])[0]
check(f"J9 at random: {tried} certificates ZTL accepted — the checker re-checked {both}, could not {ztl_only}; "
      f"false bounds (below a sampled value) accepted by the checker: {false_ok}",
      tried >= 100 and false_ok == 0 and both >= tried * 9 // 10, f"{tried} {both} {ztl_only} {false_ok}")

# 9. Z6: a quantity that depends on unknowns SOLVED from a system — the stand solves the linear laws
#    symbolically (sympy, untrusted), ZTL checks the certificate, the checker re-derives by its own Cramer
r = task("t9-load-power-system")
check("t9 the load power written as a circuit (P == VL*I, VL and I from the loop): the same answer as t8 — "
      "Rs = 11 EARNED by a certificate (before: OPEN at 11, earned at 33)",
      r["verdict"] == "EARNED" and r["design"]["Rs"]["R"]["nominal"] == "11" and r["undecided"] == 0
      and "the checker re-checked" in r["how"]["P"], json.dumps(r)[:400])
r = task("t9b-load-power-system-refuted")
check("t9b as a circuit: REFUTED at an interior point (before: 16 designs OPEN)",
      r["verdict"] == "REFUTED" and r["undecided"] == 0 and r["its_violating_point"]["RL"] not in ("1", "1000"),
      json.dumps(r)[:300])
real_sl = K.solve_linear


def wrong_solution(linear, unknowns):
    sol = real_sl(linear, unknowns)
    return dict(sol, I=sol["I"].replace("Rs__R", "(2*Rs__R)")) if sol else sol   # I = V/(RL + 2*Rs): false


K.solve_linear = wrong_solution
r = task("t9-load-power-system")
K.solve_linear = real_sl
check("MUTATION: the stand's symbolic solution made wrong — ZTL, solving the system ITSELF, refuses the certificate "
      "built on it (before c94bc5b only the checker caught this): Rs = 10, which truly fails, is not earned",
      r["design"]["Rs"]["R"]["nominal"] != "10" and "ZTL solved the linear system itself" in r["how"]["P"],
      json.dumps(r)[:300])
check("t9: ZTL solved the circuit's system itself (the stand's solution is used only to search)",
      "ZTL solved the linear system itself" in task("t9-load-power-system")["how"]["P"])
laws9 = ["Vs - VL == I*Rs__R", "VL == I*RL", "P == VL*I"]
e9 = C.explicit_expression(laws9, ["I", "VL", "P"], "P")
pts = [{"Vs": F(5), "Rs__R": F(a), "RL": F(b)} for a in (1, 7, 10) for b in (3, 10, 50)]
check("the checker's own Cramer expression equals the solved system at 9 points (exact)",
      all(C._val(e9, p) == C.solve_at(laws9, p, ["I", "VL", "P"])["P"] for p in pts))

# 10. TWO shared parameters (two steel batches, each in several stiffnesses): ZTL's rank-many rule
#     refuses; the stand decides through certificates the kernel checks on its own solved system
import itertools as _it                     # noqa: E402
r = task("t7c-truss-two-batches")
check("t7c two batches: EARNED and optimal (B2 = 150, the two cheaper refuted), every requirement through a "
      "certificate ZTL checked on its own solution (before: all 81 designs OPEN)",
      r["verdict"] == "EARNED" and r["design"]["B2"]["A"]["nominal"] == "150" and r["objective"]["optimal"]
      and all("ZTL solved the linear system itself" in h for h in r["how"].values()), json.dumps(r)[:400])
b7 = B.load(json.load(open(T / "t7c-truss-two-batches.json", encoding="utf-8")))
laws7 = [B.compile_expr(l["zfl"], b7.get("define")) for l in b7["laws"]]
d7 = next(d for d in S.designs(b7) if d["B2"][1]["A"][0] == F(150) and all(d[k][1]["A"][0] == F(100) for k in ("B1", "B3", "B4")))
fx7, bx7, dv7, _ = S.frame(b7, d7)
nm7 = sorted(bx7)
worst = {}
for t in _it.product(*[[bx7[n][0] + (bx7[n][1] - bx7[n][0]) * F(i, 6) for i in range(7)] for n in nm7]):
    v = C.solve_at(laws7, dict(fx7, **dict(zip(nm7, t))), dv7)
    for q in ("s1", "s2", "s3", "s4"):
        worst[q] = max(worst.get(q, 0), abs(v[q]))
    worst["uy"] = min(worst.get("uy", 0), v["uy"])
check(f"t7c, the earned design sampled independently on a 7^4 grid (2401 points, exact): max |s| "
      f"{float(max(worst[q] for q in ('s1','s2','s3','s4')))/1e6:.1f} MPa <= 112, min uy {float(worst['uy'])*1e3:.3f} mm >= -2.3",
      all(worst[q] <= F(112) * 10**6 for q in ("s1", "s2", "s3", "s4")) and worst["uy"] >= F(-23, 10000))

# 11. ZTL's range exact WITH interior critical points leaves the requirement, no corner does:
#     the failing point is INSIDE — searched, not left OPEN (2026-10-10)
r = task("t10-interior-peak-critical")
check("t10 x = p/(1+p^2) <= 0.45 on p in 1/4..4: nominal and corners pass, REFUTED at an interior point the "
      "checker recomputed (before: OPEN)",
      r["verdict"] == "REFUTED" and r["failed_at_nominal"] == 0 and r["its_violating_point"]["p"] not in ("1/4", "4"),
      json.dumps(r)[:300])
from ustand import certify as _K1          # noqa: E402
_rp = _K1.prove
_K1.prove = lambda *a, **k: {"proved": 1, "cert": {"leaf": "interval"}}
r = task("t10-interior-peak-critical")
_K1.prove = _rp
check("MUTATION: a certificate check that 'proves' the bound ZTL's exact range contradicts -> STAND FAULT",
      r["verdict"] == "STAND FAULT", json.dumps(r)[:200])

# 12. OPERATING MODES (J8): the design must hold in every mode at once
r = task("t11-heatsink-two-modes-refuted")
check("t11 heatsink, full load (Tj <= 125) and cold idle (Tj >= -6): no catalog design holds both — REFUTED, "
      "the failing mode named, Tj = -827/125 at Ta = -10 (checked by hand)",
      r["verdict"] == "REFUTED" and r["failing_mode"] == "cold idle" and r["value_there"]["Tj"].startswith("-827/125"),
      json.dumps(r)[:300])
check("minimal_conflicts ACROSS MODES: neither mode's requirement alone, only the pair conflicts — named with "
      "its mode", (r.get("minimal_conflicts") or {}).get("sets") == [["[full load] max junction temperature",
                                                                       "[cold idle] no ice on the die at idle"]],
      str(r.get("minimal_conflicts"))[:300])
r = task("t11b-heatsink-two-modes-earned")
check("t11b the same with Tj >= -7 at idle: EARNED and optimal (HS 1.2, pad 0.5, 7.1), guaranteed per mode",
      r["verdict"] == "EARNED" and r["objective"]["optimal"] and r["objective"]["value"].startswith("71/10")
      and r["per_mode"]["full load"]["guaranteed"]["Tj"][1].startswith("1143/10")
      and r["per_mode"]["cold idle"]["guaranteed"]["Tj"][0].startswith("-827/125"), json.dumps(r)[:300])
same = []
for name in ("divider-1pct-req-1pct", "divider-1pct-req-0.5pct", "power-16thW-only"):
    b0 = ex(name)
    b1 = dict(b0, requirements=[], modes={"only": {"requirements": b0["requirements"]}})
    r0, r1 = S.run(b0, conflicts=False), S.run(b1)
    same.append((r0["verdict"], r0.get("design")) == (r1["verdict"], r1.get("design")))
for name in ("t1-thermal-heatsink", "t5-divider-tcr", "t8-load-power-peak-inside"):
    b0 = json.load(open(T / f"{name}.json", encoding="utf-8"))
    b1 = dict(b0, requirements=[], modes={"only": {"requirements": b0["requirements"]}})
    r0, r1 = S.run(b0, conflicts=False), S.run(b1)
    same.append((r0["verdict"], r0.get("design")) == (r1["verdict"], r1.get("design")))
check(f"one mode equal to the plain brick gives the same verdict and design on 6 examples: {same}", all(same))
bad = dict(ex("divider-1pct-req-1pct"), modes={"x": {"quantities": {"Vout": {"value": "1"}},
                                                     "requirements": []}})
check("a mode overriding a DERIVED quantity is a BRICK ERROR", S.run(bad)["verdict"] == "BRICK ERROR", str(S.run(bad))[:200])

# 13. VOCABULARY after the blind test (G3 units, G4 bounds as expressions, G7 constants)
from ustand import units as U                       # noqa: E402
ok_units = all(U.parse(u)[0] == want for u, want in (("J/(kg*K)", 1), ("m^3/h", F(1, 3600)), ("L/(h*kg)", F(1, 3600000)),
                                                      ("kWh", 3600000), ("Ah", 3600), ("cm^4", F(1, 10**8)), ("mL", F(1, 10**6)),
                                                      ("bar", 10**5), ("EUR/day", F(1, 86400))))
check("units: parentheses, h, min, L, mol, Ah, Wh, bar, dB, currencies, the c prefix", ok_units)
try:
    U.parse("USD/EUR"); usd_eur = U.parse("USD")[1] != U.parse("EUR")[1]
except U.UnitError:
    usd_eur = False
check("each currency is its own dimension (USD + EUR is a unit error, a rate is a quantity)", usd_eur)
b13 = json.load(open(T / "t3-rc-cutoff.json", encoding="utf-8"))
r_decl = S.run(b13, conflicts=False)
b13b = json.loads(json.dumps(b13)); del b13b["quantities"]["pi"]
r_built = S.run(b13b, conflicts=False)
check("pi undeclared: the built-in bracket is used — same verdict and design as the brick's own pi",
      r_decl["verdict"] == r_built["verdict"] and r_decl.get("closest_design") == r_built.get("closest_design"), str(r_built)[:200])
check("load never edits the caller's brick (the constant went into a copy)", "pi" not in b13b["quantities"])
b14 = ex("power-16thW-or-quarterW")
b14e = json.loads(json.dumps(b14))
for q in b14e["requirements"]:
    if q["value"] == "R1.P":
        q["value"] = "R1.P*2/2"
    if q["quantity"] == "Vout":
        q["value"] = ["2.5*99/100", "2.5*101/100"]
r0, r1 = S.run(b14, conflicts=False), S.run(b14e, conflicts=False)
check("bounds as expressions: R1.P*2/2 and 2.5*99/100 decide exactly as R1.P and 2.475",
      (r0["verdict"], r0.get("design")) == (r1["verdict"], r1.get("design")), str(r1)[:200])
b15 = json.loads(json.dumps(b14)); b15["requirements"][2]["value"] = "R1.P*R1.P"
check("a bound whose dimension is not the quantity's (W*W for a W) is a BRICK ERROR",
      S.run(b15, conflicts=False)["verdict"] == "BRICK ERROR")
b16 = ex("divider-1pct-req-1pct"); b16["quantities"]["Vin"] = {"role": "given", "value": "5", "tolerance": "0.02", "unit": "V"}
b16["requirements"] = [{"quantity": "Vout", "op": "within", "value": ["Vin*49/100", "Vin*51/100"], "why": "ratiometric"}]
r16 = S.run(b16, conflicts=False)
check("a ratiometric window Vin*0.49..Vin*0.51 with Vin +-2% (true ratio 0.495..0.505): OPEN, not a false STAND FAULT "
      "— the bound's least favourable end is taken apart from Vout, so the correlation is lost and it is said",
      r16["verdict"] == "OPEN", str(r16)[:200])
b17 = json.loads(json.dumps(b16)); b17["quantities"]["k"] = {"role": "derived", "unit": ""}
b17["laws"].append({"zfl": "Vout == k*Vin", "source": "the ratio"})
b17["requirements"] = [{"quantity": "k", "op": "within", "value": ["0.49", "0.51"], "why": "ratiometric"}]
r17 = S.run(b17, conflicts=False)
check("the same window written as the RATIO k (Vout == k*Vin): EARNED — the correlation kept",
      r17["verdict"] == "EARNED", str(r17)[:200])

# 14. EVERY DESIGN'S OUTCOME (G5): which pass, and why each other fails
b18 = json.load(open(EX / "blind" / "b01.json", encoding="utf-8")); b18["report"] = "all"
r18 = S.run(b18, conflicts=False)
v18 = [o["verdict"] for o in r18["designs"]]
check("valve springs, report all: S2 the only EARNED, each other REFUTED with the requirement it fails and by how much "
      "(S1 installed force short by ~2.06 N; S3 shear stress over by ~8.67 MPa; S4 full-lift force over by ~2.81 N)",
      v18 == ["REFUTED", "EARNED", "REFUTED", "REFUTED"] and r18["objective"]["optimal"]
      and "installed" in r18["designs"][0]["fails"] and "stress" in r18["designs"][2]["fails"], json.dumps(r18["designs"])[:400])
r19 = S.run(json.load(open(EX / "blind" / "b01.json", encoding="utf-8")), conflicts=False)
check("without report all: the same verdict, the list stops at the first EARNED", [o["verdict"] for o in r19["designs"]] == ["REFUTED", "EARNED"]
      and r19["design"] == r18["design"])
b20 = json.load(open(T / "t11b-heatsink-two-modes-earned.json", encoding="utf-8")); b20["report"] = "all"
r20 = S.run(b20)
check("with modes, report all: every design listed, each REFUTED one names its failing mode",
      len(r20["designs"]) == 8 and all("mode" in o for o in r20["designs"] if o["verdict"] == "REFUTED")
      and r20["objective"]["optimal"], json.dumps(r20.get("designs"))[:300])

# 15. FUNCTIONS (G1): the blind problems rewritten with the real ln, sqrt, exp, pow, min, atan, tan —
#     the same answers the blind authors reached with their hand approximations
def outs(r):
    # the label's own value (labels are listed first in a design's name since 2026-10-10)
    return [(re.split(r"[,)]", o["design"].split("name=")[-1].split("label=")[-1])[0], o["verdict"])
            for o in r["designs"]]


r = task("t12-rocket-motor-functions")
check("rocket motor with the real ln (Tsiolkovsky) and sqrt (rail speed): REFUTED like the blind author's — M4 closest, "
      "v_rail 14.989 < 15 m/s; M3 fails the acceleration limit",
      r["verdict"] == "REFUTED" and r["value_there"]["v_rail"][0].startswith("~14.988")
      and any(o["verdict"] == "REFUTED" and "a_max" in o["fails"] for o in r["designs"]), json.dumps(r)[:300])
r = task("t13-dosing-functions")
check("dosing with the real exp: every regimen REFUTED (the author's corner scan with the true exp agrees)",
      r["verdict"] == "REFUTED" and len(r["designs"]) == 5 and all(o["verdict"] == "REFUTED" for o in r["designs"]),
      json.dumps(r)[:300])
r = task("t14-mortgage-functions")
check("mortgage with the real annuity (pow) and the rate cap (min): L2 the only feasible product, as the author found",
      r["verdict"] == "EARNED" and [v for _, v in outs(r)] == ["REFUTED", "EARNED", "REFUTED", "REFUTED"], json.dumps(r)[:300])
r = task("t15-lens-trig")
check("lens with the real atan and tan: L4 the only lens that holds W and s, as the author found",
      r["verdict"] == "EARNED" and [n for n, v in outs(r) if v == "EARNED"] == ["L4"], json.dumps(outs(r)))
b21 = json.load(open(T / "t13-dosing-functions.json", encoding="utf-8"))
b21["laws"][1]["zfl"] = "Cmin == Cmax*exp(REG.tau)"
check("exp of a time (unit h): a BRICK ERROR — a transcendental function reads a dimensionless argument",
      S.run(b21, conflicts=False)["verdict"] == "BRICK ERROR")
b22 = json.load(open(T / "t13-dosing-functions.json", encoding="utf-8"))
b22["laws"][0]["zfl"] = "Cmax == (REG.dose/V)/(1 - sinh(0 - k*REG.tau))"   # sin exists since 2026-10-13
r22 = S.run(b22, conflicts=False)
check("an unknown function (sinh): a BRICK ERROR naming the functions that exist", r22["verdict"] == "BRICK ERROR"
      and "only these functions exist" in r22["why"], str(r22)[:200])

# 16. A LAW'S DOMAIN (G8) and strict bounds
r = task("t16b-servers-no-domain-WRONG")
check("WITHOUT the law's domain the stand 'earns' I1 x 2 — mu 220 < lambda/N 900, a negative M/M/1 latency: "
      "kept as the warning the blind author found", r["verdict"] == "EARNED" and r["design"]["INST"]["type"] == "I1",
      str(r.get("design"))[:150])
r = task("t16-servers-law-domain")
check("WITH \"valid\": \"INST.mu > lam/CNT.N\": I1 x 2 REFUTED as outside the law's domain; I2 x 7 EARNED (the author's optimum)",
      r["verdict"] == "EARNED" and r["design"]["INST"]["type"] == "I2" and r["design"]["CNT"]["N"]["nominal"] == "7"
      and r["designs"][0]["verdict"] == "REFUTED" and "holds only where" in r["designs"][0]["fails"], json.dumps(r["designs"][:2])[:300])
w = B.Win(F(0), None, True, False)
check("a strict bound: 0 does not satisfy > 0, and a value exactly 0 violates it",
      not B.inside(F(0), F(1), w) and B.violates(F(0), w) and B.inside(F(1, 10**9), F(1), w))

# 17. MODE-SPECIFIC DEFINES AND LAWS (G9)
r = task("t17-servers-modes-define")
check("servers, normal (N_active = N) and degraded (a mode define N_active = N - 1): I2 x 7 EARNED and OPTIMAL "
      "— every cheaper design refuted in some mode (the blind author had to duplicate every law by hand)",
      r["verdict"] == "EARNED" and r["design"]["INST"]["type"] == "I2" and r["design"]["CNT"]["N"]["nominal"] == "7"
      and r["objective"]["optimal"], json.dumps(r.get("objective")))

# 18. IMPLICIT LAWS (G6): an operating point where two curves meet; ZTL checks a root-exclusion
#     certificate the stand searched, the checker finds its own enclosure (and confirms ZTL's ends)
r = task("t18-fan-implicit")
hot = r.get("per_mode", {}).get("hot", {}).get("guaranteed", {}).get("Tout", ["", ""])
check("fan (blind b02) with the REAL operating point pmax(1 - Q/Qmax) = K Q^2: F3 EARNED and OPTIMAL; hot Tout <= "
      "54.9706 C — the blind author's true root 54.97 vs the limit 55 (they used a 7-fold fixed-point bound)",
      r["verdict"] == "EARNED" and r["design"]["F"]["price"]["nominal"] == "19" and r["objective"]["optimal"]
      and hot[1].startswith("~54.9706"), json.dumps(hot))
pump = task("t19-pump-implicit")
pump_all = dict(json.load(open(T / "t19-pump-implicit.json", encoding="utf-8")))
check("pump (blind b03) with Swamee-Jain friction AT THE FLOW ITSELF (log10, Re^0.9): P2 EARNED, optimal; "
      "Q in [9.288, 12.729] m3/h (the author's frozen-f answer: 9.2..12.8); P <= 1500 W by a certificate "
      "with Q as a box of its proved range",
      pump["verdict"] == "EARNED" and pump["design"]["PUMP"]["price"]["nominal"] == "510" and pump["objective"]["optimal"]
      and pump["guaranteed"]["Q"][0].endswith("(~9.28796)") and pump["guaranteed"]["Q"][1].endswith("(~12.7289)")
      and "certificate" in pump["how"]["P"], json.dumps(pump.get("guaranteed")))

def imp(laws, search=("-3", "3"), p=("1", "4"), req=("<=", "5"), extra=None):
    b = {"stand": "universal-stand/1",
         "quantities": {"p": {"role": "given", "range": list(p), "unit": ""},
                        "x": {"role": "derived", "unit": "", "search": list(search)},
                        "y": {"role": "derived", "unit": ""}},
         "slots": {"S": {"from": ["c"]}},
         "catalog": {"c": {"items": [{"k": "1"}], "fields": {"k": {"unit": ""}}}},
         "laws": [{"zfl": l} for l in laws],
         "requirements": [{"quantity": "y", "op": req[0], "value": req[1]}]}
    if extra:
        extra(b)
    return S.run(b, conflicts=False)

r = imp(["x*x*x + x == p", "y == S.k*x*x"], search=("-3", "3"))
check("x^3 + x = p (one root, monotone in p): y = x^2 EARNED inside its bound", r["verdict"] == "EARNED", str(r)[:300])
r = imp(["x*x*x + x == p", "y == S.k*x*x"], req=("<=", "1"))
check("the same, y <= 1: REFUTED at a concrete point (x^2 reaches 1.38 at p = 4), recomputed by the checker",
      r["verdict"] == "REFUTED", str(r)[:300])
r = imp(["x*x == p", "y == S.k*x"], search=("-3", "3"), req=("<=", "3"))
check("x^2 = p: TWO roots (-2..-1 and 1..2) — the enclosure holds both, y = x is bounded by 2: EARNED, not a guess "
      "at one branch", r["verdict"] == "EARNED", str(r)[:300])
r = imp(["x*x == p", "y == S.k*x"], search=("-3", "3"), req=(">=", "0"))
check("x^2 = p, y >= 0: the negative branch exists, so NOT earned (the enclosure keeps it)", r["verdict"] != "EARNED",
      str(r)[:300])
r = imp(["x*x*x + x == p", "y == S.k*x"], search=("2", "3"))
check("no root in the search range for this design: OPEN with the reason, never a value", r["verdict"] == "OPEN"
      and any("no root" in n for n in r.get("checker_could_not_evaluate", [])), str(r)[:300])
for laws, extra, what in [
        (["x == p + 1", "y == S.k*x"], None, "an explicit law with \"search\""),
        (["x*x*x + x == p", "x*x == p + 1", "y == S.k*x"], None, "two implicit laws for one quantity"),
        (["x*x*x + x == p + y", "y == S.k*p"], None, "an implicit law over a derived quantity (version 1)"),
        (["x*x*x + x == p", "y == S.k*x"], lambda b: b["quantities"]["p"].__setitem__("search", ["0", "1"]),
         "\"search\" on a given quantity"),
        (["x*x*x + x == p", "y == S.k*x"], lambda b: b["quantities"]["x"].__setitem__("search", ["3", "-3"]),
         "a search range upside down")]:
    r = imp(laws, extra=extra)
    check(f"refused aloud: {what}", r["verdict"] == "BRICK ERROR", str(r)[:200])

real_impl = J.implicit
def narrowing_impl(*a, **k):
    got, how, cert = real_impl(*a, **k)
    return ((got[1] - (got[1] - got[0]) / 4, got[1]), how, cert) if got else (got, how, cert)
J.implicit = narrowing_impl
try:
    r = imp(["x*x == p", "y == S.k*x"], search=("-3", "3"), req=(">=", "-1.5"))
finally:
    J.implicit = real_impl
check("MUTATION: ZTL hides the negative branch of x^2 = p (reports the top quarter, so y >= -1.5 looks safe); no "
      "corner shows it (each point reads both roots) — the checker's OWN enclosure does: STAND FAULT",
      r["verdict"] == "STAND FAULT", str(r)[:300])

# 19. THE WORST-CASE OBJECTIVE (G11): minimize the objective's worst over the box, not its nominal value
r = task("t20-mortgage-worst-case")
check("mortgage (blind b09), minimize the WORST-CASE total paid: L2 EARNED and optimal, worst total <= 601838.456 "
      "and reached at a corner (the blind author's hand figure 601 838.5)",
      r["verdict"] == "EARNED" and r["design"]["M"]["label"] == "L2" and r["objective"]["optimal"]
      and r["objective"]["value"].startswith("~601838.45579") and r["objective"]["reached_at_least"] == r["objective"]["value"],
      json.dumps(r.get("objective"))[:300])

def wc(items, law="c == P.a + P.b*x*x", case="worst", modes=None):
    b = {"stand": "universal-stand/1",
         "quantities": {"x": {"role": "given", "range": ["0", "1"], "unit": ""}, "c": {"role": "derived", "unit": ""}},
         "slots": {"P": {"from": ["opts"]}},
         "catalog": {"opts": {"items": items, "fields": {"a": {"unit": ""}, "b": {"unit": ""}}}},
         "laws": [{"zfl": law}], "requirements": [{"quantity": "c", "op": "<=", "value": "100"}],
         "objective": {"minimize": "c", "case": case}}
    if modes:
        b["modes"] = modes
    return S.run(b, conflicts=False)

r = wc([{"a": "1", "b": "5", "label": "A"}, {"a": "3", "b": "1", "label": "B"}])
check("worst case reorders: A is cheaper at nominal (2.25 vs 3.25) but B wins the worst case (4 vs 6), proved optimal",
      r["verdict"] == "EARNED" and r["design"]["P"]["label"] == "B" and r["objective"]["optimal"], str(r)[:300])
r = wc([{"a": "1", "b": "4", "label": "A"}, {"a": "5/2", "b": "0", "label": "B"}], law="c == P.a + P.b*x*(1 - x)")
check("a loose bound is NOT called optimal: A's worst (truly 2) is proved only <= 5, so B (2.5) is the best PROVED "
      "and the stand names A as the design that may be lower",
      r["verdict"] == "EARNED" and r["design"]["P"]["label"] == "B" and not r["objective"]["optimal"]
      and "label=A" in r["objective"]["note"], str(r.get("objective"))[:300])
r = wc([{"a": "1", "b": "5", "label": "A"}, {"a": "3", "b": "1", "label": "B"}], case="nominal")
check("I3: a NOMINAL objective naming a derived quantity is read at the nominal point by the laws (x = 1/2): "
      "A costs 1 + 5/4 = 2.25 < B 3.25, so A first",
      r["verdict"] == "EARNED" and r["design"]["P"]["label"] == "A" and r["objective"]["value"].startswith("9/4"),
      str(r.get("objective")))
r = wc([{"a": "1", "b": "5"}], modes={"m1": {"requirements": []}, "m2": {"requirements": []}})
check("worst case with modes: refused aloud (not supported yet)", r["verdict"] == "BRICK ERROR", str(r)[:200])

# 20. EQUIVALENT FORMS (G12) and an OPEN that says why
import copy as _copy
t3 = json.load(open(T / "t3-rc-cutoff.json", encoding="utf-8")); t3["quantities"].pop("pi"); t3["report"] = "all"
t3["requirements"][0]["value"] = ["600", "2000"]
seen = {}
for name, laws in {"tau": ["tau == R.R*C.C", "f == 1/(2*pi*tau)"], "product": ["f*(2*pi*R.R*C.C) == 1"],
                   "quotient": ["f == 1/(2*pi*R.R*C.C)"], "product2": ["2*pi*f*R.R*C.C == 1"]}.items():
    bb = _copy.deepcopy(t3); bb["laws"] = [{"zfl": l} for l in laws]
    if name != "tau":
        bb["quantities"].pop("tau")
    seen[name] = "".join(d["verdict"][0] for d in S.run(bb, conflicts=False)["designs"])
check("G12: four spellings of fc = 1/(2 pi R C) give the SAME verdict on every one of the 216 designs "
      "(the blind b06 author's product form had come out OPEN)", len(set(seen.values())) == 1 and "E" in seen["tau"],
      str({k: v.count("E") for k, v in seen.items()}))
ob = {"stand": "universal-stand/1",
      "quantities": {"x": {"role": "given", "range": ["0", "1"], "unit": ""}, "c": {"role": "derived", "unit": "W"}},
      "slots": {"P": {"from": ["opts"]}},
      "catalog": {"opts": {"items": [{"a": "1", "b": "4"}], "fields": {"a": {"unit": "W"}, "b": {"unit": "W"}}}},
      "laws": [{"zfl": "c == P.a + P.b*x*(1 - x)"}],
      "requirements": [{"quantity": "c", "op": "<", "value": "2.5", "why": "power below 2.5 W"}]}
r = S.run(ob, conflicts=False)
check("an OPEN design says WHICH requirement, the proved range and why it stayed open (blind b06: 'OPEN with no reason')",
      r["verdict"] == "OPEN" and "power below 2.5 W" in r["designs"][0]["why"] and "[1, 5]" in r["designs"][0]["why"]
      and "non-strict" in r["designs"][0]["why"], str(r.get("designs"))[:300])

# 21. BUGS FOUND BY BLIND TEST 2
check("H7: a define named like a catalog field (Uc vs HX.Uc) is NOT substituted inside the field",
      B.compile_expr("HX.Uc*2 + Uc", {"Uc": "HX.Uc0*(1+a)"}) == "HX__Uc*2 + (HX__Uc0*(1+a))",
      B.compile_expr("HX.Uc*2 + Uc", {"Uc": "HX.Uc0*(1+a)"}))
def implicit_brick(law, items, search=("0", "10")):
    return {"stand": "universal-stand/1",
            "quantities": {"p": {"role": "given", "range": ["1", "2"], "unit": ""},
                           "x": {"role": "derived", "unit": "", "search": list(search)},
                           "v": {"role": "derived", "unit": ""}, "y": {"role": "derived", "unit": ""}},
            "slots": {"S": {"from": ["c"]}},
            "catalog": {"c": {"items": items, "fields": {"k": {"unit": ""}, "w": {"unit": ""}}}},
            "laws": [{"zfl": law}, {"zfl": "y == x"}, {"zfl": "v == S.w*p"}],
            "requirements": [{"quantity": "v", "op": "<=", "value": "5", "why": "velocity"},
                             {"quantity": "y", "op": "<=", "value": "10"}],
            "report": "all"}
r = S.run(implicit_brick("min(10 - x, 20 - 3*x) == p*S.k*x", [{"k": "1", "w": "1"}]), conflicts=False)
check("H8: min inside an implicit law (a piecewise fan curve) is read as an enclosure — no STAND ERROR",
      r["verdict"] == "EARNED", str(r)[:300])
r = S.run(implicit_brick("x*x*x + x == p*S.k", [{"k": "1", "w": "10"}, {"k": "2", "w": "1"}], search=("2", "3")),
          conflicts=False)
check("H9: an implicit law with no root no longer hides a refutation that does not depend on it (the duct too "
      "narrow for its velocity limit): w = 10 REFUTED by 'velocity', w = 1 OPEN saying the implicit law has no root",
      r["designs"][0]["verdict"] == "REFUTED" and r["designs"][0]["fails"] == "velocity"
      and r["designs"][1]["verdict"] == "OPEN" and "no root" in r["designs"][1]["why"], str(r.get("designs"))[:300])

# 22. OUTPUT AND SERIES FROM BLIND TEST 2 (H4, H6, H14)
E96_PRINTED = [100, 102, 105, 107, 110, 113, 115, 118, 121, 124, 127, 130, 133, 137, 140, 143, 147, 150, 154, 158,
               162, 165, 169, 174, 178, 182, 187, 191, 196, 200, 205, 210, 215, 221, 226, 232, 237, 243, 249, 255,
               261, 267, 274, 280, 287, 294, 301, 309, 316, 324, 332, 340, 348, 357, 365, 374, 383, 392, 402, 412,
               422, 432, 442, 453, 464, 475, 487, 499, 511, 523, 536, 549, 562, 576, 590, 604, 619, 634, 649, 665,
               681, 698, 715, 732, 750, 768, 787, 806, 825, 845, 866, 887, 909, 931, 953, 976]
check("H4: E96 generated by the IEC rule equals the printed table, E48 is every other value, E192 has 9.20",
      B.E_SERIES["E96"] == E96_PRINTED and B.E_SERIES["E48"] == E96_PRINTED[::2] and 920 in B.E_SERIES["E192"]
      and 919 not in B.E_SERIES["E192"] and len(B.E_SERIES["E192"]) == 192)
items96 = B.items({"series": "E96", "decades": [1000], "fields": {"R": {"series": True, "tolerance": "0.01", "unit": "ohm"}}})
check("H4: an E96 decade of 1000 runs 1000 .. 9760 ohm (as E24's runs 1000 .. 9100)",
      items96[0]["R"][0] == 1000 and items96[-1]["R"][0] == 9760 and len(items96) == 96)
pv = json.load(open(EX / "blind2" / "c09.json", encoding="utf-8")); pv["report"] = "all"
r = S.run(pv, conflicts=False)
check("H6: 576 designs, 5 earned: the cut list shows the EARNED first and counts every verdict (the first 200 by "
      "cost were all refuted and hid them)",
      r["designs_count"] == {"REFUTED": 571, "EARNED": 5} and [d["verdict"] for d in r["designs"][:5]] == ["EARNED"] * 5
      and r["designs_not_listed"] == 376, str(r.get("designs_count")))
r = S.run(json.load(open(EX / "blind2" / "c02.json", encoding="utf-8")), conflicts=False)
check("H14: designs with the SAME objective as the reported optimum are said (bolts at $5.60)",
      r["objective"].get("ties", {}).get("same_objective", 0) > 0, str(r.get("objective"))[:200])

# 23. A STRICT law domain no longer switches certificates off (blind test 2, c06)
bf = json.load(open(EX / "blind2" / "c06.json", encoding="utf-8")); bf.pop("report", None)
bf["catalog"]["systems"]["items"] = bf["catalog"]["systems"]["items"][:1]
bf["catalog"]["mLA"]["integers"].update({"from": "15", "to": "17"})
bf["catalog"]["mLB"]["integers"].update({"from": "34", "to": "36"})
r = S.run(bf, conflicts=False)
check("buffer (blind c06): phosphate 16 + 35 mL EARNED and optimal at $1.02 — the author's true cheapest; it was "
      "OPEN because the law's domain 'valid: > 0' (strict, already met) switched every certificate off",
      r["verdict"] == "EARNED" and r["objective"]["value"].startswith("51/50") and r["objective"]["optimal"]
      and r["design"]["VA"]["N"]["nominal"] == "16" and r["design"]["VB"]["N"]["nominal"] == "35",
      json.dumps(r.get("objective"))[:200])

# 24. WHERE and COMPUTED (blind test 2: c09 strings per input, c06 windows, c10 pairs)
r = task("t21-pv-computed-where")
check("PV (blind c09) with computed spi = ceil(NP / inputs) and where NP <= 2*inputs: the author's answer — "
      "M-380 / INV-10, 16 x 2, 6380, optimal; 576 of 1152 combinations excluded by where",
      r["verdict"] == "EARNED" and r["objective"]["value"] == "6380" and r["objective"]["optimal"]
      and r["excluded_by_where"] == 576 and r["design"]["STR"]["NP"]["nominal"] == "2", str(r.get("objective")))
def ww(where=None, computed=None, law="y == S.k*x", unit_k=""):
    b = {"stand": "universal-stand/1",
         "quantities": {"x": {"role": "given", "value": "2", "unit": ""},
                        "L": {"role": "given", "value": "3", "unit": "mL"},
                        "y": {"role": "derived", "unit": ""}},
         "slots": {"S": {"from": ["c"]}},
         "catalog": {"c": {"items": [{"k": "1", "v": "2", "t": {"value": "5", "tolerance": "0.1"}, "name": "a"},
                                     {"k": "3", "v": "4", "t": {"value": "5", "tolerance": "0.1"}, "name": "b"}],
                           "fields": {"k": {"unit": unit_k}, "v": {"unit": "mL"}, "t": {"unit": ""}}}},
         "laws": [{"zfl": law}], "requirements": [{"quantity": "y", "op": "<=", "value": "100"}], "report": "all"}
    if where is not None:
        b["where"] = where
    if computed is not None:
        b["computed"] = computed
    return S.run(b, conflicts=False)
r = ww(where=['S.name == "b"'])
check("where on a label: only item b is a design (1 excluded)", r["verdict"] == "EARNED"
      and r["excluded_by_where"] == 1 and len(r["designs"]) == 1, str(r)[:200])
r = ww(where=["S.v <= L"])
check("where comparing two quantities in mL: exact, in SI (item a: 2 mL <= 3 mL; b excluded)",
      r["excluded_by_where"] == 1 and "k=1" in r["designs"][0]["design"], str(r)[:200])
r = ww(where=["S.v <= 3"])
check("where with a bare number beside mL: refused aloud (it would be read as 3 m^3)",
      r["verdict"] == "BRICK ERROR" and "bare number" in r["why"], str(r)[:200])
r = ww(where=["S.t <= 6"])
check("where reading a toleranced field: refused aloud (exact values only)",
      r["verdict"] == "BRICK ERROR" and "exact" in r["why"], str(r)[:200])
r = ww(computed={"m": "max(S.k, 2)"}, law="y == m*x")
check("computed m = max(k, 2) is an exact value per design: y = 4 and 6, both EARNED",
      r["verdict"] == "EARNED" and r["designs_count"] == {"EARNED": 2}, str(r)[:300])
r = ww(computed={"m": {"value": "S.v", "unit": ""}}, law="y == m*x")
check("computed with a declared unit that does not match its expression (mL declared dimensionless): refused",
      r["verdict"] == "BRICK ERROR" and "declared unit" in r["why"], str(r)[:200])
r = ww(computed={"m": "ceil(S.v / L)"}, law="y == m*x")
check("ceil of a ratio of two mL quantities: exact (ceil(2/3) = 1, ceil(4/3) = 2)",
      r["verdict"] == "EARNED", str(r)[:200])

# 25. BRANCHES: if(A > B, a, b) (blind test 2: Euler or Johnson, eps-NTU at Cr = 1)
check("if compiles to the one branch every reader knows; >= and <= swap the branches (the boundary stays where "
      "the author put it)",
      B.compile_expr("if(x > 1, a, b)") == "ifpos(x - 1, a, b)" and B.compile_expr("if(x >= 1, a, b)") == "ifpos(1 - x, b, a)"
      and B.compile_expr("if(x < 1, a, b)") == "ifpos(1 - x, a, b)" and B.compile_expr("if(x <= 1, a, b)") == "ifpos(x - 1, b, a)")
r = task("t22-columns-branch")
check("columns (blind c05) with the textbook Euler/Johnson branch as if(...): the author's answer (203.9, optimal, "
      "2 earned pairs) without the min/max identity the author had to prove by hand",
      r["verdict"] == "EARNED" and r["objective"]["value"].startswith("2039/10") and r["objective"]["optimal"], str(r)[:300])
def brb(law, req=("<=", "5"), x=("0", "2")):
    b = {"stand": "universal-stand/1",
         "quantities": {"x": {"role": "given", "range": list(x), "unit": ""}, "y": {"role": "derived", "unit": ""}},
         "slots": {"S": {"from": ["c"]}}, "catalog": {"c": {"items": [{"k": "1"}], "fields": {"k": {"unit": ""}}}},
         "laws": [{"zfl": law}], "requirements": [{"quantity": "y", "op": req[0], "value": req[1]}]}
    return S.run(b, conflicts=False)
r = brb("y == S.k*if(x > 1, 10, 0)", req=(">=", "5"))
check("a JUMP: y = 10 where x > 1, else 0, required >= 5 over x in [0, 2]: REFUTED at a point (never 'monotone')",
      r["verdict"] == "REFUTED", str(r)[:200])
r = brb("y == S.k*if(x > 1, 10, 0)", req=(">=", "5"), x=("1.5", "2"))
check("the same jump where the branch is decided (x in [1.5, 2]): EARNED, y = 10", r["verdict"] == "EARNED", str(r)[:200])
r = brb("y == if(x == 1, 1, 2)")
check("if with == : refused aloud (< <= > >= only)", r["verdict"] == "BRICK ERROR", str(r)[:200])

# 26. FROM BLIND TEST 3: the checker's corners per independent group (I5), max on the certificate path (I8),
#     the certificate's proved end labelled (I4)
q26 = {f"a{i}": {"role": "given", "value": "1", "tolerance": "0.1", "unit": ""} for i in range(20)}
q26.update({f"y{i}": {"role": "derived", "unit": ""} for i in range(10)})
b26 = {"stand": "universal-stand/1", "quantities": q26, "slots": {"S": {"from": ["c"]}},
       "catalog": {"c": {"items": [{"k": "1"}], "fields": {"k": {"unit": ""}}}},
       "laws": [{"zfl": f"y{i} == S.k*a{2*i} + a{2*i+1}"} for i in range(10)],
       "requirements": [{"quantity": f"y{i}", "op": "<=", "value": "2.3"} for i in range(10)]}
r = S.run(b26, conflicts=False)
check("I5: 20 toleranced quantities in 10 INDEPENDENT laws — the checker enumerates corners per group (40, not "
      "2^20) and confirms: EARNED", r["verdict"] == "EARNED", str(r)[:300])
r = S.run({"stand": "universal-stand/1",
           "quantities": {"x": {"role": "given", "range": ["0", "2"], "unit": ""}, "y": {"role": "derived", "unit": ""}},
           "slots": {"S": {"from": ["c"]}}, "catalog": {"c": {"items": [{"k": "1"}], "fields": {"k": {"unit": ""}}}},
           "laws": [{"zfl": "y == max(0, x - 1)*S.k + x*(2 - x)"}],
           "requirements": [{"quantity": "y", "op": "<=", "value": "1.3"}]}, conflicts=False)
check("I8: max inside an expression decided by a certificate (true peak 1.25 <= 1.3): EARNED by interval leaves, "
      "no STAND ERROR", r["verdict"] == "EARNED" and "certificate" in r["how"]["y"], str(r)[:300])
r = S.run(json.load(open(EX / "blind3" / "c03.json", encoding="utf-8")), conflicts=False)
check("I4: an end a certificate proved is labelled as such (the accumulator's 6.8 L is the bound, not the minimum)",
      r["verdict"] == "EARNED" and "dVf" in r.get("guaranteed_ends", {}), str(r.get("guaranteed_ends")))

# 27. nominal() in computed (I3: the cost needed nominal values of toleranced data)
r = ww(computed={"m": "nominal(S.t) + 1"}, law="y == m*x")
check("nominal(S.t) in computed reads the toleranced field at its nominal (5): y = 12 for both items, EARNED",
      r["verdict"] == "EARNED", str(r)[:300])
r = ww(computed={"m": "S.t + 1"}, law="y == m*x")
check("without nominal() the same toleranced field is refused in computed (exact values only)",
      r["verdict"] == "BRICK ERROR", str(r)[:200])

r = task("t23-wind-nominal-objective")
check("I3: wind turbine (blind c04) — the objective names the derived energy E, read at the nominal point: "
      "30.348 EUR/MWh, the blind author's hand-duplicated model gave 30.35; shown in its own unit",
      r["verdict"] == "EARNED" and r["objective"]["value"].startswith("~30.3478") and r["objective"]["unit"] == "EUR/MWh",
      str(r.get("objective")))

# 28. GROUP PRUNING (I1, blind test 3 c11): whole runs of the catalog refuted at once, by two enclosures
from ustand import prune as P
def prb():
    return {"stand": "universal-stand/1",
            "quantities": {"x": {"role": "given", "range": ["1", "2"], "unit": ""}, "y": {"role": "derived", "unit": ""},
                           "z": {"role": "derived", "unit": ""}},
            "slots": {"A": {"from": ["n"]}, "B": {"from": ["n"]}},
            "catalog": {"n": {"integers": {"field": "N", "from": "0", "to": "60", "unit": ""}}},
            "laws": [{"zfl": "y == A.N*x + B.N*B.N/10"}, {"zfl": "z == A.N - B.N"}],
            "requirements": [{"quantity": "y", "op": "<=", "value": "150"}, {"quantity": "z", "op": ">=", "value": "-20"}],
            "objective": {"minimize": "100 - A.N - B.N"}, "report": "all"}
cap_was, S.MAX_OUTCOMES = S.MAX_OUTCOMES, 10 ** 6          # compare the WHOLE lists, not the first 200
r_p = S.run(prb(), conflicts=False)
P.PRUNE_MIN = 10 ** 12
r_0 = S.run(prb(), conflicts=False)
P.PRUNE_MIN = 2000
earned = lambda r: sorted(d["design"] for d in r["designs"] if d["verdict"] == "EARNED")
check("pruning: the same verdict, objective and EARNED set as judging all 3721 designs one by one; "
      f"{r_p.get('refuted_by_groups')} designs refuted in groups",
      r_p["verdict"] == r_0["verdict"] and r_p["objective"]["value"] == r_0["objective"]["value"]
      and earned(r_p) == earned(r_0) and (r_p.get("refuted_by_groups") or 0) > 1000
      and sum(r_p["designs_count"].values()) - r_p["groups_pruned"] + r_p["refuted_by_groups"] == 3721,
      (r_p["verdict"], r_0["verdict"], r_p.get("refuted_by_groups"), r_p.get("designs_count")))
real_z = P.ztl_ranges
P.ztl_ranges = lambda laws, fixed, boxes, derived, grounds: {d: (F(10 ** 6), F(10 ** 6 + 1)) for d in derived}
try:
    r_m = S.run(prb(), conflicts=False)
finally:
    P.ztl_ranges = real_z
    S.MAX_OUTCOMES = cap_was
check("MUTATION: ZTL claims every group violates (its readings lie) — the checker's own enclosure refuses, no "
      "group is pruned wrongly: the same EARNED set",
      earned(r_m) == earned(r_0), (len(earned(r_m)), len(earned(r_0))))

import time as _time
_t = _time.time()
r = S.run(json.load(open(EX / "scale" / "s3-acoustics-full.json", encoding="utf-8")), conflicts=False)
check("I1: room acoustics (blind c11) over the FULL integer space 0..125 per panel type (2 M combinations; the "
      "author's runs were killed at 15 min): REFUTED in groups within a minute — the author's own scan of all "
      "333k feasible-sum triples found none",
      r["verdict"] == "REFUTED" and r["refuted_by_groups"] > 1900000 and _time.time() - _t < 60,
      (r.get("verdict"), r.get("refuted_by_groups"), r.get("groups_pruned"), round(_time.time() - _t, 1)))

# 28b. GROUP PRUNING OVER A LINEAR SYSTEM: the checker reads the requirement through its own Cramer solution
_tcat = lambda: {"series": "E24", "decades": [100, 1000],
                 "fields": {"R": {"series": True, "tolerance": "0.01", "unit": "ohm"}}}
tnet = {"stand": "universal-stand/1",
        "quantities": {"V": {"role": "given", "value": "12", "tolerance": "0.02", "unit": "V"},
                       "I1": {"role": "derived", "unit": "A"}, "I2": {"role": "derived", "unit": "A"}},
        "slots": {"A": {"from": ["ra"]}, "Bb": {"from": ["rb"]}, "Cc": {"from": ["rc"]}},
        "catalog": {"ra": _tcat(), "rb": _tcat(), "rc": _tcat()},
        "laws": [{"zfl": "A.R*I1 + Cc.R*(I1 - I2) == V"}, {"zfl": "Bb.R*I2 + Cc.R*(I2 - I1) == 0"}],
        "requirements": [{"quantity": "I2", "op": "within", "value": ["0.0100", "0.0102"], "why": "load current"}]}
r = S.run(tnet, conflicts=False)
check("pruning over a LINEAR SYSTEM (a T-network, two loop laws, 110 592 designs): REFUTED as without pruning "
      "(measured 2026-10-10: the same verdict, 15.1 s), whole groups cut by ZTL and the checker's Cramer reading",
      r["verdict"] == "REFUTED" and (r.get("refuted_by_groups") or 0) > 40000, (r.get("verdict"), r.get("refuted_by_groups")))

# 29. CONTINUOUS CHOICES (I2): the solver's cheapest robust mix judged by the stand; ZTL proves the lower bound
cdiet = {"stand": "universal-stand/1",
         "quantities": {"pa": {"role": "given", "value": "0.10", "tolerance": "0.1", "unit": ""},
                        "pb": {"role": "given", "value": "0.40", "tolerance": "0.1", "unit": ""},
                        "P": {"role": "derived", "unit": ""}, "T": {"role": "derived", "unit": ""}},
         "slots": {"A": {"from": ["ia"]}, "Bs": {"from": ["ib"]}},
         "catalog": {"ia": {"continuous": {"field": "x", "from": "0", "to": "1", "unit": ""}},
                     "ib": {"continuous": {"field": "x", "from": "0", "to": "1", "unit": ""}}},
         "laws": [{"zfl": "P == pa*A.x + pb*Bs.x"}, {"zfl": "T == A.x + Bs.x"}],
         "requirements": [{"quantity": "P", "op": ">=", "value": "0.25"}, {"quantity": "T", "op": "within", "value": ["1", "1"]}],
         "objective": {"minimize": "2*A.x + 3*Bs.x"}}
r = S.run(cdiet, conflicts=False)
gap = B.num(r["objective"]["gap"].split(" ")[0]) if r.get("objective") and r["objective"].get("gap") else None
check("I2: a two-ingredient diet with uncertain protein: the solver's mix (0.4074 / 0.5926) is EARNED by the stand; "
      "ZTL proves no mix costs less than L, the gap below 1e-6 (the robust optimum 70/27)",
      r["verdict"] == "EARNED" and gap is not None and 0 <= gap < F(1, 10 ** 6)
      and r["objective"]["value"].endswith("(~2.59259)"), str(r.get("objective"))[:300])

bad_diet = _copy.deepcopy(cdiet)
bad_diet["requirements"][0]["value"] = "0.5"
r = S.run(bad_diet, conflicts=False)
check("Farkas: the diet asking protein 0.5 (0.44 at most): REFUTED — ZTL PROVES no mix exists (it was 'the LP "
      "found none, not a proof': OPEN)", r["verdict"] == "REFUTED" and r.get("combinations_proved_without_mix") == 1
      and "Farkas" in r["why"], str(r)[:400])
two = _copy.deepcopy(bad_diet)
two["quantities"]["P"] = {"role": "derived", "unit": ""}
two["slots"]["S"] = {"from": ["supp"]}
two["catalog"]["supp"] = {"items": [{"id": "none", "boost": "0"}, {"id": "premix", "boost": "0.2"}],
                          "fields": {"boost": {"unit": ""}}}
two["laws"][0] = {"zfl": "P == pa*A.x + pb*Bs.x + S.boost"}
r = S.run(two, conflicts=False)
gap2 = B.num(r["objective"]["gap"].split(" ")[0]) if r.get("objective") and r["objective"].get("gap") else None
check("Farkas with a discrete slot: without the premix no mix exists (proved), with it the cheapest mix is EARNED "
      "and its bound covers BOTH combinations (gap < 1e-6, none left uncovered)",
      r["verdict"] == "EARNED" and gap2 is not None and gap2 < F(1, 10 ** 6)
      and "not covered" not in r["objective"]["lower_bound_is"] and r.get("combinations_proved_without_mix") == 1,
      str(r.get("objective"))[:400])

md = _copy.deepcopy(cdiet)
md["requirements"] = [{"quantity": "T", "op": "within", "value": ["1", "1"]}]
md["modes"] = {"summer": {"requirements": [{"quantity": "P", "op": ">=", "value": "0.25"}]},
               "winter": {"quantities": {"pb": {"value": "0.30", "tolerance": "0.1"}},
                          "requirements": [{"quantity": "P", "op": ">=", "value": "0.22"}]}}
r = S.run(md, conflicts=False)
gap3 = B.num(r["objective"]["gap"].split(" ")[0]) if r.get("objective") and r["objective"].get("gap") else None
check("continuous choices WITH MODES: summer alone would cost 70/27 (~2.593), winter's weaker beans bind — the "
      "mix b = 13/18 at 49/18 (~2.7222) is EARNED in both modes, ZTL proves the bound over both boxes",
      r["verdict"] == "EARNED" and gap3 is not None and gap3 < F(1, 10 ** 6) and set(r.get("per_mode") or {}) ==
      {"summer", "winter"} and abs(B.num(r["objective"]["value"].split(" ")[0]) - F(49, 18)) < F(1, 10 ** 5),
      str(r.get("objective"))[:300])
md2 = _copy.deepcopy(md)
md2["modes"]["winter"]["requirements"][0]["value"] = "0.35"
r = S.run(md2, conflicts=False)
check("with modes, Farkas: winter asking 0.35 (0.33 at most) — REFUTED, proved no mix exists",
      r["verdict"] == "REFUTED" and r.get("combinations_proved_without_mix") == 1, str(r)[:300])

# SCENARIO CUTS (blind test 5, c11, 2026-10-12): two coefficients share ONE uncertain datum. The box LP takes each
# coefficient's worst case apart (s = 0.5 in one, s = 1.5 in the other: P <= 1 for every mix) and finds none; read at
# data points the robust problem has its mix — 0.6 / 0.6 (tight at both ends of s), L = 6/5 proved
sc = {"stand": "universal-stand/1",
      "quantities": {"s": {"role": "given", "value": "1", "tolerance": "0.5", "unit": ""},
                     "P": {"role": "derived", "unit": ""}},
      "slots": {"A": {"from": ["ia"]}, "Bs": {"from": ["ib"]}},
      "catalog": {"ia": {"continuous": {"field": "x", "from": "0", "to": "1", "unit": ""}},
                  "ib": {"continuous": {"field": "x", "from": "0", "to": "1", "unit": ""}}},
      "laws": [{"zfl": "P == s*A.x + (2 - s)*Bs.x"}],
      "requirements": [{"quantity": "P", "op": ">=", "value": "1.2"}],
      "objective": {"minimize": "A.x + Bs.x"}}
r = S.run(sc, conflicts=False)
gap4 = B.num(r["objective"]["gap"].split(" ")[0]) if r.get("objective") and r["objective"].get("gap") else None
check("scenario cuts: a datum shared by two coefficients — the box LP finds no mix, the cuts find 0.6 / 0.6, EARNED, "
      "ZTL proves L = 6/5 over the relaxation (gap < 1e-6)",
      r["verdict"] == "EARNED" and r["objective"]["lower_bound"] == "6/5 (~1.2)" and gap4 is not None
      and gap4 < F(1, 10 ** 6) and "scenario cuts" in r["objective"]["lower_bound_is"], str(r.get("objective"))[:400])
sc2 = _copy.deepcopy(sc)
sc2["requirements"][0]["value"] = "2.1"
r = S.run(sc2, conflicts=False)
check("scenario cuts, Farkas: asking P >= 2.1 (2 at most, at every s) — REFUTED, the cuts' own data points prove no "
      "mix exists", r["verdict"] == "REFUTED" and r.get("combinations_proved_without_mix") == 1
      and "scenario cuts" in str(r.get("mixes")), str(r)[:400])

# J3 (2026-10-12, the curator's "да"): amounts NOT affine. The mix by a local solver over data points, judged by the
# stand over the whole box; the bound by a split of the amounts checked by ZTL (zmin). The purge: c = g/(p*Fl + r)
# <= 0.008, g and r toleranced — the robust optimum p = 0.0975 (g = 1.1, r = 40), cost 97.5
nl = {"stand": "universal-stand/1",
      "quantities": {"g": {"role": "given", "value": "1", "tolerance": "0.1", "unit": ""},
                     "r": {"role": "given", "value": "50", "tolerance": "0.2", "unit": ""},
                     "Fl": {"role": "given", "value": "1000", "unit": ""},
                     "c": {"role": "derived", "unit": ""}},
      "slots": {"P": {"from": ["purge"]}},
      "catalog": {"purge": {"continuous": {"field": "p", "from": "0", "to": "0.2", "unit": ""}}},
      "laws": [{"zfl": "c == g/(P.p*Fl + r)"}],
      "requirements": [{"quantity": "c", "op": "<=", "value": "0.008"}],
      "objective": {"minimize": "1000*P.p"}}
r = S.run(nl, conflicts=False)
v_nl = B.num(r["objective"]["value"].split(" ")[0]) if r.get("objective") else None
L_nl = B.num(r["objective"]["lower_bound"].split(" ")[0]) if r.get("objective") and r["objective"].get("lower_bound") else None
check("J3: a purge inside a ratio (not affine): EARNED at p ~ 0.0975, ZTL (zmin) proves L <= 97.5 within 0.01 of the "
      "mix's cost", r["verdict"] == "EARNED" and L_nl is not None and F(9749, 100) <= L_nl <= F(195, 2) <= v_nl
      < F(9752, 100) and "zmin" in r["objective"]["lower_bound_is"], str(r.get("objective"))[:400])
nl2 = _copy.deepcopy(nl)
nl2["requirements"][0]["value"] = "0.004"
r = S.run(nl2, conflicts=False)
check("J3, no mix: asking c <= 0.004 needs p >= 0.235 > 0.2 — REFUTED, ZTL (zmin) proves every piece fails",
      r["verdict"] == "REFUTED" and r.get("combinations_proved_without_mix") == 1 and "zmin" in r["why"], str(r)[:400])
r = task("t34-pcm-mass-continuous")
m34 = B.num(r["design"]["PCM"]["m"].split(" ")[0]) if r.get("design") else None
check("J3: blind c01 with the PCM mass continuous (exp, two lanes as modes): EARNED VIP-40, m ~ 6.3667 kg at "
      "~109.384 EUR (the author's 0.01 kg grid: 6.37 kg, 109.405), the bound proved within 0.01 EUR",
      r["verdict"] == "EARNED" and m34 is not None and abs(m34 - F(63667, 10000)) < F(1, 1000)
      and B.num(r["objective"]["gap"].split(" ")[0].lstrip("~")) < F(1, 100), str(r.get("objective"))[:400])
r = task("t35-surcharge-continuous")
h35 = B.num(r["design"]["HS"]["h"].split(" ")[0]) if r.get("design") else None
check("J3: blind c05 with the surcharge height continuous (log10): EARNED h ~ 0.1762 m at ~149 647 EUR (the author's "
      "0.01 m grid: 0.18 m, 150 075 EUR, 'about 0.3 % above the real one'), the bound proved within 2 EUR",
      r["verdict"] == "EARNED" and h35 is not None and abs(h35 - F(1762, 10000)) < F(1, 1000)
      and B.num(r["objective"]["gap"].split(" ")[0].lstrip("~")) < 2, str(r.get("objective"))[:400])

r = task("t36-purge-system-continuous")
p36 = B.num(r["design"]["P"]["p"].split(" ")[0]) if r.get("design") else None
L36 = B.num(r["objective"]["lower_bound"].split(" ")[0]) if r.get("objective") and r["objective"].get("lower_bound") else None
check("J3 + a SYSTEM of laws: blind c06 with the purge continuous (concentrations from 10 linear laws, p in their "
      "coefficients; the kernel solves the system itself): EARNED p ~ 1/92 at ~137 804 EUR/yr, ZTL (zmin) proves the "
      "bound within 1 EUR — the author's hand optimum (the stand had only his grid)",
      r["verdict"] == "EARNED" and p36 is not None and abs(p36 - F(1, 92)) < F(1, 10 ** 5) and L36 is not None
      and abs(L36 - 137804) < 1 and B.num(r["objective"]["gap"].split(" ")[0].lstrip("~")) < 1,
      str(r.get("objective"))[:400])

# J10 (2026-10-12): minimal conflicts in continuous mode — protein >= 0.3 (robust: Bs >= 0.778 with the batch), the
# batch == 1 (then cost >= 2.778), the budget <= 2.6: each pair holds with room, the three cannot
j10 = {"stand": "universal-stand/1",
       "quantities": {"pa": {"role": "given", "value": "0.10", "tolerance": "0.1", "unit": ""},
                      "pb": {"role": "given", "value": "0.40", "tolerance": "0.1", "unit": ""},
                      "P": {"role": "derived", "unit": ""}, "T": {"role": "derived", "unit": ""},
                      "Cst": {"role": "derived", "unit": ""}},
       "slots": {"A": {"from": ["ia"]}, "Bs": {"from": ["ib"]}},
       "catalog": {"ia": {"continuous": {"field": "x", "from": "0", "to": "1", "unit": ""}},
                   "ib": {"continuous": {"field": "x", "from": "0", "to": "1", "unit": ""}}},
       "laws": [{"zfl": "P == pa*A.x + pb*Bs.x"}, {"zfl": "T == A.x + Bs.x"}, {"zfl": "Cst == 2*A.x + 3*Bs.x"}],
       "requirements": [{"quantity": "P", "op": ">=", "value": "0.3", "why": "protein"},
                        {"quantity": "T", "op": "within", "value": ["1", "1"], "why": "batch"},
                        {"quantity": "Cst", "op": "<=", "value": "2.6", "why": "budget"}],
       "objective": {"minimize": "2*A.x + 3*Bs.x"}}
r = S.run(j10)
check("J10: continuous mode names its minimal conflict — protein, batch and budget together (every pair holds)",
      r["verdict"] == "REFUTED" and r.get("minimal_conflicts", {}).get("sets") == [["protein", "batch", "budget"]]
      and not r["minimal_conflicts"].get("undecided_sets"),
      (r.get("verdict"), r.get("minimal_conflicts")))

# round 4, k03: a continuous brick with a bound that names the part's own limit (DEV.Tc), read at its exact value
fb = {"stand": "universal-stand/1",
      "quantities": {"P": {"role": "given", "value": "20", "tolerance": "0.1", "unit": "W"},
                     "Ta": {"role": "given", "value": "40", "unit": "K"}, "Tj": {"role": "derived", "unit": "K"}},
      "slots": {"DEV": {"from": ["dev"]}, "HS": {"from": ["hs"]}},
      "catalog": {"dev": {"items": [{"name": "C", "Tc": "125", "Rjc": "1.5"}, {"name": "M", "Tc": "150", "Rjc": "1.5"}],
                          "fields": {"Tc": {"unit": "K"}, "Rjc": {"unit": "K/W"}}},
                  "hs": {"continuous": {"field": "R", "from": "0.1", "to": "10", "unit": "K/W"}}},
      "laws": [{"zfl": "Tj == Ta + P*(DEV.Rjc + HS.R)"}],
      "requirements": [{"quantity": "Tj", "op": "<=", "value": "DEV.Tc"}],
      "objective": {"minimize": "1/HS.R"}}
r = S.run(fb)
r_hs = B.num(r["design"]["HS"]["R"].split(" ")[0]) if r.get("design") else None
check("continuous + a bound naming the part's limit (DEV.Tc): EARNED part M, sink R ~ 3.5 K/W (hand: 110/22 - 1.5), "
      "the bound proved", r["verdict"] == "EARNED" and r["design"]["DEV"]["name"] == "M" and r_hs is not None
      and abs(r_hs - F(7, 2)) < F(1, 1000) and r["objective"].get("lower_bound") is not None, str(r)[:300])
# round 4, k02: find with modes — every tried range judged in every mode
fm = {"stand": "universal-stand/1",
      "quantities": {"V": {"role": "given", "value": "5", "tolerance": "0.02", "unit": "V"},
                     "R": {"role": "given", "value": "100", "tolerance": "0.01", "unit": "ohm"},
                     "Ta": {"role": "given", "value": "25", "unit": "K"}, "k": {"role": "given", "value": "1", "unit": "K/W"},
                     "I": {"role": "derived", "unit": "A"}, "T": {"role": "derived", "unit": "K"}},
      "laws": [{"zfl": "I == V/R"}, {"zfl": "T == Ta + k*V*I"}],
      "requirements": [{"quantity": "I", "op": "<=", "value": "0.06"}],
      "modes": {"cold": {"quantities": {"Ta": {"value": "-20"}}, "requirements": [{"quantity": "T", "op": ">=", "value": "-20"}]},
                "hot": {"quantities": {"Ta": {"value": "60"}}, "requirements": [{"quantity": "T", "op": "<=", "value": "80"}]}},
      "find": {"largest": "V", "from": "5", "to": "8", "precision": "0.001"}}
r = S.run(fm)
check("find WITH MODES: the largest V both modes keep is 5.94 (hand 0.06 x 99), 5.941 refuted at a point",
      r["verdict"] == "EARNED" and r["proved"] == "297/50 (~5.94)" and r["beyond_is"].startswith("REFUTED"), str(r)[:300])
fm["modes"]["hot"]["quantities"]["V"] = {"value": "5"}
r = S.run(fm)
check("  ... and a mode that overrides the searched given — refused", r["verdict"] == "BRICK ERROR" and "overrides V"
      in r["why"], r.get("why"))
from ustand import units as _U
check("units of round 4: oz (1/16 lb), ozf, gal (231 in^3), gpm — exact; 1 gpm = 3.785411784 L/min",
      _U.parse("oz")[0] == F("0.45359237") / 16 and _U.parse("gal")[0] == F("0.003785411784")
      and _U.parse("gpm")[0] / _U.parse("L/min")[0] == F("3.785411784"), _U.parse("gpm"))

# BLIND TEST 6, c10 (2026-10-12): the ONE wrong verdict of six rounds — a mix found for one discrete combination was
# judged with the OTHER discrete slots free, and a combination it passed in lent its EARNED (DR6 without a fan,
# 44.02 kEUR, "optimal"; only DR10 without a fan holds among these four, 57.07 kEUR, by the writer's own scan)
r = S.run(str(EX / "blind6" / "work_c10" / "k_dr610_nf15.json"))
check("blind 6 c10: a mix is judged in ITS OWN combination — DR6/DR10 x none/F15: EARNED DR10 without a fan at "
      "~57.07 kEUR (was a false EARNED DR6 at 44.02, gap -0.34)", r["verdict"] == "EARNED"
      and r["design"]["DRY"]["name"] == "DR10" and r["design"]["FAN"]["name"] == "none"
      and r["objective"]["value"].endswith("(~57.0669)") and not r["objective"]["gap"].startswith("-"), str(r)[:400])

# BLIND TEST 6, the other findings (2026-10-12)
r = S.run(str(EX / "blind6" / "work_c03" / "v_novalid.json"))
check("blind 6 c03: a stalled pack (sqrt of a negative number at the nominal point) no longer a STAND ERROR on 'Vt' — "
      "the same EARNED design as the guarded brick", r["verdict"] == "EARNED", (r.get("verdict"), str(r.get("why"))[:200]))
r = S.run(str(EX / "blind6" / "c04.json"))
check("blind 6 c04: a brick with `find` also returns the DECISION as written — the limit -37.86 C and, at -40 C, "
      "REFUTED with its conflict {R1, R2, R3}", r["verdict"] == "EARNED" and r["proved"] == "-1893/50 (~-37.86)"
      and r["decision"]["verdict"] == "REFUTED" and len(r["decision"]["minimal_conflicts"]["sets"]) == 1
      and len(r["decision"]["minimal_conflicts"]["sets"][0]) == 3, str(r.get("decision"))[:300])
check("scientific notation in a law (8.6541e-5) is read as an exact fraction (blind 6, c10: 'malformed arithmetic')",
      B.compile_expr("k == 8.6541e-5*x - y2e5") == "k == (86541/1000000000)*x - y2e5", B.compile_expr("k == 8.6541e-5*x - y2e5"))
check("units: daN (the lashing tables' decanewton, blind 6 c09) = 10 N", _U.parse("daN")[0] == 10)
import subprocess as _sp6, time as _t6
# the slow NONLINEAR case changed (2026-10-19): c07 without R3 ran past 900 s; since the search skips rows the amounts
# do not move (a plate's "d >= 80" met exactly) it is EARNED in 4 s — c10's nonlinear path (~19 s) under `timeout 5`
_t0 = _t6.time()
_p6 = _sp6.run(["timeout", "5", sys.executable, "-m", "ustand.stand", str(EX / "blind6" / "c10.json")],
               capture_output=True, text=True, cwd=str(EX.parent), env=dict(os.environ, OPENBLAS_NUM_THREADS="1"))
_dt = _t6.time() - _t0
try:
    _r6 = json.loads(_p6.stdout)
except ValueError:
    _r6 = {}
check(f"blind 6 c10 (the NONLINEAR continuous path): `timeout 5` stops it ({_dt:.0f} s; c07's ran past 900 s once) "
      "and the partial JSON is printed", _dt < 15 and _r6.get("verdict") == "OPEN" and "stopped" in str(_r6.get("why")),
      (_dt, str(_p6.stdout)[:200]))

# sin / cos (2026-10-13, blind test 6 c09, the curator's "да": ZTL zfunc reads them; the checker with mpmath)
sc_ = {"stand": "ztl-stand/1",
       "quantities": {"alpha": {"role": "given", "range": ["55", "65"], "unit": "deg"},
                      "F": {"role": "given", "value": "1000", "unit": "N"},
                      "Fv": {"role": "derived", "unit": "N"}, "Fh": {"role": "derived", "unit": "N"}},
       "laws": [{"zfl": "Fv == F*sin(alpha)"}, {"zfl": "Fh == F*cos(alpha)"}],
       "requirements": [{"quantity": "Fv", "op": ">=", "value": "800"}, {"quantity": "Fh", "op": "<=", "value": "580"}]}
r = S.run(sc_)
fv = [B.num(x.split(" ")[0]) for x in r["guaranteed"]["Fv"]] if r.get("guaranteed") else None
check("sin and cos: a strap at 55..65 deg, 1000 N — Fv >= 800 and Fh <= 580 EARNED, Fv from 1000 sin 55 deg = 819.152 "
      "(ZTL and the checker agree)", r["verdict"] == "EARNED" and fv is not None and abs(fv[0] - F(8191520, 10000)) < 1,
      str(r)[:300])
sc_["requirements"][0]["value"] = "830"
r = S.run(sc_)
check("  ... Fv >= 830 REFUTED at alpha = 55 deg", r["verdict"] == "REFUTED" and r.get("its_violating_point", {}).get("alpha")
      == "55", str(r)[:300])

# J1 (blind test 4, c12, 2026-10-11): the ONLY wrong verdict class in four rounds. The robust LP's vertex had a binding
# margin; the rounded mix missed it by 1.7e-7 and the stand said REFUTED — though a feasible mix existed (the author's
# integer portfolio at 2 271 690 EUR is EARNED in the same box). Now: REFUTED only with a Farkas proof; the LP is
# retried further inside, and an unproved miss is OPEN.
r = task("t25-pension-tight-vertex")
v25 = B.num(r["objective"]["value"].split(" ")[0].lstrip("~")) if r.get("objective") else None
check("J1: a pension portfolio whose LP vertex is tight: EARNED (was a false REFUTED), the continuous cost below the "
      "author's integer 2 271 690 EUR", r["verdict"] == "EARNED" and v25 is not None and v25 <= 2271690,
      (r.get("verdict"), r.get("why"), str(r.get("objective"))[:200]))

# J6 (blind test 4, c02, 2026-10-11): a quantity read through an implicit root that leans on the same data. The author
# rearranged the law by hand (the literal form went OPEN); now the root moves with the box in the certificate.
r = task("t26-anode-implicit-literal")
check("J6: the anode bed in its LITERAL form (Es = Ea - I*R, I implicit): EARNED Mg-S-32 x 4 at 680 EUR, optimal — the "
      "author's hand-rearranged answer; Esd >= 0.85 holds by 0.002 V at the worst corner",
      r["verdict"] == "EARNED" and r["objective"]["value"] == "680" and r["objective"]["optimal"]
      and "roots that move with the box" in r["per_mode"]["protection"]["how"]["Esd"], str(r)[:400])

# K9 (blind test 5, c09, 2026-10-11): the literal coverage margin, exactly 0 over regions — branches read by cases
r = task("t27-warehouse-coverage-literal")
check("K9: c09's literal coverage B + F + S - N >= 0 (min/max chains, 0 over whole regions; read [-944, 944] before): "
      "EARNED — ZTL's case reading proves it, the checker's own case reading confirms",
      r["verdict"] == "EARNED" and "certificate" in r["how"]["Mmin"], str(r)[:300])

r = task("t24-feed-continuous")
gap = B.num(r["objective"]["gap"].split(" ")[0].lstrip("~")) if r.get("objective") and r["objective"].get("gap") else None
check("I2: broiler feed (blind c12) with CONTINUOUS amounts over the full uncertainty box: EARNED at 336.770 EUR/t, "
      "ZTL proves no mix costs less (gap < 0.001 EUR/t) — the author had 337.07 'optimal among 13 recipes' and an "
      "LP bound 336.77 outside the stand",
      r["verdict"] == "EARNED" and r["objective"]["value"].startswith("~336.770") and gap is not None
      and gap < F(1, 1000), str(r.get("objective"))[:300])

# J4 (blind test 4, 2026-10-11): a run stopped by the time limit prints what it decided, not nothing
import subprocess as _sp
_p = _sp.run(["timeout", "45", sys.executable, "-m", "ustand.stand", str(EX / "blind4" / "c04.json")],
             capture_output=True, text=True, cwd=str(EX.parent), env=dict(os.environ, OPENBLAS_NUM_THREADS="1"))
try:
    _r = json.loads(_p.stdout)
except ValueError:
    _r = {}
check("J4: a run killed by `timeout` (SIGTERM) still prints JSON: OPEN, how far it got, and the designs decided",
      _r.get("verdict") == "OPEN" and "stopped by a signal" in _r.get("why", "")
      and _r.get("designs_total") == 12 and 0 < _r.get("designs_tried", 0) <= 12, (_p.returncode, _p.stdout[:300]))

# J5 (blind test 4, 2026-10-11): table(x, x0, y0, ...) — linear between knots, ends held; read as ifpos branches
def _tb(reqs, law="y == table(x, 0, 1, 10, 3, 20, 2)"):
    return {"stand": "universal-stand/1",
            "quantities": {"x": {"role": "given", "range": ["2", "14"], "unit": ""}, "y": {"role": "derived", "unit": ""}},
            "slots": {}, "catalog": {}, "laws": [{"zfl": law}],
            "requirements": [{"quantity": "y", "op": o, "value": v} for o, v in reqs]}


check("table compiles to the ifpos chain an author typed by hand (the same text)",
      B.compile_expr("table(T, 0, 1, 10, 3, 20, 2)") == "ifpos(T - 0, ifpos(T - 10, ifpos(T - 20, 2, 3 + (2 - 3) * "
      "(T - 10) / (20 - 10)), 1 + (3 - 1) * (T - 0) / (10 - 0)), 1)", B.compile_expr("table(T, 0, 1, 10, 3, 20, 2)"))
r = S.run(_tb([("<=", "2.9")]), conflicts=False)
check("table: the maximum 3 at the INNER knot x = 10 (both corners pass): y <= 2.9 REFUTED at a point inside",
      r["verdict"] == "REFUTED", str(r)[:200])
r = S.run(_tb([("<=", "3.01")]), conflicts=False)
check("table: y <= 3.01 EARNED by a certificate (the box cut at the knot)",
      r["verdict"] == "EARNED" and "certificate" in r["how"]["y"], str(r)[:300])
r = S.run(_tb([("<=", "3.01")], "y == table(x, 0, 1, 20, 2)"), conflicts=False)
check("table with two knots is a line, held flat beyond the ends", r["verdict"] == "EARNED", str(r)[:200])
try:
    B.compile_expr("table(T, 0, 1, 0, 3)"); refused_t = False
except B.BrickError:
    refused_t = True
check("table with x-knots that do not increase: BRICK ERROR", refused_t)

def _raises(f, exc):
    try:
        f()
    except exc:
        return True
    return False


# J7 (blind test 4, 2026-10-11): units the authors could not write — the year (the curator: Julian, 365.25 d),
# kEUR, fractional powers (a weir's C in m^0.5/s, H^1.5)
from ustand import units as _U7
check("J7: year = yr = 365.25 days = 31 557 600 s; kEUR = 1000 EUR, MUSD = 10^6 USD; mEUR refused (a typo, not money)",
      _U7.parse("year")[0] == 31557600 and _U7.parse("yr") == _U7.parse("year")
      and _U7.parse("kEUR") == (1000, _U7.parse("EUR")[1]) and _U7.parse("MUSD")[0] == 10 ** 6
      and _raises(lambda: _U7.parse("mEUR"), _U7.UnitError))
check("J7: fractional powers read and written back (m^2.5/s, m^(1/2)); a fractional power of a scaled unit refused",
      _U7.parse("m^2.5/s") == _U7.parse("m^(5/2)*s^-1") and _U7.parse(_U7.unit_of(_U7.parse("m^(1/2)/s")[1]))[1]
      == _U7.parse("m^(1/2)/s")[1] and _raises(lambda: _U7.parse("km^0.5"), _U7.UnitError))


def _weir(cu, law="Q == C*L*pow(H, 1.5)"):
    return {"stand": "universal-stand/1",
            "quantities": {"C": {"role": "given", "value": "1.7", "unit": cu},
                           "L": {"role": "given", "value": "2", "unit": "m"},
                           "H": {"role": "given", "range": ["0.2", "0.3"], "unit": "m"},
                           "Q": {"role": "derived", "unit": "m^3/s"}},
            "slots": {}, "catalog": {}, "laws": [{"zfl": law}],
            "requirements": [{"quantity": "Q", "op": "<=", "value": "0.6"}]}


r = S.run(_weir("m^(1/2)/s"), conflicts=False)
check("J7: a weir Q = C*L*H^1.5 with C in m^0.5/s — units checked, EARNED (Q <= 1.7*2*0.3^1.5 = 0.559)",
      r["verdict"] == "EARNED" and "agree" in r.get("units", ""), str(r)[:300])
r = S.run(_weir("m^(1/2)/s", "Q == C*L*H*sqrt(H)"), conflicts=False)
check("J7: the same with H*sqrt(H) — sqrt of metres is a half power now, not an error", r["verdict"] == "EARNED",
      str(r)[:300])
r = S.run(_weir("m/s"), conflicts=False)
check("J7: C in m/s (the wrong unit) — BRICK ERROR: the right side is m^(7/2)/s", r["verdict"] == "BRICK ERROR"
      and "m^(7/2)" in r.get("why", ""), str(r)[:300])

# J11 vocabulary (blind test 4, 2026-10-11, the curator's "да"): abs(x) and x^n
check("J11: x^n is pow(x, n) (never xor); abs(x) is the branch if(x > 0, x, -x)",
      B.compile_expr("-x^2 + A.r^1.5") == "-pow(x, 2) + pow(A__r, 1.5)"
      and B.compile_expr("abs(a - b)") == "ifpos(a - b, a - b, -(a - b))", B.compile_expr("abs(a - b)"))
r1 = S.run(_tb([("<=", "9")], "y == abs(x - 5)"), conflicts=False)
r2 = S.run(_tb([(">=", "0.01")], "y == abs(x - 5)"), conflicts=False)
r3 = S.run(_tb([("<=", "154")], "y == x^2 - 3*x"), conflicts=False)
r4 = S.run(_tb([("<=", "153")], "y == x^2 - 3*x"), conflicts=False)
check("J11: |x - 5| <= 9 EARNED on [2, 14]; |x - 5| >= 0.01 REFUTED (x = 5 inside); x^2 - 3x <= 154 EARNED, <= 153 "
      "REFUTED (154 at x = 14)", [r["verdict"] for r in (r1, r2, r3, r4)] == ["EARNED", "REFUTED", "EARNED", "REFUTED"],
      [r["verdict"] for r in (r1, r2, r3, r4)])

# J8 (blind test 4, 2026-10-11, the curator's "да"): totals over the modes — the modes judged as ONE brick
def _tot(shared=True):
    b = {"stand": "universal-stand/1",
         "quantities": {"rho": {"role": "given", "value": "1000", "unit": "kg/m^3"},
                        "g": {"role": "given", "value": "9.81", "unit": "m/s^2"},
                        "Q": {"role": "given", "value": "0.05", "unit": "m^3/s"},
                        "H": {"role": "given", "value": "20", "tolerance": "0.05", "unit": "m"},
                        "P": {"role": "derived", "unit": "kW"}},
         "slots": {}, "catalog": {}, "laws": [{"zfl": "P == rho*g*Q*H/0.6"}],
         "modes": {"low": {"weight": "-1", "quantities": {"Q": {"value": "0.03"}},
                           "requirements": [{"quantity": "P", "op": "<=", "value": "10.5"}]},
                   "high": {"weight": "1", "quantities": {"Q": {"value": "0.06"}}}},
         "totals": {"D": {"sum": "P", "unit": "kW"}},
         "requirements": [{"quantity": "D", "op": "<=", "value": "10.4"}]}
    if not shared:
        for m in b["modes"].values():
            m["quantities"]["H"] = {"value": "20", "tolerance": "0.05"}
    return b


r = S.run(_tot(), conflicts=False)
check("J8: a total over two modes (P_high - P_low) with the head H shared: 9.32..10.30 kW, D <= 10.4 EARNED; the low "
      "mode's own requirement on P_in_low", r["verdict"] == "EARNED" and r["guaranteed"]["D"][1].startswith("20601/2000")
      and "P_in_low" in r["guaranteed"] and "ONE brick" in r.get("modes_joined", ""), str(r)[:300])
r = S.run(_tot(shared=False), conflicts=False)
check("J8: the same with H overridden in each mode (two independent draws): up to 11.28 kW, D <= 10.4 REFUTED",
      r["verdict"] == "REFUTED", str(r)[:200])
_b = _tot(); del _b["modes"]["low"]["weight"]
_c = _tot(); _c["objective"] = {"minimize": "P"}
check("J8: a mode without a weight, an objective on a per-mode quantity: BRICK ERROR, said where",
      "weight" in S.run(_b, conflicts=False)["why"] and "minimize a total" in S.run(_c, conflicts=False)["why"])

# J11 (blind test 4, 2026-10-11, the curator's "да"): an OPTIONAL slot — the part may be left out ("none", fields 0)
def _opt(lim):
    return {"stand": "universal-stand/1",
            "quantities": {"Ta": {"role": "given", "range": ["20", "40"], "unit": "C"},
                           "P": {"role": "given", "value": "2", "tolerance": "0.1", "unit": "W"},
                           "Gbare": {"role": "given", "value": "0.02", "unit": "W/C"}, "Tj": {"role": "derived", "unit": "C"}},
            "slots": {"HS": {"from": ["sinks"], "optional": True}},
            "catalog": {"sinks": {"fields": {"G": {"unit": "W/C"}, "price": {"unit": "EUR"}},
                                  "items": [{"name": "small", "G": "0.1", "price": "2"},
                                            {"name": "big", "G": "0.3", "price": "5"}]}},
            "laws": [{"zfl": "Tj == Ta + P/(Gbare + HS.G)"}],
            "requirements": [{"quantity": "Tj", "op": "<=", "value": lim}], "objective": {"minimize": "HS.price"}}


_o = [S.run(_opt(x), conflicts=False) for x in ("150", "100", "50")]
check("J11 optional slot: Tj <= 150 with NO heatsink (0 EUR; 40 + 2.2/0.02 = 150), <= 100 the small one, <= 50 the big one",
      [(r["verdict"], r["design"]["HS"]["name"]) for r in _o] == [("EARNED", "none"), ("EARNED", "small"), ("EARNED", "big")],
      [(r["verdict"], (r.get("design") or {}).get("HS")) for r in _o])

# J11 (blind test 4, c07, 2026-10-11): exp/ln/log10/sqrt in `where` — read as exact-fraction intervals; a comparison
# they do not decide is said, never guessed; a `computed` value must stay exact
from ustand import exact as _X
_env = {"a": F(2), "b": F(7389, 1000)}


def _xw(t):
    try:
        return _X.evaluate(_X.parse(t), _env, "w")
    except _X.ExactError as e:
        return "ERR " + str(e)


check("J11 where: exp(2) > 7.389 True, ln(7.389) < 2 True, ceil(exp(2)) == 8 True; log10(1000) == 3 too close -> said; "
      "ln of a negative -> said",
      _xw("exp(a) > b") is True and _xw("ln(b) < 2") is True and _xw("ceil(exp(a)) == 8") is True
      and "too close" in str(_xw("log10(1000) == 3")) and "not positive" in str(_xw("ln(0 - a) > 1")),
      [_xw(t) for t in ("exp(a) > b", "ln(b) < 2", "ceil(exp(a)) == 8", "log10(1000) == 3", "ln(0 - a) > 1")])
_w = _opt("100"); _w["where"] = ["exp(HS.price/E1) > 10"]
_w["quantities"]["E1"] = {"role": "given", "value": "1", "unit": "EUR"}
r = S.run(_w, conflicts=False)
check("J11 where with exp in a real brick: exp(price/1 EUR) > 10 drops the 2 EUR sink and 'none' — the big one is "
      "chosen; exp of a price in EUR (a unit) is refused", r["verdict"] == "EARNED" and r["design"]["HS"]["name"] == "big"
      and S.run(dict(_w, where=["exp(HS.price) > 10"]), conflicts=False)["verdict"] == "BRICK ERROR", str(r)[:300])
_w = _opt("100"); _w["computed"] = {"q": "exp(HS.price)"}
check("J11: exp in `computed` is a BRICK ERROR (a computed value must stay exact)",
      S.run(_w, conflicts=False)["verdict"] == "BRICK ERROR")

# J11 (blind test 4, c06, 2026-10-11): a singular point NAMED — with purge p = 0 a balance has no way out
_sg = {"stand": "universal-stand/1",
       "quantities": {"F": {"role": "given", "value": "10", "unit": ""}, "cin": {"role": "given", "value": "0.1", "unit": ""},
                      "c": {"role": "derived", "unit": ""}},
       "slots": {"PG": {"from": ["purge"]}},
       "catalog": {"purge": {"items": [{"name": "p0", "p": "0"}, {"name": "p1", "p": "0.5"}]}},
       "laws": [{"zfl": "F*cin == PG.p*F*c"}],
       "requirements": [{"quantity": "c", "op": "<=", "value": "1"}], "report": "all"}
r = S.run(_sg, conflicts=False)
_w0 = [d["why"] for d in r.get("designs", []) if "p0" in d["design"]]
check("J11: p = 0 (no purge) is named — 'the linear laws have NO solution ... no steady state', at PG.p = 0; p = 0.5 "
      "EARNED", r["verdict"] == "EARNED" and _w0 and "NO solution" in _w0[0] and "PG.p = 0" in _w0[0], str(r)[:400])

# BLIND TEST 5 (2026-10-11) — what the twelve authors met
# a stop (SIGTERM, `timeout`) while minimal_conflicts judges the subsets: it was cleared by every subset's run()
_sq = {"stand": "universal-stand/1",
       "quantities": {"x": {"role": "given", "range": ["2", "14"], "unit": ""}, "y": {"role": "derived", "unit": ""}},
       "slots": {}, "catalog": {}, "laws": [{"zfl": "y == x*x"}],
       "requirements": [{"quantity": "y", "op": "<=", "value": "100"}, {"quantity": "y", "op": ">=", "value": "1"}]}
_mc0 = S.minimal_conflicts


def _mc_stop(bb, *a):           # *a: the proof's core, passed since 2026-10-18
    S._STOP[0] = True
    return _mc0(bb, *a)


S.minimal_conflicts = _mc_stop
r = S.run(_sq)
S.minimal_conflicts = _mc0
r2 = S.run(_sq)
check("B5: a stop while the conflict subsets are judged is HEARD (it was cleared by each subset's run and the "
      "enumeration ran on: c07 1041 s, c06 57 min past `timeout 900`); the verdict stays, the list says 'stopped'",
      r["verdict"] == "REFUTED" and "stopped" in r.get("minimal_conflicts", {}) and S._DEPTH == [0]
      and r2.get("minimal_conflicts", {}).get("sets") == [["y <= 100"]], (r.get("minimal_conflicts"), S._DEPTH))
# an optional slot together with modes (c10: BRICK ERROR "the catalog name 'OX_none' is taken")
_om = _opt("100")
_om["requirements"] = []
_om["modes"] = {"cool": {"quantities": {"Ta": {"range": ["20", "25"]}},
                         "requirements": [{"quantity": "Tj", "op": "<=", "value": "140"}]},
                "hot": {"requirements": [{"quantity": "Tj", "op": "<=", "value": "100"}]}}
r = S.run(_om, conflicts=False)
check("B5: an optional slot with modes (it was a BRICK ERROR): EARNED the small sink — 'none' passes cool (135 C) "
      "but not hot (150 C); each mode's checker named in per_mode",
      r["verdict"] == "EARNED" and r["design"]["HS"]["name"] == "small"
      and all(pm.get("checker") for pm in r["per_mode"].values()), str(r)[:300])
# pow(x, 2/3) — Manning (c04: "a non-integer exponent written as 2/3 is not read as a constant")
_mn = {"stand": "universal-stand/1",
       "quantities": {"R": {"role": "given", "range": ["0.1", "0.2"], "unit": "m"}, "S": {"role": "given", "value": "0.005", "unit": ""},
                      "n": {"role": "given", "value": "0.011", "unit": "s/m^(1/3)"}, "v": {"role": "derived", "unit": "m/s"}},
       "slots": {}, "catalog": {}, "laws": [{"zfl": "v == pow(R, 2/3)*sqrt(S)/n"}],
       "requirements": [{"quantity": "v", "op": ">=", "value": "1.3"}]}
r = S.run(_mn, conflicts=False)
check("B5: Manning v = R^(2/3) S^(1/2) / n with n in s/m^(1/3): units checked, v >= 1.3 EARNED (1.385 at R = 0.1)",
      r["verdict"] == "EARNED" and "agree" in r.get("units", ""), str(r)[:300])
# the objective in the prices' own unit (c01, c02, c08: 1700, 141514, 14850 shown for kEUR prices)
_ok = _opt("100")
_ok["catalog"]["sinks"]["fields"]["price"]["unit"] = "kEUR"
r = S.run(_ok, conflicts=False)
check("B5: with prices in kEUR and no objective unit, the cost is shown in kEUR (2, not 2000), the unit's origin said",
      r["objective"]["value"] == "2" and r["objective"]["unit"] == "kEUR" and "unit_from" in r["objective"],
      r.get("objective"))

# vocabulary after blind test 5 (the curator's "да", 2026-10-11): units Gy Sv VA var deg and a number in a unit;
# a requirement directly on a given or a catalog field; "conflicts": false
check("B5 units: kWh/100km = 36 N, mSv = 0.001 J/kg, kvar = 1000 W, deg = pi/180 to 40 digits",
      _U7.parse("kWh/100km") == (36, _U7.parse("N")[1]) and _U7.parse("mSv") == (F(1, 1000), _U7.parse("J/kg")[1])
      and _U7.parse("kvar") == (1000, _U7.parse("W")[1]) and abs(float(_U7.parse("deg")[0]) - 3.141592653589793 / 180) < 1e-17,
      [_U7.parse(u) for u in ("kWh/100km", "mSv", "kvar")])
_dg = {"stand": "universal-stand/1",
       "quantities": {"phi": {"role": "given", "range": ["25", "29"], "unit": "deg"}, "t": {"role": "derived", "unit": ""}},
       "slots": {}, "catalog": {}, "laws": [{"zfl": "t == tan(phi)"}],
       "requirements": [{"quantity": "t", "op": "<=", "value": "0.56"}]}
r1 = S.run(_dg, conflicts=False)
_dg["requirements"][0]["value"] = "0.55"
r2 = S.run(_dg, conflicts=False)
check("B5 degrees: tan(phi) for phi 25..29 deg <= 0.56 EARNED, <= 0.55 REFUTED (tan 29 deg = 0.5543)",
      (r1["verdict"], r2["verdict"]) == ("EARNED", "REFUTED"), (r1["verdict"], r2["verdict"]))
_dr = _opt("50")
_dr["slots"]["HS"].pop("optional")
_dr.pop("objective")
_dr["requirements"].append({"quantity": "HS.price", "op": "<=", "value": "3"})
r = S.run(_dr)
check("B5: a requirement directly on a catalog field (HS.price <= 3, no dummy quantity) — REFUTED with the minimal "
      "conflict {Tj <= 50, HS.price <= 3}", r["verdict"] == "REFUTED"
      and r["minimal_conflicts"]["sets"] == [["Tj <= 50", "HS.price <= 3"]], str(r.get("minimal_conflicts"))[:300])
_dr["conflicts"] = False
check("B5: \"conflicts\": false switches minimal_conflicts off", "minimal_conflicts" not in S.run(_dr))
_dq = _opt("100")
_dq["requirements"].append({"quantity": "P", "op": "<=", "value": "2.3"})
r = S.run(_dq, conflicts=False)
check("B5: a requirement directly on a given (P <= 2.3 W with P = 2 W +-10 %) EARNED, its range shown as P_req",
      r["verdict"] == "EARNED" and r["guaranteed"]["P_req"] == ["9/5 (~1.8)", "11/5 (~2.2)"], str(r)[:300])

# SPEED after blind test 5 (c03: 4016 corners x 4 implicit roots, ~110 s a design): corners are not read when the
# checker's own bounds already show every requirement, and a violating corner is first sought by a greedy walk
_gq = {"stand": "universal-stand/1",
       "quantities": dict({f"x{i}": {"role": "given", "value": "1", "tolerance": "0.1", "unit": ""} for i in range(12)},
                          y={"role": "derived", "unit": ""}),
       "slots": {}, "catalog": {}, "laws": [{"zfl": "y == " + " + ".join(f"x{i}*x{i}" for i in range(12))}],
       "requirements": [{"quantity": "y", "op": "<=", "value": "14.5"}]}
r = S.run(_gq, conflicts=False)
_gq["requirements"][0]["value"] = "14.6"
r2 = S.run(_gq, conflicts=False)
check("speed: 12 toleranced quantities, y = sum x_i^2 (nominal 12, all-high corner 14.52): y <= 14.5 REFUTED at the "
      "all-high corner (found greedily, not among 4096), y <= 14.6 EARNED",
      r["verdict"] == "REFUTED" and r2["verdict"] == "EARNED", (r["verdict"], r2["verdict"], str(r)[:200]))

# PARALLEL judging (ustand/parallel.py, 2026-10-11): --jobs N gives the same output, plain and with modes
from ustand import parallel as _PL
_pq = _opt("50")
_pq["slots"]["HS"].pop("optional")
_pq["catalog"]["sinks"]["items"] = [{"name": f"s{i}", "G": str(F(i, 100)), "price": str(i)} for i in range(1, 41)]
_pq["report"] = "all"
_pm = dict(_pq, requirements=[], modes={"cool": {"quantities": {"Ta": {"range": ["20", "25"]}},
                                                 "requirements": [{"quantity": "Tj", "op": "<=", "value": "45"}]},
                                        "hot": {"requirements": [{"quantity": "Tj", "op": "<=", "value": "50"}]}})
_seq = [S.run(x, conflicts=False) for x in (_pq, _pm)]
_PL.JOBS[0] = 3
_par = [S.run(x, conflicts=False) for x in (_pq, _pm)]
_PL.JOBS[0] = 1
check("parallel: --jobs 3 gives the SAME output as one process, plain (40 sinks, report all) and with modes",
      _seq == _par and _seq[0]["verdict"] == "EARNED", [(a == b, a["verdict"]) for a, b in zip(_seq, _par)])
# SPECULATIVE VISITS in the nonlinear continuous search (lp._Speculation, 2026-10-13): the same output, byte for
# byte, with workers computing the visits ahead (c06: 54 -> 28 s on 8 jobs, measured)
_nls = [S.run(x, conflicts=False) for x in (nl, nl2)]
_PL.JOBS[0] = 3
_nlp_ = [S.run(x, conflicts=False) for x in (nl, nl2)]
_PL.JOBS[0] = 1
check("parallel: --jobs 3 gives the SAME output on the nonlinear continuous path (EARNED and REFUTED by zmin)",
      _nls == _nlp_ and [x["verdict"] for x in _nls] == ["EARNED", "REFUTED"],
      [(a == b, a["verdict"]) for a, b in zip(_nls, _nlp_)])

# TWO MODES (2026-10-11, the curator): work (default) — ZTL's verdicts; dev — the independent checker on every design
_MODE.DEV[0] = False
_rw = S.run(_opt("100"), conflicts=False)
_MODE.DEV[0] = True
_rd = S.run(_opt("100"), conflicts=False)
check("modes: the same verdict and design in work and dev mode; checked_by says which judged",
      (_rw["verdict"], _rw["design"]["HS"]["name"]) == (_rd["verdict"], _rd["design"]["HS"]["name"]) == ("EARNED", "small")
      and _rw["checked_by"].startswith("ZTL (work mode") and _rd["checked_by"].startswith("ZTL + the independent"),
      (_rw.get("checked_by"), _rd.get("checked_by")))

# REAL PROBLEMS round 1 (2026-10-11): the format's tails they found
check("real r04: table() inside an if() condition reads (it was 'not a readable expression')",
      B.compile_expr("if(table(x, 0, 1, 10, 3) > 2, a, b)").startswith("ifpos(ifpos(x - 0"))
_m2 = _opt("100"); _m2["requirements"] = []; _m2.pop("objective")
_m2["catalog"]["sinks"]["items"] = [{"name": "small", "G": "0.1", "price": "2"}]
_m2["modes"] = {"a": {"requirements": [{"quantity": "Tj", "op": "<=", "value": "40"}]},
                "b": {"requirements": [{"quantity": "Tj", "op": "<=", "value": "45"}]}}
r = S.run(_m2, conflicts=False)
check("real r01/r02: with modes, REFUTED lists EVERY failing mode (failing_modes), not only the first",
      r["verdict"] == "REFUTED" and r.get("failing_modes") == ["a", "b"], str(r)[:300])
_ra = _opt("150"); _ra["report"] = "all"
r = S.run(_ra, conflicts=False)
check("real r06: with report all, every EARNED design shows its guaranteed ranges",
      sum(1 for d in r["designs"] if d["verdict"] == "EARNED" and d.get("guaranteed")) == 3, str(r["designs"])[:300])

# two requirements on ONE quantity (2026-10-11): kept in a dict by quantity, the second overwrote the first — y <= 2.9
# then y >= 1.39 was EARNED although y reaches 3 (order-dependent). Merged now.
r1 = S.run(_tb([("<=", "2.9"), (">=", "1.39")]), conflicts=False)
r2 = S.run(_tb([(">=", "1.39"), ("<=", "2.9")]), conflicts=False)
check("FALSE EARNED fixed: two requirements on one quantity, in either order, REFUTED (it was EARNED in one order)",
      r1["verdict"] == "REFUTED" and r2["verdict"] == "REFUTED", (r1["verdict"], r2["verdict"]))
r3 = S.run(_tb([("<=", "3.01"), (">=", "1.39")]), conflicts=False)
check("... and EARNED when both hold, the shown range the merged one [1.4, 3.01]",
      r3["verdict"] == "EARNED" and r3["guaranteed"]["y"][1].startswith("301/100"), str(r3.get("guaranteed")))

# inverse questions (2026-10-12; real round 1, r03 could only bracket the limit with invented catalogs)
_f = json.load(open("examples/tasks/t28-heatsink-largest-find.json"))
r = S.run(_f)
check("find largest: r03 case B, every Rsa in [0, 1.525] proved, a failing point within [0, 1.526] (the source: 1.525)",
      r["verdict"] == "EARNED" and r["proved"] == "61/40 (~1.525)" and r["beyond_is"].startswith("REFUTED")
      and r["beyond"].startswith("763/500"), str(r)[:300])
_f2 = json.loads(json.dumps(_f)); _f2["requirements"][0]["op"] = ">="; _f2["requirements"][0]["value"] = "100"
_f2["find"] = {"smallest": "Rsa", "from": "0", "to": "20", "precision": "0.001"}
r = S.run(_f2)
# TjB = 40 + 40*(1.85 + Rsa) >= 100 holds from Rsa = -0.35: the WHOLE range works
check("find smallest: when the whole search range works, it says so (widen it)",
      r["verdict"] == "EARNED" and r["proved"] == "0" and "WHOLE" in r["proved_means"], str(r)[:300])
_f2["requirements"][0]["value"] = "200"
r = S.run(_f2)
# 40 + 40*(1.85 + Rsa) >= 200 from Rsa = 2.15
check("find smallest: Rsa >= 2.15 exactly, every Rsa in [2.15, 20] proved, a failing point in [2.149, 20]",
      r["verdict"] == "EARNED" and r["proved"] == "43/20 (~2.15)" and r["beyond"].startswith("2149/1000"), str(r)[:300])
_f2["requirements"][0]["value"] = "2000"
r = S.run(_f2)
check("find: no value works — REFUTED at the end every range shares", r["verdict"] == "REFUTED"
      and "no value" in r["why"], str(r)[:300])
_f3 = json.loads(json.dumps(_f)); del _f3["find"]["from"]
check("find: a missing 'from' is a BRICK ERROR", S.run(_f3)["verdict"] == "BRICK ERROR")

# network bricks (2026-10-12, the curator's "да"): the network certificate's verdict, every corner exact in dev
_n = json.load(open("examples/tasks/t29-bridge-network.json"))
r = S.run(_n)
check("network: a 1 % bridge, I(b5) within +-0.2 mA and I(b1) <= 5.1 mA EARNED; the proved range of I(b5) is the "
      "exact corner extreme 2000/39497 mA (dev: all 32 corners solved in fractions agree)",
      r["verdict"] == "EARNED" and all(q["dev_check"].startswith("agrees") for q in r["requirements"])
      and "2000/39497" in r["requirements"][0]["dev_check"], str(r)[:400])
_n2 = json.loads(json.dumps(_n)); _n2["requirements"] = [{"quantity": "I(b5)", "op": "within", "value": ["-0.04", "0.04"], "unit": "mA"}]
r = S.run(_n2)
check("network: +-0.04 mA REFUTED at a corner whose current is enclosed exactly above 0.04 mA",
      r["verdict"] == "REFUTED" and r["requirements"][0].get("its_violating_point")
      and F(r["requirements"][0]["value_there"][0].split()[0].lstrip("~")) > F("0.04"), str(r)[:400])
_n3 = json.loads(json.dumps(_n)); _n3["network"]["branches"]["b6"] = {"from": "n3", "to": "n4", "R": "R1"}
check("network: a floating node is a BRICK ERROR", S.run(_n3)["verdict"] == "BRICK ERROR")
_n4 = json.loads(json.dumps(_n)); _n4["requirements"][0]["unit"] = "V"
check("network: a requirement in volts on a current is a unit error", S.run(_n4)["verdict"] == "BRICK ERROR")
_n5 = json.loads(json.dumps(_n2)); _n5["requirements"][0]["value"] = ["-0.06", "0.06"]
_n5["quantities"]["V"] = {"role": "given", "range": ["9", "11"], "unit": "V"}
_n5["quantities"]["R5"] = {"role": "given", "value": "500", "unit": "ohm"}
_n5["find"] = {"smallest": "R5", "from": "1", "to": "2000", "precision": "1"}
r = S.run(_n5)
# by hand (Thevenin at the worst corner): |I| <= 0.06 mA from R5 = 333.48 ohm
check("network + find: every R5 in [334, 2000] ohm proved, 333 fails (by hand 333.48)",
      r["verdict"] == "EARNED" and r["proved"] == "334" and r["beyond"] == "333", str(r)[:300])

check("real round 2, s05: a quotient of decimals reads exactly ('76.8/1000000' = 0.0000768)",
      B.num("76.8/1000000") == F(768, 10 ** 7) and B.num("1/3") == F(1, 3))
_n6 = json.loads(json.dumps(_n)); _n6["quantities"]["R1"]["unit"] = 7
check("a unit written as a number is a BRICK ERROR (the fuzz: it reached .replace)", S.run(_n6)["verdict"] == "BRICK ERROR")

# real round 2, s02: a name only in a requirement's bound (F >= Fneed) sat at its low end in the checker's corners,
# so --dev left OPEN what work mode refuted with an exact witness; the bound's names now move with the quantity
_s2 = json.load(open("examples/real2/s02/brick.json")); del _s2["find"]
_s2["quantities"]["Fneed"] = {"role": "given", "range": ["0", "25.9"], "unit": "kN"}
r = S.run(_s2, conflicts=False)
check("dev: F >= Fneed with Fneed in [0, 25.9] kN REFUTED at mu 0.24, F 25.8914 (was OPEN: 'no corner violates it')",
      r["verdict"] == "REFUTED" and r["its_violating_point"].get("mu", "").startswith("6/25"), str(r)[:300])

# the curator's two "да" of 2026-10-12: several finds in one brick; every requirement's own verdict in a REFUTED
r = task("t30-ntc-trip-limits-find-list")
check("find list: s05's four NTC trip limits in ONE brick, each its own requirement — 320.51 / 315.75 / 279.97 / "
      "286.25 K, the four separate bricks' answers",
      r["verdict"] == "EARNED" and [f["proved"].split(" ")[0] for f in r["finds"]]
      == ["32051/100", "1263/4", "27997/100", "1145/4"], str(r)[:300])
_fl = json.load(open("examples/tasks/t30-ntc-trip-limits-find-list.json")); _fl["find"].append("x")
r = S.run(_fl)
check("find list: a malformed item is its own BRICK ERROR, and the weakest verdict", r["verdict"] == "BRICK ERROR"
      and r["finds"][4]["verdict"] == "BRICK ERROR" and r["finds"][0]["verdict"] == "EARNED", str(r)[:300])
r = S.run(json.load(open("examples/real2/s03/brick.json")), conflicts=False)
_er = {e["requirement"]["quantity"]: e for e in r.get("each_requirement", [])}
check("each_requirement: s03's combined budget REFUTED by the gain; the offset's own verdict EARNED +-2.20319 mV "
      "(the author split the brick by hand to see it)",
      r["verdict"] == "REFUTED" and _er["Eoff"]["verdict"] == "EARNED" and _er["Eg"]["verdict"] == "REFUTED"
      and _er["Eoff"]["guaranteed"]["Eoff"][1].startswith("481177/218400"), str(r.get("each_requirement"))[:300])

# real round 3 vocabulary (the curator's "да", 2026-10-12): US customary units; a tolerance naming a quantity
from ustand import units as U
check("units: psi is exactly lbf/in^2 (6894.757293168... Pa), ft = 12 in, ksi = 1000 psi; no 'kin'",
      U.parse("psi")[0] == U.parse("lbf/in^2")[0] and U.parse("ft")[0] == 12 * U.parse("in")[0]
      and U.parse("ksi")[0] == 1000 * U.parse("psi")[0] and str(U.parse("psi")[0]).startswith("8896443230521/"),
      str(U.parse("psi")[0]))
_nt = json.load(open("examples/tasks/t29-bridge-network.json"))
_nt["quantities"]["tol"] = {"role": "given", "value": "0.01", "unit": ""}
for _r in ("R1", "R2", "R3", "R4"):
    _nt["quantities"][_r]["tolerance"] = "tol"
_nt["requirements"] = [{"quantity": "I(b5)", "op": "within", "value": ["-0.06", "0.06"], "unit": "mA"}]
_nt["find"] = {"largest": "tol", "from": "0", "to": "0.1", "precision": "0.0001"}
r = S.run(_nt)
check("named tolerance + find on a network: the largest shared resistor tolerance keeping |I(b5)| <= 0.06 mA is "
      "1.18 % (1.19 % refuted)", r["verdict"] == "EARNED" and r["proved"].startswith("59/5000")
      and r["beyond"].startswith("119/10000"), str(r)[:300])
_nb = json.loads(json.dumps(_nt)); del _nb["find"]; _nb["quantities"]["tol"]["unit"] = "ohm"
check("a tolerance naming a quantity with a unit is a BRICK ERROR", S.run(_nb)["verdict"] == "BRICK ERROR")

# network v2 (the curator's "да", 2026-10-12): node potentials, a current source, the reference's own potential
r = task("t32-bridge-offset-voltage")
check("network v2: a bridge's UNLOADED offset V(n1, n2) proved within exactly [-5, 5] mV = TOL x VEX (an equality: "
      "the pinned point solved exactly) — real round 3 n01 needed a 1 Gohm detector before",
      r["verdict"] == "EARNED" and r["requirements"][0]["proved_range"] == ["-5", "5"]
      and r["requirements"][0]["dev_check"].startswith("agrees"), str(r)[:300])
r = task("t31-mosfet-thermal-network")
_rq = {q["requirement"]["quantity"]: q for q in r["requirements"]}
check("network v2: a MOSFET's thermal network with a power source and ambient at Ta — Tj in [80.27, 116.54] C "
      "(by hand: 40 + 10.4 * (8.25 || 68.2) = 116.54), V(j, s) EARNED, the sink's heat >= 8 W REFUTED (7.84 W)",
      r["verdict"] == "REFUTED" and _rq["V(j)"]["verdict"] == "EARNED"
      and _rq["V(j)"]["proved_range"][1].startswith("80996/695") and _rq["V(j, s)"]["verdict"] == "EARNED"
      and _rq["I(sa)"]["verdict"] == "REFUTED" and all(q["dev_check"].startswith("agrees") for q in r["requirements"]),
      str(r)[:400])
_t = json.load(open("examples/tasks/t32-bridge-offset-voltage.json"))
_t["requirements"][0]["value"] = ["-4.999", "4.999"]
r = S.run(_t)
check("network v2: 4.999 mV REFUTED at the corner R1 = R4 = 9990, R2 = R3 = 10010",
      r["verdict"] == "REFUTED" and r["requirements"][0]["its_violating_point"] ==
      {"R1": "9990", "R2": "10010", "R3": "10010", "R4": "9990"}, str(r)[:300])
_t["requirements"][0]["unit"] = "A"
check("network v2: a potential required in amperes is a unit error", S.run(_t)["verdict"] == "BRICK ERROR")
_t["requirements"][0] = {"quantity": "V(n9)", "op": "<=", "value": "1", "unit": "V"}
check("network v2: V() of an unknown node is a BRICK ERROR", S.run(_t)["verdict"] == "BRICK ERROR")

# network + laws, v1 one way (the curator's "да", 2026-10-12; real round 3 n02)
r = task("t33-mosfet-network-with-laws")
check("network + laws: P = ID^2 RDS into the MOSFET's thermal network; the largest drain current keeping Tj <= 175 C "
      "is 52.22 A (52.23 refuted; by hand sqrt(135 / (8.25 * 0.006)) = 52.223)",
      r["verdict"] == "EARNED" and r["proved"].startswith("2611/50") and r["beyond"].startswith("5223/100"), str(r)[:300])
_ml = json.load(open("examples/tasks/t33-mosfet-network-with-laws.json")); del _ml["find"]; _ml["quantities"]["ID"]["value"] = "40"
r = S.run(_ml)
check("network + laws at ID = 40 A: Tj in [67.6, 119.2] C exactly (40 + 1600*0.0025*6.9, 40 + 1600*0.006*8.25); "
      "P's range proved from the law first", r["verdict"] == "EARNED" and r["requirements"][0]["proved_range"] ==
      ["338/5 (~67.6)", "596/5 (~119.2)"] and r["inputs_from_laws"]["P"][1].startswith("48/5"), str(r)[:300])
_mk = json.loads(json.dumps(_ml)); _mk["quantities"]["k"] = {"role": "given", "range": ["0.9", "1.1"], "unit": ""}
_mk["quantities"]["Rsa0"] = _mk["quantities"].pop("Rsa"); _mk["quantities"]["Rsa"] = {"role": "derived", "unit": "C/W"}
_mk["laws"] = [{"zfl": "P == ID*ID*RDS*k", "source": "x"}, {"zfl": "Rsa == Rsa0*k", "source": "y"}]
r = S.run(_mk)
check("network + laws: two inputs resting on one toleranced given — the correlation_note says so",
      "k" in (r.get("correlation_note") or ""), str(r)[:300])
_mn = json.loads(json.dumps(_ml)); del _mn["laws"]
check("network: a derived input with no laws is a BRICK ERROR", S.run(_mn)["verdict"] == "BRICK ERROR")

# 4. bricks are refused aloud when malformed
bad = ex("divider-1pct-req-1pct"); bad["quantities"]["I"]["role"] = "maybe"
try:
    B.load(bad); refused = False
except B.BrickError:
    refused = True
check("a brick with an unknown role is refused", refused)

# COMPONENTS (2026-10-12, the curator's "да"): assume-guarantee contracts, bands, recursion
from ustand import components as CM
CD = pathlib.Path("examples/components")
cs = json.load(open(CD / "phone-charging-system.json"))


def comp_run(raw):
    return CM.run_system(raw, str(CD))
r_flat = S.run(str(CD / "phone-charging-flat.json"))
r_sys = S.run(str(CD / "phone-charging-system.json"))
g = lambda r, q: tuple(B.num(x.split(" ")[0]) for x in r["guaranteed"][q])
check("components: socket -> adapter -> charging board -> battery, each proved once per band: EARNED as the flat "
      "brick, and the system's Vend range ENCLOSES the flat one (only ranges travel: sound, wider)",
      r_flat["verdict"] == r_sys["verdict"] == "EARNED" and g(r_sys, "Vend")[0] <= g(r_flat, "Vend")[0]
      and g(r_flat, "Vend")[1] <= g(r_sys, "Vend")[1] and set(r_sys["components"]) == {"AD", "CH", "BT"},
      (r_sys.get("verdict"), r_sys.get("why")))
r = S.run(str(CD / "phone-charging-hierarchy.json"))
check("components, RECURSION: the adapter and the board as one component (a system with an interface), then the "
      "battery: EARNED, the same Vend range as the one-level system",
      r["verdict"] == "EARNED" and g(r, "Vend") == g(r_sys, "Vend"), (r.get("verdict"), r.get("why")))
x = _copy.deepcopy(cs)
x["quantities"]["Vmains"]["tolerance"] = "0.12"
r = comp_run(x)
check("components: mains +-12 % arrives at [202.4, 257.6] V, outside the adapter's assume [200, 250] — OPEN (not "
      "REFUTED: the contract does not cover it)", r["verdict"] == "OPEN" and "leaves the component's assume" in r["why"],
      r.get("why"))
x = _copy.deepcopy(cs)
x["components"]["CH"] = {"brick": json.load(open(CD / "charging-board.json"))}
x["components"]["CH"]["brick"]["interface"]["inputs"]["Vin"].pop("bands")
r = comp_run(x)
check("components: the charging board as ONE band [4.5, 5.5]: its headroom fails at 4.5 V, the band has no guarantee "
      "— OPEN with the board's own reason (bands [4.5, 4.6, 5, 5.5] earn it)",
      r["verdict"] == "OPEN" and "has no guarantee" in r["why"], r.get("why"))
x = _copy.deepcopy(cs)
x["requirements"][0]["value"] = ["4.15", "4.25"]
xf = json.load(open(CD / "phone-charging-flat.json"))
xf["requirements"][-1]["value"] = ["4.15", "4.25"]
r, rf = comp_run(x), S.run(xf)
check("components: Vend >= 4.15 — the flat brick EARNS it (4.152), the system's enclosure reaches 4.144: OPEN, NOT "
      "REFUTED (a failing point of an enclosure is not a refutation)",
      rf["verdict"] == "EARNED" and r["verdict"] == "OPEN" and "not a refutation" in r["why"], (rf["verdict"], r))
x = _copy.deepcopy(cs)
x["connect"]["AD.Vin"] = "CH.Vchg"
try:
    comp_run(x)
    check("components: a feedback between siblings (the adapter fed by the board) — refused (version 1)", False,
          "no error")
except B.BrickError as e:
    check("components: a feedback between siblings (the adapter fed by the board) — refused (version 1)",
          "feedback" in str(e), str(e))
x = _copy.deepcopy(cs)
del x["connect"]["BT.Vchg"]
try:
    comp_run(x)
    check("components: an input left unconnected — refused", False, "no error")
except B.BrickError as e:
    check("components: an input left unconnected — refused", "not connected" in str(e), str(e))
import tempfile as _tf
with _tf.TemporaryDirectory() as td:
    loop = {"stand": "universal-stand/1", "interface": {"inputs": {"Vi": {"assume": ["0", "1"]}}, "outputs": ["Vo"]},
            "components": {"ME": {"file": "loop.json"}}, "connect": {"ME.Vi": "Vi"},
            "quantities": {"Vi": {"role": "given", "value": "0.5", "unit": ""}, "Vo": {"role": "derived", "unit": ""}},
            "laws": [{"zfl": "Vo == ME.Vo"}], "requirements": [{"quantity": "Vo", "op": "<=", "value": "2"}]}
    json.dump(loop, open(os.path.join(td, "loop.json"), "w"))
    r = S.run(os.path.join(td, "loop.json"))
    check("components: a brick that contains itself (a cycle in the hierarchy) — BRICK ERROR",
          r["verdict"] == "BRICK ERROR" and "contains itself" in r["why"], r.get("why"))
real_run = CM.run_brick
calls = []
CM.run_brick = lambda raw, base: (calls.append(1), real_run(raw, base))[1]
try:
    CM._CACHE.clear()
    comp_run(cs)
    one = len(calls)
    calls.clear()
    CM._CACHE.clear()
    two = _copy.deepcopy(cs)
    two["components"]["AD2"] = {"file": "adapter-5v.json"}
    two["connect"]["AD2.Vin"] = "Vmains"
    comp_run(two)
finally:
    CM.run_brick = real_run
check(f"components: a second identical adapter on the same mains reuses the contract ({len(calls)} contract runs "
      f"with it, {one} without)", len(calls) == one and one > 0, (len(calls), one))
r = S.run(str(CD / "phone-charging-choose.json"))
check("components, CHOICE: three adapters cheapest first — the cheap one (+-10 %) leaves the board's assume (OPEN), "
      "the standard one (3 EUR) is EARNED; optimal FALSE (a cheaper combination is open, not refuted); 2 of 3 judged",
      r["verdict"] == "EARNED" and r["design"]["component AD"] == "standard" and r["objective"]["value"] == "3"
      and r["objective"]["optimal"] is False and r["combinations_judged"].startswith("2 of 3"), str(r)[:400])
x = json.load(open(CD / "phone-charging-choose.json"))
x["components"]["AD"]["choose"][0] = {"label": "cheap-3pct", "brick": json.load(open(CD / "adapter-5v.json")),
                                      "fields": {"price": {"value": "1.5", "unit": "EUR"}}}
x["components"]["AD"]["choose"][0]["brick"]["quantities"]["V0"]["tolerance"] = "0.03"
r = comp_run(x)
check("components, CHOICE: the cheap adapter at +-3 % keeps the chain earned — it wins at 1.5, optimal TRUE (nothing "
      "cheaper), 1 of 3 judged", r["verdict"] == "EARNED" and r["design"]["component AD"] == "cheap-3pct"
      and r["objective"]["optimal"] is True and r["combinations_judged"].startswith("1 of 3"), str(r)[:400])
for label, edit, want in (("an empty choice", lambda y: y["components"]["AD"].update(choose=[]), "non-empty"),
                          ("two candidates with one label",
                           lambda y: y["components"]["AD"]["choose"][1].update(label="cheap"), "one label"),
                          ("a field that is not a number",
                           lambda y: y["components"]["AD"]["choose"][0]["fields"].update(price="cheap"),
                           "exact number")):
    y = json.load(open(CD / "phone-charging-choose.json"))
    edit(y)
    try:
        comp_run(y)
        check(f"components, CHOICE: {label} — refused", False, "no error")
    except B.BrickError as e:
        check(f"components, CHOICE: {label} — refused", want in str(e), str(e))
y = json.load(open(CD / "phone-charging-choose.json"))
y["components"]["AD"]["choose"][1]["fields"]["price"] = "3.0"
r = comp_run(y)
check("components, CHOICE: a candidate's price without its unit against an objective in EUR — BRICK ERROR, said "
      "(not skipped as if the design had failed)", r["verdict"] == "BRICK ERROR" and "units" in r["why"], r.get("why"))
y = json.load(open(CD / "phone-charging-choose.json"))
y["components"]["AD"]["choose"][0]["fields"]["price"] = "1.5"
from ustand import units as U
try:
    comp_run(y)
    check("components, CHOICE: the EARLY-blocked candidate's price without a unit is still said (checked before "
          "judging)", False, "no error")
except (B.BrickError, U.UnitError) as e:
    check("components, CHOICE: the EARLY-blocked candidate's price without a unit is still said (checked before "
          "judging)", "units" in str(e) or "EUR" in str(e) or "dimensionless" in str(e), str(e))
y = json.load(open(CD / "phone-charging-choose.json"))
bad_c = json.load(open(CD / "adapter-5v-cheap.json"))
bad_c["laws"][0]["zfl"] = "Vout == V0 + a"                            # volts + dimensionless: a units error
y["components"]["AD"]["choose"][0] = {"label": "cheap", "brick": bad_c, "fields": {"price": {"value": "1.5",
                                                                                         "unit": "EUR"}}}
try:
    comp_run(y)
    check("components, CHOICE: a candidate whose own law mixes volts with a number — refused before judging", False,
          "no error")
except (B.BrickError, U.UnitError) as e:
    check("components, CHOICE: a candidate whose own law mixes volts with a number — refused before judging",
          "candidate cheap" in str(e), str(e))
r = S.run(str(CD / "phone-charging-find.json"))
check("components, FIND over a system: the widest mains the chain earns is 250 V (the adapter's assume); 250.1 is "
      "OPEN — not decided, never a false 'cannot'", r["verdict"] == "EARNED" and r["proved"] == "250"
      and r["beyond_is"].startswith("OPEN"), str(r)[:300])
r = S.run(str(CD / "phone-charging-tune.json"))
check("components, PARAMETERS: the adapter's feedback resistor from its own catalog — 2k7 and 3k3 (cheapest) put "
      "Vout outside the board's assume (OPEN), 3k0 1 % is EARNED at 0.012 EUR, the 0.1 % part never needed",
      r["verdict"] == "EARNED" and r["design"]["component AD"] == "R1=3k0-1%" and r["objective"]["value"] ==
      "3/250 (~0.012)" and r["combinations_judged"].startswith("3 of 4")
      and r["design"]["component CH"] == "charging-board.json", str(r)[:400])
r = S.run(str(CD / "bridge-two-sensors.json"))
check("components, AFFINE contracts: two ratiometric sensors on one supply 5 V +-5 % — each output is 1/2 x supply "
      "+ a proved remainder, the supply cancels: Diff within +-3.1 mV, EARNED (hand: 2 x 0.0001 x 5.5 + 2 mV)",
      r["verdict"] == "EARNED" and r["guaranteed"]["Diff"] == ["-31/10000 (~-0.0031)", "31/10000 (~0.0031)"]
      and r["components"]["S1"]["outputs_affine"]["Vo"]["slope"] == {"Vs": "1/2"}, str(r)[:300])
x = json.load(open(CD / "bridge-two-sensors.json"))
x["contracts"] = "ranges"
r = comp_run(x)
check("components, the same with RANGES only (\"contracts\": \"ranges\"): each output +-0.13 V on its own, the "
      "difference cannot be shown — OPEN (and not a refutation)", r["verdict"] == "OPEN", (r.get("verdict"),
                                                                                       str(r.get("why"))[:200]))
x = json.load(open(CD / "phone-charging-system.json"))
x["quantities"]["Vmains"] = {"role": "given", "value": "0.23", "tolerance": "0.08", "unit": "kV"}
r1, r2 = comp_run(x), S.run(str(CD / "phone-charging-system.json"))
check("components: the mains given in kV reaches the adapter's input in V — the same arriving range, the same "
      "answer (the arriving range goes through SI)", r1["verdict"] == "EARNED" and r1["guaranteed"] == r2["guaranteed"]
      and r1["components"]["AD"]["inputs"]["Vin"]["arrives"] == ["1058/5", "1242/5"], str(r1)[:300])
x = json.load(open(CD / "phone-charging-system.json"))
x["quantities"]["Vmains"]["unit"] = "A"
try:
    comp_run(x)
    check("components: an ampere source wired to a volt input — refused (dimensions differ)", False, "no error")
except B.BrickError as e:
    check("components: an ampere source wired to a volt input — refused (dimensions differ)", "dimensions differ"
          in str(e), str(e))
# TIGHT CONTRACTS (2026-10-12, real round 4): a contract's ranges were the stand's OUTER reading — R1 twice in
# Vr*(R1+R2)/R1 did not cancel; now each end is proved just past the attained extreme
r = S.run(str(EX / "real4" / "k01" / "brick_system.json"))
check("tight contracts: k01's original single-band divider system (all 12 OPEN in round 4) — EARNED on Vref 1 % + "
      "R 1 %, the flat brick's cheapest passing pair", r["verdict"] == "EARNED" and r["design"].get("component DIV")
      == "RES=R +-1%" and r["design"].get("component REF") == "REF=Vref +-1%", str(r)[:300])
_MODE.DEV[0] = False                        # WORK mode: ZTL's verdict (the tight ADC remainder is ZTL's affine reading)
CM._CACHE.clear()
r = S.run(str(EX / "real4" / "k02" / "sys-total20.json"))
_MODE.DEV[0] = True
CM._CACHE.clear()
e20 = [B.num(x.split(" ")[0].lstrip("~")) for x in r["guaranteed"]["Err"]] if r.get("guaranteed") else None
check("tight contracts (work mode): k02's amplifier + ADC as components within 20 mV (OPEN in round 4, +-32 mV) — "
      "EARNED, within 0.2 mV of the flat range [-16.06, 16.31] mV", r["verdict"] == "EARNED" and e20 is not None
      and abs(e20[0] + F(1606, 100000)) < F(2, 10000) and abs(e20[1] - F(1631, 100000)) < F(2, 10000), str(r)[:300])
r = S.run(str(EX / "real4" / "k02" / "sys-total20.json"))
check("  ... and in --dev it stays OPEN, said: the checker cannot confirm the ADC remainder's tight bound (a product "
      "input x 1/Vref with a slope near zero — ZTL's affine reading; the class of blind test 5's c09)",
      r["verdict"] == "OPEN", (r.get("verdict"), str(r.get("why"))[:200]))
# ROUND 4's gaps closed (2026-10-12)
x = json.load(open(CD / "phone-charging-system.json"))
for c_, f_ in (("AD", "adapter-5v.json"), ("CH", "charging-board.json"), ("BT", "battery-cell.json")):
    bb_ = json.load(open(CD / f_))
    for n_ in bb_["interface"]["inputs"]:
        bb_["interface"]["inputs"][n_]["bands"] = "arriving"
    x["components"][c_] = {"brick": bb_}
r = comp_run(x)
check("components, \"bands\": \"arriving\": each contract judged on what arrives — the charger's Vend equals the "
      "FLAT brick's [4.152, 4.238] V exactly (hand bands: [4.144, 4.246])", r["verdict"] == "EARNED"
      and r["guaranteed"]["Vend"] == ["519/125 (~4.152)", "2119/500 (~4.238)"], str(r)[:300])
x = json.load(open(CD / "phone-charging-tune.json"))
x["objective"] = {"minimize": "AD.R1.price", "unit": "EUR"}
x["laws"].append({"zfl": "Rsel == AD.R1.R"})
x["quantities"]["Rsel"] = {"role": "derived", "unit": "ohm"}
x["requirements"].append({"quantity": "Rsel", "op": ">=", "value": "2900"})
r = comp_run(x)
check("components: the chosen part's fields reach the system — AD.R1.price as the objective (the same pick, 3k0 1 %), "
      "AD.R1.R as 3 kohm +-1 % ([2970, 3030])", r["verdict"] == "EARNED" and r["design"]["component AD"] ==
      "R1=3k0-1%" and r["guaranteed"]["Rsel"] == ["2970", "3030"], str(r)[:300])
x["laws"].append({"zfl": "Q == AD.R1.nope"})
x["quantities"]["Q"] = {"role": "derived", "unit": ""}
try:
    comp_run(x)
    check("components: AD.R1.nope (no such field) — refused, said plainly", False, "no error")
except B.BrickError as e:
    check("components: AD.R1.nope (no such field) — refused, said plainly", "neither an output" in str(e), str(e))
# blind 6 c03: an OPTIONAL slot inside a component; c03: `valid` on a system law; c02: a component's price that reads
# an input the system decides is not given as `cost`
_pack = json.load(open(EX / "blind6" / "work_c03" / "pack.json"))
_pack["catalog"]["heater"]["items"] = [i_ for i_ in _pack["catalog"]["heater"]["items"]
                                       if "none" not in json.dumps(i_).lower()]
_pack["slots"]["HT"]["optional"] = True
_sys3 = json.load(open(EX / "blind6" / "work_c03" / "system.json"))
for c_, sp_ in _sys3["components"].items():
    if sp_.get("file", "").endswith("pack.json"):
        _sys3["components"][c_] = {"brick": _pack}
r = CM.run_system(_sys3, str(EX / "blind6" / "work_c03"))
check("blind 6 c03: an optional slot inside a component (KeyError 'HT_none' before) — EARNED", r["verdict"] == "EARNED",
      str(r)[:200])
x = json.load(open(CD / "phone-charging-system.json"))
x["laws"] = [{"zfl": "Vend == BT.Vcell", "valid": "BT.Vcell > 0"}]
r = comp_run(x)
check("blind 6 c03: `valid` on a system law naming a component output (a units BRICK ERROR before) — EARNED",
      r["verdict"] == "EARNED", str(r)[:200])
ad_ = json.load(open(CD / "adapter-divider.json"))
ad_["objective"] = {"minimize": "R1.price*Vin", "unit": "EUR*V"}
x = json.load(open(CD / "phone-charging-tune.json"))
x["components"]["AD"] = {"brick": ad_}
try:
    comp_run(x)
    check("blind 6 c02: AD.cost read from a price that depends on the system's input — refused, said", False, "no error")
except B.BrickError as e:
    check("blind 6 c02: AD.cost read from a price that depends on the system's input — refused, said",
          "decided by the system" in str(e), str(e))
ps = json.load(open(CD / "power-supply.json"))
ps["components"]["AD"] = json.load(open(CD / "phone-charging-choose.json"))["components"]["AD"]
hier = json.load(open(CD / "phone-charging-hierarchy.json"))
ps2 = json.load(open(CD / "power-supply.json"))
ps2["components"]["AD"] = {"brick": json.load(open(CD / "adapter-divider.json"))}
h2 = _copy.deepcopy(hier)
h2["components"]["PS"] = {"brick": ps2}
try:
    comp_run(h2)
    check("components: a component with PARAMETERS inside a component that is a system — refused", False, "no error")
except B.BrickError as e:
    check("components: a component with PARAMETERS inside a component that is a system — refused",
          "may not CHOOSE" in str(e), str(e))
hier["components"]["PS"] = {"brick": ps}
try:
    comp_run(hier)
    check("components: a CHOICE inside a component that is a system — refused (its contract is one device's)", False,
          "no error")
except B.BrickError as e:
    check("components: a CHOICE inside a component that is a system — refused (its contract is one device's)",
          "may not CHOOSE" in str(e), str(e))

# CAPACITY BENCH (2026-10-13): a linear ladder of 8 coupled unknowns came back OPEN "no proved range" with no reason —
# the symbolic cap (certify.MAX_SYSTEM = 6) is now named in the OPEN
import sys as _sys
_sys.path.insert(0, "bench")
import scale as _SC  # noqa: E402
from ustand import mode as _MD
_dev, _MD.DEV[0] = _MD.DEV[0], False        # in --dev the checker's own corner cap speaks first (its reason is named too)
try:
    r = S.run(_SC.lin_system(8), conflicts=False)
finally:
    _MD.DEV[0] = _dev
check("a linear system above the symbolic cap (8 unknowns): no longer OPEN — zlin certifies it (2026-10-15)",
      r["verdict"] == "EARNED", str(r)[:300])

# SOUNDNESS AUDIT 2026-10-13 (cloud session; PR inventor1975/ztl-stand#1): three false EARNED from the code that
# rewrites a brick before the judge sees it; each checked locally on 2026-10-15 against the brick by hand
AU = pathlib.Path(__file__).resolve().parent / "audit-2026-10-13"
r = S.run(str(AU / "system-same-source-ge1.json"))
check("audit cx1: both inputs of a difference stage wired to ONE source — Out = G*(S - S) = 0, so Out >= 1 fails "
      "everywhere: the slopes add, and the requirement fails at EVERY point of the components' ranges — REFUTED",
      r["verdict"] == "REFUTED" and "fails at EVERY point" in str(r.get("why")), (r.get("verdict"), str(r.get("why"))[:200]))
x = json.load(open(AU / "system-same-source-ge1.json"))
x["requirements"][0]["value"] = "0"
r = CM.run_system(x, str(AU))
check("audit cx1, the twin: Out >= 0 — true (Out = 0), but the ranges hold points on both sides: not refuted (OPEN), "
      "since a failing point of an enclosure is not a refutation", r["verdict"] == "OPEN",
      (r.get("verdict"), str(r.get("why"))[:200]))
r = S.run(str(AU / "named-tol-modes.json"))
check("audit cx2: a mode overriding a NAMED tolerance (hot: R = 1000 +-10 %, y reaches 1.1 > 1.05): REFUTED",
      r["verdict"] == "REFUTED", (r.get("verdict"), str(r.get("why"))[:200]))
r = S.run(str(AU / "named-tol-modes-totals.json"))
check("audit cx2 with totals: the same named tolerance per mode: REFUTED",
      r["verdict"] == "REFUTED", (r.get("verdict"), str(r.get("why"))[:200]))
r = S.run(str(AU / "mm1-domain-modes-totals.json"))
check("audit cx3: modes with totals — a law's `valid` read in the mode (peak: mu - lam = -2, outside mu > lam): "
      "REFUTED", r["verdict"] == "REFUTED", (r.get("verdict"), str(r.get("why"))[:200]))

r = S.run(str(AU / "fz-1.json"))
check("audit fuzz fz-1: `x0 - -19` (as ast.unparse writes it) is read — ZTL's parser took the second minus for a "
      "subtraction and the stand died (STAND ERROR); now EARNED", r["verdict"] == "EARNED",
      (r.get("verdict"), str(r.get("why"))[:200]))
r = S.run(str(AU / "fz-3020-dev.json"))
check("audit fz-3020 (dev): a bound tight through min/max — every corner inside, the checker's own bound wider: "
      "not confirmed (OPEN), never a STAND FAULT", r["verdict"] == "OPEN" and "not confirmed" in json.dumps(r),
      (r.get("verdict"), str(r.get("why"))[:200]))

# LARGE LINEAR SYSTEMS (2026-10-15, the curator's "да"): a certificate over the box — linsearch searches, zlin (a kernel
# module, exact fractions) checks; the symbolic path stopped near 7 unknowns (the formula grew ~3x per unknown)
import itertools as _it
import zlin as ZL                                      # ZTL's kernel module (moved there 2026-10-15)
from ustand import linsearch as LSR, checker as _CK
from znumjudge import parse_quantities as _pq
_lb = _SC.lin_system(3)
_bx = {nm: (B.num(q["value"]) * (1 - B.num(q["tolerance"])), B.num(q["value"]) * (1 + B.num(q["tolerance"])))
       for nm, q in _lb["quantities"].items() if q["role"] == "given"}
_un, _lw = ["u0", "u1", "u2"], [l["zfl"] for l in _lb["laws"]]
_qs = _pq(J.sheet({}, _bx, _un, {}))[0]
_nm = sorted(_bx)
_vals = [_CK.solve_at(_lw, dict(zip(_nm, c)), _un)["u2"] for c in _it.product(*[_bx[n] for n in _nm])]
_lo, _hi = min(_vals), max(_vals)
_g = LSR.search(_lw, _un, _qs, "u2", "<=", _hi)
check("zlin: a 3-unknown ladder, 7 tolerances — the max over all 128 corners (solved exactly) is PROVED with no slack",
      "cert" in _g and ZL.check(_lw, _un, _qs, "u2", "<=", _hi, _g["cert"])[0], str(_g)[:200])
_g2 = LSR.search(_lw, _un, _qs, "u2", ">=", _lo)
check("zlin: and the min, with no slack", "cert" in _g2 and ZL.check(_lw, _un, _qs, "u2", ">=", _lo, _g2["cert"])[0])
_below = _hi * (1 - F(1, 10**9))
_g3 = LSR.search(_lw, _un, _qs, "u2", "<=", _below)
check("zlin: a bound a billionth below the max — a witness, and the witness truly fails (solved exactly)",
      "witness" in _g3 and _CK.solve_at(_lw, _g3["witness"], _un)["u2"] > _below, str(_g3)[:200])
check("zlin MUTATION: the max's certificate for a bound below the max — refused",
      not ZL.check(_lw, _un, _qs, "u2", "<=", _below, _g["cert"])[0])
import copy as _cp
_m = _cp.deepcopy(_g["cert"])
_p = _m["tree"]
while _p.get("leaf") != "pin" and "split" in _p:
    _p = _p["lo"]
if _p.get("leaf") == "pin":
    _k = next(iter(_p["signs"]))
    _p["signs"][_k] = "-" if _p["signs"][_k] == "+" else "+"
    check("zlin MUTATION: a flipped monotonicity sign — refused", not ZL.check(_lw, _un, _qs, "u2", "<=", _hi, _m)[0])
    _m = _cp.deepcopy(_g["cert"])
    _p = _m["tree"]
    while _p.get("leaf") != "pin" and "split" in _p:
        _p = _p["lo"]
    _p["R"] = [["0"] * 3 for _ in range(3)]
    check("zlin MUTATION: a zero R (no inverse) — refused (beta >= 1)", not ZL.check(_lw, _un, _qs, "u2", "<=", _hi, _m)[0])
else:
    check("zlin: the certificate has a pin leaf to mutate", False, str(_g["cert"])[:200])
check("zlin MUTATION: an exact leaf on a piece that is not a point — refused",
      not ZL.check(_lw, _un, _qs, "u2", "<=", _hi, {"leaf": "exact"})[0])
_dev, _MD.DEV[0] = _MD.DEV[0], False        # the dev checker enumerates corners: 17+ tolerances are past it
try:
    _r8 = S.run(_SC.lin_system(8), conflicts=False)
    _b20 = _SC.lin_system(20)
    _b20["requirements"] = [{"quantity": "u19", "op": ">=", "value": "0.0000001"}, {"quantity": "u19", "op": "<=", "value": "1"}]
    _r20 = S.run(_b20, conflicts=False)
finally:
    _MD.DEV[0] = _dev
check("a ladder of 8 coupled linear unknowns (was OPEN at the cap of 6): EARNED by zlin", _r8["verdict"] == "EARNED",
      str(_r8)[:300])
check("a ladder of 20 coupled linear unknowns, 41 tolerances: EARNED by zlin", _r20["verdict"] == "EARNED", str(_r20)[:300])

# --dev PAST ITS CORNER WALL (2026-10-15): more than 16 tolerances in one coupled group — the checker re-checks zlin's
# certificate with its OWN means (checker.check_linear_certificate: its own reading, derivatives and arithmetic)
_b20d = _SC.lin_system(20)
_b20d["requirements"] = [{"quantity": "u19", "op": ">=", "value": "0.0000001"}, {"quantity": "u19", "op": "<=", "value": "1"}]
_r = S.run(_b20d, conflicts=False)
check("--dev, a ladder of 20 unknowns / 41 tolerances (past the checker's 16-corner wall): EARNED — zlin's certificate "
      "re-checked by the checker's own code", _r["verdict"] == "EARNED", str(_r)[:300])
_rlc = C.check_linear_certificate
C.check_linear_certificate = lambda *a, **k: (False, "mutated checker")
try:
    _r = S.run(_b20d, conflicts=False)
finally:
    C.check_linear_certificate = _rlc
check("--dev MUTATION: the checker's re-check refuses — the design stays OPEN (not earned), said",
      _r["verdict"] == "OPEN" and "re-check" in json.dumps(_r), str(_r)[:300])
_lb3 = _SC.lin_system(3)
_bx3 = {nm: (B.num(q["value"]) * (1 - B.num(q["tolerance"])), B.num(q["value"]) * (1 + B.num(q["tolerance"])))
        for nm, q in _lb3["quantities"].items() if q["role"] == "given"}
_un3, _lw3 = ["u0", "u1", "u2"], [l["zfl"] for l in _lb3["laws"]]
_q3 = _pq(J.sheet({}, _bx3, _un3, {}))[0]
_v3 = [_CK.solve_at(_lw3, dict(zip(sorted(_bx3), c)), _un3)["u2"] for c in _it.product(*[_bx3[n] for n in sorted(_bx3)])]
_g3c = LSR.search(_lw3, _un3, _q3, "u2", "<=", max(_v3))
check("the checker's re-check agrees with zlin at the exact maximum, and refuses a billionth below it",
      C.check_linear_certificate(_lw3, {}, _bx3, _un3, "u2", "<=", max(_v3), _g3c["cert"])[0]
      and not C.check_linear_certificate(_lw3, {}, _bx3, _un3, "u2", "<=", max(_v3) * (1 - F(1, 10**9)), _g3c["cert"])[0])

# AN EXPRESSION of many unknowns (2026-10-15): a linear one joins the system as one more unknown (q == expression); a
# nonlinear one reads the unknowns' ranges proved by zlin, as boxes, in ZTL's certificate
_bx = _SC.lin_system(20)
_bx["quantities"].update({"dV": {"role": "derived", "unit": "V"}, "I19": {"role": "derived", "unit": "A"},
                          "P19": {"role": "derived", "unit": "W"}})
_bx["laws"] += [{"zfl": "dV == u18 - u19"}, {"zfl": "I19 == (u18 - u19)/R19"}, {"zfl": "P19 == u19*u19/G19"}]
_rx = {}
for _nm, _rq in (("dV>=0", {"quantity": "dV", "op": ">=", "value": "0"}),
                 ("I<=1mA", {"quantity": "I19", "op": "<=", "value": "0.001"}),
                 ("dV<=1e-10", {"quantity": "dV", "op": "<=", "value": "0.0000000001"}),
                 ("P<=1", {"quantity": "P19", "op": "<=", "value": "1"}),
                 ("P<=1e-15", {"quantity": "P19", "op": "<=", "value": "0.000000000000001"})):
    _rx[_nm] = S.run(dict(_bx, requirements=[_rq]), conflicts=False)
check("a linear expression of 20 unknowns: u18 - u19 >= 0 and the current (u18 - u19)/R19 <= 1 mA EARNED (--dev: "
      "re-checked); u18 - u19 <= 1e-10 REFUTED at an exact point",
      (_rx["dV>=0"]["verdict"], _rx["I<=1mA"]["verdict"], _rx["dV<=1e-10"]["verdict"]) == ("EARNED", "EARNED", "REFUTED"),
      {k: v["verdict"] for k, v in _rx.items()})
check("a PRODUCT of unknowns (P19 = u19^2/G19, ~2.3e-14 W): u19's range proved by zlin enters ZTL's certificate as a "
      "box — P19 <= 1 EARNED; P19 <= 1e-15 (false) REFUTED at an exact point",
      (_rx["P<=1"]["verdict"], _rx["P<=1e-15"]["verdict"]) == ("EARNED", "REFUTED"),
      (_rx["P<=1"]["verdict"], _rx["P<=1e-15"]["verdict"]))

# WIDE TOLERANCES ON EVERY PART (2026-10-15): zlin step 6 — quantities that enter by one layer (proved by an exact
# identity on a grid): signs by three factors, vertex branches; the checker re-checks with its own means in --dev
_bw = _SC.lin_system(10)
for _q in _bw["quantities"].values():
    if _q.get("tolerance"):
        _q["tolerance"] = "0.05"
_mx = F("0.01468210528723179")          # the exact worst case of u9 (MEASURED: descent + certificate, 2026-10-15)
_rw = {}
for _nm, _val in (("above", _mx * (1 + F(1, 10**6))), ("below", _mx * (1 - F(1, 10**6)))):
    _rw[_nm] = S.run(dict(_bw, requirements=[{"quantity": "u9", "op": "<=", "value": str(_val)}]), conflicts=False)
check("EVERY part +-5 %, 10 unknowns (21 tolerances; the first-order sign read found no certificate): u9 a millionth "
      "above its exact worst case EARNED (--dev: re-checked), a millionth below REFUTED",
      (_rw["above"]["verdict"], _rw["below"]["verdict"]) == ("EARNED", "REFUTED"),
      {k: (v["verdict"], str(v.get("why"))[:120]) for k, v in _rw.items()})

# THE GREEDY VERTEX (2026-10-15): before any tree, coordinate ascent over the vertices — a bound below the extreme is
# refuted at once by the very worst vertex (it measured 9 descent steps of whole searches before, ~500 s at 20)
_bwq = _pq(J.sheet({}, {nm: (B.num(q["value"]) * F(19, 20), B.num(q["value"]) * F(21, 20))
                         for nm, q in _bw["quantities"].items() if q["role"] == "given"}, [f"u{i}" for i in range(10)], {}))[0]
_gw = LSR.search([l["zfl"] for l in _bw["laws"]], [f"u{i}" for i in range(10)], _bwq, "u9", "<=", _mx * (1 - F(1, 10**6)))
check("the greedy vertex: a bound a millionth below u9's exact worst case is refuted at once, at THE worst vertex "
      "(its exact value equals the proved extreme to 1e-12; _mx is its decimal)", _gw.get("greedy") is True and
      abs(_CK.solve_at([l["zfl"] for l in _bw["laws"]], _gw["witness"], [f"u{i}" for i in range(10)])["u9"] - _mx)
      <= _mx * F(1, 10**12),
      str(_gw)[:200])

# SPICE NETLIST IMPORT (2026-10-15, the curator's "да"): what an engineer's CAD writes — netlist + BOM + requirements
from ustand import spice as SP
_SPD = pathlib.Path(__file__).resolve().parent.parent / "examples" / "spice"


def _sp(cir, reqs, bom=None):
    return S.run(SP.to_brick((_SPD / cir).read_text(), SP.read_bom(str(_SPD / bom)) if bom else None, reqs),
                 conflicts=False)["verdict"]


check("spice: 5 V divider 10k/10k, all 1 % (by hand V(out) in [2.45025, 2.55025]): 2.4..2.6 EARNED, 2.45..2.55 REFUTED",
      (_sp("divider.cir", ["V(out) within 2.4 2.6"], "divider-bom.csv"),
       _sp("divider.cir", ["V(out) within 2.45 2.55"], "divider-bom.csv")) == ("EARNED", "REFUTED"))
check("spice: a non-inverting op-amp (VCVS, open loop 1e5), 1k/9k at 1 % (by hand gain 9.82..10.18): 9.7..10.3 EARNED, "
      "9.9..10.1 REFUTED", (_sp("noninv-opamp.cir", ["V(out) within 9.7 10.3"], "noninv-opamp-bom.csv"),
                            _sp("noninv-opamp.cir", ["V(out) within 9.9 10.1"], "noninv-opamp-bom.csv")) == ("EARNED", "REFUTED"))
check("spice: a Wheatstone bridge, 0.1 % (tol= on the line): |V(a,b)| <= 0.01 EARNED exactly at the edge, 0.0099 REFUTED",
      (_sp("bridge.cir", ["V(a,b) within -0.01 0.01"]), _sp("bridge.cir", ["V(a,b) within -0.0099 0.0099"]))
      == ("EARNED", "REFUTED"))
check("spice: an LM317-like regulator (Vref 4 %, Iadj 0..100 uA, R 1 %; by hand V(out) in [4.7287, 5.3516]): the exact "
      "bounds EARNED, 4.8..5.3 REFUTED, the load's power P(Rload) <= 0.3 W EARNED (a nonlinear expression)",
      (_sp("lm317.cir", ["V(out) within 4.7287 5.3516"], "lm317-bom.csv"),
       _sp("lm317.cir", ["V(out) within 4.8 5.3"], "lm317-bom.csv"),
       _sp("lm317.cir", ["P(Rload) <= 0.3"], "lm317-bom.csv")) == ("EARNED", "REFUTED", "EARNED"))
check("spice: a 12-node ladder (beyond the 6-unknown symbolic cap): V(n12) >= 1 uV and I(R11) <= 1 mA EARNED (zlin)",
      (_sp("ladder12.cir", ["V(n12) >= 1u"], "ladder12-bom.csv"), _sp("ladder12.cir", ["I(R11) <= 1m"], "ladder12-bom.csv"))
      == ("EARNED", "EARNED"))
# RANGE OF a quantity (spice.range_of) — the duel of 2026-10-15, T09: 24 resistors at 0.1 % give exact fractions of ~80
# digits; the door shortened them to "~6.4579273651" and the descent read that back -> BRICK ERROR. The values are
# now kept whole for the descent; both ends exact (by an independent 2^24-corner enumeration: 6.457927365099..,
# 6.481533859570..)
_t09 = pathlib.Path(__file__).resolve().parent.parent / "bench" / "spice-duel" / "tasks" / "T09"
_r9 = SP.range_of((_t09 / "circuit.cir").read_text(), SP.read_bom(str(_t09 / "bom.csv")), "V(n11)")
check("spice range: a 24-resistor ladder at 0.1 % — both ends attained AND proved (exact), the long fractions read "
      "back whole (not the door's '~...')",
      _r9["min"]["exact"] and _r9["max"]["exact"] and len(_r9["min"]["attained"]) > 70
      and abs(_r9["min"]["attained_approx"] - 6.457927365099428) < 1e-12
      and abs(_r9["max"]["attained_approx"] - 6.481533859570416) < 1e-12, json.dumps(_r9)[:300])
# OKUMURA'S PROBLEM (Popova & Kraemer 2008; Hladik, SCAN 2010): a 5-node conductance ladder, p1..p9 in [0.99, 1.01],
# whose EXACT interval hull is published — x1 in [7.0170, 7.1663], x5 in [1.0614, 1.1211] (4 decimals, outward)
import math
_ok = pathlib.Path(__file__).resolve().parent.parent / "bench" / "hard-tasks" / "okumura"
_okn, _okb = (_ok / "circuit.cir").read_text(), SP.read_bom(str(_ok / "bom.csv"))
# WORK mode (the CLI's default). In dev mode x1's minimum stays a bracket (proved >= 6.9624, attained 7.0327 after 16
# runs, exact = false — sound, but the descent does not reach 7.0170): a known gap of the dev route (2026-10-16)
_MODE.DEV[0] = False
_ok1, _ok5 = SP.range_of(_okn, _okb, "V(n1)"), SP.range_of(_okn, _okb, "V(n5)")
_MODE.DEV[0] = True
check("Okumura's problem: the stand's exact range (attained = proved) is the published exact hull, x1 and x5",
      all(r[s_]["exact"] for r in (_ok1, _ok5) for s_ in ("min", "max"))
      and [(math.floor if s_ == "min" else math.ceil)(r[s_]["attained_approx"] * 10**4) for r in (_ok1, _ok5)
           for s_ in ("min", "max")] == [70170, 71663, 10614, 11211],         # the hull rounded OUTWARD, as published
      [(r["min"].get("attained_approx"), r["max"].get("attained_approx")) for r in (_ok1, _ok5)])
# THE MULTI-NODE MOTOR (2026-10-16): three faults that stopped a four-unit design — (1) 0.000000001 in a law came
# back from ast as 1e-09, which ZTL's reader split at the minus (STAND ERROR); (2) a HAIR-WIDE implicit root (the
# nozzle's exit Mach, a design constant 1e-12 wide) read as a free box needed a sign it cannot show: the search cut
# every other quantity, OPEN after 15 min — as a root first: one monotone leaf; (3) the nominal price solved EVERY law,
# and a weak design's sqrt(negative) rail speed made the whole catalog a BRICK ERROR — now only the price's own laws
check("bricks: a decimal Python would print in scientific notation becomes an exact fraction; others are kept",
      B.compile_expr("x == 0.000000001*y + 0.5") == "x == (1/1000000000)*y + 0.5", B.compile_expr("x == 0.000000001*y + 0.5"))
_m37 = json.load(open(pathlib.Path(__file__).resolve().parent.parent / "examples" / "tasks" / "t37-srm-four-units.json"))
_m37["where"] = ['PR.name == "APCP" and GD.d == 30 and GL.Lg == 90 and GN.N == 2 and NT.Dt == 12 and NE.eps == 3 '
                 'and CT.t == 4.0']
_r37 = S.run(_m37, conflicts=False)
check("the four-unit motor, its optimum pinned: EARNED at 62.9007 EUR (the root read as a root; before: OPEN at 15 min)",
      _r37["verdict"] == "EARNED" and "62.9007" in json.dumps(_r37.get("objective")), json.dumps(_r37)[:300])
_m37w = json.load(open(pathlib.Path(__file__).resolve().parent.parent / "examples" / "tasks" / "t37-srm-four-units.json"))
_m37w["where"] = ['PR.name == "APCP" and GD.d == 20 and GL.Lg == 90 and GN.N == 1 and NT.Dt == 20 and NE.eps == 8 '
                  'and CT.t == 2.0']                  # nominal thrust NEGATIVE (overexpanded at 0.1 MPa): no rail speed
_r37w = S.run(_m37w, conflicts=False)
check("a design with no rail speed at its nominal point (thrust below weight) is that design's failure, not a BRICK "
      "ERROR of the brick (the price reads only its own laws)", _r37w["verdict"] in ("REFUTED", "OPEN")
      and "BRICK" not in json.dumps(_r37w), json.dumps(_r37w)[:300])
# THE 28-DATUM MOTOR (2026-10-16): per-segment batches. Two faults made a good design OPEN at 15 min: (1) the exact
# zeros of absent segments were folded through simplify, whose one-fraction form EXPANDED (Dt + dDt)^2 into terms of
# 5e8 that cancel — readings 1e6 wide; now only the zeros fold (certify.fold_zeros); (2) no PIN: 16 of 18 signs were
# shown but every split kept them at full width — now they pin (ZTL zcertify "pin", checked by the kernel)
check("fold_zeros: only the zeros fold, the factored rest is kept (no expansion)",
      K.fold_zeros("s3*(a + b)*(c + d) + x*(s4 - 0) + (Dt + dDt)*(Dt + dDt)/(1 + s3*y)", {"s3", "s4"})
      == "(Dt + dDt) * (Dt + dDt) / 1", K.fold_zeros("s3*(a + b) + (Dt + dDt)*(Dt + dDt)", {"s3"}))
_m38 = json.load(open(pathlib.Path(__file__).resolve().parent.parent / "examples" / "tasks" / "t38-srm-28-uncertain.json"))
_m38["where"] = ['PR.name == "APCP" and GD.d == 25 and GL.Lg == 90 and GN.N == 2 and NT.Dt == 12 and NE.eps == 3 '
                 'and CT.t == 2.0']
_MODE.DEV[0] = False
_r38 = S.run(_m38, conflicts=False)
_MODE.DEV[0] = True
check("the 28-datum motor's optimum pinned: EARNED at 65.0122 EUR (work mode; before: OPEN at 15 min)",
      _r38["verdict"] == "EARNED" and "65.0122" in json.dumps(_r38.get("objective")), json.dumps(_r38)[:300])
from ustand import fwitness as FW
_m38f = json.load(open(pathlib.Path(__file__).resolve().parent.parent / "examples" / "tasks" / "t38-srm-28-uncertain.json"))
_m38f["where"] = ['PR.name == "APCP" and GD.d == 30 and GL.Lg == 90 and GN.N == 2 and NT.Dt == 12 and NE.eps == 3 '
                  'and CT.t == 4.0']
_fw = []
_real_gc = S._greedy_corner
S._greedy_corner = lambda *a, **k: None                          # the float search alone must find the failing point
_orig_find = FW.find
FW_find_calls = []
def _spy_find(*a, **k):
    r_ = _orig_find(*a, **k)
    _fw.append(r_)
    return r_
S.FW.find = _spy_find
_MODE.DEV[0] = False
_r38f = S.run(_m38f, conflicts=False)
_MODE.DEV[0] = True
S._greedy_corner = _real_gc
S.FW.find = _orig_find
check("fwitness: with the exact greedy walk silenced, the float search finds the failing point of the t37 optimum "
      "under 28 data (a_max > 25 g) — re-solved exactly, REFUTED",
      _r38f["verdict"] == "REFUTED" and any(x is not None for x in _fw), json.dumps(_r38f)[:200])
# A PLANE TRUSS from an ANSYS deck (ustand/truss.py, 2026-10-16) — Muhanna's IFEM benchmark 2 geometry. The unknowns'
# and the equations' UNITS (certify._scaling): a tall cantilever's plain contraction is 1.2 at 12 floors (3.2 at 20)
# where rho(|C|) is 0.03 — the search split 256 pieces in 540 s; rescaled, ONE piece (MEASURED)
from ustand import truss as TR
_TRD = pathlib.Path(__file__).resolve().parent.parent / "examples" / "truss"
_tr20 = (_TRD / "cantilever20.txt").read_text()
_bk20 = TR.to_brick(_tr20, None)
_v20 = C.solve_at([l["zfl"] for l in _bk20["laws"]],
                  {n: B.num(q["value"]) for n, q in _bk20["quantities"].items() if q["role"] == "given"},
                  [n for n, q in _bk20["quantities"].items() if q["role"] == "derived"])
check("truss: the 20-floor cantilever (101 bars, 81 unknowns) at its nominal point — corner D as the benchmark "
      "publishes it (UX 18208.5, UY -806.663)",
      abs(float(_v20["U_42_X"]) - 18208.5) < 0.05 and abs(float(_v20["U_42_Y"]) + 806.663) < 0.002,
      (float(_v20["U_42_X"]), float(_v20["U_42_Y"])))
_tr12 = (_TRD / "cantilever12.txt").read_text()
_r12 = TR.judge(_tr12, "0.5%", [TR._req("U(26,X) <= 10000")])
check("truss: 12 floors, every modulus +-0.5 %: a bound on the top corner EARNED in ONE piece (the rescaled system; "
      "unscaled the kernel's beta was 1.2 and the search split 256 pieces)",
      _r12["verdict"] == "EARNED" and "(1 pieces" in json.dumps(_r12.get("how")), json.dumps(_r12)[:300])
_lw = ["2*x + y == 3", "x - y == 0"]
_sc = {"v": {"x": F(1, 4), "y": F(2)}, "w": [F(8), F(1, 2)]}
_rl = K._rescale(_lw, _sc)
_sol = C.solve_at(_rl, {}, ["x", "y"])
check("rescaling is an exact change of variables: x = v_x x', every law times w_i — the rescaled system's solution "
      "is the original's divided by v (x = y = 1 -> 4, 1/2)", _sol == {"x": F(4), "y": F(1, 2)}, (_rl, _sol))
_trbad = []
for _txt in ("N, 1, 0, 0\nN, 2, 1, 1\nE, 1, 2\nMP, EX, 1, 1\nR, 1, 1\nD, 1, UX, 0\n",       # length sqrt 2
             "N, 1, 0, 0\nN, 2, 1, 0\nE, 1, 2\nMP, EX, 1, 1\nR, 1, 1\nSFE, 1, 1\n",      # a command not read
             "N, 1, 0, 0\nN, 2, 1, 0\nE, 1, 3\nMP, EX, 1, 1\nR, 1, 1\n"):                  # a bar to no node
    try:
        TR.to_brick(_txt, "1%")
        _trbad.append(None)
    except B.BrickError as _e:
        _trbad.append(str(_e)[:50])
check("truss: refused aloud — an irrational bar length (not exact), a command it does not read, a bar to a node "
      "that does not exist", all(_trbad), _trbad)
_refused = []
for _txt, _bom, _rq in (("V1 a 0 5\nD1 a b dmod\nR1 b 0 1k\n", None, ["V(b) <= 5"]),
                        ("V1 in 0 5\nR1 in out 10k\nR2 out 0 10k\n", {"R1": ("12k", None)}, ["V(out) <= 3"]),
                        ("V1 in 0 5\nR1 in out 10k\nR2 out 0 10k\n", None, ["V(nowhere) <= 3"]),
                        ("V1 in 0 5\nR1 in out 10k\nC1 out 0 1u\nR2 x 0 1k\nC2 x out 1n\n", None, ["V(out) <= 3"])):
    try:
        SP.to_brick("* t\n" + _txt, _bom, _rq)
        _refused.append(None)
    except B.BrickError as _e:
        _refused.append(str(_e)[:40])
check("spice: refused aloud — a diode with no .model, a BOM value against the netlist, a node that does not exist; a "
      "tolerance with no unit (0.5: 0.5 % or 50 %?)", all(_refused[:3]) and
      _raises(lambda: SP.tolerance("0.5"), SP.SpiceError), _refused)

# DEVICES BY OPERATING REGION (2026-10-15, the curator's "да"): D and Q as piecewise-linear models; the regions chosen
# at the nominal point, their conditions PROVED over the whole box first, then the requirements


def _spj(cir, reqs, bom=None, regions=None):
    return SP.judge((_SPD / cir).read_text(), SP.read_bom(str(_SPD / bom)) if bom else None, reqs, regions)


_j = {"d": _spj("diode.cir", ["V(b) within 0.6 0.9", "I(R1) within 4m 4.5m"], "diode-bom.csv"),
      "dr": _spj("diode-reversed.cir", ["V(b) within 4.9 5.1"]),
      "ce": _spj("ce-amp.cir", ["V(c) within 7 11.5"], "ce-amp-bom.csv"),
      "pnp": _spj("pnp-stage.cir", ["V(c) within 2.3 2.4"]),
      "sat": _spj("ce-amp-saturating.cir", ["V(c) within 0 12"], "ce-amp-saturating-bom.csv")}
check("regions: a forward diode (Vfwd 0.7 +-10 %, Ron 10) — on, proved over the box; V(b) and I(R1) EARNED; reversed — "
      "off, V(b) = 5 exactly", (_j["d"]["verdict"], _j["d"]["operating_points"][0]["regions"], _j["dr"]["verdict"],
                                _j["dr"]["operating_points"][0]["regions"]) == ("EARNED", {"D1": "on"}, "EARNED", {"D1": "off"}))
check("regions: a common-emitter stage, BF 100 +-50 %: active over the whole box (proved), V(c) in [7, 11.5] EARNED; a "
      "PNP stage (by hand V(c) = 2.364): active, V(c) in [2.3, 2.4] EARNED",
      (_j["ce"]["verdict"], _j["ce"]["operating_points"][0]["regions"], _j["pnp"]["verdict"]) ==
      ("EARNED", {"Q1": "active"}, "EARNED"))
_sp0 = _j["sat"]["operating_points"][0]
check("regions: the same stage with a too-small Rb SATURATES at high BF — said: Q1 leaves its active region at a point "
      "(OPEN, never a false verdict of the requirement)", _j["sat"]["verdict"] == "OPEN" and _sp0["regions_hold"] ==
      "REFUTED" and "Vce" in str(_sp0.get("which")) and _sp0.get("leaves_its_region_at", {}).get("Q1_bf") == "150", _j["sat"])
check("regions: a model without the parameters the region model needs — refused aloud (nothing assumed)",
      _raises(lambda: SP.to_brick("* t\nV1 a 0 5\nR1 a b 1k\nD1 b 0 dm\n.model dm D(IS=1e-14)\n", None, [],
                                  {"D1": "on"}), SP.SpiceError))

# THE DUEL'S WEAKNESSES (2026-10-18, the curator's "Да, делай. Оптимизируй."; bench/competitors/RESULTS.md)
from ustand import components as _CMW          # noqa: E402


def _wchain(n, bound):
    """bench/scale.py's chain: n components out = g*in + off (g 1.01 +-1 %, off +-1 mV), arriving bands."""
    g = lambda v, tol=None, unit="", rng=None: dict({"role": "given", "unit": unit}, **(
        {"range": list(rng)} if rng else dict({"value": v}, **({"tolerance": tol} if tol else {}))))
    comps = {f"C{i}": {"brick": {
        "stand": "ztl-stand/1",
        "interface": {"inputs": {"vin": {"assume": ["0", "100"], "bands": "arriving"}}, "outputs": ["vout"]},
        "quantities": {"vin": g("1", unit="V"), "g": g("1.01", "0.01"), "off": g(None, unit="V", rng=("-0.001", "0.001")),
                       "vout": {"role": "derived", "unit": "V"}},
        "laws": [{"zfl": "vout == g*vin + off"}], "requirements": []}} for i in range(n)}
    return {"stand": "ztl-stand/1", "components": comps,
            "connect": {f"C{i}.vin": ("Vs" if i == 0 else f"C{i - 1}.vout") for i in range(n)},
            "quantities": {"Vs": g("5", "0.01", "V"), "Vend": {"role": "derived", "unit": "V"}},
            "laws": [{"zfl": f"Vend == C{n - 1}.vout"}],
            "requirements": [{"quantity": "Vend", "op": "<=", "value": bound}]}


_wl = _CMW.run_system(_wchain(3, "5.15"), ".")          # nominal 5*1.01^3 = 5.151505 > 5.15
_wp = _CMW.run_system(_wchain(3, "5.6"), ".")
check("W1: WITNESS LIFTING — a chain failing inside its components' ranges was OPEN (the point might be no component's);"
      " lifted (each component at its real input, its own point, outputs exact) it is REFUTED at 5.151505 V; a bound it "
      "meets stays EARNED", _wl["verdict"] == "REFUTED" and "LIFTED" in _wl["why"] and "1030301/200000" in str(
          _wl.get("value_there")) and len(_wl.get("lifted_states", {})) == 3 and _wp["verdict"] == "EARNED",
      (_wl.get("verdict"), str(_wl.get("why"))[:200], _wl.get("value_there"), _wp.get("verdict")))
_wm = {"stand": "universal-stand/1",
       "quantities": {"x": {"role": "given", "range": ["2", "14"], "unit": ""}, "y": {"role": "derived", "unit": ""}},
       "slots": {}, "catalog": {}, "laws": [{"zfl": "y == x*x"}],
       "requirements": [{"quantity": "y", "op": "<=", "value": "100"}, {"quantity": "y", "op": ">=", "value": "1"},
                        {"quantity": "x", "op": ">=", "value": "1"}, {"quantity": "x", "op": "<=", "value": "20"}]}
_rm = S.run(_wm)
_mcw = _rm.get("minimal_conflicts", {})
check("W2: MONOTONE conflicts + the CORE — y = x^2 over [2, 14]: only y <= 100 fails; the proof's core is that "
      "requirement, so every drop of another is decided without a run; the list is complete",
      _rm["verdict"] == "REFUTED" and _rm.get("_core") == [0] and _mcw.get("sets") == [["y <= 100"]]
      and _mcw.get("complete") is True and _mcw.get("subsets_inferred", 0) > 0, (_rm.get("_core"), _mcw))
_wc = dict(_wm, requirements=[_wm["requirements"][i] for i in _rm.get("_core") or []])
check("W3: the core is a refutation on its own (any set holding it is refuted by the same proof)",
      S.run(_wc, conflicts=False)["verdict"] == "REFUTED")

print(f"ztl-stand: {ok} ok, {fail} failed")
print("USTAND GREEN" if fail == 0 else "USTAND RED")
