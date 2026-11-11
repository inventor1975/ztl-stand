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
import itertools
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
    tets, bey = [], []
    for t in deck["tets"]:
        loc = {(a, b): mid[frozenset((t[a], t[b]))] for a, b in EDGES}
        s0 = np.sign(_det(np.array([Xf[n] for n in t])))
        for c in children(t, loc):
            bey.append(c)                                     # Bey's vertex order, for a further refinement
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
    out["parent"] = [i for i in range(len(deck["tets"])) for _ in range(8)]
    out["bey"] = bey
    return out


# ------------------------------------------------------------------------------------------------ graded (red-green)
# LOCAL refinement (2026-11-11, PLAN-level3 "Graded refinement", road A): marked tets are split red (Bey 1:8); a
# GREEN closure keeps the mesh CONFORMING (no hanging node), so both bounds apply unchanged:
#   lower: the fine P1 space is conforming and contains the coarse one (a coarse P1 field is P1 on every child);
#   upper: every tet is a tet, every interior face has exactly two tets — the Alfeld hybrid and the exact push as is.
# Closure on EDGES. The marked-edge set of a tet must be one of these patterns; each face is then split by 0, 1 or 3 of
# its edges, and that split is UNIQUE (1 edge: the median to the opposite vertex; 3: the 4 red triangles), so two
# tets sharing a face split it the same way:
#   none | one edge (2 children) | two OPPOSITE edges (4) | the 3 edges of one face (4) | all 6 = red (8).
# Rules, to a fixed point: a face with exactly 2 marked edges gets its third marked; a tet whose set is no pattern
# becomes red (all 6 marked). Each child keeps the index of its ROOT coarse tet in "parent".
# A GREEN TET IS NEVER REFINED (2026-11-11). The first version refined the closed deck as it was, green tets included.
# MEASURED on SimJEB 631, tets under quality 0.03 (volume / longest edge^3, 1 = regular) / the 0.1 % quantile / the
# median: coarse 9 / 0.066 / 0.406 -> round 1: 22 / 0.061 / 0.403 -> round 2: 168 / 0.029 / 0.374 -> round 3:
# 1980 / 0.019 / 0.298; and the trace CG's whole tail sat in those slivers. Now a round starts by UN-GREENING: every
# green family is replaced by its parent (the midpoints of its split edges are kept in deck["green"]), the marks pass
# to the parent, and the closure runs on these red leaves to a fixed point: a leaf is split red FOR REAL (its 8
# children become leaves) when it is marked, when its split edges form no pattern, or when its green children would
# have a split edge of their own (a neighbour two levels finer). Every tet is then a red descendant of a coarse tet or
# one green child of such: a bounded family of shapes, whatever the number of rounds. The price: a round's mesh is
# not a refinement of the previous round's CLOSED mesh (only of its red leaves), so the lower bounds of successive
# rounds need not be monotone; each round still refines the coarse deck, and every bracket stands on its own.
OPP = ((0, 5), (1, 4), (2, 3))                    # opposite edge pairs, as indices into EDGES
FACE_EDGES = tuple(tuple(i for i, (a, b) in enumerate(EDGES) if k not in (a, b)) for k in range(4))   # face opp. k


def pattern(mask):
    """The closure pattern of a tet's 6-edge mark mask: 'none', 'one', 'opp', 'face', 'red', or None (no pattern)."""
    s = tuple(i for i in range(6) if mask[i])
    if not s:
        return "none"
    if len(s) == 6:
        return "red"
    if len(s) == 1:
        return "one"
    if len(s) == 2 and s in OPP:
        return "opp"
    if len(s) == 3 and s in FACE_EDGES:
        return "face"
    return None


