# -*- coding: utf-8 -*-
"""
refine — uniform RED refinement (Bey 1:8) of a tet FEA deck, posing THE SAME continuum problem (2026-11-11, level 3
narrowing; plan: research/cad/PLAN-level3.md "Narrowing 3b/3c — mesh refinement").

    python3 -m ustand.refine part.fem part_r1.deck.pkl [--subcase 1]

What stays the same, and why the exact compliance is the same number:
  GEOMETRY: every new node is an edge midpoint, its coordinates EXACT decimals (the midpoint of two decimals with k
    digits has at most k + 1). Flat faces stay flat; the children of a tet fill it exactly (the volume is preserved).
  SUPPORTS: u = 0 at the RBE2 dependents of an SPC'd node. A midpoint between two such nodes is fixed too, so a face
    fixed before is fixed in all four of its children, and a P1 field of the coarse mesh that vanished on the supports
    still does (the coarse P1 space nests in the fine one WITH its constraints — the lower bound can only improve).
  LOAD: NOT a new RBE3 distribution over more nodes (that would be another load). The coarse deck's load is read as
    its traction t: linear on each loaded face, its nodal values the solution of M_s t = f_RBE3 (tetmesh.rbe3_traction,
    the same t the upper bound already uses). On the fine mesh the SAME t is given by its values at the nodes (at a
    midpoint of a loaded edge, the mean of the two ends — exact for a linear field), and the fine nodal loads are its
    consistent loads. The deck carries it as deck["traction"]; tetfea and cadbracket take the load from there.
The refined deck is a dict in read_deck's format plus "traction" and "refined_from", saved with pickle (a file we
write and read ourselves).
"""
from __future__ import annotations

import hashlib
import pickle
import sys
from fractions import Fraction as Fr

import numpy as np

from . import tetfea as TF, tetmesh as TM

EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


def dec_str(x: Fr) -> str:
    """An exact decimal string for a Fraction whose denominator is 2^a 5^b (read back by tetfea._nas exactly)."""
    m = 0
    while (x * 10 ** m).denominator != 1:
        m += 1
        if m > 60:
            raise ValueError(f"{x} is not a finite decimal")
    n = int(x * 10 ** m)
    s = "-" if n < 0 else ""
    n = abs(n)
    if m == 0:
        return f"{s}{n}.0"
    digits = str(n).rjust(m + 1, "0")
    return f"{s}{digits[:-m]}.{digits[-m:]}"


def children(v, mid):
    """The 8 children of tet v = (v0, v1, v2, v3) by Bey's red rule; mid[(a, b)] the midpoint node of edge a-b
    (local indices, a < b). The octahedron is cut along the diagonal m02 - m13."""
    m = lambda a, b: mid[(a, b)]
    return [
        (v[0], m(0, 1), m(0, 2), m(0, 3)),
        (m(0, 1), v[1], m(1, 2), m(1, 3)),
        (m(0, 2), m(1, 2), v[2], m(2, 3)),
        (m(0, 3), m(1, 3), m(2, 3), v[3]),
        (m(0, 1), m(0, 2), m(0, 3), m(1, 3)),
        (m(0, 1), m(0, 2), m(1, 2), m(1, 3)),
        (m(0, 2), m(0, 3), m(1, 3), m(2, 3)),
        (m(0, 2), m(1, 2), m(1, 3), m(2, 3)),
    ]


def _det(P):
    a, b, c = P[1] - P[0], P[2] - P[0], P[3] - P[0]
    return float(np.dot(a, np.cross(b, c)))


def coarse_traction(deck, subcase=1):
    """The coarse deck's load as a traction: {grid: (tx, ty, tz)} on the loaded faces' nodes, F, M, and the faces."""
    ids = sorted(deck["grids"])
    idx = {n: i for i, n in enumerate(ids)}
    X = np.array([[float(TF._nas(c)) for c in deck["grids"][n]] for n in ids])
    T = np.array([[idx[n] for n in t] for t in deck["tets"]])
    F, own, lf, tf = TM.faces(T)
    fixed = {idx[n] for ind, deps in deck["rbe2"] for n in deps if deck["spc"].get(ind, "").startswith("123")}
    ref, _, rn = deck["rbe3"][0]
    kind = TM.classify(F, own, fixed, {idx[n] for n in rn})
    lid = int(deck["subcases"][subcase]["LOAD"])
    Fv, Mv = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    if lid in deck["force"]:
        _, sc, v = deck["force"][lid]
        Fv = tuple(float(sc * x) for x in v)
    if lid in deck["moment"]:
        _, sc, v = deck["moment"][lid]
        Mv = tuple(float(sc * x) for x in v)
    xyz = {n: list(X[idx[n]]) for n in rn + [ref]}
    fl = TF.rbe3_loads(xyz, ref, rn, Fv, Mv)
    tr, res, lost = TM.rbe3_traction(X, F, kind, {idx[n]: fl[i] for i, n in enumerate(rn)})
    if lost:
        raise ValueError(f"{len(lost)} RBE3 nodal forces on nodes of no loaded face: the load is not a traction here")
    nodal = {ids[i]: tuple(float(c) for c in t) for i, t in tr.items()}
    loaded_faces = [tuple(ids[int(i)] for i in F[f]) for f in np.where(kind == 2)[0]]
    return nodal, Fv, Mv, loaded_faces, res


