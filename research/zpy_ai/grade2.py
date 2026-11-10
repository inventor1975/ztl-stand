# -*- coding: utf-8 -*-
"""
The SEALED grader for round 2 of the zpy AI experiment (2026-11-10). Written and committed BEFORE any model ran.

Round 2's tasks (TASKS2.md) state the rules in prose, and inputs REPEAT inside a rule (premium in both tiers; amount in
two complementary comparisons; badge_valid twice; hotfix twice; test_mode as a selector; weight in two complementary
comparisons and dose against two limits). Where an input repeats, a hand-written three-valued (Kleene) evaluation is
NOT exact: `(t & s) | (~t & h)` with t unknown and s, h true is decided (alarm) but Kleene says unknown.

GROUND TRUTH: classical, by completions. Every unverified boolean is completed True/False; every unverified number
ranges over representative points of every region its thresholds cut the line into (each threshold, and points
between and beyond) — exact for rules whose numbers are compared with constants only, as here. All completions give
the positive outcome -> positive; all negative -> negative; else needs_check. The rule texts are encoded once below;
`RULES` is the reading of TASKS2.md the grader holds, sealed with it.

Measures: correct / SILENT (definite where the truth is needs_check) / WRONG (the opposite definite answer) /
CAUTIOUS (needs_check where the truth is definite — the round-2 trap for hand-written Kleene) / BAD.
And against the ZTL TRUTH (the judge's disposition, IF STABLE not upgraded — the curator's word): ztl_correct,
ztl_SILENT. Two truths, both reported: the classical one is what the task text asks; the ZTL one is what the
layer is.
"""
import itertools
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ZTL = os.path.abspath(os.path.join(HERE, "..", "..", "..", "ZTL"))
B = "bool"

RULES = {
    "approve_purchase": dict(out=("approve", "reject"),
        inputs={"premium": B, "fraud_flag": B, "amount": (1000, 5000)},
        rule=lambda v: (not v["fraud_flag"]) and (v["amount"] <= (5000 if v["premium"] else 1000))),
    "route_order": dict(out=("approve", "hold"),
        inputs={"amount": (100,), "manager_ok": B, "clerk_ok": B},
        rule=lambda v: v["manager_ok"] if v["amount"] > 100 else v["clerk_ok"]),
    "open_gate": dict(out=("open", "keep_closed"),
        inputs={"badge_valid": B, "revoked": B, "emergency": B, "guard_present": B},
        rule=lambda v: (v["badge_valid"] and not v["revoked"]) or (v["emergency"] and v["guard_present"])
        or (v["badge_valid"] and v["guard_present"])),
    "deploy": dict(out=("deploy", "block"),
        inputs={"tests_pass": B, "freeze": B, "hotfix": B, "security_review": B},
        rule=lambda v: v["tests_pass"] and ((not v["freeze"]) or v["hotfix"])
        and ((not v["hotfix"]) or v["security_review"])),
    "fire_alarm": dict(out=("alarm", "quiet"),
        inputs={"test_mode": B, "smoke": B, "heat": B},
        rule=lambda v: v["heat"] if v["test_mode"] else v["smoke"]),
    "dispense": dict(out=("give", "withhold"),
        inputs={"allergy": B, "prescription": B, "weight_kg": (40,), "dose_mg": (250, 500)},
        rule=lambda v: (not v["allergy"]) and v["prescription"]
        and v["dose_mg"] <= (500 if v["weight_kg"] >= 40 else 250)),
}


# THE ZTL TRUTH (2026-11-10, the curator: «В этом весь ЗТЛ» — EARNED IF STABLE is not EARNED). Each rule as ONE ZTL
# formula over atoms; a comparison is an atom, a complementary comparison is that atom negated (`amount <= 100` is
# ~big); the judge's disposition decides: EARNED -> positive, REFUTED -> negative, anything else -> needs_check.
ZTL_RULES = {
    "approve_purchase": ("(~fraud_flag & ((premium & a5) | (~premium & a1)))",
                         {"a5": ("amount", lambda x: x <= 5000), "a1": ("amount", lambda x: x <= 1000)}),
    "route_order": ("((big & manager_ok) | (~big & clerk_ok))", {"big": ("amount", lambda x: x > 100)}),
    "open_gate": ("(((badge_valid & ~revoked) | (emergency & guard_present)) | (badge_valid & guard_present))", {}),
    "deploy": ("((tests_pass & (~freeze | hotfix)) & (hotfix -> security_review))", {}),
    "fire_alarm": ("((test_mode & heat) | (~test_mode & smoke))", {}),
    "dispense": ("((~allergy & prescription) & ((heavy & d5) | (~heavy & d2)))",
                 {"heavy": ("weight_kg", lambda x: x >= 40), "d5": ("dose_mg", lambda x: x <= 500),
                  "d2": ("dose_mg", lambda x: x <= 250)}),
}


