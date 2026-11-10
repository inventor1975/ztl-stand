# -*- coding: utf-8 -*-
"""
cadmesh — what a CAD part's surface mesh PROVES about the part (2026-11-10, CAD/FEA level 1).

    python3 -m ustand.cadmesh part.obj|part.stl [--density LO:HI] [--mass-max M] [--mass-min M] [--json]

Reads OBJ (v / f) or STL (ASCII or binary) with THIS code — no foreign geometry library (the curator's rule 18.10:
foreign solvers are competitors, not components). Every coordinate is read EXACTLY: a decimal in the text as written
(OBJ, ASCII STL), a binary32 in a binary STL as its exact value; all coordinates are put over one common power-of-ten
or power-of-two denominator, so every computation below is integer arithmetic.

PROVED, exactly:
  * TOPOLOGY. Closed: every undirected edge belongs to exactly two faces. Oriented: every directed edge occurs once (the
    two faces of an edge traverse it in opposite directions). No degenerate face (three distinct vertices, nonzero
    cross product). Connected components; Euler characteristic chi = V - E + F; for a closed oriented connected
    surface the genus g = (2 - chi) / 2. A failure is named (the edges, the faces), not smoothed over.
  * VOLUME, exactly: V = (1/6) sum over faces of det(v0, v1, v2) — the divergence theorem, valid for a closed
    oriented surface that does NOT INTERSECT ITSELF — checked: every pair of faces that share no vertex and whose boxes
    meet is tested with exact integer orientation predicates (a fold between faces that share an edge is not caught —
    said). The sign says the orientation (outward normals give V > 0).
  * BOUNDING BOX, exactly.
  * SURFACE AREA, a proved bracket: sum of |cross| / 2, each |cross| = sqrt(an integer) enclosed by isqrt below and
    above.
WHAT IT IS NOT: the part itself. A mesh is the CAD's triangulation of it (a faceting error the file does not
state) — so every number here is a property of THIS MESH, of THIS FILE; its sha256 is in the report, and a verdict
on it holds IF the file is the revision named (ZTL's EARNED IF STABLE: one revision at every reading).

REQUIREMENTS (mass): mass = V x density, density a range (a datasheet's word: ON CREDIT unless earned) — judged by
ZTL's numeric judge (znumjudge), the volume as an EARNED exact quantity of this mesh.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
from fractions import Fraction as Fr


# ------------------------------------------------------------------------------------------------ reading
def _dec(s):
    """A decimal string -> (integer mantissa, decimal exponent) exactly: '56.50188' -> (5650188, -5)."""
    s = s.strip()
    m = s.lower().split("e")
    base, ex = m[0], int(m[1]) if len(m) > 1 else 0
    neg = base.startswith("-")
    base = base.lstrip("+-")
    if "." in base:
        a, b = base.split(".")
        mant, ex = int((a or "0") + b), ex - len(b)
    else:
        mant = int(base)
    return (-mant if neg else mant), ex


def _from_decimals(rows):
    """rows of decimal strings -> integer coordinates over one denominator 10^k: (ints, k)."""
    parsed = [[_dec(x) for x in r] for r in rows]
    k = max((-e for r in parsed for _, e in r), default=0)
    k = max(k, 0)
    return [tuple(m * 10 ** (k + e) for m, e in r) for r in parsed], Fr(1, 10 ** k)


def read_obj(path):
    verts, faces = [], []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                verts.append(line.split()[1:4])
            elif line.startswith("f "):
                idx = [int(t.split("/")[0]) for t in line.split()[1:]]
                idx = [i - 1 if i > 0 else len(verts) + i for i in idx]
                for j in range(1, len(idx) - 1):          # a polygon fanned into triangles
                    faces.append((idx[0], idx[j], idx[j + 1]))
    ints, unit = _from_decimals(verts)
    return ints, faces, unit


def _weld(points):
    """STL lists each triangle's corners: identical coordinates are one vertex (exact equality, no tolerance)."""
    index, verts, faces = {}, [], []
    for tri in points:
        f = []
        for p in tri:
            if p not in index:
                index[p] = len(verts)
                verts.append(p)
            f.append(index[p])
        faces.append(tuple(f))
    return verts, faces


