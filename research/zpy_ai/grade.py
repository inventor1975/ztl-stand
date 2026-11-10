# -*- coding: utf-8 -*-
"""
The SEALED grader for the zpy AI experiment (2026-11-09). Written and committed BEFORE any model wrote a line.

Ground truth is CLASSICAL and independent of ZTL: for each case, every unverified input (claimed or unknown) is
completed both ways — a boolean True/False, a comparison over an unverified number True/False (any number possible;
each number occurs in one comparison only, so the comparisons are independent) — and the condition is evaluated in
every completion. All true -> positive; all false -> negative; else needs_check.

Every case is enumerated: per boolean input {verified T, verified F, claimed T, claimed F, unknown}; per number
{verified at three values around its threshold, claimed, unknown}. 625-3125 cases per task, 6250 in all (MEASURED).

Per function: correct / SILENT (a definite answer where the truth is needs_check — an unverified input decided
silently) / WRONG (the opposite definite answer) / CAUTIOUS (needs_check where the truth is definite) / BAD (an
exception or an answer outside the three). Usage: python3 grade.py runs/A1/solutions.py ...
"""
import itertools
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ZTL = os.path.abspath(os.path.join(HERE, "..", "..", "..", "ZTL"))

B = "bool"
TASKS = {
    "approve_payment": dict(out=("approve", "reject"), inputs={
        "amount": [500, 1000, 1500], "account_verified": B, "manager_ok": B, "fraud_flag": B},
        cond=lambda c, b: c["amount<=1000"] and (b["account_verified"] or b["manager_ok"]) and not b["fraud_flag"],
        comps={"amount<=1000": (("amount",), lambda v: v["amount"] <= 1000)}),
    "open_door": dict(out=("open", "keep_closed"), inputs={
        "badge_valid": B, "in_schedule": B, "escort_present": B, "revoked": B},
        cond=lambda c, b: b["badge_valid"] and (b["in_schedule"] or b["escort_present"]) and not b["revoked"],
        comps={}),
    "allow_deploy": dict(out=("deploy", "block"), inputs={
        "tests_pass": B, "review_approved": B, "freeze_active": B, "hotfix": B},
        cond=lambda c, b: b["tests_pass"] and b["review_approved"] and ((not b["freeze_active"]) or b["hotfix"]),
        comps={}),
    "machine_action": dict(out=("shutdown", "run"), inputs={
        "temp": [80, 90, 95], "pressure": [4, 5, 6], "vibration_alarm": B, "maintenance_mode": B},
        cond=lambda c, b: c["temp>90"] or c["pressure>5"] or (b["vibration_alarm"] and not b["maintenance_mode"]),
        comps={"temp>90": (("temp",), lambda v: v["temp"] > 90),
               "pressure>5": (("pressure",), lambda v: v["pressure"] > 5)}),
    "approve_loan": dict(out=("approve", "decline"), inputs={
        "income": [2900, 3000, 3100], "payment": [1000], "default_history": B, "collateral": B, "guarantor": B},
        cond=lambda c, b: c["income>=3p"] and not b["default_history"] and (b["collateral"] or b["guarantor"]),
        comps={"income>=3p": (("income", "payment"), lambda v: v["income"] >= 3 * v["payment"])}),
    "give_medication": dict(out=("give", "withhold"), inputs={
        "dose": [5, 10, 15], "max_dose": [10], "allergy": B, "prescription": B, "emergency": B},
        cond=lambda c, b: (not b["allergy"]) and c["dose<=max"] and (b["prescription"] or b["emergency"]),
        comps={"dose<=max": (("dose", "max_dose"), lambda v: v["dose"] <= v["max_dose"])}),
}


