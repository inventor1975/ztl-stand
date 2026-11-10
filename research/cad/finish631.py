"""The EXACT finish of the 2b upper bound on a real bracket: the float choice g (from upper631.py) -> exact fluxes,
the forest push, the exact energy (in parallel) -> a PROVED upper bound on the compliance; with the proved lower bound
(2a) a two-sided bracket. Usage: python3 research/cad/finish631.py <deck.fem> <g.npy> <q.npy> [subcase] [jobs]"""
import sys, time, os, json
from fractions import Fraction as Fr
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ustand import tetfea as TF, tetmesh as TM, equil as EQ, alfeld as AL


def _energy_chunk(args):
    Ps, gs = args
    tt = tr2 = Fr(0)
    for P, g in zip(Ps, gs):
        a, b = AL.energy(P, g)
        tt += a
        tr2 += b
    return tt, tr2


if __name__ == "__main__":
    path, gpath, qpath = sys.argv[1:4]
    sc = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    jobs = int(sys.argv[5]) if len(sys.argv) > 5 else 8
    t0 = time.time()
    d = TF.read_deck(path)
    ids = sorted(d["grids"]); idx = {n: i for i, n in enumerate(ids)}
    Xq = [tuple(TF._nas(x) for x in d["grids"][n]) for n in ids]
    X = np.array([[float(c) for c in p] for p in Xq])
    T = np.array([[idx[n] for n in t] for t in d["tets"]])
    F, own, lf, tf = TM.faces(T)
    fixed = {idx[n] for ind, deps in d["rbe2"] for n in deps if d["spc"].get(ind, "").startswith("123")}
    ref, _, rn = d["rbe3"][0]
    kind = TM.classify(F, own, fixed, {idx[n] for n in rn})
    g = np.load(gpath)
    qf = np.load(qpath)
    qp = {int(f): [[Fr(float(qf[f, p, c])) for c in range(3)] for p in range(3)] for f in np.where(kind == 2)[0]}
    qp.update({int(f): [[Fr(0)] * 3 for _ in range(3)] for f in np.where(kind == 3)[0]})
    print(f"read {len(T)} tets; {time.time() - t0:.1f} s", flush=True)
    q, bad, _, bits = EQ.finish(Xq, T, F, own, tf, kind, g, qp, fixed_faces=set(qp))
    print(f"exact push: unbalanced {bad}, largest denominator {bits} bits; {time.time() - t0:.1f} s", flush=True)
    pos, sgn = EQ.slot_maps(T, F, own, tf)
    Ps, gs = [], []
    for t in range(len(T)):
        out = []
        for f in range(4):
            qq = q[int(tf[t, f])]
            s_ = int(sgn[t, f])
            for jv in range(3):
                r = qq[int(pos[t, f, jv])]
                out += [r[0] * s_, r[1] * s_, r[2] * s_]
        Ps.append([list(Xq[v]) for v in T[t]])
        gs.append(out)
    E, nu = d["mat"][0], d["mat"][1]
    if os.environ.get("EV"):
        # the VECTORISED rigorous upper bound (errfloat) instead of the exact Fractions
        t1 = time.time()
        up_ev = AL.energy_upper_ev(Ps, gs, E, nu)
        print(json.dumps({"subcase": sc, "unbalanced": bad, "bits": bits, "upper_proved_errfloat": up_ev,
                          "energy_seconds": round(time.time() - t1, 1), "seconds": round(time.time() - t0, 1)}), flush=True)
        sys.exit(0)
    ch = max(1, len(T) // (jobs * 8))
    tt = tr2 = Fr(0)
    with Pool(jobs) as pool:
        for a, b in pool.imap_unordered(_energy_chunk, [(Ps[i:i + ch], gs[i:i + ch]) for i in range(0, len(T), ch)]):
            tt += a
            tr2 += b
    up = ((1 + nu) * tt - nu * tr2) / E
    # (2026-11-10: printing the exact Fraction crashed — over Python's 4300-digit int-to-str limit — after the whole
    # computation; only its float, rounded UP, is printed now)
    import math
    print(json.dumps({"subcase": sc, "unbalanced": bad, "bits": bits, "numerator_bits": up.numerator.bit_length(),
                      "upper_proved": math.nextafter(float(up), math.inf), "seconds": round(time.time() - t0, 1)}),
          flush=True)