def read_stl(path):
    raw = open(path, "rb").read()
    if len(raw) >= 84:
        n = struct.unpack("<I", raw[80:84])[0]
        if 84 + 50 * n == len(raw):                       # binary
            tris = []
            for i in range(n):
                vals = struct.unpack("<12f", raw[84 + 50 * i: 84 + 50 * i + 48])
                tris.append([vals[3:6], vals[6:9], vals[9:12]])
            # binary32 values exactly: each is m * 2^e; one common power of two
            frs = [[Fr(x) for x in p] for t in tris for p in t]
            den = 1
            for p in frs:
                for x in p:
                    den = max(den, x.denominator)
            pts = [tuple(int(x * den) for x in p) for p in frs]
            verts, faces = _weld([pts[3 * i:3 * i + 3] for i in range(n)])
            return verts, faces, Fr(1, den)
    text = raw.decode("utf-8", errors="replace").split()
    rows = [text[i + 1:i + 4] for i, t in enumerate(text) if t == "vertex"]
    ints, unit = _from_decimals(rows)
    verts, faces = _weld([ints[3 * i:3 * i + 3] for i in range(len(ints) // 3)])
    return verts, faces, unit


def read(path):
    return read_obj(path) if path.lower().endswith(".obj") else read_stl(path)


# ------------------------------------------------------------------------------------------------ what it proves
def _cross(a, b, c):
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    w = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    return (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])


def analyse(verts, faces, unit):
    out = {}
    used = sorted({i for f in faces for i in f})
    # topology
    directed, undirected = {}, {}
    degenerate = []
    for fi, (a, b, c) in enumerate(faces):
        if len({a, b, c}) < 3 or _cross(verts[a], verts[b], verts[c]) == (0, 0, 0):
            degenerate.append(fi)
        for e in ((a, b), (b, c), (c, a)):
            directed[e] = directed.get(e, 0) + 1
            k = (min(e), max(e))
            undirected[k] = undirected.get(k, 0) + 1
    open_edges = [e for e, n in undirected.items() if n == 1]
    nonmanifold = [e for e, n in undirected.items() if n > 2]
    flipped = [e for e, n in directed.items() if n > 1]
    closed = not open_edges and not nonmanifold
    oriented = closed and not flipped
    # components (union-find over faces sharing a vertex)
    parent = list(range(len(verts)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b, c in faces:
        for x, y in ((a, b), (b, c)):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry
    comps = len({find(i) for i in used})
    chi = len(used) - len(undirected) + len(faces)
    out["topology"] = {
        "vertices": len(used), "edges": len(undirected), "faces": len(faces), "components": comps,
        "euler_characteristic": chi, "closed": closed, "oriented": oriented,
        "degenerate_faces": len(degenerate), "open_edges": len(open_edges), "nonmanifold_edges": len(nonmanifold),
        "doubly_traversed_edges": len(flipped),
        "genus": ((2 * comps - chi) // 2 if (2 * comps - chi) % 2 == 0 else None) if oriented else None,
        "genus_note": "for a closed oriented surface: g = (2 c - chi) / 2 summed over its c components",
    }
    # bounding box, exact
    lo = [min(verts[i][k] for i in used) for k in range(3)]
    hi = [max(verts[i][k] for i in used) for k in range(3)]
    out["bounding_box"] = {"min": [str(x * unit) for x in lo], "max": [str(x * unit) for x in hi],
                           "size": [float((h - l) * unit) for l, h in zip(lo, hi)]}
    # volume, exact (integer determinant sum)
    s6 = 0
    for a, b, c in faces:
        p, q, r = verts[a], verts[b], verts[c]
        s6 += (p[0] * (q[1] * r[2] - q[2] * r[1]) - p[1] * (q[0] * r[2] - q[2] * r[0])
               + p[2] * (q[0] * r[1] - q[1] * r[0]))
    vol = Fr(s6, 6) * unit ** 3
    hits, tested = self_intersections(verts, faces) if oriented else ([], 0)
    out["self_intersection"] = {"pairs_found": len(hits), "first": hits[:5], "pairs_tested": tested,
                                "checked": oriented,
                                "not_caught": "a fold between two faces that share an edge or a vertex"}
    out["volume"] = {"exact": f"{vol.numerator}/{vol.denominator}", "value": float(vol),
                     "proved": oriented and not degenerate and not hits,
                     "premise": ("none left but the not_caught case of self_intersection" if oriented and not hits
                                 else "NOT proved: see topology / self_intersection")}
    # surface area, a proved bracket from integer square roots
    alo = ahi = 0
    for a, b, c in faces:
        n = _cross(verts[a], verts[b], verts[c])
        q = n[0] * n[0] + n[1] * n[1] + n[2] * n[2]
        r = math.isqrt(q)
        alo += r
        ahi += r if r * r == q else r + 1
    out["surface_area"] = {"lo": float(Fr(alo, 2) * unit ** 2), "hi": float(Fr(ahi, 2) * unit ** 2),
                           "rounded_outward": True}
    return out, vol


def _o3(a, b, c, d):
    """orient3d, exact: the sign of det(b - a, c - a, d - a)."""
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    w = (d[0] - a[0], d[1] - a[1], d[2] - a[2])
    x = u[0] * (v[1] * w[2] - v[2] * w[1]) - u[1] * (v[0] * w[2] - v[2] * w[0]) + u[2] * (v[0] * w[1] - v[1] * w[0])
    return (x > 0) - (x < 0)


def _o2(a, b, c, i, j):
    x = (b[i] - a[i]) * (c[j] - a[j]) - (b[j] - a[j]) * (c[i] - a[i])
    return (x > 0) - (x < 0)


def _seg_tri(a, b, p, q, r):
    """Does the closed segment ab meet the closed triangle pqr (not coplanar with it)? Exact."""
    sa, sb = _o3(p, q, r, a), _o3(p, q, r, b)
    if sa * sb > 0 or (sa == 0 and sb == 0):
        return False
    s1, s2, s3 = _o3(a, b, p, q), _o3(a, b, q, r), _o3(a, b, r, p)
    return not ((s1 > 0 or s2 > 0 or s3 > 0) and (s1 < 0 or s2 < 0 or s3 < 0))


def _coplanar_meet(P, Q, n):
    """Two coplanar triangles: do they meet? Projected on the plane dropping the normal's largest axis. Exact."""
    k = max(range(3), key=lambda t: abs(n[t]))
    i, j = [t for t in range(3) if t != k]

    def inside(x, T):
        s = [_o2(T[0], T[1], x, i, j), _o2(T[1], T[2], x, i, j), _o2(T[2], T[0], x, i, j)]
        return not ((1 in s) and (-1 in s))

    def segs(a, b, c, d):
        d1, d2 = _o2(a, b, c, i, j), _o2(a, b, d, i, j)
        d3, d4 = _o2(c, d, a, i, j), _o2(c, d, b, i, j)
        if d1 * d2 > 0 or d3 * d4 > 0:
            return False
        if d1 == d2 == 0:                                 # collinear: overlap of the projections
            return all(min(a[t], b[t]) <= max(c[t], d[t]) and min(c[t], d[t]) <= max(a[t], b[t]) for t in (i, j))
        return True
    if any(inside(x, Q) for x in P) or any(inside(x, P) for x in Q):
        return True
    return any(segs(P[a], P[(a + 1) % 3], Q[b], Q[(b + 1) % 3]) for a in range(3) for b in range(3))


def self_intersections(verts, faces, limit=20):
    """Pairs of faces that share NO vertex and meet (cross or touch) — exact integer predicates over a uniform grid of
    the faces' boxes. Faces that share a vertex or an edge are not tested (a fold along a shared edge is not caught —
    said). -> (pairs found, up to `limit`; pairs tested)."""
    n = len(faces)
    boxes = []
    for f in faces:
        P = [verts[x] for x in f]
        boxes.append(([min(p[t] for p in P) for t in range(3)], [max(p[t] for p in P) for t in range(3)]))
    ext = [max(b[1][t] - b[0][t] for b in boxes) or 1 for t in range(3)]
    cell = [e for e in ext]                                 # cell = the largest face extent per axis
    grid = {}
    for fi, (lo, hi) in enumerate(boxes):
        r = [range(lo[t] // cell[t], hi[t] // cell[t] + 1) for t in range(3)]
        for x in r[0]:
            for y in r[1]:
                for z in r[2]:
                    grid.setdefault((x, y, z), []).append(fi)
    found, tested, seen = [], 0, set()
    for bucket in grid.values():
        for ii in range(len(bucket)):
            a = bucket[ii]
            la, ha = boxes[a]
            for b in bucket[ii + 1:]:
                if (a, b) in seen:
                    continue
                lb, hb = boxes[b]
                if any(ha[t] < lb[t] or hb[t] < la[t] for t in range(3)):
                    continue
                seen.add((a, b))
                if set(faces[a]) & set(faces[b]):
                    continue
                tested += 1
                P = [verts[x] for x in faces[a]]
                Q = [verts[x] for x in faces[b]]
                sq = [_o3(P[0], P[1], P[2], q) for q in Q]
                if all(x > 0 for x in sq) or all(x < 0 for x in sq):
                    continue
                if all(x == 0 for x in sq):
                    meet = _coplanar_meet(P, Q, _cross(*P))
                else:
                    meet = any(_seg_tri(P[e], P[(e + 1) % 3], *Q) for e in range(3)) or \
                        any(_seg_tri(Q[e], Q[(e + 1) % 3], *P) for e in range(3))
                if meet:
                    found.append((a, b))
                    if len(found) >= limit:
                        return found, tested
    return found, tested


def judge_mass(vol, density, mass_max=None, mass_min=None):
    """mass = V x density, the volume EARNED (this mesh, exactly), the density a datasheet's range ON CREDIT."""
    sys.path.insert(0, _ztl())
    import znumjudge as ZJ
    lo, hi = density

    def num(x):
        x = Fr(x)
        return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"
    sheet = f"vol=[{num(vol)},{num(vol)}] earned, rho=[{num(Fr(str(lo)))},{num(Fr(str(hi)))}] credit"
    qs = ZJ.parse_quantities(sheet)[0]
    out = {}
    for name, claim in (("mass_max", f"vol*rho <= {num(Fr(str(mass_max)))}" if mass_max is not None else None),
                        ("mass_min", f"vol*rho >= {num(Fr(str(mass_min)))}" if mass_min is not None else None)):
        if claim:
            r = ZJ.judge_sheet_claim(claim, dict(qs), {})
            # a verdict riding the density's credit stays ON CREDIT whatever its value (the kernel's provenance cap);
            # its DIRECTION is `polarity` (toward T / toward F) and `next_check` says what would earn it
            out[name] = {"claim": claim, "disposition": r["disposition"], "polarity": r.get("polarity"),
                         "next_check": r.get("next_check"), "why": r.get("why")}
    out["mass_range"] = [float(vol * Fr(str(lo))), float(vol * Fr(str(hi)))]
    return out


def _ztl():
    import os
    return os.environ.get("USTAND_ZTL") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "ZTL")


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="ustand.cadmesh")
    ap.add_argument("mesh")
    ap.add_argument("--density", help="LO:HI in the file's mass/length^3 unit")
    ap.add_argument("--mass-max", type=float)
    ap.add_argument("--mass-min", type=float)
    a = ap.parse_args(argv)
    sha = hashlib.sha256(open(a.mesh, "rb").read()).hexdigest()
    verts, faces, unit = read(a.mesh)
    rep, vol = analyse(verts, faces, unit)
    rep = {"file": a.mesh, "sha256": sha, **rep,
           "rests_on": f"this file (sha256 {sha[:16]}…): every number is of THIS mesh — EARNED IF STABLE on the revision"}
    if a.density:
        lo, hi = (float(x) for x in a.density.split(":"))
        if rep["volume"]["proved"]:
            rep["mass"] = judge_mass(vol, (lo, hi), a.mass_max, a.mass_min)
        else:
            rep["mass"] = {"refused": "the volume is not proved: the surface is not closed and oriented (see topology)"}
    print(json.dumps(rep, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
