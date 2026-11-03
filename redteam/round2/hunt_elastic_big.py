"""Round 2: elastic3d on LARGER samples (4-7 voxels a side, past HYBRID_FROM or with force_hybrid), and with
refine = 2: the hybridized float choice + the exact phase, against Q1 (ref_elastic, r = 1, 2: >= the truth).
LOWER: a hard check (lower <= Q1 at every soft corner). UPPER: >= the Aitken estimate at the stiff corners (a flag).
--mutant lower_e_high: the lower bound's sabotage — must be seen.
    PYTHONPATH=. python3 redteam/round2/hunt_elastic_big.py SEED0 COUNT [--mutant lower_e_high]"""
import itertools, json, os, random, sys, time
from fractions import Fraction as F
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref_elastic as RE  # noqa: E402
from hunt_elastic import aitken  # noqa: E402
from ustand import elastic3d as E3  # noqa: E402


def gen(seed):
    rng = random.Random(seed)
    n = rng.randint(4, 7)
    nx, ny, nz = n, rng.randint(3, n), rng.randint(3, n)
    p_pore = rng.choice([0.0, 0.1, 0.2, 0.3])
    nph = rng.choice([1, 2])
    rs = np.random.default_rng(seed)
    V = np.where(rs.random((nx, ny, nz)) < p_pore, 0, rs.integers(1, nph + 1, (nx, ny, nz)))
    phases = {0: {"E": [F(0), F(0)], "nu": [F(0), F(0)]}}
    for p in range(1, nph + 1):
        E = F(rng.choice([1, 100, 10000]))
        phases[p] = {"E": [E, E * rng.choice([1, 2])], "nu": rng.choice([[F(3, 10), F(3, 10)], [F(-2, 10), F(4, 10)],
                                                                     [F(48, 100), F(49, 100)]])}
    return V, phases, rng.choice([1, 1, 2]) if n <= 5 else 1, rng.random() < 0.5


def check(seed, mutant=None):
    V, phases, refine, force = gen(seed)
    solid = [p for p in sorted(int(x) for x in np.unique(V)) if p != 0]
    E3._MUTANT.clear()
    if force:
        E3._MUTANT["force_hybrid"] = True
    if mutant:
        E3._MUTANT[mutant] = True
    t0 = time.time()
    try:
        up = float(E3.upper(V, phases, refine)[0])
        lo, note = E3.lower(V, phases, refine)
        lo = float(lo)
    except Exception as e:                                  # noqa: BLE001
        E3._MUTANT.clear()
        return {"seed": seed, "status": "error", "why": repr(e)[:160]}
    E3._MUTANT.clear()
    out = {"seed": seed, "shape": list(V.shape), "refine": refine, "force_hybrid": force, "lower": lo, "upper": up,
           "note": note, "t_stand": round(time.time() - t0, 1), "viol": []}

    def ph_at(ch):
        d = {0: (0.0, 0.0)}
        for p, (ei, ni) in zip(solid, ch):
            d[p] = (float(phases[p]["E"][ei]), float(phases[p]["nu"][ni]))
        return d
    for ch in itertools.product(*[[(0, 0), (0, 1)] for _ in solid]):
        q = [RE.solve(V, ph_at(ch), r=rr) for rr in (1, 2)]
        if lo > min(q) * (1 + 1e-9):
            out["viol"].append({"what": "LOWER above Q1", "corner": ch, "lower": lo, "q1": q})
    for ch in itertools.product(*[[(1, 0), (1, 1)] for _ in solid]):
        q = [RE.solve(V, ph_at(ch), r=rr) for rr in (1, 2, 3)]
        est = aitken(*q)
        if up < est * (1 - 1e-6) and up < q[-1]:
            out["viol"].append({"what": "UPPER below the extrapolated truth (flag)", "corner": ch, "upper": up, "q1": q})
    out["status"] = "checked"
    return out


if __name__ == "__main__":
    s0, n = int(sys.argv[1]), int(sys.argv[2])
    mut = sys.argv[sys.argv.index("--mutant") + 1] if "--mutant" in sys.argv else None
    for s in range(s0, s0 + n):
        try:
            print(json.dumps(check(s, mut), default=str), flush=True)
        except Exception as e:                              # noqa: BLE001
            print(json.dumps({"seed": s, "status": "harness_error", "why": repr(e)[:300]}), flush=True)