def options(kind):
    if kind == B:
        return [{"value": True, "status": "verified"}, {"value": False, "status": "verified"},
                {"value": True, "status": "claimed"}, {"value": False, "status": "claimed"},
                {"value": None, "status": "unknown"}]
    return ([{"value": x, "status": "verified"} for x in kind]
            + [{"value": kind[len(kind) // 2], "status": "claimed"}, {"value": None, "status": "unknown"}])


def truth(task, inp):
    t = TASKS[task]
    known_b = {n: x["value"] for n, x in inp.items() if t["inputs"][n] == B and x["status"] == "verified"}
    free_b = [n for n, k in t["inputs"].items() if k == B and n not in known_b]
    known_c, free_c = {}, []
    for cn, (nums, f) in t["comps"].items():
        if all(inp[n]["status"] == "verified" for n in nums):
            known_c[cn] = f({n: inp[n]["value"] for n in nums})
        else:
            free_c.append(cn)
    seen = set()
    for bits in itertools.product((True, False), repeat=len(free_b) + len(free_c)):
        b = dict(known_b, **dict(zip(free_b, bits[:len(free_b)])))
        c = dict(known_c, **dict(zip(free_c, bits[len(free_b):])))
        seen.add(bool(t["cond"](c, b)))
        if len(seen) == 2:
            return "needs_check"
    pos, neg = t["out"]
    return pos if seen == {True} else neg


def cases(task):
    names = list(TASKS[task]["inputs"])
    for combo in itertools.product(*(options(TASKS[task]["inputs"][n]) for n in names)):
        yield dict(zip(names, combo))


RUNNER = r'''
import json, sys, importlib.util
spec = importlib.util.spec_from_file_location("sol", sys.argv[1]); sol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sol)
out = {}
for task, cs in json.load(open(sys.argv[2])).items():
    f = getattr(sol, task, None); res = []
    for inp in cs:
        try:
            res.append(f(inp) if f else "MISSING")
        except Exception as e:
            res.append("EXC:" + type(e).__name__)
    out[task] = res
json.dump(out, open(sys.argv[3], "w"))
'''


def grade(path):
    allc = {t: list(cases(t)) for t in TASKS}
    work = os.path.dirname(os.path.abspath(path))
    cpath, rpath, opath = (os.path.join(work, f) for f in ("_cases.json", "_runner.py", "_out.json"))
    json.dump(allc, open(cpath, "w"))
    open(rpath, "w").write(RUNNER)
    env = dict(os.environ, PYTHONPATH=ZTL)
    p = subprocess.run([sys.executable, rpath, path, cpath, opath], capture_output=True, text=True, timeout=600,
                       env=env, cwd=work)
    if p.returncode != 0:
        return {"error": p.stderr[-2000:]}
    got = json.load(open(opath))
    rep = {}
    for t, cs in allc.items():
        pos, neg = TASKS[t]["out"]
        r = dict(cases=len(cs), correct=0, SILENT=0, WRONG=0, CAUTIOUS=0, BAD=0)
        for inp, ans in zip(cs, got[t]):
            tr = truth(t, inp)
            if ans == tr:
                r["correct"] += 1
            elif ans not in (pos, neg, "needs_check"):
                r["BAD"] += 1
            elif tr == "needs_check":
                r["SILENT"] += 1
            elif ans == "needs_check":
                r["CAUTIOUS"] += 1
            else:
                r["WRONG"] += 1
        rep[t] = r
    tot = {k: sum(r[k] for r in rep.values()) for k in ("cases", "correct", "SILENT", "WRONG", "CAUTIOUS", "BAD")}
    sys.path.insert(0, ZTL)
    import zpy_lint
    lint = [f"{ln}:{k}:{w}" for _, ln, k, w in zpy_lint.lint_source(open(path).read(), path)]
    return {"per_task": rep, "total": tot, "lint": lint, "uses_zpy": "import zpy" in open(path).read()
            or "from zpy" in open(path).read()}


if __name__ == "__main__":
    for pth in sys.argv[1:]:
        g = grade(pth)
        print(pth, json.dumps(g if "error" in g else {**g["total"], "lint": len(g["lint"]), "uses_zpy": g["uses_zpy"]}))
