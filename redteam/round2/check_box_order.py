"""Round 2, FINDING 1 (low severity, input validation): elastic3d accepts an E box written high-to-low and returns
FALSE proved bounds. The box is read as E[0] .. E[-1] without ordering (`_lame_hi` takes E_hi = E[-1], `_phase_soft`
E_lo = E[0]); nu is checked (a reversed nu box is refused), E is not. On a homogeneous sample E_app = E exactly, so
the truth over the box {E in [100, 200]} is the whole interval [100, 200]:
  phases E = [100, 200]: upper 200, lower 100 (right);  E = [200, 100] (the same box): upper 100, lower 200 — both
  FALSE for part of the box. The ZTL verdict on the inverted bracket is 'E' (no subject), not EARNED/REFUTED; the API
  functions upper() and lower() return the false values as proved bounds. conduction3d's judge reads its phase box
  the same way (s[0], s[-1]).
    PYTHONPATH=. python3 redteam/round2/check_box_order.py"""
import json
import os
import subprocess
import sys
from fractions import Fraction as F

import numpy as np
from ustand import elastic3d as E3

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = np.ones((3, 2, 2), dtype=np.int64)
npy = os.path.join(ROOT, "redteam", "round2", "samples", "homog-3x2x2.npy")
np.save(npy, V)
out = {}
for name, E in (("ascending", [F(100), F(200)]), ("descending", [F(200), F(100)])):
    ph = {1: {"E": E, "nu": [F(3, 10), F(3, 10)], "earned": True}}
    up = float(E3.upper(V, ph)[0]); lo = float(E3.lower(V, ph)[0])
    j = E3.judge(V, ph, need_max=150, need_min=150)
    out[name] = {"E_box_as_written": [str(x) for x in E], "api_upper": up, "api_lower": lo,
                 "truth_over_the_box": [100.0, 200.0], "upper_false": up < 200 - 1e-6, "lower_false": lo > 100 + 1e-6,
                 "judge_verdicts": [j["verdict_max"], j["verdict_min"]]}
cli = subprocess.run([sys.executable, "-m", "ustand.elastic3d", npy, "--e", "1:200,100", "--nu", "1:0.3",
                      "--need-max", "150"], capture_output=True, text=True, cwd=ROOT)
out["cli_descending"] = json.loads(cli.stdout) if cli.stdout.strip().startswith("{") else cli.stderr[-300:]
cli = subprocess.run([sys.executable, "-m", "ustand.elastic3d", npy, "--e", "1:200", "--nu", "1:0.3,0.1"],
                     capture_output=True, text=True, cwd=ROOT)
out["cli_descending_nu_is_refused"] = (cli.stderr.strip().splitlines() or ["?"])[-1]
# conduction3d: the same reading of a phase box
from ustand import conduction3d as C3
Vc = np.ones((3, 2, 2), dtype=np.int64)
for name, s in (("ascending", ["1", "2"]), ("descending", ["2", "1"])):
    r = C3.judge(Vc, {1: {"s": s, "earned": True}}, "1.5")
    out[f"conduction3d_{name}"] = {"lower": r["lower"], "upper": r["upper"], "verdict": r["verdict"],
                                   "truth_over_the_box": [1.0, 2.0]}
# THE FALSE EARNED: a NARROW reversed box on a sample whose bracket is loose enough not to invert. A central pore in
# 3^3, E written [205, 200] (the box E in [200, 205]), nu 0.3: the stand's lower (computed at 205) is 188.18, so
# "E_app >= 188" is EARNED; at E = 200 — inside the box — the truth is <= 185.97 (Q1, r = 8, a conforming
# displacement field: its energy is >= the true one), so the requirement FAILS there.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref_elastic as RE
Vp = np.ones((3, 3, 3), dtype=np.int64); Vp[1, 1, 1] = 0
np.save(os.path.join(ROOT, "redteam", "round2", "samples", "pore-3x3x3.npy"), Vp)
for name, E in (("reversed [205, 200]", [F(205), F(200)]), ("ordered [200, 205]", [F(200), F(205)])):
    ph = {0: {"E": [F(0), F(0)], "nu": [F(0), F(0)], "earned": True}, 1: {"E": E, "nu": [F(3, 10), F(3, 10)], "earned": True}}
    j = E3.judge(Vp, ph, need_min=188)
    out[f"false_earned_{name}"] = {"lower": j["lower"], "upper": j["upper"], "E_app >= 188": j["verdict_min"]}
out["false_earned_independent"] = {f"Q1 r={r} at E=200 (>= truth)": RE.solve(Vp, {0: (0.0, 0.0), 1: (200.0, 0.3)}, r=r)
                                   for r in (2, 4, 8)}
print(json.dumps(out, indent=1, default=str))