def truth_ztl(task, inp):
    sys.path.insert(0, ZTL)
    import ztljudge
    text, comps = ZTL_RULES[task]
    m = {}
    for n, x in inp.items():
        if RULES[task]["inputs"][n] == B:
            m[n] = ("T" if x["value"] else "F") if x["status"] == "verified" else "Z"
    for a, (n, f) in comps.items():
        x = inp[n]
        m[a] = ("T" if f(x["value"]) else "F") if x["status"] == "verified" else "Z"
    d = ztljudge.judge(text, m)["disposition"]
    pos, neg = RULES[task]["out"]
    return pos if d == "EARNED" else neg if d == "REFUTED" else "needs_check"


def points(th):
    """Representative values of every region the thresholds cut the line into (and the thresholds themselves)."""
    th = sorted(th)
    pts = [th[0] - 1] + [t for t in th] + [(a + b) / 2 for a, b in zip(th, th[1:])] + [th[-1] + 1]
    return sorted(set(pts))


def options(kind):
    if kind == B:
        return [{"value": True, "status": "verified"}, {"value": False, "status": "verified"},
                {"value": True, "status": "claimed"}, {"value": False, "status": "claimed"},
                {"value": None, "status": "unknown"}]
    pts = points(kind)
    return ([{"value": x, "status": "verified"} for x in pts]
            + [{"value": pts[len(pts) // 2], "status": "claimed"}, {"value": None, "status": "unknown"}])


def truth(task, inp):
    t = RULES[task]
    fixed = {n: x["value"] for n, x in inp.items() if x["status"] == "verified"}
    free = [n for n in t["inputs"] if n not in fixed]
    doms = [(True, False) if t["inputs"][n] == B else points(t["inputs"][n]) for n in free]
    seen = set()
    for combo in itertools.product(*doms):
        seen.add(bool(t["rule"](dict(fixed, **dict(zip(free, combo))))))
        if len(seen) == 2:
            return "needs_check"
    pos, neg = t["out"]
    return pos if seen == {True} else neg


def cases(task):
    names = list(RULES[task]["inputs"])
    for combo in itertools.product(*(options(RULES[task]["inputs"][n]) for n in names)):
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
    path = os.path.abspath(path)
    allc = {t: list(cases(t)) for t in RULES}
    work = os.path.dirname(path)
    cpath, rpath, opath = (os.path.join(work, f) for f in ("_cases.json", "_runner.py", "_out.json"))
    json.dump(allc, open(cpath, "w"))
    open(rpath, "w").write(RUNNER)
    p = subprocess.run([sys.executable, rpath, path, cpath, opath], capture_output=True, text=True, timeout=1800,
                       env=dict(os.environ, PYTHONPATH=ZTL), cwd=work)
    for f in (cpath, rpath):
        os.remove(f)
    if p.returncode != 0:
        return {"error": p.stderr[-2000:]}
    got = json.load(open(opath))
    os.remove(opath)
    rep = {}
    for t, cs in allc.items():
        pos, neg = RULES[t]["out"]
        r = dict(cases=len(cs), correct=0, SILENT=0, WRONG=0, CAUTIOUS=0, BAD=0, ztl_correct=0, ztl_SILENT=0)
        for inp, ans in zip(cs, got[t]):
            tz = truth_ztl(t, inp)
            r["ztl_correct"] += ans == tz
            r["ztl_SILENT"] += (tz == "needs_check" and ans in (pos, neg))
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
    tot = {k: sum(r[k] for r in rep.values()) for k in ("cases", "correct", "SILENT", "WRONG", "CAUTIOUS", "BAD",
                                                         "ztl_correct", "ztl_SILENT")}
    sys.path.insert(0, ZTL)
    import zpy_lint
    src = open(path).read()
    lint = [f"{ln}:{k}:{w}" for _, ln, k, w in zpy_lint.lint_source(src, path)]
    return {"per_task": rep, "total": tot, "lint": lint, "uses_zpy": "import zpy" in src or "from zpy" in src}


if __name__ == "__main__":
    for pth in sys.argv[1:]:
        g = grade(pth)
        print(os.path.basename(os.path.dirname(os.path.abspath(pth))), json.dumps(
            g if "error" in g else {**g["total"], "lint": len(g["lint"]), "uses_zpy": g["uses_zpy"],
                                    "per_task_errors": {t: r["cases"] - r["correct"] for t, r in g["per_task"].items()}}))