def red_refine(deck, subcase=1, fix_mixed=True, planted=None):
    """-> the refined deck. fix_mixed: also fix a midpoint between fixed nodes of DIFFERENT RBE2s (both ends u = 0, so
    the coarse field vanishes there; leaving it free would free the coarse fixed faces between them).
    planted (tests only): "unfixed_bolt_midpoints" — no midpoint joins an RBE2; "rbe3_over_fine_nodes" — no traction,
    the RBE3 spread anew over the coarse AND midpoint nodes of the loaded faces (another load with the same resultant)."""
    g = deck["grids"]
    dec = {n: tuple(TF._nas(c) for c in g[n]) for n in g}
    nodal, Fv, Mv, loaded_faces, res = coarse_traction(deck, subcase)
    nid = max(g) + 1
    mid = {}                          # frozenset(grid a, grid b) -> new grid
    grids = dict(g)
    for t in deck["tets"]:
        for a, b in EDGES:
            e = frozenset((t[a], t[b]))
            if e not in mid:
                mid[e] = nid
                pa, pb = dec[t[a]], dec[t[b]]
                grids[nid] = tuple(dec_str((x + y) / 2) for x, y in zip(pa, pb))
                nid += 1
    Xf = {n: np.array([float(TF._nas(c)) for c in grids[n]]) for n in grids}
    tets = []
    for t in deck["tets"]:
        loc = {(a, b): mid[frozenset((t[a], t[b]))] for a, b in EDGES}
        s0 = np.sign(_det(np.array([Xf[n] for n in t])))
        for c in children(t, loc):
            if np.sign(_det(np.array([Xf[n] for n in c]))) != s0:
                c = (c[1], c[0], c[2], c[3])
            tets.append(c)
    # supports
    rbe2 = []
    owner_of = {}
    spc_dep = set()
    for ind, deps in deck["rbe2"]:
        if deck["spc"].get(ind, "").startswith("123"):
            spc_dep |= set(deps)
        for n in deps:
            owner_of.setdefault(n, len(rbe2))
        rbe2.append((ind, list(deps)))
    mixed = 0
    depsets = [set(deps) for ind, deps in deck["rbe2"]]
    for e, m in mid.items():
        a, b = tuple(e)
        same = [i for i, s in enumerate(depsets) if a in s and b in s]
        if planted == "unfixed_bolt_midpoints":
            continue
        if same:
            rbe2[same[0]][1].append(m)
        elif fix_mixed and a in spc_dep and b in spc_dep:
            rbe2[owner_of[a]][1].append(m)
            mixed += 1
    # the SAME traction at the fine loaded nodes
    tr = dict(nodal)
    for fa in loaded_faces:
        for i in range(3):
            for j in range(i + 1, 3):
                a, b = fa[i], fa[j]
                m = mid[frozenset((a, b))]
                tr[m] = tuple((x + y) / 2 for x, y in zip(nodal[a], nodal[b]))
    rbe3 = deck["rbe3"]
    if planted == "rbe3_over_fine_nodes":
        ref, wt, rn = rbe3[0]
        rbe3 = [(ref, wt, sorted(tr))] + list(rbe3[1:])
    out = dict(grids=grids, tets=tets, rbe2=rbe2, rbe3=rbe3, spc=deck["spc"], force=deck["force"],
               moment=deck["moment"], mat=deck["mat"], subcases=deck["subcases"])
    if planted != "rbe3_over_fine_nodes":
        out["traction"] = {"subcase": subcase, "F": Fv, "M": Mv, "nodal": tr}
    out["refined_from"] = {"tets": len(deck["tets"]), "grids": len(g), "mixed_fixed_midpoints": mixed,
                           "traction_residual": res}
    return out


def traction_loads(X, F, kind, tr_idx):
    """Consistent P1 nodal loads of a nodal-linear traction on the faces of kind 2: f_a += A/12 (2 t_a + t_b + t_c)."""
    f = np.zeros((len(X), 3))
    for fid in np.where(kind == 2)[0]:
        a, b, c = (int(x) for x in F[fid])
        A = 0.5 * np.linalg.norm(np.cross(X[b] - X[a], X[c] - X[a]))
        ta, tb, tc = (np.asarray(tr_idx[v], float) for v in (a, b, c))
        f[a] += A / 12 * (2 * ta + tb + tc)
        f[b] += A / 12 * (ta + 2 * tb + tc)
        f[c] += A / 12 * (ta + tb + 2 * tc)
    return f


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="ustand.refine")
    ap.add_argument("deck")
    ap.add_argument("out")
    ap.add_argument("--subcase", type=int, default=1)
    a = ap.parse_args(argv)
    d = TF.read_deck(a.deck)
    r = red_refine(d, a.subcase)
    r["refined_from"]["deck"] = a.deck
    r["refined_from"]["sha256"] = hashlib.sha256(open(a.deck, "rb").read()).hexdigest()
    with open(a.out, "wb") as f:
        pickle.dump(r, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"{a.deck}: {len(d['tets'])} tets, {len(d['grids'])} grids -> {len(r['tets'])} tets, {len(r['grids'])} "
          f"grids; mixed fixed midpoints {r['refined_from']['mixed_fixed_midpoints']}; traction residual "
          f"{r['refined_from']['traction_residual']:.2e}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
