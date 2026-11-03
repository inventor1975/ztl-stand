"""Round 2 hunt: elastic3d's proved [lower, upper] against redteam/round2/ref_elastic.py on random voxel samples.
  LOWER (a hard check): lower <= Q1_r(corner) for every corner of the moduli box and every r (Q1 >= the truth at that
        corner, so lower > Q1 is a FALSE lower bound).
  UPPER (a flag, then confirmed by refinement): upper >= the truth at every box point; the truth estimated at the box's
        stiff corners (E_hi, nu at each end) by Aitken extrapolation of Q1 at r = 1, 2, 4 (Q1 converges from above).
Samples: 2-4 voxels a side, pores, two or three solid phases (contrast up to 1e4), wide E boxes, nu boxes negative,
near 1/2 and mixed. --mutant NAME sets elastic3d._MUTANT[NAME] (e_low: the upper at E_lo; lower_e_high: the lower at
E_hi) — the matching check must see it.
    PYTHONPATH=. python3 redteam/round2/hunt_elastic.py SEED0 COUNT [--mutant NAME]"""
import itertools, json, os, random, sys, time
from fractions import Fraction as F
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref_elastic as RE  # noqa: E402
from ustand import elastic3d as E3  # noqa: E402

NU_BOXES = [(F(3, 10), F(3, 10)), (F(1, 10), F(4, 10)), (F(45, 100), F(499, 1000)), (F(-1, 2), F(0)),
            (F(-9, 10), F(-5, 10)), (F(0), F(0)), (F(-3, 10), F(49, 100))]


def gen(seed):
    rng = random.Random(seed)
    nx, ny, nz = rng.randint(2, 4), rng.randint(1, 3), rng.randint(1, 3)
    nph = rng.choice([1, 2, 2, 3])
    pore = rng.random() < 0.6
    ids = list(range(1, nph + 1)) + ([0] if pore else [])
    w = [1.0] * nph + ([rng.choice([0.15, 0.3])] if pore else [])
    V = np.array([rng.choices(ids, w)[0] for _ in range(nx * ny * nz)]).reshape(nx, ny, nz)
    if rng.random() < 0.3:                                  # make sure a solid path exists: one full solid row
        j, k = rng.randrange(ny), rng.randrange(nz)
        V[:, j, k] = 1
    phases = {0: {"E": [F(0), F(0)], "nu": [F(0), F(0)]}}
    for p in range(1, nph + 1):
        E = F(rng.choice([1, 10, 100, 1000, 10000])) * rng.randint(1, 9)
        wide = rng.choice([1, 1, F(11, 10), 2, 10])
        nu = rng.choice(NU_BOXES)
        phases[p] = {"E": [E, E * wide], "nu": list(nu)}
    return V, phases


def aitken(a, b, c):
    d1, d2 = a - b, b - c
    if d1 <= 0 or d2 <= 0 or d1 <= d2:
        return c - d2                                       # no clean geometric decay: a cautious guess
    return c - d2 * d2 / (d1 - d2)


def check(seed, mutant=None):
    V, phases = gen(seed)
    used = sorted(int(x) for x in np.unique(V))
    solid = [p for p in used if p != 0]
    E3._MUTANT.clear()
    if mutant:
        E3._MUTANT[mutant] = True
    t0 = time.time()
    try:
        up = float(E3.upper(V, phases)[0])
        lo, note = E3.lower(V, phases)
        lo = float(lo)
    except Exception as e:                                  # noqa: BLE001
        E3._MUTANT.clear()
        return {"seed": seed, "status": "error", "why": repr(e)[:160]}
    E3._MUTANT.clear()
    ts = time.time() - t0
    out = {"seed": seed, "shape": list(V.shape), "phases_used": used, "lower": lo, "upper": up, "note": note,
           "t_stand": round(ts, 2), "viol": []}
    # corners of the box (E and nu ends per used solid phase)
    def ph_at(choice):
        d = {0: (0.0, 0.0)}
        for p in phases:
            if p != 0:
                d[p] = (float(phases[p]["E"][0]), float(phases[p]["nu"][0]))
        for p, (ei, ni) in zip(solid, choice):
            d[p] = (float(phases[p]["E"][ei]), float(phases[p]["nu"][ni]))
        return d
    combos = list(itertools.product(*[[(0, 0), (0, 1)] for _ in solid]))          # E_lo with both nu ends
    lows = []
    for ch in combos:
        q = [RE.solve(V, ph_at(ch), r=rr) for rr in (1, 2)]
        lows.append(min(q))
        if lo > min(q) * (1 + 1e-9) + 1e-12:
            out["viol"].append({"what": "LOWER above a Q1 value (>= truth)", "corner": ch, "lower": lo, "q1": q})
    out["q1_min_at_soft_corners"] = min(lows) if lows else None
    hcombos = list(itertools.product(*[[(1, 0), (1, 1)] for _ in solid]))         # E_hi with both nu ends
    for ch in hcombos:
        q = [RE.solve(V, ph_at(ch), r=rr) for rr in (1, 2, 4)]
        est = aitken(*q)
        out.setdefault("truth_est_stiff", []).append(est)
        if up < est * (1 - 1e-6) and up < q[-1]:
            out["viol"].append({"what": "UPPER below the extrapolated truth (flag)", "corner": ch, "upper": up,
                                "q1": q, "est": est})
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
