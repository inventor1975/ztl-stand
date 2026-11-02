"""Red team: conduction3d's two-sided bracket on s_eff.
(1) closed forms: uniform; layers across the flow (series: the harmonic mean, exact); columns along the flow
    (parallel: the arithmetic mean, exact); a straight 1-voxel channel through an insulator (s / (ny nz), exact);
(2) random volumes (2-3 phases, insulators included, 50 % or checkerboard-like): the brackets at refine 1, 2 and 3 must
    OVERLAP (each contains the same continuum value) and lower <= upper.
--mutant: the reported upper bound scaled by 0.97 (a false upper bound) — the checks must see it.
    PYTHONPATH=. python3 redteam/check_conduction3d.py [COUNT] [--mutant]"""
import json, random, sys
from fractions import Fraction as F
import numpy as np
from ustand import conduction3d as C3

MUT = "--mutant" in sys.argv


def seff(V, s, refine=1):
    lo, up, note = C3.s_eff(V, s, refine)
    return float(lo), float(up) * (0.97 if MUT else 1)


def main(count):
    rng = random.Random(11)
    res = {"exact_cases": 0, "exact_violations": [], "overlap_cases": 0, "overlap_violations": []}
    for trial in range(count):
        nx, ny, nz = rng.randint(2, 6), rng.randint(1, 4), rng.randint(1, 4)
        s = {0: F(0), 1: F(rng.randint(1, 50), 10), 2: F(rng.randint(1, 50), 7)}
        cases = []
        cases.append(("uniform", np.ones((nx, ny, nz), int), float(s[1])))
        lay = np.array([rng.choice([1, 2]) for _ in range(nx)])
        V = np.repeat(np.repeat(lay[:, None, None], ny, 1), nz, 2)
        cases.append(("series", V, float(nx / sum(1 / s[int(p)] for p in lay))))
        col = np.array([[rng.choice([1, 2]) for _ in range(nz)] for _ in range(ny)])
        V = np.repeat(col[None, :, :], nx, 0)
        cases.append(("parallel", V, float(sum(s[int(p)] for p in col.flat) / (ny * nz))))
        V = np.zeros((nx, ny, nz), int)
        y0, z0 = rng.randrange(ny), rng.randrange(nz)
        V[:, y0, z0] = 1
        cases.append(("channel", V, float(s[1]) / (ny * nz)))
        for name, V, exact in cases:
            for rf in (1, 2):
                lo, up = seff(V, s, rf)
                res["exact_cases"] += 1
                if not (lo <= exact * (1 + 1e-12) and exact <= up * (1 + 1e-12)):
                    res["exact_violations"].append({"case": name, "shape": V.shape, "refine": rf, "lo": lo, "up": up,
                                                    "exact": exact})
        # random volumes: overlap across refinements
        n = rng.randint(2, 4)
        p = rng.choice([0.3, 0.5, 0.7])
        V = np.where(np.random.default_rng(trial).random((n, n, n)) < p, rng.choice([0, 2]), 1)
        if rng.random() < 0.3:                                # a 3D checkerboard
            V = (np.indices((n, n, n)).sum(0) % 2).astype(int) * rng.choice([1, 2])
        brs = []
        for rf in (1, 2, 3):
            try:
                brs.append((rf, *seff(V, s, rf)))
            except Exception as e:                            # noqa: BLE001
                brs.append((rf, None, repr(e)[:80]))
        ok = [b for b in brs if b[1] is not None]
        res["overlap_cases"] += 1
        if ok:
            lo_max, up_min = max(b[1] for b in ok), min(b[2] for b in ok)
            if lo_max > up_min * (1 + 1e-12) or any(b[1] > b[2] for b in ok):
                res["overlap_violations"].append({"V": V.tolist(), "brackets": brs})
    print(json.dumps({"mutant": MUT, "exact_cases": res["exact_cases"], "exact_violations": len(res["exact_violations"]),
                      "first_exact": res["exact_violations"][:2], "overlap_cases": res["overlap_cases"],
                      "overlap_violations": len(res["overlap_violations"]),
                      "first_overlap": res["overlap_violations"][:1]}, default=str))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 40)
