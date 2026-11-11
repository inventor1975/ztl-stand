"""Level 3c float PILOT for an SCL on a SimJEB deck (choosing only; nothing here is a bound).

    python3 research/cad/scl_pilot.py DECK --point x,y,z [--R R] [--subcase 1] > spec.json

1. the wall normal n: the shortest chord through the point to the mesh boundary (cadbracket.wall_chord);
   c = the chord's mid-plane, t_w = its length; n made EXACTLY unit and rational (cadbracket.rational_unit);
2. the slab omega (cadbracket.omega_slab) and the float P1 solution's mean stress over it; the tangent t = the
   principal direction of that mean stress projected on the plane perpendicular to n (largest |eigenvalue|), and t2,
   reported, with the ratio of the two eigenvalues;
3. s for each functional: sqrt(C_f / C_p) (the balance; any s > 0 is valid).
Writes a JSON spec for cadbracket --scl (one per tangent) and prints the float values of sigma_m and sigma_b."""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ustand import tetfea as TF, cadbracket as CB          # noqa: E402


def main(argv):
    import argparse
    from fractions import Fraction as Fr
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("--point", required=True)
    ap.add_argument("--R", type=float, help="the slab radius across the line (default: t_w)")
    ap.add_argument("--subcase", type=int, default=1)
    ap.add_argument("--out", required=True, help="prefix for the spec files <out>_t1.json, <out>_t2.json")
    a = ap.parse_args(argv)
    say = lambda m: print(m, file=sys.stderr, flush=True)
    d = TF.read_deck(a.deck)
    p = np.array([float(x) for x in a.point.split(",")])
    nd, L, h1, h2 = CB.wall_chord(d, p)
    say(f"wall chord through {p.tolist()}: direction {nd.round(5).tolist()}, length {L:.4f} mm, "
        f"hits {h1.round(4).tolist()} / {h2.round(4).tolist()}")
    n = CB.rational_unit(nd)
    nf = np.array([float(x) for x in n])
    c = Fr(round(float((h1 + h2) @ nf / 2), 4)).limit_denominator(10 ** 4)
    tw = Fr(round(L, 4)).limit_denominator(10 ** 4)
    R = Fr(round(a.R if a.R else L, 4)).limit_denominator(10 ** 4)
    mask, vol = CB.omega_slab(d, p.tolist(), n, c, tw, R)
    say(f"slab: c = {float(c)}, t_w = {float(tw)}, R = {float(R)}: {int(mask.sum())} tets, |omega| = {float(vol):.6f}")
    # float P1 solution and the mean stress over the slab
    r = TF.solve_cases(d, [a.subcase], log=lambda m: None, return_u=True)[0]
    u = r["u"]
    ids = sorted(d["grids"])
    idx = {q: i for i, q in enumerate(ids)}
    X = np.array([[float(TF._nas(x)) for x in d["grids"][q]] for q in ids])
    T = np.array([[idx[q] for q in t] for t in d["tets"]])
    P = X[T[mask]]
    D = np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]], axis=2)
    Di = np.linalg.inv(D)
    gr = np.concatenate([-Di.sum(axis=1, keepdims=True), Di], axis=1)
    vv = np.abs(np.linalg.det(D)) / 6
    Gu = np.einsum("nia,nib->nab", u[T[mask]], gr)
    eps = 0.5 * (Gu + Gu.transpose(0, 2, 1))
    E, nu = float(d["mat"][0]), float(d["mat"][1])
    mu, lam = E / (2 * (1 + nu)), E * nu / ((1 + nu) * (1 - 2 * nu))
    sig = 2 * mu * eps + lam * np.trace(eps, axis1=1, axis2=2)[:, None, None] * np.eye(3)
    msig = (sig * vv[:, None, None]).sum(0) / vv.sum()
    Pp = np.eye(3) - np.outer(nf, nf)
    st = Pp @ msig @ Pp
    w, V = np.linalg.eigh(st)
    order = np.argsort(-np.abs(w))
    tangents = [V[:, order[0]], V[:, order[1]]]
    say(f"mean stress over the slab (float P1): {np.round(msig, 3).tolist()}")
    say(f"in-plane principal: {w[order[0]]:.3f} along {tangents[0].round(4).tolist()}, {w[order[1]]:.3f} along "
        f"{tangents[1].round(4).tolist()} (ratio {abs(w[order[1]] / w[order[0]]):.3f})")
    out = {}
    for ti, tvec in enumerate(tangents, 1):
        Pi, tp = CB.tangent_projector(tvec, n)
        rec = {"point": [str(x) for x in a.point.split(",")], "n": [str(x) for x in n],
               "u": [float(x) for x in tvec], "c": str(c), "tw": str(tw), "R": str(R),
               "tets": int(mask.sum()), "omega_volume": float(vol)}
        for kind in ("membrane", "bending"):
            S0, S1 = CB.scl_extractor(kind, Pi, n, c, tw, vol, d["mat"][0], d["mat"][1])
            pre = {"omega": mask, "S0": S0, "S1": S1}
            cp = TF.solve_cases(d, [{"F": (0.0, 0.0, 0.0), "M": (0.0, 0.0, 0.0), "label": "p", "prestress": pre}],
                                log=lambda m: None)[0]["compliance_float"]
            Fd, Md = CB.subcase_load(d, a.subcase)
            # the float value of the functional: l(u_f) = (C(f + p) - C(f - p)) / 4
            cpl = TF.solve_cases(d, [{"F": Fd, "M": Md, "label": "+", "prestress": pre}], log=lambda m: None)[0]
            mi = {"omega": mask, "S0": [[-x for x in rw] for rw in S0], "S1": [[[-x for x in cc] for cc in rw] for rw in S1]}
            cmi = TF.solve_cases(d, [{"F": Fd, "M": Md, "label": "-", "prestress": mi}], log=lambda m: None)[0]
            val = (cpl["compliance_float"] - cmi["compliance_float"]) / 4
            s = math.sqrt(r["compliance_float"] / cp)
            rec[kind] = {"float_value": val, "C_p_float": cp, "s_balance": s}
            say(f"t{ti} {kind}: float value {val:.4f} MPa, C_p {cp:.4f}, s = {s:.4f}")
        out[f"t{ti}"] = rec
        json.dump(rec, open(f"{a.out}_t{ti}.json", "w"), indent=1)
    print(json.dumps({"C_f_float": r["compliance_float"], "eig_ratio": float(abs(w[order[1]] / w[order[0]])),
                      **{k: {kk: v[kk] for kk in ("membrane", "bending", "tets", "c", "tw", "R")} for k, v in out.items()}},
                     indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
