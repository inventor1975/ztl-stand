"""Round 2: hand-built adversarial voxel maps for elastic3d's exact phase — an island without a grip, a stub on one
grip, two spanning components, edge-only contacts (a staircase), a 3D checkerboard, a one-voxel channel, a
stiff/soft contrast of 1e6 and SI-scale moduli (2e11 / 1e5 Pa) — each: lower <= Q1(r) for r = 1, 2, 4 (Q1 >= the
truth) and upper >= the r = 4 Aitken estimate. --mutant: lower x 1.5 (must be seen).
    PYTHONPATH=. python3 redteam/round2/check_elastic_special.py [--mutant]"""
import json, os, sys
from fractions import Fraction as F
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref_elastic as RE  # noqa: E402
from hunt_elastic import aitken  # noqa: E402
from ustand import elastic3d as E3  # noqa: E402

MUT = "--mutant" in sys.argv


def ph(**kw):
    d = {0: {"E": [F(0), F(0)], "nu": [F(0), F(0)]}}
    d.update(kw)
    return d


S = {"E": [F(200), F(200)], "nu": [F(3, 10), F(3, 10)]}
cases = {}
V = np.ones((4, 3, 3), int); V[:, :, :] = 0; V[:, 1, 1] = 1; V[1:3, 0, 0] = 1           # bar + island not touching
V[1:3, 0, 0] = 1; V[0, 0, 0] = 0; V[3, 0, 0] = 0
cases["island"] = (V.copy(), ph(**{"1": S}))
V = np.zeros((4, 3, 3), int); V[:, 1, 1] = 1; V[0:2, 0, 0] = 1                           # bar + a stub on x = 0
cases["stub_one_grip"] = (V.copy(), ph(**{"1": S}))
V = np.zeros((4, 3, 3), int); V[:, 0, 0] = 1; V[:, 2, 2] = 1                             # two spanning bars
cases["two_components"] = (V.copy(), ph(**{"1": S}))
V = np.zeros((4, 4, 4), int)
for i in range(4):
    V[i, i, i] = 1                                                                         # corner-only staircase
V[:, 3, 0] = 1                                                                             # plus one real bar
cases["corner_staircase"] = (V.copy(), ph(**{"1": S}))
V = np.zeros((4, 3, 2), int)
for i in range(4):
    V[i, i % 2, :] = 1                                                                     # edge-contact zigzag
cases["edge_zigzag"] = (V.copy(), ph(**{"1": S}))
V = (np.indices((4, 4, 4)).sum(0) % 2).astype(int) + 1                                     # 3D checkerboard
cases["checkerboard_1e6"] = (V.copy(), ph(**{"1": {"E": [F(1), F(1)], "nu": [F(3, 10), F(3, 10)]},
                                         "2": {"E": [F(10 ** 6), F(10 ** 6)], "nu": [F(-1, 2), F(49, 100)]}}))
V = np.zeros((5, 3, 3), int); V[:, 1, 1] = 2; V[:, 0, :] = 1                               # stiff channel in soft
cases["channel_SI"] = (V.copy(), ph(**{"1": {"E": [F(10 ** 5), F(2 * 10 ** 5)], "nu": [F(0), F(45, 100)]},
                                   "2": {"E": [F(2 * 10 ** 11), F(21 * 10 ** 10)], "nu": [F(29, 100), F(3, 10)]}}))
out = {}
for name, (V, phs) in cases.items():
    phs = {int(k): v for k, v in phs.items()}
    used = [int(x) for x in np.unique(V) if x != 0]
    lo = float(E3.lower(V, phs)[0]) * (1.5 if MUT else 1)
    up = float(E3.upper(V, phs)[0])
    soft = {0: (0.0, 0.0)}; stiff = {0: (0.0, 0.0)}
    for p in used:
        soft[p] = (float(phs[p]["E"][0]), float(phs[p]["nu"][0]))
        stiff[p] = (float(phs[p]["E"][-1]), float(phs[p]["nu"][-1]))
    qs = [RE.solve(V, soft, r=r) for r in (1, 2, 4)]
    qh = [RE.solve(V, stiff, r=r) for r in (1, 2, 4)]
    est = aitken(*qh)
    out[name] = {"lower": lo, "upper": up, "q1_soft": qs, "q1_stiff": qh, "truth_est_stiff": est,
                 "lower_ok": lo <= min(qs) * (1 + 1e-9) + 1e-300, "upper_ok": up >= est * (1 - 1e-6) or up >= qh[-1]}
print(json.dumps({"mutant": MUT, "all_ok": all(v["lower_ok"] and v["upper_ok"] for v in out.values()), "cases": out}))
