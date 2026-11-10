# -*- coding: utf-8 -*-
"""
The SEALED grader for round 3 of the zpy AI experiment (2026-11-10): MODIFYING working code (CHANGES3.md applied to a
round-2 solution). Committed BEFORE any model ran. The machinery is grade2.py's (imported); the rules are the CHANGED
ones below. Two truths as in round 2: classical (completions) and ZTL (the judge on one formula per rule).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grade2 as G                     # noqa: E402

B = G.B
G.RULES = {
    "approve_purchase": dict(out=("approve", "reject"),
        inputs={"premium": B, "gold": B, "fraud_flag": B, "amount": (1000, 5000, 20000)},
        rule=lambda v: (not v["fraud_flag"]) and v["amount"] <= (20000 if v["gold"] else 5000 if v["premium"]
                                                                  else 1000)),
    "route_order": dict(out=("approve", "hold"),
        inputs={"amount": (100, 10000), "manager_ok": B, "clerk_ok": B, "director_ok": B},
        rule=lambda v: (v["manager_ok"] and v["director_ok"]) if v["amount"] > 10000 else
        v["manager_ok"] if v["amount"] > 100 else v["clerk_ok"]),
    "open_gate": dict(out=("open", "keep_closed"),
        inputs={"badge_valid": B, "revoked": B, "emergency": B, "guard_present": B, "lockdown": B},
        rule=lambda v: (v["emergency"] and v["guard_present"]) or ((not v["lockdown"]) and (
            (v["badge_valid"] and not v["revoked"]) or (v["badge_valid"] and v["guard_present"])))),
    "deploy": dict(out=("deploy", "block"),
        inputs={"tests_pass": B, "freeze": B, "hotfix": B, "security_review": B, "ci_green": B},
        rule=lambda v: v["tests_pass"] and v["ci_green"] and ((not v["freeze"]) or v["hotfix"])
        and ((not v["hotfix"]) or v["security_review"])),
    "fire_alarm": dict(out=("alarm", "quiet"),
        inputs={"test_mode": B, "smoke": B, "heat": B, "manual_pull": B},
        rule=lambda v: v["manual_pull"] or (v["heat"] if v["test_mode"] else v["smoke"])),
    "dispense": dict(out=("give", "withhold"),
        inputs={"allergy": B, "prescription": B, "doctor_override": B, "weight_kg": (40,), "dose_mg": (250, 500, 750)},
        rule=lambda v: (not v["allergy"]) and v["prescription"] and v["dose_mg"] <= (
            750 if v["doctor_override"] else 500 if v["weight_kg"] >= 40 else 250)),
}
G.ZTL_RULES = {
    "approve_purchase": ("(~fraud_flag & (((gold & a20) | ((~gold & premium) & a5)) | ((~gold & ~premium) & a1)))",
                         {"a20": ("amount", lambda x: x <= 20000), "a5": ("amount", lambda x: x <= 5000),
                          "a1": ("amount", lambda x: x <= 1000)}),
    "route_order": ("(((huge & (manager_ok & director_ok)) | ((~huge & big) & manager_ok)) | (~big & clerk_ok))",
                    {"huge": ("amount", lambda x: x > 10000), "big": ("amount", lambda x: x > 100)}),
    "open_gate": ("((emergency & guard_present) | (~lockdown & ((badge_valid & ~revoked) | (badge_valid & guard_present))))",
                  {}),
    "deploy": ("(((tests_pass & ci_green) & (~freeze | hotfix)) & (hotfix -> security_review))", {}),
    "fire_alarm": ("(manual_pull | ((test_mode & heat) | (~test_mode & smoke)))", {}),
    "dispense": ("((~allergy & prescription) & ((doctor_override & d7) | (~doctor_override & ((heavy & d5) | (~heavy & d2)))))",
                 {"heavy": ("weight_kg", lambda x: x >= 40), "d7": ("dose_mg", lambda x: x <= 750),
                  "d5": ("dose_mg", lambda x: x <= 500), "d2": ("dose_mg", lambda x: x <= 250)}),
}

if __name__ == "__main__":
    for pth in sys.argv[1:]:
        g = G.grade(pth)
        print(os.path.basename(os.path.dirname(os.path.abspath(pth))), json.dumps(
            g if "error" in g else {**g["total"], "lint": g["lint"], "uses_zpy": g["uses_zpy"],
                                    "per_task_errors": {t: r["cases"] - r["correct"] for t, r in g["per_task"].items()},
                                    "per_task_SILENT": {t: r["SILENT"] for t, r in g["per_task"].items()}}))