def green_children(v, mid, pat, mask):
    """Children of tet v under pattern pat; mid[(a, b)] the midpoint of LOCAL edge a-b (a < b) where marked."""
    if pat == "none":
        return [tuple(v)]
    if pat == "red":
        return children(v, mid)
    s = [i for i in range(6) if mask[i]]
    if pat == "one":
        a, b = EDGES[s[0]]
        c, d = [k for k in range(4) if k not in (a, b)]
        m = mid[(a, b)]
        return [(v[a], m, v[c], v[d]), (m, v[b], v[c], v[d])]
    if pat == "opp":
        (a, b), (c, d) = EDGES[s[0]], EDGES[s[1]]
        m, n = mid[(a, b)], mid[(c, d)]
        return [(v[a], m, v[c], n), (v[a], m, n, v[d]), (m, v[b], v[c], n), (m, v[b], n, v[d])]
    if pat == "face":
        k = [q for q in range(4) if FACE_EDGES[q] == tuple(s)][0]          # the apex: the vertex off the face
        a, b, c = [q for q in range(4) if q != k]
        mab, mac, mbc = mid[(a, b)], mid[(a, c)], mid[(b, c)]
        return [(v[a], mab, mac, v[k]), (mab, v[b], mbc, v[k]), (mac, mbc, v[c], v[k]), (mab, mbc, mac, v[k])]
    raise ValueError(f"no closure pattern {pat}")


def _pairs(f):
    return itertools.combinations(sorted(f), 2)


def _face_counts(tets):
    cnt = {}
    for t in tets:
        for k in range(4):
            key = frozenset(t[q] for q in range(4) if q != k)
            cnt[key] = cnt.get(key, 0) + 1
    return cnt


def _deck_traction(deck, subcase):
    """(nodal traction, F, M, loaded faces as grid triples, residual): from deck["traction"] when the deck is itself a
    refined one (a second level), else read off the RBE3 (coarse_traction)."""
    trc = deck.get("traction")
    if trc is None:
        return coarse_traction(deck, subcase)
    nodal = dict(trc["nodal"])
    cnt = _face_counts(deck["tets"])
    loaded = [tuple(sorted(key)) for key, c in cnt.items() if c == 1 and all(n in nodal for n in key)]
    return (nodal, tuple(trc["F"]), tuple(trc["M"]), loaded,
            (deck.get("refined_from") or {}).get("traction_residual", 0.0))


