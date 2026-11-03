"""Round 2: elastic3d.judge's verdicts at the boundary on samples whose E_app is EXACT over the whole box:
homogeneous (E_app = E), Voigt (layers along x, equal nu: the mean E), Reuss (layers across x, nu = 0: the harmonic
mean). For each, need_max / need_min at the true extremes x (1 -+ 1e-9, 1e-6, 1e-3): EARNED must hold at EVERY box
point, REFUTED must fail at EVERY box point. --mutant: the stand's bracket reported widened inward by 1e-5 (a false
bracket) — the check must see it.
    PYTHONPATH=. python3 redteam/round2/check_judge.py [--mutant]"""
import json, sys
from fractions import Fraction as F
import numpy as np
from ustand import elastic3d as E3

MUT = "--mutant" in sys.argv
if MUT:
    _u, _l = E3.upper, E3.lower
    E3.upper = lambda V, p, r=1: (lambda o: (o[0] * (1 - F(1, 10 ** 5)),) + o[1:])(_u(V, p, r))
    E3.lower = lambda V, p, r=1: (lambda o: (o[0] * (1 + F(1, 10 ** 5)), o[1]))(_l(V, p, r))


def ph(E, nu):
    return {"E": [F(E[0]), F(E[1])], "nu": [F(nu[0]), F(nu[1])], "earned": True}


cases = []
cases.append(("homog", np.ones((3, 2, 2), int), {1: ph((100, 200), ("0.1", "0.4"))}, (100.0, 200.0)))
V = np.ones((3, 2, 2), int); V[:, 1, :] = 2
cases.append(("voigt", V, {1: ph((100, 150), ("0.25", "0.25")), 2: ph((300, 400), ("0.25", "0.25"))},
              ((100 + 300) / 2, (150 + 400) / 2)))
V = np.ones((4, 2, 2), int); V[2:, :, :] = 2
hm = lambda a, b: 2 / (1 / a + 1 / b)
cases.append(("reuss", V, {1: ph((100, 120), (0, 0)), 2: ph((300, 330), (0, 0))}, (hm(100, 300), hm(120, 330))))
out, bad, n = [], [], 0
for name, V, phases, (tmin, tmax) in cases:
    for rel in (1e-9, 1e-6, 1e-3):
        for need, kind in ((tmax * (1 + rel), "max"), (tmax * (1 - rel), "max"), (tmin * (1 - rel), "min"),
                           (tmin * (1 + rel), "min"), (tmin * (1 - rel), "max"), (tmax * (1 + rel), "min")):
            r = E3.judge(V, phases, need_max=need if kind == "max" else None, need_min=need if kind == "min" else None)
            v = r[f"verdict_{kind}"]
            n += 1
            holds_all = (tmax <= need) if kind == "max" else (tmin >= need)
            fails_all = (tmin > need) if kind == "max" else (tmax < need)
            wrong = (v.startswith("EARNED") and not holds_all) or (v.startswith("REFUTED") and not fails_all)
            out.append({"case": name, "kind": kind, "need": need, "verdict": v})
            if wrong:
                bad.append(out[-1])
print(json.dumps({"mutant": MUT, "judged": n, "wrong": len(bad), "first": bad[:3],
                  "verdicts": sorted({o["verdict"] for o in out})}))