def graded_refine(deck, marked, subcase=1, fix_mixed=True, planted=None):
    """Local red-green refinement: marked (bool per tet of deck) split red, the rest closed green. Works on a coarse
    deck or on one this module refined ("parent" then maps to the ORIGINAL coarse tets).
    A GREEN TET IS NEVER REFINED (2026-11-11): on a deck this function made, every green family is first replaced by
    its parent (un-greening), the marks pass to the parent, and the closure runs on the red leaves; see the block
    comment above. planted (tests only): "no_closure" — red on the marked tets and NOTHING else (hanging nodes on the
    transition); "green_on_green" — no un-greening, the green tets are refined like any other (the fault itself)."""
    g = deck["grids"]
    dec = {n: tuple(TF._nas(c) for c in g[n]) for n in g}
    nodal, Fv, Mv, loaded_faces, res = _deck_traction(deck, subcase)
    tets_in = [tuple(t) for t in deck["tets"]]
    par_in = deck.get("parent") or list(range(len(tets_in)))
    # BEY'S VERTEX ORDER is kept beside the oriented tets (deck["bey"]): the red rule cuts the octahedron along
    # m02 - m13 of THAT order, and his bound on the shapes holds only if the children are refined in the order the
    # rule gave them. The first version refined the ORIENTED children (first two vertices swapped where the sign
    # flipped). MEASURED, the worst quality over 5 red levels: a Kuhn tet 0.2722 -> 0.2722, 0.1265, 0.0962, 0.0388
    # with the swap, 0.2722 at every level without; a random tet 0.0318 -> 0.0016 with, 0.0318 without.
    bey_in = [tuple(t) for t in deck["bey"]] if (deck.get("bey") and planted != "green_on_green") else tets_in
    Xc = {n: np.array([float(c) for c in dec[n]]) for n in dec}
    sgn = [np.sign(_det(np.array([Xc[n] for n in t]))) for t in tets_in]
    edges = lambda t: [frozenset((t[a], t[b])) for a, b in EDGES]
    faces = lambda t: [frozenset(t[q] for q in range(4) if q != k) for k in range(4)]
    LF = {frozenset(f) for f in loaded_faces}                 # loaded faces of the current leaves
    mid, new_mids = {}, []                                    # edge -> midpoint node; the ones made here, in order
    gin = deck.get("green") if planted != "green_on_green" else None
    if gin:
        mid = {frozenset(e): m for e, m in gin["mids"]}
        fam_mark, fam_par, fam_faces = [False] * len(gin["parents"]), [None] * len(gin["parents"]), {}
        leaves, lpar, lmark = [], [], []
        for i, t in enumerate(tets_in):
            f = gin["of"][i]
            if f < 0:
                leaves.append(bey_in[i]), lpar.append((par_in[i], sgn[i])), lmark.append(bool(marked[i]))
            else:
                fam_mark[f] = fam_mark[f] or bool(marked[i])
                fam_par[f] = (par_in[i], sgn[i])
                fam_faces.setdefault(f, []).extend(faces(t))
        for f, p in enumerate(gin["parents"]):
            p = tuple(p)
            leaves.append(p), lpar.append(fam_par[f]), lmark.append(fam_mark[f])
            for ph in faces(p):                               # a parent face is loaded when a child face in it is
                on = set(ph) | {mid[e] for e in (frozenset(c) for c in _pairs(ph)) if e in mid}
                if any(cf <= on and cf in LF for cf in fam_faces[f]):
                    LF.add(ph)
    else:
        leaves, lpar, lmark = list(bey_in), list(zip(par_in, sgn)), [bool(x) for x in marked]
    LE = {frozenset(c) for f in LF for c in _pairs(f)}
    grids = dict(g)
    Xf = Xc
    tr = dict(nodal)
    nid = [max(g) + 1]

    def emark(e):
        """Give edge e a midpoint node (once). On a loaded face the midpoint carries the mean traction (t is linear)."""
        if e in mid:
            return False
        a, b = sorted(e)
        m = nid[0]
        nid[0] += 1
        mid[e] = m
        dec[m] = tuple((x + y) / 2 for x, y in zip(dec[a], dec[b]))
        grids[m] = tuple(dec_str(x) for x in dec[m])
        Xf[m] = np.array([float(x) for x in dec[m]])
        new_mids.append(e)
        if e in LE:
            tr[m] = tuple((x + y) / 2 for x, y in zip(tr[a], tr[b]))
            LE.update((frozenset((a, m)), frozenset((m, b))))
        return True

    def oriented(c, s0):
        return c if np.sign(_det(np.array([Xf[n] for n in c]))) == s0 else (c[1], c[0], c[2], c[3])

    def split_red(t):
        E = edges(t)
        loc = {(a, b): mid[E[j]] for j, (a, b) in enumerate(EDGES)}
        out = children(t, loc)                                # in Bey's order, NOT re-oriented
        for ph in faces(t):                                   # the 4 red triangles of a loaded face are loaded
            if ph in LF:
                a, b, c = sorted(ph)
                mab, mac, mbc = mid[frozenset((a, b))], mid[frozenset((a, c))], mid[frozenset((b, c))]
                for sub in ((a, mab, mac), (mab, b, mbc), (mac, mbc, c), (mab, mbc, mac)):
                    LF.add(frozenset(sub))
                    LE.update(frozenset(c2) for c2 in _pairs(sub))
        return out

    rounds, nred = 0, 0
    if planted == "no_closure":
        nxt, nxp = [], []
        for t, p, mkd in zip(leaves, lpar, lmark):
            if mkd:
                for e in edges(t):
                    emark(e)
                kids = split_red(t)
                nred += 1
                nxt.extend(kids), nxp.extend([p] * 8)
            else:
                nxt.append(t), nxp.append(p)
        leaves, lpar = nxt, nxp
    else:
        for t, mkd in zip(leaves, lmark):
            if mkd:
                for e in edges(t):
                    emark(e)
        while True:
            rounds += 1
            changed = False
            nxt, nxp = [], []
            for t, p in zip(leaves, lpar):
                E = edges(t)
                m = [e in mid for e in E]
                if not any(m):
                    nxt.append(t), nxp.append(p)
                    continue
                for fe in FACE_EDGES:
                    if sum(m[j] for j in fe) == 2:
                        for j in fe:
                            if not m[j]:
                                emark(E[j])
                                m[j] = True
                                changed = True
                pat = pattern(m)
                if pat is not None and pat != "red":
                    # a green tet whose children would have a split edge of their own (a neighbour two levels finer)
                    loc = {(a, b): mid[E[j]] for j, (a, b) in enumerate(EDGES) if m[j]}
                    own = set(E)
                    if any(ce in mid for c in green_children(t, loc, pat, m) for ce in edges(c) if ce not in own):
                        pat = None
                if pat is None:
                    for e in E:
                        emark(e)
                    pat = "red"
                if pat == "red":
                    nxt.extend(split_red(t)), nxp.extend([p] * 8)
                    nred += 1
                    changed = True
                else:
                    nxt.append(t), nxp.append(p)
            leaves, lpar = nxt, nxp
            if not changed:
                break
    # emit: an unsplit leaf as it is, a green leaf as its children — the family is recorded for the next un-greening
    tets, bey, parent, gof, gpar, gmids, pats = [], [], [], [], [], {}, {"red": nred}
    for t, (p, s0) in zip(leaves, lpar):
        E = edges(t)
        m = [e in mid for e in E]
        pat = "none" if planted == "no_closure" else pattern(m)
        pats[pat] = pats.get(pat, 0) + 1
        if pat == "none":
            tets.append(oriented(t, s0)), bey.append(t), parent.append(p), gof.append(-1)
            continue
        loc = {(a, b): mid[E[j]] for j, (a, b) in enumerate(EDGES) if m[j]}
        for c in green_children(t, loc, pat, m):
            tets.append(oriented(c, s0)), bey.append(c), parent.append(p), gof.append(len(gpar))
        gpar.append(t)
        for j in range(6):
            if m[j]:
                gmids[tuple(sorted(E[j]))] = mid[E[j]]
    # supports: a midpoint between two dependents of one RBE2 joins it (as red_refine); in creation order, so that a
    # midpoint of a midpoint sees its ends already placed
    rbe2 = [(ind, list(deps)) for ind, deps in deck["rbe2"]]
    spc_dep, owner_of = set(), {}
    for k, (ind, deps) in enumerate(deck["rbe2"]):
        if deck["spc"].get(ind, "").startswith("123"):
            spc_dep |= set(deps)
        for n in deps:
            owner_of.setdefault(n, k)
    depsets = [set(deps) for ind, deps in deck["rbe2"]]
    mixed = 0
    for e in new_mids:
        a, b = tuple(e)
        m = mid[e]
        same = [k for k, s in enumerate(depsets) if a in s and b in s]
        k = same[0] if same else (owner_of[a] if fix_mixed and a in spc_dep and b in spc_dep else None)
        if k is None:
            continue
        mixed += 0 if same else 1
        rbe2[k][1].append(m)
        depsets[k].add(m)
        owner_of.setdefault(m, k)
        if deck["spc"].get(deck["rbe2"][k][0], "").startswith("123"):
            spc_dep.add(m)
    rf_in = deck.get("refined_from") or {}
    out = dict(grids=grids, tets=tets, rbe2=rbe2, rbe3=deck["rbe3"], spc=deck["spc"], force=deck["force"],
               moment=deck["moment"], mat=deck["mat"], subcases=deck["subcases"],
               traction={"subcase": subcase, "F": Fv, "M": Mv, "nodal": tr}, parent=parent, bey=bey,
               green={"of": gof, "parents": gpar, "mids": sorted(gmids.items())})
    out["refined_from"] = {"tets": rf_in.get("tets", len(tets_in)), "grids": rf_in.get("grids", len(g)),
                           "mixed_fixed_midpoints": mixed, "traction_residual": res, "graded": True,
                           "closure_rounds": rounds, "patterns": pats, "marked": int(np.sum(marked)),
                           "level_from_tets": len(tets_in)}
    for k in ("deck", "sha256"):
        if k in rf_in:
            out["refined_from"][k] = rf_in[k]
    return out


def conformity(deck):
    """Combinatorial check -> (faces shared by > 2 tets, HANGING edges). An edge hangs when its midpoint is a node of the
    mesh while the edge itself is still an edge of some tet (a neighbour split it, this tet did not)."""
    cnt = _face_counts(deck["tets"])
    used = set()
    for t in deck["tets"]:
        for a, b in EDGES:
            used.add(frozenset((t[a], t[b])))
    over = sum(1 for v in cnt.values() if v > 2)
    g = deck["grids"]
    dec = {n: tuple(TF._nas(c) for c in g[n]) for n in g}
    pos = {v: n for n, v in dec.items()}
    hanging = 0
    for e in used:
        a, b = tuple(e)
        if tuple((x + y) / 2 for x, y in zip(dec[a], dec[b])) in pos:
            hanging += 1
    return over, hanging


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
