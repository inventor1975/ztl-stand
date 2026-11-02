"""frame3d — SPACE FRAMES (the stand's 3D phase, track 2, version 1, 2026-11-02): ANSYS-style BEAM4 decks, every
displacement as a PROVED range for every modulus in the tolerance box (first order), judged by ZTL zenergy — the 2D
frame's energy path one dimension up.

    python3 -m ustand.frame3d deck.txt --tol 0.5% --target "U(5,Z)" [--le 0.012]

Deck (version 1):
    ET, 1, BEAM4
    MP, EX, 1, 210e9          MP, PRXY, 1, 0.3          (G = E / (2 (1 + nu)))
    R, id, AREA, IZZ, IYY, TKZ, TKY, THETA, ISTRN, IXX   (IXX = the torsion constant J; THETA 0 or 90 only)
    MAT, id    REAL, id   (the current material and section for the E lines that follow)
    N, id, x, y, z            E, i, j
    D, n, UX|UY|UZ|ROTX|ROTY|ROTZ|ALL, 0                 F, n, FX|FY|FZ|MX|MY|MZ, value
LOCAL AXES (stated, as ANSYS BEAM4 with THETA = 0): x' from I to J; y' horizontal (parallel to the global XY plane),
y' = e_Z x x' normalised, for a non-vertical member; y' = global Y for a vertical member; z' = x' x y'. THETA = 90
swaps the roles (y' -> z', z' -> -y'). IZZ is the second moment for bending in the x'-y' plane (about z'), IYY in
the x'-z' plane.
THE ENERGY (Euler-Bernoulli + Saint-Venant torsion, exact for the member): six rank-one terms per element,
    EA/L a^2 + GJ/L t^2 + EI_z/L (b_z^2 + 3 c_z^2) + EI_y/L (b_y^2 + 3 c_y^2),
    a = u'_x,j - u'_x,i;  t = th'_x,j - th'_x,i;  b_z = th'_z,i - th'_z,j;  c_z = th'_z,i + th'_z,j - 2 (v'_j - v'_i)/L;
    b_y = th'_y,i - th'_y,j;  c_y = th'_y,i + th'_y,j + 2 (w'_j - w'_i)/L       (dw'/dx' = -th'_y).
EXACTNESS: L must be rational (as in 2D). The local y', z' carry 1/H with H = sqrt(dx^2 + dy^2) — in the SQUARED
terms only H^2 appears, so the stiffness is exact for any orientation; version 1 also asks H rational (members
along the axes, or with a rational horizontal projection — every building grid), so that every output functional
is exact too, and refuses otherwise.
One part per element (E and G scale together with the modulus factor p in the box).
MATERIALS AND SECTIONS: `MP, EX|PRXY, id, value` and `R, id, ...` define them by id; `MAT, id` and `REAL, id` set the
current pair and every `E` takes it (as ANSYS; default 1).
END RELEASES: `RELEASE, elem, I|J, MY|MZ[, MY|MZ]` — the member's end rotation about that local axis becomes its own
unknown (a hinge for that bending moment; torsion stays connected). MEMBER LOADS: `QLOAD, elem, FX|FY|FZ, q` — a
uniform load per length along a global axis (in the current load case), as consistent nodal loads: the nodal
displacements are exact; member STRESSES and SECOND ORDER with member loads are not yet (they refuse, said).
LOAD CASES: `LC, name` opens a case (F lines before any LC form case BASE); `LCOMB, name, case, factor, ...` builds a
combination; with LCOMB lines the combinations are judged, otherwise the cases. A requirement must hold in EVERY one
(one ZTL conjunction); all share one factorization and one proved lambda_min (ZTL certify_cases).
NOT YET (said): second order and stability in 3D, member stresses / EN checks, member loads, rigid offsets.
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction as F

from . import bricks as B
from .spice import tolerance
from .truss import _num, _sqrt, _show

DIRS = ("X", "Y", "Z", "RX", "RY", "RZ")
_D_OF = {"UX": "X", "UY": "Y", "UZ": "Z", "ROTX": "RX", "ROTY": "RY", "ROTZ": "RZ"}
_F_OF = {"FX": "X", "FY": "Y", "FZ": "Z", "MX": "RX", "MY": "RY", "MZ": "RZ"}


class Frame3DError(B.BrickError):
    pass


from collections import namedtuple   # noqa: E402
Props = namedtuple("Props", "ex nu area izz iyy tkz tky theta ixx")   # one member's material and section


def read_deck(text):
    nodes, elems, supports = {}, [], set()
    cases, combos, cur = {"BASE": {}}, {}, "BASE"
    loads = cases["BASE"]
    releases = {}
    mats, reals, cur_m, cur_r = {}, {}, 1, 1
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.split("!")[0].strip()
        if not line or line.startswith("/"):
            continue
        f = [x.strip() for x in (line.split(",") if "," in line else line.split())]
        cmd, where = f[0].upper(), f"line {ln}"
        if cmd == "N":
            vals = [(_num(f[k], where) if len(f) > k and f[k] else F(0)) for k in (2, 3, 4)]
            nodes[int(f[1])] = tuple(vals)
        elif cmd == "E":
            elems.append((int(f[1]), int(f[2]), cur_m, cur_r))
        elif cmd == "MP":
            prop, mid, v = f[1].upper(), int(f[2]) if f[2] else 1, _num(f[3], where)
            if prop == "EX":
                mats.setdefault(mid, {})["EX"] = v
            elif prop in ("PRXY", "NUXY"):
                mats.setdefault(mid, {})["PRXY"] = v
            else:
                raise Frame3DError(f"{where}: MP {f[1]} — only EX and PRXY are read")
        elif cmd == "R":
            if len(f) < 10:
                raise Frame3DError(f"{where}: R needs AREA, IZZ, IYY, TKZ, TKY, THETA, ISTRN, IXX")
            area, izz, iyy = (_num(f[k], where) for k in (2, 3, 4))
            tkz, tky = (_num(f[k], where) if f[k] else F(0) for k in (5, 6))
            theta = _num(f[7], where) if f[7] else F(0)
            ixx = _num(f[9], where)
            if theta not in (0, 90):
                raise Frame3DError(f"{where}: THETA {theta} — 0 or 90 only (version 1: exact local axes)")
            rid = int(f[1]) if f[1] else 1
            if rid in reals and reals[rid] != (area, izz, iyy, tkz, tky, theta, ixx):
                raise Frame3DError(f"{where}: real constant set {rid} given twice, differently")
            reals[rid] = (area, izz, iyy, tkz, tky, theta, ixx)
        elif cmd == "F":
            d = f[2].upper()
            if d not in _F_OF:
                raise Frame3DError(f"{where}: load {f[2]} — FX FY FZ MX MY MZ only")
            k = (int(f[1]), _F_OF[d])
            loads[k] = loads.get(k, F(0)) + _num(f[3], where)
        elif cmd == "D":
            d = f[2].upper()
            if _num(f[3], where) != 0:
                raise Frame3DError(f"{where}: a prescribed nonzero displacement — not read (version 1)")
            for dd in (_D_OF.values() if d == "ALL" else [_D_OF.get(d)]):
                if dd is None:
                    raise Frame3DError(f"{where}: support {f[2]} — UX UY UZ ROTX ROTY ROTZ ALL only")
                supports.add((int(f[1]), dd))
        elif cmd == "RELEASE":
            k, end = int(f[1]), f[2].upper()
            if end not in ("I", "J"):
                raise Frame3DError(f"{where}: RELEASE, elem, I|J, MY|MZ[, MY|MZ]")
            for comp in f[3:]:
                c_ = comp.strip().upper()
                if c_ not in ("MY", "MZ"):
                    raise Frame3DError(f"{where}: release {comp} — MY or MZ (local bending moments) only")
                releases.setdefault(k, set()).add((end, c_[1]))
        elif cmd == "QLOAD":
            k, d = int(f[1]), f[2].upper()
            if d not in ("FX", "FY", "FZ"):
                raise Frame3DError(f"{where}: QLOAD, elem, FX|FY|FZ, q (per unit length, global direction)")
            key = (("Q", k), d[1])
            loads[key] = loads.get(key, F(0)) + _num(f[3], where)
        elif cmd == "LC":
            cur = f[1].strip()
            if cur in cases and cases[cur]:
                raise Frame3DError(f"{where}: load case {cur} given twice")
            loads = cases.setdefault(cur, {})
        elif cmd == "LCOMB":
            if len(f) < 4 or len(f) % 2:
                raise Frame3DError(f"{where}: LCOMB, name, case, factor[, case, factor ...]")
            combos[f[1].strip()] = [(f[k].strip(), _num(f[k + 1], where)) for k in range(2, len(f), 2)]
        elif cmd == "ET":
            if f[2].upper() not in ("BEAM4", "4"):
                raise Frame3DError(f"{where}: element type {f[2]} — only BEAM4 (3D beam)")
        elif cmd == "MAT":
            cur_m = int(f[1])
        elif cmd == "REAL":
            cur_r = int(f[1])
        elif cmd == "TYPE":
            if len(f) > 1 and f[1] not in ("1", ""):
                raise Frame3DError(f"{where}: TYPE,{f[1]} — one element type (BEAM4) only")
        else:
            raise Frame3DError(f"{where}: {f[0]} — not read (only N E MP R F D ET MAT REAL TYPE LC LCOMB)")
    if not nodes or not elems:
        raise Frame3DError("no nodes or no elements")
    props = {}
    for k, (i, j, m, r) in enumerate(elems, 1):
        for n in (i, j):
            if n not in nodes:
                raise Frame3DError(f"element {i}-{j}: node {n} does not exist")
        if m not in mats or "EX" not in mats[m] or "PRXY" not in mats[m]:
            raise Frame3DError(f"element {k}: material {m} needs MP,EX and MP,PRXY")
        if r not in reals:
            raise Frame3DError(f"element {k}: real constant set {r} is not defined (R, {r}, ...)")
        props[k] = Props(mats[m]["EX"], mats[m]["PRXY"], *reals[r])
    elems = [(i, j) for i, j, _, _ in elems]
    if not cases["BASE"] and len(cases) > 1:
        del cases["BASE"]
    for name, terms in combos.items():
        for c, _ in terms:
            if c not in cases:
                raise Frame3DError(f"LCOMB {name}: no load case {c}")
    judged = {}
    if combos:                                          # the combinations are what is judged
        for name, terms in combos.items():
            tot = {}
            for c, fac in terms:
                for key, v in cases[c].items():
                    tot[key] = tot.get(key, F(0)) + fac * v
            judged[name] = tot
    else:
        judged = cases
    for k in releases:
        if not 1 <= k <= len(elems):
            raise Frame3DError(f"RELEASE on element {k}: no such element")
    return nodes, elems, judged, supports, props


def _releases(text):
    """{elem: {(end, axis)}} from the RELEASE lines (read_deck validates them)."""
    out = {}
    for raw in text.splitlines():
        line = raw.split("!")[0].strip()
        f = [x.strip() for x in (line.split(",") if "," in line else line.split())]
        if f and f[0].upper() == "RELEASE":
            for comp in f[3:]:
                out.setdefault(int(f[1]), set()).add((f[2].upper(), comp.strip().upper()[1]))
    return out


def _has_qload(text):
    return any(raw.split("!")[0].strip().upper().startswith("QLOAD") for raw in text.splitlines())


def _no_axial_qload(text, what):
    """Transverse member loads leave the axial force constant along the member; an AXIAL component makes N vary —
    stability and second-order DISPLACEMENTS take it (G_a/G_b split, 2026-11-02); second-order STRESSES not yet."""
    if not _has_qload(text):
        return
    nodes, elems, loads, supports, props = read_deck(text)
    for c, per in _qloads(text).items():
        for k, q in per.items():
            i, j = elems[k - 1]
            L, xp, yp, zp = _axes(nodes[i], nodes[j], props[k].theta)
            if sum(q[t] * xp[t] for t in range(3)):
                raise Frame3DError(f"{what}: member {k} carries an AXIAL member load (QLOAD along it) — N varies along "
                                   f"the member, not yet in 3D (transverse member loads are in)")


def _no_qload(text, what):
    if _has_qload(text):
        raise Frame3DError(f"{what} with member loads (QLOAD) is not yet in version 1 — displacements are exact with "
                           f"them; member stresses and second order need the interior bounds (the 2D frame has them)")


def _axes(pi, pj, theta):
    """(L, x', H-scaled y', (L H)-scaled z', H): x' = d/L exactly; y' = yh/H, z' = zh/(L H) with yh, zh rational."""
    d = tuple(pj[k] - pi[k] for k in range(3))
    L = _sqrt(sum(c * c for c in d))
    if not L:
        raise Frame3DError("a member's length is irrational or zero — not exact (version 1)")
    xp = tuple(c / L for c in d)
    H2 = d[0] * d[0] + d[1] * d[1]
    if H2 == 0:                                         # vertical: y' = global Y, z' = x' x y'
        yh, H = (F(0), F(1), F(0)), F(1)
        zh = (xp[1] * 0 - xp[2] * 1, xp[2] * 0 - xp[0] * 0, xp[0] * 1 - xp[1] * 0)
        zh = tuple(c * L for c in zh)                   # scaled by L H (H = 1)
    else:
        H = _sqrt(H2)
        if not H:
            raise Frame3DError("a member's horizontal projection has an irrational length — version 1 asks it "
                               "rational (exact output functionals)")
        yh = (-d[1], d[0], F(0))                        # e_Z x d: length H
        zh = (d[1] * yh[2] - d[2] * yh[1], d[2] * yh[0] - d[0] * yh[2], d[0] * yh[1] - d[1] * yh[0])   # d x yh
    yp = tuple(c / H for c in yh)
    zp = tuple(c / (L * H) for c in zh)
    if theta == 90:
        yp, zp = zp, tuple(-c for c in yp)
    return L, xp, yp, zp


def energy_system(text, tol):
    nodes, elems, loads, supports, props = read_deck(text)
    t = F(0) if tol in (None, "0", 0) else tolerance(tol) if isinstance(tol, str) else F(tol)
    releases = _releases(text)
    free = [(n, d) for n in sorted(nodes) for d in DIRS if (n, d) not in supports]
    # a released end: the member's own rotation about that local axis, an unknown of its own (not the node's)
    free += [(("IR", k, end), ax) for k in sorted(releases) for end, ax in sorted(releases[k])]
    dof = {nd: k for k, nd in enumerate(free)}
    parts, emap = [], {}
    for k, (i, j) in enumerate(elems, 1):
        pk = props[k]
        ex, area, izz, iyy, ixx = pk.ex, pk.area, pk.izz, pk.iyy, pk.ixx
        G = ex / (2 * (1 + pk.nu))
        L, xp, yp, zp = _axes(nodes[i], nodes[j], pk.theta)

        def row(pairs):
            g = {}
            for (n, dd), v in pairs:
                if v and (n, dd) in dof:
                    g[dof[(n, dd)]] = g.get(dof[(n, dd)], F(0)) + v
            return g

        def proj(n, axis, rot):                        # local component along `axis` of node n's displacement/rotation
            names = ("RX", "RY", "RZ") if rot else ("X", "Y", "Z")
            return [((n, names[q]), axis[q]) for q in range(3)]

        def rot(n, end, axis, ax):                    # the member end's rotation about local `ax` ("Y" or "Z")
            if (end, ax) in releases.get(k, ()):
                return [((("IR", k, end), ax), F(1))]
            return proj(n, axis, True)

        def neg(lst):
            return [(key, -v) for key, v in lst]

        def sc(lst, s):
            return [(key, s * v) for key, v in lst]
        a = row(proj(j, xp, False) + neg(proj(i, xp, False)))
        tt = row(proj(j, xp, True) + neg(proj(i, xp, True)))
        bz = row(rot(i, "I", zp, "Z") + neg(rot(j, "J", zp, "Z")))
        cz = row(rot(i, "I", zp, "Z") + rot(j, "J", zp, "Z") + sc(proj(j, yp, False), -2 / L) + sc(proj(i, yp, False), 2 / L))
        by = row(rot(i, "I", yp, "Y") + neg(rot(j, "J", yp, "Y")))
        cy = row(rot(i, "I", yp, "Y") + rot(j, "J", yp, "Y") + sc(proj(j, zp, False), 2 / L) + sc(proj(i, zp, False), -2 / L))
        emap[k] = {"part": len(parts), "L": L, "a": a, "t": tt, "bz": bz, "cz": cz, "by": by, "cy": cy, "p": pk,
                   "ij": (i, j), "axes": (xp, yp, zp)}
        parts.append({"t": t, "terms": [(ex * area / L, a), (G * ixx / L, tt), (ex * izz / L, bz),
                                        (3 * ex * izz / L, cz), (ex * iyy / L, by), (3 * ex * iyy / L, cy)]})
    fs = {}
    for name, ld in loads.items():
        f = [F(0)] * len(free)

        def put(key, v):
            if v and key in dof:
                f[dof[key]] += v
        for (n, d), v in ld.items():
            if isinstance(n, tuple) and n[0] == "Q":
                # QLOAD: a uniform load per length along a global axis, its CONSISTENT nodal loads (Hermite: the
                # nodal displacements are exact): the axial part in halves; per bending plane w L/2 at each end and
                # the end moments +-w L^2/12 (about z': +, - at I, J; about y': -, + since dw'/dx' = -th_y)
                k = n[1]
                m = emap[k]
                i, j = m["ij"]
                xp, yp, zp = m["axes"]
                L = m["L"]
                q = [F(0)] * 3
                q["XYZ".index(d)] = v
                for nd in (i, j):
                    for c_, ax in zip(q, "XYZ"):
                        put((nd, ax), c_ * L / 2)
                wy = sum(q[c_] * yp[c_] for c_ in range(3))
                wz = sum(q[c_] * zp[c_] for c_ in range(3))
                for nd, end, sgn in ((i, "I", 1), (j, "J", -1)):
                    mz, my = sgn * wy * L * L / 12, -sgn * wz * L * L / 12
                    for mval, ax_name, axis in ((mz, "Z", zp), (my, "Y", yp)):
                        if (end, ax_name) in releases.get(k, ()):
                            put((("IR", k, end), ax_name), mval)
                        else:
                            for c_, rn in zip(axis, ("RX", "RY", "RZ")):
                                put((nd, rn), mval * c_)
                continue
            put((n, d), v)
        fs[name] = f
    return parts, fs, dof, emap


PHI0 = F(1, 200)        # EN 1993-1-1 5.3.2(3): phi = phi0 alpha_h alpha_m with alpha_h, alpha_m <= 1 -> phi0 bounds it


def with_imperfections(text, phi=PHI0):
    """The deck with EN 1993-1-1 5.3.2(7)'s global sway imperfection as equivalent horizontal forces, in each
    horizontal direction SEPARATELY and both signs: every judged load case / combination c becomes four explicit cases
    c+X, c-X, c+Y, c-Y, each carrying c's loads plus +-phi |V| along X or Y at every node with a vertical load V
    (gravity along Z: the nodal FZ plus each QLOAD FZ's half at either end node). A text transform: every function of
    this module judges the result unchanged (all four in one conjunction)."""
    nodes, elems, loads, supports, props = read_deck(text)
    keep = []
    for raw in text.splitlines():
        head = raw.split("!")[0].strip().split(",")[0].strip().upper()
        if head not in ("F", "QLOAD", "LC", "LCOMB"):
            keep.append(raw)
    out = []
    for c, ld in loads.items():
        vert = {}
        lines = []
        for (n, d), v in sorted(ld.items(), key=str):
            if not v:
                continue
            if isinstance(n, tuple) and n[0] == "Q":
                k = n[1]
                lines.append(f"QLOAD, {k}, F{d}, {v}")
                if d == "Z":
                    i, j = elems[k - 1]
                    pi, pj = nodes[i], nodes[j]
                    L = _sqrt(sum((pj[t] - pi[t]) ** 2 for t in range(3)))
                    for nd in (i, j):
                        vert[nd] = vert.get(nd, F(0)) + v * L / 2
                continue
            name = {"X": "FX", "Y": "FY", "Z": "FZ", "RX": "MX", "RY": "MY", "RZ": "MZ"}[d]
            lines.append(f"F, {n}, {name}, {v}")
            if d == "Z":
                vert[n] = vert.get(n, F(0)) + v
        for ax in ("X", "Y"):
            for sg, tag in ((1, "+"), (-1, "-")):
                out.append(f"LC, {c}{tag}{ax}")
                out += lines
                out += [f"F, {nd}, F{ax}, {sg * phi * abs(V)}" for nd, V in sorted(vert.items()) if V]
    return "\n".join(keep + out) + "\n"


def _target(s):
    s = s.strip().upper()
    if not (s.startswith("U(") and s.endswith(")")):
        raise Frame3DError(f"target {s}: write U(node,X|Y|Z|RX|RY|RZ)")
    n, d = s[2:-1].split(",")
    d = d.strip()
    if d not in DIRS:
        raise Frame3DError(f"target {s}: direction X Y Z RX RY RZ")
    return int(n), d


def ranges(text, tol, target):
    """{case: (lo, hi, nominal)} — a proved range of one displacement for every load case / combination, every
    modulus in the box (first order); all cases share one factor and one proved lambda_min (ZTL certify_cases)."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    parts, fs, dof, _ = energy_system(text, tol)
    nd, d = _target(target)
    names = list(fs)
    if (nd, d) not in dof:
        return {c: (F(0), F(0), F(0)) for c in names}
    e = [F(0)] * len(dof)
    e[dof[(nd, d)]] = F(1)
    rs = ZE.certify_cases(parts, [fs[c] for c in names], [e], len(dof))
    return {c: (r[0]["lo"], r[0]["hi"], r[0]["nominal"]) for c, r in zip(names, rs)}


def range_of(text, tol, target):
    """One load case (or the first): a proved range of one displacement for every modulus in the box."""
    rs = ranges(text, tol, target)
    c, (lo, hi, nom) = next(iter(rs.items()))
    return {"target": target, "case": c, "nominal": _show(nom), "lo": lo, "hi": hi,
            "proved_range": [_show(lo, -1), _show(hi, 1)],
            "note": "FIRST ORDER (version 1): an enclosure for every modulus in the box"}


def judge(text, tol, target, le=None, ge=None):
    """A displacement requirement for EVERY load case / combination, judged by ZTL as one conjunction."""
    from . import judge_ztl as J  # noqa: F401
    from znumjudge import parse_quantities, judge_sheet_claim
    rs = ranges(text, tol, target)
    fr = lambda x: f"{x.numerator}/{x.denominator}"
    qs, atoms = [], []
    for k, (c, (lo, hi, _)) in enumerate(rs.items()):
        qs.append(f"u{k}=[{fr(lo)},{fr(hi)}] earned:frame3d-energy-path")
        if le is not None:
            atoms.append(f"u{k} <= {fr(F(le))}")
        if ge is not None:
            atoms.append(f"u{k} >= {fr(F(ge))}")
    out = {"target": target, "cases": {c: [_show(lo, -1), _show(hi, 1)] for c, (lo, hi, _) in rs.items()},
           "note": "FIRST ORDER (version 1); every load case / combination; one factor and one proved lambda_min"}
    if atoms:
        q, m = parse_quantities(", ".join(qs))
        res = judge_sheet_claim(" & ".join(atoms), q, m)
        out["verdict"] = res["disposition"] + (f" ({res['polarity']})" if res.get("polarity") else "")
        if le is not None or ge is not None:
            bad = [c for c, (lo, hi, _) in rs.items()
                   if (le is not None and lo > F(le)) or (ge is not None and hi < F(ge))]
            out["refuted_in"] = bad
    return out


def fibre_vectors(emap, k, tky, tkz):
    """The 8 corner functionals of element k: (end, (sy, sz), g) with sigma = E p_k (g.u) at the section corner
    y' = sy TKY/2, z' = sz TKZ/2 (a rectangle's corners bound every fibre of a section inside that box):
        sigma = N/A + E/L (b_z +- 3 c_z).u y' - E/L (b_y +- 3 c_y).u z'      (+ at I, - at J; the x'-z' plane's
    curvature is -dth_y/dx — every sign combination of y', z' is checked, so the |sigma| check does not depend on it)."""
    m = emap[k]
    L = m["L"]
    out = []
    for end, sb in (("I", 1), ("J", -1)):
        for sy in (1, -1):
            for sz in (1, -1):
                g = {}
                def add(vec, c):
                    for i, v in vec.items():
                        g[i] = g.get(i, F(0)) + c * v
                add(m["a"], 1 / L)
                add(m["bz"], sy * (tky / 2) / L)
                add(m["cz"], sy * (tky / 2) / L * 3 * sb)
                add(m["by"], -sz * (tkz / 2) / L)
                add(m["cy"], -sz * (tkz / 2) / L * 3 * sb)
                out.append((end, (sy, sz), {i: v for i, v in g.items() if v}))
    return out


def stresses(text, tol, ks=None):
    """{case: {k: (lo, hi) of the largest |sigma| over the 8 corners}} — proved, every modulus in the box, every load
    case (first order). sigma = E p_k (g.u): an output scaled by the element's own modulus factor (ZTL)."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    if _has_qload(text):
        return _stresses_q(text, tol, ks)
    parts, fs, dof, emap = energy_system(text, tol)
    ks = sorted(emap) if ks is None else ks
    es, idx = [], []
    for k in ks:
        pk = emap[k]["p"]
        if not pk.tky or not pk.tkz:
            raise Frame3DError(f"member {k}: stresses need TKY and TKZ (the section's depths along y' and z')")
        for end, corner, g in fibre_vectors(emap, k, pk.tky, pk.tkz):
            e = [F(0)] * len(dof)
            for i, v in g.items():
                e[i] = v
            es.append(e)
            idx.append(k)
    names = list(fs)
    scale = [emap[k]["part"] for k in idx]
    rs = ZE.certify_cases(parts, [fs[c] for c in names], es, len(dof), scale=scale)
    out = {}
    for c, rc in zip(names, rs):
        per = {}
        for k, r in zip(idx, rc):
            lo, hi = emap[k]["p"].ex * r["lo"], emap[k]["p"].ex * r["hi"]
            mx_hi = max(abs(lo), abs(hi))
            mx_lo = F(0) if lo <= 0 <= hi else min(abs(lo), abs(hi))
            a, b = per.get(k, (F(0), F(0)))
            per[k] = (max(a, mx_lo), max(b, mx_hi))
        out[c] = per
    return out


def _qloads(text):
    """{case: {elem: (q_x, q_y, q_z)}} — the uniform member loads of every judged case / combination."""
    nodes, elems, loads, supports, props = read_deck(text)
    out = {}
    for c, ld in loads.items():
        per = {}
        for (n, d), v in ld.items():
            if isinstance(n, tuple) and n[0] == "Q":
                q = list(per.get(n[1], (F(0), F(0), F(0))))
                q["XYZ".index(d)] += v
                per[n[1]] = tuple(q)
        out[c] = per
    return out


def _stresses_q(text, tol, ks=None):
    """Member stresses WITH uniform member loads (first order): the member's true moment is the Hermite part (linear
    between the end moments M = E p (I/L)(b +- 3c).u) plus the clamped-clamped beam's own moment under the load, whose
    size never exceeds |w| L^2/12; so per plane max |M| <= max |M_end| + |w| L^2/12 and, at the ends,
    |M| >= |M_end| - |w| L^2/12 (no sign convention needed); the axial force |N(x)| <= |N_FE| + |q_axial| L/2. The
    corner bound |N|/A + M_z,max (TKY/2)/I_z + M_y,max (TKZ/2)/I_y (planes' maxima added: safe)."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    parts, fs, dof, emap = energy_system(text, tol)
    qs = _qloads(text)
    ks = sorted(emap) if ks is None else ks
    n = len(dof)
    es, items, scale = [], [], []
    for k in ks:
        m = emap[k]
        pk, L = m["p"], m["L"]
        if not pk.tky or not pk.tkz:
            raise Frame3DError(f"member {k}: stresses need TKY and TKZ")
        def vec(g):
            e = [F(0)] * n
            for i_, v in g.items():
                e[i_] = v
            return e
        es.append(vec({i_: pk.area / L * v for i_, v in m["a"].items()})); items.append((k, "N")); scale.append(m["part"])
        for plane, (bb, cc, I) in (("y", ("bz", "cz", pk.izz)), ("z", ("by", "cy", pk.iyy))):
            for end, sb in (("I", 1), ("J", -1)):
                g = {}
                for i_, v in m[bb].items():
                    g[i_] = g.get(i_, F(0)) + I / L * v
                for i_, v in m[cc].items():
                    g[i_] = g.get(i_, F(0)) + I / L * 3 * sb * v
                es.append(vec(g)); items.append((k, plane + end)); scale.append(m["part"])
    names = list(fs)
    rs = ZE.certify_cases(parts, [fs[c] for c in names], es, n, scale=scale)
    out = {}
    for c, rc in zip(names, rs):
        rng = {}
        for (k, what), r in zip(items, rc):
            ex = emap[k]["p"].ex
            rng[(k, what)] = (ex * r["lo"], ex * r["hi"])
        per = {}
        for k in ks:
            m = emap[k]
            pk, L = m["p"], m["L"]
            xp, yp, zp = m["axes"]
            q = qs[c].get(k, (F(0), F(0), F(0)))
            qa = abs(sum(q[t] * xp[t] for t in range(3)))
            wy = abs(sum(q[t] * yp[t] for t in range(3)))
            wz = abs(sum(q[t] * zp[t] for t in range(3)))
            Nl, Nh = rng[(k, "N")]
            nmax = max(abs(Nl), abs(Nh)) + qa * L / 2
            mx, mlo = {}, {}
            for plane, w in (("y", wy), ("z", wz)):
                ends = [rng[(k, plane + e)] for e in ("I", "J")]
                mend = max(max(abs(a), abs(b)) for a, b in ends)
                mx[plane] = mend + w * L * L / 12
                mlo[plane] = max(max(F(0), min(abs(a), abs(b)) if not (a <= 0 <= b) else F(0)) for a, b in ends) \
                    - w * L * L / 12
            hi = nmax / pk.area + mx["y"] * (pk.tky / 2) / pk.izz + mx["z"] * (pk.tkz / 2) / pk.iyy
            # a proved lower bound of max |sigma|: one plane's end moment alone, the other plane and N ignored
            # would not bound the corner; keep it simple and safe: the larger single-plane bending stress minus |N|/A
            nmin = F(0) if Nl <= 0 <= Nh else min(abs(Nl), abs(Nh))
            lo = max(F(0), max(mlo["y"] * (pk.tky / 2) / pk.izz, mlo["z"] * (pk.tkz / 2) / pk.iyy) - nmax / pk.area,
                     nmin / pk.area - qa * L / 2 / pk.area if nmin else F(0))
            per[k] = (lo, hi)
        out[c] = per
    return out


def judge_stress(text, tol, fy, gamma_m0=F(1), ks=None):
    """|sigma| <= fy / gamma_M0 at every corner of every checked member in every load case — EN 1993-1-1 6.2.1(7)'s
    elastic check (first order, version 1: no buckling, no shear/torsion stress). Judged by ZTL as one conjunction."""
    from . import judge_ztl  # noqa: F401
    from znumjudge import parse_quantities, judge_sheet_claim
    st = stresses(text, tol, ks)
    lim = F(fy) / F(gamma_m0)
    fr = lambda x: f"{x.numerator}/{x.denominator}"
    qs, atoms, worst = [], [], (None, None, F(0))
    for c, per in st.items():
        for k, (lo, hi) in per.items():
            nm = f"s{len(qs)}"
            qs.append(f"{nm}=[{fr(lo)},{fr(hi)}] earned:frame3d-energy-path")
            atoms.append(f"{nm} <= {fr(lim)}")
            if hi > worst[2]:
                worst = (c, k, hi)
    q, m = parse_quantities(", ".join(qs))
    res = judge_sheet_claim(" & ".join(atoms), q, m)
    return {"verdict": res["disposition"] + (f" ({res['polarity']})" if res.get("polarity") else ""),
            "limit": _show(lim), "worst": {"case": worst[0], "element": worst[1], "max_abs_sigma_upper": _show(worst[2], 1)},
            "note": "FIRST ORDER elastic check |sigma| <= fy/gamma_M0 at the 8 section corners of every member, every "
                    "load case; NOT here: buckling, shear and torsion stresses, second order"}


def _form3(i, j, vax, rax, rsign, dof, M4):
    """A local 4 x 4 form over (v_i, r_i, v_j, r_j) on the global DOFs (lower triangle): v_n = vax . u_n,
    r_n = rsign * rax . th_n."""
    def comp(n, ax, rot, sg):
        names = ("RX", "RY", "RZ") if rot else ("X", "Y", "Z")
        return [((n, names[q]), sg * ax[q]) for q in range(3) if ax[q]]
    loc = [comp(i, vax, False, 1), comp(i, rax, True, rsign), comp(j, vax, False, 1), comp(j, rax, True, rsign)]
    out = {}
    for a in range(4):
        for b in range(4):
            if not M4[a][b]:
                continue
            for (na, va) in loc[a]:
                for (nb, vb) in loc[b]:
                    if na in dof and nb in dof:
                        key = (dof[na], dof[nb])
                        if key[0] >= key[1]:
                            out[key] = out.get(key, F(0)) + M4[a][b] * va * vb
    return out


def _axial_ranges(text, c, parts, fs, dof, emap, nodes, elems, props):
    """Every member's proved axial-force range in load case c (first order, the box's moduli): (Nlo, Nhi, Nnom,
    Nnodes_lo, qax). AXIAL member loads (2026-11-02): N(x) = N_mean + a (L/2 - x), a = q . x', the range widened by
    |a| L/2 (Nnodes_lo: the mean's lower end; qax[k] = a L/2)."""
    import zenergy as ZE
    n = len(dof)
    ks = [k for k in emap if emap[k]["a"]]
    rs = ZE.certify_many(parts, fs[c], [dict(emap[k]["a"]) for k in ks], n, scale=[emap[k]["part"] for k in ks])
    Nlo, Nhi, Nnom = {}, {}, {}
    for k, r in zip(ks, rs):
        fac = props[k].ex * props[k].area / emap[k]["L"]
        Nlo[k] = min(fac * r["lo"], fac * r["hi"])
        Nhi[k] = max(fac * r["lo"], fac * r["hi"])
        Nnom[k] = fac * r["nominal"]
    Nnodes_lo, qax = dict(Nlo), {}
    for k, q in _qloads(text).get(c, {}).items():
        i, j = elems[k - 1]
        L, xp, yp, zp = _axes(nodes[i], nodes[j], props[k].theta)
        a_ = sum(q[t] * xp[t] for t in range(3))
        if a_:
            qax[k] = a_ * L / 2
            Nlo[k] = Nlo.get(k, F(0)) - abs(qax[k])
            Nhi[k] = Nhi.get(k, F(0)) + abs(qax[k])
            Nnom[k] = Nnom.get(k, F(0))
    return Nlo, Nhi, Nnom, Nnodes_lo, qax


def stability_lower(text, tol, case=None, rel=F(1, 1000)):
    """A PROVED lower bound on the critical load factor of ONE load case (or the smallest over all cases) — the 2D
    frame's continuum stability (frame.stability_lower) in both bending planes of every member:
        K_exact(lam) >= (1 - T) K0 + sum_members sum_planes [ -P G - P^2 k/(1 - P k) Q   (compressed, P = -lam N_lo)
                                                               | lam N_lo b b^T / L       (in tension) ],
    k = L^2 / (4 pi^2 E_lo I_plane), one positive definite matrix proved at each bisection step (ZTL
    pd_ieee_float, the matrix built in floats with a proved distance). PREMISE (stated): doubly symmetric sections,
    no torsional / flexural-torsional / lateral-torsional buckling (Wagner terms not in); Euler-Bernoulli members."""
    from . import judge_ztl  # noqa: F401
    from .frame import PI2_LO, _dy, _geo_split
    import zenergy as ZE
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as sla
    nodes, elems, loads, supports, props = read_deck(text)
    parts, fs, dof, emap = energy_system(text, tol)
    names = list(fs) if case is None else [case]
    if len(names) > 1:
        res = [stability_lower(text, tol, c, rel) for c in names]
        best = min((r for r in res if r.get("lam_low") is not None), key=lambda r: r["lam_low"], default=res[0])
        return dict(best, cases={c: r.get("lam_low") for c, r in zip(names, res)})
    n = len(dof)
    T = max((p["t"] for p in parts), default=F(0))
    Nlo, Nhi, Nnom, Nnodes_lo, qax = _axial_ranges(text, names[0], parts, fs, dof, emap, nodes, elems, props)
    base = {"case": names[0], "Nlo": Nlo, "Nhi": Nhi, "Nnom": Nnom}
    if all(v >= 0 for v in Nlo.values()):
        return dict(base, lam_low=None, why="no compressed member: no buckling under these loads")
    K0 = ZE.matrix(parts, n)
    forms, gab = {}, {}                             # (k, plane) -> (G, Q, B, kk); -> (G_a, G_b) with a member load
    for k, (i, j) in enumerate(elems, 1):
        if k not in Nlo:
            continue
        pk = props[k]
        Elo, izz, iyy = (1 - T) * pk.ex, pk.izz, pk.iyy
        L, xp, yp, zp = _axes(nodes[i], nodes[j], pk.theta)
        Gloc = [[F(v) / (30 * L) for v in r] for r in [[36, 3 * L, -36, 3 * L], [3 * L, 4 * L * L, -3 * L, -L * L],
                                                        [-36, -3 * L, 36, -3 * L], [3 * L, -L * L, -3 * L, 4 * L * L]]]
        Bloc = [[F(v) / L for v in r] for r in [[1, 0, -1, 0], [0, 0, 0, 0], [-1, 0, 1, 0], [0, 0, 0, 0]]]
        Qloc = [[Gloc[a][b] - Bloc[a][b] for b in range(4)] for a in range(4)]
        if k in qax:
            Ga_, Gb_ = _geo_split(L)
        for plane, (vax, rax, sg, I) in (("y", (yp, zp, 1, izz)), ("z", (zp, yp, -1, iyy))):
            forms[(k, plane)] = tuple(_form3(i, j, vax, rax, sg, dof, X) for X in (Gloc, Qloc, Bloc)) + \
                (L * L / (4 * PI2_LO * Elo * I),)
            if k in qax:
                gab[(k, plane)] = (_form3(i, j, vax, rax, sg, dof, Ga_), _form3(i, j, vax, rax, sg, dof, Gb_))
    # nominal estimate: K0 v = -lam K_G(N_nom) v, the linear N of a member load included
    Gn = {}
    for (k, plane), (G, Q, Bf, kk) in forms.items():
        for key, v in G.items():
            Gn[key] = Gn.get(key, F(0)) + Nnom[k] * v
        if (k, plane) in gab:
            for key, v in gab[(k, plane)][0].items():
                Gn[key] = Gn.get(key, F(0)) + qax[k] * v
            for key, v in gab[(k, plane)][1].items():
                Gn[key] = Gn.get(key, F(0)) - qax[k] * v
    A = ZE._float_matrix(K0, n)
    Bm = ZE._float_matrix(Gn, n)
    try:
        lam_est = float(1 / sla.eigsh(-Bm, k=1, M=A, which="LA", return_eigenvectors=False, v0=np.ones(n))[0])
    except Exception:
        lam_est = None
    if not lam_est or lam_est <= 0:
        # a member IS compressed (all Nlo >= 0 returned above): no estimate is not "no buckling" (2026-11-02); the
        # bisection starts from the compressed members' own Euler factor min 1/(P k) — only the proof decides
        lam_est = None
        guess = min((1 / (-Nlo[k] * kk) for (k, plane), (G, Q, Bf, kk) in forms.items() if Nlo[k] < 0), default=None)
        if guess is None:
            return dict(base, lam_low=F(0), lam_est=None, why="a member is compressed but no buckling estimate")
    keys = list(K0)
    kidx = {key: q for q, key in enumerate(keys)}
    def _arr(mat):
        ix = []
        for key in mat:
            if key not in kidx:
                kidx[key] = len(keys); keys.append(key)
            ix.append(kidx[key])
        return np.array(ix, dtype=np.int64), np.array([float(v) for v in mat.values()])
    arrs = {kp: tuple(_arr(m) for m in fq[:3]) for kp, fq in forms.items()}
    arrs_ab = {kp: tuple(_arr(m) for m in ab) for kp, ab in gab.items()}
    K0i = np.array([kidx[key] for key in K0], dtype=np.int64)
    K0v = np.array([float(v) for v in K0.values()])
    nk_ = len(keys)
    cnt = np.bincount(np.concatenate([K0i] + [a[0] for t3 in list(arrs.values()) + list(arrs_ab.values())
                                          for a in t3]), minlength=nk_)
    m_ = int(cnt.max()) + 4
    u_ = F(1, 2 ** 53)
    gam = m_ * u_ / (1 - m_ * u_)
    rr = np.array([a for a, b in keys], dtype=np.int64); cc = np.array([b for a, b in keys], dtype=np.int64)
    offd = (rr != cc).astype(float)
    import math

    def _fl(x, up):
        v = float(x)
        if up and F(v) < x:
            v = math.nextafter(v, math.inf)
        elif not up and F(v) > x:
            v = math.nextafter(v, -math.inf)
        return v

    def proved(lam):
        a0 = _fl(1 - T, False)
        ix, vv, av = [K0i], [a0 * K0v], [abs(a0) * np.abs(K0v)]
        for (k, plane), (G, Q, Bf, kk) in forms.items():
            (Gi, Gv), (Qi, Qv), (Bi, Bv) = arrs[(k, plane)]
            if (k, plane) in arrs_ab and Nlo[k] < 0:
                # the LINEAR N (the 2D frame's branch): N_a G_a + N_b G_b from below, CLIPPED at 0 when the tension
                # end outweighs the compression (the cross term needs max|N|), the continuum correction P^2 k/(1-Pk) G
                (Ai, Av), (Bbi, Bbv) = arrs_ab[(k, plane)]
                Na, Nb = Nnodes_lo.get(k, F(0)) + qax[k], Nnodes_lo.get(k, F(0)) - qax[k]
                if Nhi[k] > -Nlo[k]:
                    Na, Nb = min(Na, F(0)), min(Nb, F(0))
                P = -lam * Nlo[k]
                if P * kk >= 1:
                    return False
                ca, cb, cG = _fl(lam * Na, False), _fl(lam * Nb, False), -_fl(P * P * kk / (1 - P * kk), True)
                ix += [Ai, Bbi, Gi]; vv += [ca * Av, cb * Bbv, cG * Gv]
                av += [abs(ca) * np.abs(Av), abs(cb) * np.abs(Bbv), abs(cG) * np.abs(Gv)]
            elif Nlo[k] < 0:
                P = -lam * Nlo[k]
                if P * kk >= 1:
                    return False
                cP, cQ = -_fl(P, True), -_fl(P * P * kk / (1 - P * kk), True)
                ix += [Gi, Qi]; vv += [cP * Gv, cQ * Qv]; av += [abs(cP) * np.abs(Gv), abs(cQ) * np.abs(Qv)]
            elif Nlo[k] > 0:
                cB = _fl(lam * Nlo[k], False)
                ix.append(Bi); vv.append(cB * Bv); av.append(abs(cB) * np.abs(Bv))
        ixc = np.concatenate(ix)
        Mv = np.bincount(ixc, weights=np.concatenate(vv), minlength=nk_)
        Ma = np.bincount(ixc, weights=np.concatenate(av), minlength=nk_)
        dl = Ma * float(gam) * 1.0000001
        d2 = F(float(np.sum(dl * dl * (1 + offd)))) * (1 + 4 * gam) + F(nk_, 2 ** 1000)
        Mf = sp.csc_matrix((np.concatenate([Mv, Mv[offd > 0]]), (np.concatenate([rr, cc[offd > 0]]),
                                                                  np.concatenate([cc, rr[offd > 0]]))), shape=(n, n))
        try:
            mu = float(sla.eigsh(Mf, k=1, sigma=0, which="LM", return_eigenvectors=False, v0=np.ones(n))[0])
        except Exception:
            return False
        if mu <= 0:
            return False
        return ZE.pd_ieee_float(n, rr, cc, Mv, d2, F(mu) * F(9, 10)) is not None
    top = F(lam_est) if lam_est is not None else _dy(guess, True)
    lo, hi = F(0), top * F(11, 10)
    start = top / 1000
    for _ in range(20):
        if proved(start):
            break
        hi, start = start, start / 10
    else:
        return dict(base, lam_low=F(0), lam_est=lam_est, why="not even a small factor proved")
    lo = start
    for _ in range(40):
        mid = (lo + hi) / 2
        if proved(mid):
            lo = mid
        else:
            hi = mid
        if hi - lo <= rel * hi:
            break
    return dict(base, lam_low=lo, lam_est=lam_est, unknowns=n,
                premise="doubly symmetric sections; torsional and flexural-torsional buckling NOT checked")


def _glob3(i, j, vax, rax, rsign, dof, l):
    """A local 4-vector over (v_i, r_i, v_j, r_j) as a global row."""
    g = {}
    for (n, ax, rot, sg), c in zip(((i, vax, False, 1), (i, rax, True, rsign), (j, vax, False, 1), (j, rax, True, rsign)), l):
        if not c:
            continue
        names = ("RX", "RY", "RZ") if rot else ("X", "Y", "Z")
        for q in range(3):
            if ax[q] and (n, names[q]) in dof:
                g[dof[(n, names[q])]] = g.get(dof[(n, names[q])], F(0)) + c * sg * ax[q]
    return {a: v for a, v in g.items() if v}


_MUTANT = {}       # TEST-ONLY sabotage switches (bench/night/verify_all.py sweep G); empty = the real bounds


def second_order_disp(text, tol, targets, case=None):
    """PHYSICAL SECOND ORDER displacements of a space frame (one load case, or every case): the 2D frame's
    second_order_case for displacements in both bending planes —
        A0 = K0 + sum_members N_mid (G_y + G_z);  parts: the stiffness (radius t), each member's G_y + G_z (radius
        (N_hi - N_lo)/2);  D in [0, C], C = sum_members sum_planes max(P^2 k/(1 - P k), N_hi+) Q_plane;
    ZTL zenergy.certify_general (theta proved, first order + rest). Requires the proved critical factor > 1.
    PREMISES (stated): axial forces from the first-order analysis; doubly symmetric sections, no torsional /
    flexural-torsional buckling; Euler-Bernoulli members."""
    from . import judge_ztl  # noqa: F401
    from .frame import PI2_LO, _psd_terms, _dy, _geo_split
    import zenergy as ZE
    nodes, elems, loads, supports, props = read_deck(text)
    parts, fs, dof, emap = energy_system(text, tol)
    names = list(fs) if case is None else [case]
    if len(names) > 1:
        return {c: second_order_disp(text, tol, targets, c)[c] for c in names}
    # AXIAL member loads (2026-11-02, as the 2D frame): displacements only, members without a transverse load
    qax3 = {}
    for k, q in _qloads(text).get(names[0], {}).items():
        i, j = elems[k - 1]
        L, xp, yp, zp = _axes(nodes[i], nodes[j], props[k].theta)
        a_ = sum(q[t] * xp[t] for t in range(3))
        if a_:
            if any(sum(q[t] * ax[t] for t in range(3)) for ax in (yp, zp)):
                raise Frame3DError(f"second order: member {k} carries an AXIAL and a transverse member load — not "
                                   f"yet (axial alone is in)")
            qax3[k] = a_ * L / 2
    # the axial forces only (2026-11-02, the size bench: the stability bisection here was HALF of the time; it is not
    # needed — certify_general proves A > 0 over the whole box itself, theta < 1, or the frame may buckle: OPEN)
    Nlo, Nhi, _nn, _nl, _qa = _axial_ranges(text, names[0], parts, fs, dof, emap, nodes, elems, props)
    lam = None
    n = len(dof)
    T = max((p["t"] for p in parts), default=F(0))
    A0 = ZE.matrix(parts, n)
    gparts, cterms, cqd, cgrp = [], [], {}, {}
    for k, (i, j) in enumerate(elems, 1):
        if k not in Nlo:
            continue
        pk = props[k]
        Elo, izz, iyy = (1 - T) * pk.ex, pk.izz, pk.iyy
        L, xp, yp, zp = _axes(nodes[i], nodes[j], pk.theta)
        Gloc = [[F(v) / (30 * L) for v in r] for r in [[36, 3 * L, -36, 3 * L], [3 * L, 4 * L * L, -3 * L, -L * L],
                                                        [-36, -3 * L, 36, -3 * L], [3 * L, -L * L, -3 * L, 4 * L * L]]]
        Bloc = [[F(v) / L for v in r] for r in [[1, 0, -1, 0], [0, 0, 0, 0], [-1, 0, 1, 0], [0, 0, 0, 0]]]
        Qloc = [[Gloc[a][b] - Bloc[a][b] for b in range(4)] for a in range(4)]
        mid0 = (Nlo[k] + Nhi[k]) / 2
        mid = _dy(mid0, False)
        rad = _dy((Nhi[k] - Nlo[k]) / 2 + abs(mid0 - mid), True)
        if k in qax3:
            # an AXIAL member load: N_a G_a + N_b G_b per plane with N_a, N_b intervals (the mean N: stability widened
            # Nlo/Nhi by |a| L/2); D in [0, C], C = Nmax^2 k/(1 - P k) G (the 2D frame's derivation)
            qa = qax3[k]
            nn_lo, nn_hi = Nlo[k] + abs(qa), Nhi[k] - abs(qa)
            Ga_, Gb_ = _geo_split(L)
            P = max(F(0), -Nlo[k])
            nmax = max(-Nlo[k], Nhi[k], F(0))
            for (plane, vax, rax, sg, I) in (("y", yp, zp, 1, izz), ("z", zp, yp, -1, iyy)):
                for (lo_, hi_), Gx in (((nn_lo + qa, nn_hi + qa), Ga_), ((nn_lo - qa, nn_hi - qa), Gb_)):
                    Gt = [(d, g) for d, g in ((d, _glob3(i, j, vax, rax, sg, dof, l)) for d, l in _psd_terms(Gx)) if g]
                    if _MUTANT.get("no_geo"):
                        Gt = []
                    m0 = (lo_ + hi_) / 2
                    mm = _dy(m0, False)
                    rr_ = _dy((hi_ - lo_) / 2 + abs(m0 - mm), True)
                    for d, g in Gt:
                        items = list(g.items())
                        for a, ga in items:
                            for b, gb in items:
                                if a >= b:
                                    A0[(a, b)] = A0.get((a, b), F(0)) + mm * d * ga * gb
                    if rr_ and Gt:
                        gparts.append({"t": rr_, "terms": Gt})
                kk = L * L / (4 * PI2_LO * Elo * I)
                if P * kk >= 1:
                    return {names[0]: {"verdict": "OPEN", "why": f"element {k} could buckle between its nodes: subdivide"}}
                cq = nmax * nmax * kk / (1 - P * kk)
                cqd[(k, plane)] = cq
                if cq:
                    for d, l in _psd_terms(Gloc):
                        g = _glob3(i, j, vax, rax, sg, dof, l)
                        if g:
                            cterms.append((_dy(cq * d, True), g))
            continue
        Gt = []
        P = max(F(0), -Nlo[k])
        for (plane, vax, rax, sg, I) in (("y", yp, zp, 1, izz), ("z", zp, yp, -1, iyy)):
            terms = [(d, _glob3(i, j, vax, rax, sg, dof, l)) for d, l in _psd_terms(Gloc)]
            Gt += [(d, g) for d, g in terms if g]
            kk = L * L / (4 * PI2_LO * Elo * I)
            if P * kk >= 1:
                return {names[0]: {"verdict": "OPEN", "why": f"element {k} could buckle between its nodes: subdivide"}}
            cq = max(P * P * kk / (1 - P * kk), max(F(0), Nhi[k]))
            cqd[(k, plane)] = cq
            if cq:
                for d, l in _psd_terms(Qloc):
                    g = _glob3(i, j, vax, rax, sg, dof, l)
                    if g:
                        cterms.append((_dy(cq * d, True), g))
                        cgrp.setdefault((k, plane), []).append(cterms[-1])
        if _MUTANT.get("no_geo"):                          # sabotage (tests only): first-order stiffness
            Gt = []
        for d, g in Gt:
            items = list(g.items())
            for a, ga in items:
                for b, gb in items:
                    if a >= b:
                        A0[(a, b)] = A0.get((a, b), F(0)) + mid * d * ga * gb
        if rad and Gt:
            gparts.append({"t": rad, "terms": Gt})
    es = []
    for tg in targets:
        nd, d = _target(tg)
        e = [F(0)] * n
        if (nd, d) in dof:
            e[dof[(nd, d)]] = F(1)
        es.append(e)
    # TRANSVERSE MEMBER LOADS in second order (the 2D frame's v2, per plane): inside a member the load couples to the
    # nodal motion through the condensed inner field, |g.d| <= sum_e ||d||_{C_e} r_e with
    # r_e^2 <= w^2 L^5 / (720 E I (1 - P k)) per member and plane; the response on an output, y = A^-1 e:
    #   |e.u_g| = |y.g| <= sum_e ||y~||_{C_e} r_e + ||y - y~||_C R,   R = sqrt(sum r_e^2),
    #   ||y - y~||_C <= sqrt(theta) ||y - y~||_A0 <= sqrt(theta) (e_y + theta/(1 - theta) ||y0||_A0)
    # (C <= theta A0; y - y0 = -A^-1 Delta y0, A >= (1 - theta) A0). PER MEMBER since 2026-11-02: the old global
    # sqrt(theta) ||y||_A0 R / (1 - theta) made ~93 % of a loaded frame's end-moment brackets (MEASURED, sweep G).
    qs = _qloads(text).get(names[0], {})
    re2 = {}
    for k, q in qs.items():
        i, j = elems[k - 1]
        pk = props[k]
        L, xp, yp, zp = _axes(nodes[i], nodes[j], pk.theta)
        P = max(F(0), -Nlo.get(k, F(0)))
        for plane, axis, I in (("y", yp, pk.izz), ("z", zp, pk.iyy)):
            w = sum(q[t] * axis[t] for t in range(3))
            if w and (k, plane) in cgrp:                   # no C_e (cq = 0): the member load does not couple
                Elo = (1 - T) * pk.ex
                kk = L * L / (4 * PI2_LO * Elo * I)
                re2[(k, plane)] = _dy(w * w * L ** 5 / (720 * Elo * I * (1 - P * kk)), True)   # UP: 64-bit (cost)
    keys = sorted(re2)
    extra = _EXTRA.pop("outputs", [])
    try:
        rs = ZE.certify_general_many(A0, parts + gparts, cterms, fs[names[0]], es + extra + [list(fs[names[0]])], n,
                                     cgroups=[cgrp[key] for key in keys] if keys else None)
    except ArithmeticError as ex_:
        return {names[0]: {"verdict": "OPEN", "why": f"the critical factor is not proved above 1 (second order: "
                                                     f"{ex_}): the frame may buckle under these loads"}}
    if keys:
        Rq = ZE._sqrt_up(sum(re2.values()))
        rq = [ZE._sqrt_up(re2[key]) for key in keys]
        th = rs[0]["theta"]
        sth = ZE._sqrt_up(th)
        for r in rs:
            ny = r["ny_t"] + r["ey"]
            ex_ = sum((_dy(c * q_, True) for c, q_ in zip(r["c_groups"], rq)), F(0)) + \
                sth * (r["ey"] + th / (1 - th) * ny) * Rq             # each term rounded UP (2026-11-02: the cost)
            r["lo"] -= ex_
            r["hi"] += ex_
    # OUTWARD to 64-bit dyadics (2026-11-02, the night battery's sweep G: the proved outputs came back with up to 3361
    # digits, N_lo/N_hi 567, cq 1141, and second_order_stress's corner sums passed 4300 digits — a crash). Wider
    # intervals stay true; a lower bound computed from them stays a lower bound.
    for r in rs:
        r["lo"], r["hi"] = _dy(r["lo"], False), _dy(r["hi"], True)
    Nlo = {k: _dy(v, False) for k, v in Nlo.items()}
    Nhi = {k: _dy(v, True) for k, v in Nhi.items()}
    cqd = {k: _dy(v, True) for k, v in cqd.items()}
    _EXTRA["last"] = {"rs": rs[len(es):], "theta": rs[0]["theta"], "cq": cqd, "Nlo": Nlo, "Nhi": Nhi, "T": T,
                      "lam": lam, "emap": emap, "dof": dof, "n": n}
    return {names[0]: {tg: (r["lo"], r["hi"], r["nominal"]) for tg, r in zip(targets, rs)}}


_EXTRA = {}


def second_order_stress(text, tol, fy, gamma_m0=F(1), case=None, ks=None):
    """|sigma| <= fy/gamma_M0 for every member in PHYSICAL SECOND ORDER (the 2D frame's second_order_case, both
    planes): end moments M = E p (I/L)(b +- 3c).u per plane, each widened by the continuum correction
    sqrt(C_thth) ||u||_C (||u||_C <= sqrt(theta f.u/(1 - theta))); the interior maximum per plane by the
    beam-column bounds (none in tension, none if psi <= 1 - 2 phi^2, else min of m(1 + psi)/(2 cos^2 phi) and
    sqrt(A^2 + B^2)); the corner stress bounded by |N|/A + M_z,max (TKY/2)/I_z + M_y,max (TKZ/2)/I_y (the two planes'
    maxima added: safe even if they peak at different points). Transverse member loads (QLOAD): the clamped-beam end
    moment w L^2/12 sign-free, the own-load end correction, the interior by the Dirichlet Green function. Judged by
    ZTL over [a proved lower bound of max|sigma| (the end corners), its upper bound]. Premises as second_order_disp;
    no AXIAL member loads in second order."""
    from . import judge_ztl  # noqa: F401
    from .frame import _sqrt_down, PI2_LO
    import zenergy as ZE
    from znumjudge import parse_quantities, judge_sheet_claim
    _no_axial_qload(text, "second-order stresses")       # the end moments / interior bounds assume a constant N
    parts, fs, dof, emap = energy_system(text, tol)
    names = list(fs) if case is None else [case]
    ks = sorted(emap) if ks is None else ks
    lim = F(fy) / F(gamma_m0)
    n = len(dof)
    fr = lambda x: f"{x.numerator}/{x.denominator}"
    qs, atoms, rows = [], [], []
    for c in names:
        def vec(g):
            e = [F(0)] * n
            for i_, v in g.items():
                e[i_] = v
            return e
        outs, items = [], []
        for k in ks:
            m = emap[k]
            L = m["L"]
            area, izz, iyy = m["p"].area, m["p"].izz, m["p"].iyy
            if not m["p"].tky or not m["p"].tkz:
                raise Frame3DError(f"member {k}: stresses need TKY and TKZ")
            outs.append(vec({i_: area / L * v for i_, v in m["a"].items()})); items.append((k, "N"))
            ii, jj = m["ij"]
            xp_, yp_, zp_ = m["axes"]
            Gl_ = [[F(v) / (30 * L) for v in r] for r in [[36, 3 * L, -36, 3 * L], [3 * L, 4 * L * L, -3 * L, -L * L],
                                                           [-36, -3 * L, 36, -3 * L], [3 * L, -L * L, -3 * L, 4 * L * L]]]
            for plane, (bb, cc, I), (vax, rax, sg) in (("y", ("bz", "cz", izz), (yp_, zp_, 1)),
                                                        ("z", ("by", "cy", iyy), (zp_, yp_, -1))):
                for end, sb in (("I", 1), ("J", -1)):
                    g = {}
                    for i_, v in m[bb].items():
                        g[i_] = g.get(i_, F(0)) + I / L * v
                    for i_, v in m[cc].items():
                        g[i_] = g.get(i_, F(0)) + I / L * 3 * sb * v
                    outs.append(vec(g)); items.append((k, plane + end))
                # the GEOMETRIC part of the end moment (2026-11-02): the (K_E + N G) row, not K_E's alone — the G row
                # at each end in the plane's own coordinates (v, th_z) or (w, phi = -th_y), unscaled
                for end, row in (("I", Gl_[1]), ("J", Gl_[3])):
                    outs.append(vec(_glob3(ii, jj, vax, rax, sg, dof, row))); items.append((k, plane + "G" + end))
        _EXTRA["outputs"] = outs
        res = second_order_disp(text, tol, [], c)[c]
        if isinstance(res, dict) and res.get("verdict") == "OPEN":
            return {"verdict": "OPEN", "why": res["why"], "case": c}
        X = _EXTRA.pop("last")
        rs, th, T = X["rs"], X["theta"], X["T"]
        qmap = _qloads(text).get(c, {})
        fu_hi = rs[-1]["hi"]
        unC = ZE._sqrt_up(th * max(fu_hi, F(0)) / (1 - th))
        rng = {}
        for (k, what), r in zip(items, rs[:-1]):
            ex = emap[k]["p"].ex
            if "G" in what:
                rng[(k, what)] = (r["lo"], r["hi"])     # (G u)_th: not scaled by the modulus
                continue
            rng[(k, what)] = (min(ex * (1 - T) * r["lo"], ex * (1 + T) * r["lo"]),
                              max(ex * (1 - T) * r["hi"], ex * (1 + T) * r["hi"]))
        for k in ks:
            L = emap[k]["L"]
            pk = emap[k]["p"]
            ex, area, izz, iyy, tky, tkz = pk.ex, pk.area, pk.izz, pk.iyy, pk.tky, pk.tkz
            Nl, Nh = rng[(k, "N")]
            P = max(F(0), -Nl)
            mmax, Mends = {}, {}
            xp_, yp_, zp_ = emap[k]["axes"]
            qk = qmap.get(k, (F(0), F(0), F(0)))
            for plane, I, axis in (("y", izz, yp_), ("z", iyy, zp_)):
                cth = ZE._sqrt_up(X["cq"].get((k, plane), F(0)) * 4 * L / 30)
                corr = cth * unC
                ws = sum(qk[t] * axis[t] for t in range(3))
                w = abs(ws)
                mb = F(0)
                if w:
                    # the member load: the P = 0 inner solution's end moment, EXACT and signed (as the 2D frame's mb;
                    # both ends; -w L^2/12 in the (v, th_z) plane, +w L^2/12 in the (w, phi) plane — its outputs carry
                    # the flipped sign; the sign-free |w| L^2/12 widening before 2026-11-02 doubled loaded brackets), and
                    # the own-load end correction sqrt(C_thth) r_e, r_e^2 <= w^2 L^5/(720 E I (1 - P k))
                    mb = (-ws if plane == "y" else ws) * L * L / 12
                    kk_ = L * L / (4 * PI2_LO * (1 - T) * ex * I)
                    corr += cth * ZE._sqrt_up(w * w * L ** 5 / (720 * (1 - T) * ex * I * (1 - P * kk_)))
                Ml = {e_: (rng[(k, plane + e_)][0] + mb - corr, rng[(k, plane + e_)][1] + mb + corr) for e_ in ("I", "J")}
                # + N (G u) at I, - N (G u) at J in the (v, th_z) plane; the (w, phi) plane's output is -(K_E u)_phi,
                # so there the signs flip. N in [N_lo, N_hi] (the axial forces of the geometric stiffness).
                pl_s = 1 if plane == "y" else -1
                nl_, nh_ = X["Nlo"].get(k, F(0)), X["Nhi"].get(k, F(0))
                for e_, es_ in (("I", 1), ("J", -1)):
                    if _MUTANT.get("no_geo_moment"):           # sabotage (tests only): the K_E-row moment alone
                        break
                    gl_, gh_ = rng[(k, plane + "G" + e_)]
                    prods = [pl_s * es_ * a_ * b_ for a_ in (nl_, nh_) for b_ in (gl_, gh_)]
                    Ml[e_] = (Ml[e_][0] + min(prods), Ml[e_][1] + max(prods))
                Mends[plane] = Ml
                mend = max(max(abs(a_), abs(b_)) for a_, b_ in Ml.values())
                mint = mend
                if w:
                    # M = M_lin + m, m'' +- k^2 m = -q -+ k^2 M_lin, m = 0 at the ends: the Dirichlet Green function is
                    # positive, its integral <= (L^2/8)/(1 - k^2 L^2/8) in compression, <= L^2/8 in tension (2D frame)
                    if P:
                        k2 = P / ((1 - T) * ex * I)
                        if k2 * L * L / 8 >= 1:
                            return {"verdict": "OPEN", "why": f"element {k}: too slender between its nodes (subdivide)"}
                        mint = mend + (w + k2 * mend) * (L * L / 8) / (1 - k2 * L * L / 8)
                    if Nh > 0:
                        kt = Nh / ((1 - T) * ex * I)
                        mint = max(mint, mend + (w + kt * mend) * L * L / 8)
                    if not P and not Nh > 0:
                        mint = mend + w * L * L / 8
                elif P:
                    phi2 = L * L * P / (4 * (1 - T) * ex * I)
                    (al, ah), (bl, bh) = Ml["I"], Ml["J"]
                    if (al > 0 and bh < 0) or (ah < 0 and bl > 0):
                        psi = F(0)
                    elif (al > 0 and bl > 0) or (ah < 0 and bh < 0):
                        A_ = (min(abs(al), abs(ah)), max(abs(al), abs(ah)))
                        B_ = (min(abs(bl), abs(bh)), max(abs(bl), abs(bh)))
                        psi = min(F(1), min(A_[1], B_[1]) / max(A_[0], B_[0]))
                    else:
                        psi = F(1)
                    if psi > 1 - 2 * phi2:
                        if phi2 >= 2:
                            return {"verdict": "OPEN", "why": f"element {k}: too slender between its nodes (subdivide)"}
                        c_lo = 1 - phi2 / 2
                        b1 = mend * (1 + psi) / (2 * c_lo * c_lo)
                        ph_lo = _sqrt_down(phi2)
                        s_lo = ph_lo * (1 - ph_lo * ph_lo / 6)
                        msum = max(abs(al + bl), abs(ah + bh), abs(al + bh), abs(ah + bl))
                        mdif = max(abs(bh - al), abs(ah - bl))
                        b2 = ZE._sqrt_up((msum / (2 * c_lo)) ** 2 + (mdif / (2 * s_lo)) ** 2) if s_lo > 0 else b1
                        mint = max(mend, min(b1, b2))
                mmax[plane] = mint
            hi_abs = max(abs(Nl), abs(Nh)) / area + mmax["y"] * (tky / 2) / izz + mmax["z"] * (tkz / 2) / iyy
            lo_abs = F(0)                                   # a proved lower bound of max |sigma|: the end corners
            for e_ in ("I", "J"):
                (yl, yh), (zl, zh) = Mends["y"][e_], Mends["z"][e_]
                for sy in (1, -1):
                    for sz in (1, -1):
                        ys = sorted((sy * yl * (tky / 2) / izz, sy * yh * (tky / 2) / izz))
                        zs = sorted((-sz * zl * (tkz / 2) / iyy, -sz * zh * (tkz / 2) / iyy))
                        a_, b_ = Nl / area + ys[0] + zs[0], Nh / area + ys[1] + zs[1]
                        lo_abs = max(lo_abs, F(0) if a_ <= 0 <= b_ else min(abs(a_), abs(b_)))
            nm = f"s{len(qs)}"
            qs.append(f"{nm}=[{fr(lo_abs)},{fr(hi_abs)}] earned:frame3d-second-order")
            atoms.append(f"{nm} <= {fr(lim)}")
            rows.append({"case": c, "element": k, "sigma_abs": [_show(lo_abs, -1), _show(hi_abs, 1)],
                         "M_ends": {pl: {e_: (_show(a_, -1), _show(b_, 1)) for e_, (a_, b_) in Mends[pl].items()}
                                    for pl in Mends}})
    q, m = parse_quantities(", ".join(qs))
    r = judge_sheet_claim(" & ".join(atoms), q, m)
    worst = max(rows, key=lambda x: F(x["sigma_abs"][1].split()[0]))
    return {"verdict": r["disposition"] + (f" ({r['polarity']})" if r.get("polarity") else ""), "limit": _show(lim),
            "worst": worst, "members": rows,
            "note": "PHYSICAL SECOND ORDER (continuum members, both planes); premises: first-order axial forces, no "
                    "torsional / flexural-torsional buckling, no axial member loads"}


_SU = {}


def stability_upper(text, case=None):
    """A proved UPPER bound on the critical factor at the NOMINAL moduli by a WITNESS (the 2D frame's
    stability_upper, both planes): the float buckling mode x (dyadic, exact from here on) with
    x'K0x + lam sum_e N_hi,e x'(G_y + G_z)_e x <= 0 — the Hermite field is an admissible continuum field, N_hi >= N
    proved by one solve (ZTL enclose_linear), x'G x >= 0 — so lam_cr <= lam (ZTL lean ZStability `witness_upper`)."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    import numpy as np
    import scipy.sparse.linalg as sla
    from .frame import _geo_split
    nodes, elems, loads, supports, props = read_deck(text)
    parts, fs, dof, emap = energy_system(text, "0")
    c = list(fs)[0] if case is None else case
    f = fs[c]
    n = len(dof)
    nom = [{"t": 0, "terms": p["terms"]} for p in parts]
    ks = [k for k in emap if emap[k]["a"]]
    encl = ZE.enclose_linear(nom, f, n, [emap[k]["a"] for k in ks])
    Nhi, Nmid = {}, {}
    for k, (lo, hi) in zip(ks, encl):
        fac = props[k].ex * props[k].area / emap[k]["L"]
        Nhi[k], Nmid[k] = fac * hi, fac * (lo + hi) / 2
    K0 = ZE.matrix(nom, n)
    Ge, Gn, qax, Gd = {}, {}, {}, {}
    qs = _qloads(text).get(c, {})
    for k, (i, j) in enumerate(elems, 1):
        if k not in Nhi:
            continue
        L, xp, yp, zp = _axes(nodes[i], nodes[j], props[k].theta)
        Gloc = [[F(v) / (30 * L) for v in r] for r in [[36, 3 * L, -36, 3 * L], [3 * L, 4 * L * L, -3 * L, -L * L],
                                                        [-36, -3 * L, 36, -3 * L], [3 * L, -L * L, -3 * L, 4 * L * L]]]
        G = {}
        for (vax, rax, sg) in ((yp, zp, 1), (zp, yp, -1)):
            for key, v in _form3(i, j, vax, rax, sg, dof, Gloc).items():
                G[key] = G.get(key, F(0)) + v
        Ge[k] = G
        for key, v in G.items():
            Gn[key] = Gn.get(key, F(0)) + Nmid[k] * v
        a_ = sum(qk[t] * xp[t] for t in range(3)) if (qk := qs.get(k)) else F(0)
        if a_:
            # an AXIAL member load: the Hermite field's form is N_mean G + (aL/2)(G_a - G_b) (the 2D witness's fix)
            Ga_, Gb_ = _geo_split(L)
            D = [[Ga_[r][q_] - Gb_[r][q_] for q_ in range(4)] for r in range(4)]
            Dk = {}
            for (vax, rax, sg) in ((yp, zp, 1), (zp, yp, -1)):
                for key, v in _form3(i, j, vax, rax, sg, dof, D).items():
                    Dk[key] = Dk.get(key, F(0)) + v
            qax[k], Gd[k] = a_ * L / 2, Dk
            for key, v in Dk.items():
                Gn[key] = Gn.get(key, F(0)) + qax[k] * v
    A = ZE._float_matrix(K0, n)
    Bm = ZE._float_matrix(Gn, n)
    try:
        vals, vecs = sla.eigsh(-Bm, k=1, M=A, which="LA", v0=np.ones(n))
    except Exception:
        return {"lam_high": None, "why": "no buckling mode found"}
    if vals[0] <= 0:
        return {"lam_high": None, "why": "the estimate found no buckling mode: no upper bound"}
    x = [F(float(v)) for v in vecs[:, 0]]
    qK = sum(a * b for a, b in zip(x, ZE._kmul(K0, x, n)))
    den = F(0)
    for k, G in Ge.items():
        g = F(0)
        for (a, b), v in G.items():                 # lower triangle -> the full form
            g += v * x[a] * x[b] * (1 if a == b else 2)
        den -= Nhi[k] * g
    for k, Dk in Gd.items():
        den -= qax[k] * sum(v * x[a] * x[b] * (1 if a == b else 2) for (a, b), v in Dk.items())
    if den <= 0:
        return {"lam_high": None, "why": "the witness does not load the mode in compression"}
    lam = qK / den
    S = 1 << 64
    lam = F(-((-lam.numerator * S) // lam.denominator), S)
    return {"lam_high": lam, "lam_est": float(1 / vals[0]), "Nhi": Nhi, "case": c}


def judge_buckling(text, tol, fy, curve_y, curve_z, gamma_m1=F(1), case=None):
    """EN 1993-1-1 6.3.1 flexural buckling of every compressed member of a SPACE frame, N_Ed <= chi A fy / gamma_M1,
    N_cr,i = alpha_cr |N_Ed,i| with alpha_cr the PROVED lower bound of the 3D stability (every mode, both axes), and
    chi on the WORSE of the two members' curves (the larger imperfection factor: chi lower — safe). The 2D frame's
    argument (frame.judge_buckling_case): the check is gamma_M1 <= alpha_cr g(lb), g = chi lb^2 increasing (ZTL lean
    ZChi `chi_curves_monotone`), so the proved alpha_cr from below and |N| from above give a proved lower bound.
    EARNED when every member clears it in every case; REFUTED when a member fails at the NOMINAL moduli (alpha_cr from
    above by stability_upper's witness, |N| from below); OPEN otherwise.
    NOT here: 5.3.2 sway imperfections, torsional / flexural-torsional / lateral-torsional buckling, 6.3.3."""
    from .frame import CURVES, _curve_premises, _sqrt_down, _g_lower
    nodes, elems, loads, supports, props = read_deck(text)
    for cv in (curve_y, curve_z):
        if cv not in CURVES:
            raise Frame3DError(f"{cv!r}: a buckling curve is one of {', '.join(CURVES)}")
    a = max(CURVES[curve_y], CURVES[curve_z])
    _curve_premises(a)
    _, fs, _, _ = energy_system(text, tol)
    names = list(fs) if case is None else [case]
    rows, worst = [], F(0)
    for c in names:
        st = stability_lower(text, tol, c)
        lam = st.get("lam_low")
        for k in sorted(st.get("Nlo", {})):
            nlo = st["Nlo"][k]
            if nlo >= 0:
                continue
            nhi = -nlo
            if not lam or lam <= 0:
                rows.append({"case": c, "member": k, "N_max": _show(nhi, 1), "verdict": "OPEN"})
                continue
            area = props[k].area
            lb_lo = _sqrt_down(area * F(fy) / (lam * nhi))
            H = lam * _g_lower(lb_lo, a)
            u = F(gamma_m1) / H if H > 0 else None
            if u is not None:
                worst = max(worst, u)
            row = {"case": c, "member": k, "N_max": _show(nhi, 1), "lambda_bar_min": _show(lb_lo, -1),
                   "alpha_cr_proved_lower": _show(lam, -1), "utilisation_max": _show(u, 1) if u else None,
                   "verdict": "EARNED" if u is not None and u <= 1 else "OPEN"}
            if row["verdict"] == "OPEN":            # REFUTED at the nominal moduli (a point of the box): the witness
                su = _SU.get((text, c)) or _SU.setdefault((text, c), stability_upper(text, c))
                lam_hi, nn = su.get("lam_high"), su.get("Nhi", {}).get(k)
                from .frame import _g_upper
                if lam_hi and nn is not None and nn < 0:
                    lb_hi = _sqrt_down(area * F(fy) / (lam_hi * -nn)) + F(1, 1 << 64)
                    Hh = lam_hi * _g_upper(lb_hi, a)
                    if F(gamma_m1) > Hh:
                        row["verdict"] = "REFUTED"
                        row["at_nominal_utilisation_min"] = _show(F(gamma_m1) / Hh, -1)
            rows.append(row)
    vs = [r["verdict"] for r in rows]
    return {"verdict": "REFUTED" if "REFUTED" in vs else "EARNED" if all(v == "EARNED" for v in vs) else "OPEN",
            "utilisation_max": _show(worst, 1),
            "members": rows, "path": "EN 1993-1-1 6.3.1, N_cr,i = alpha_cr |N_Ed,i|, alpha_cr from the 3D stability",
            "not_checked": "5.3.2 sway imperfections; torsional, flexural-torsional and lateral-torsional buckling; "
                           "6.3.3 interaction"}


def judge_interaction(text, tol, fy, curve_z, curve_y, gamma_m1=F(1), case=None, phi=None):
    """EN 1993-1-1 6.3.3, formulas (6.61) AND (6.62), Annex B Method 2, BIAXIAL, every compressed member of a space
    frame. Axis a = bending in the x'-y' plane (about z', I_z, W_a = I_z/(TKY/2)), axis b = in the x'-z' plane (about y',
    I_y, W_b = I_y/(TKZ/2)); curve_z / curve_y the buckling curves for those planes.
      n_a = N_Ed/(chi_a N_Rk/gamma_M1) <= gamma_M1/H_a, H_a = alpha_cr g_a(lb), N_cr = alpha_cr N_Ed (as judge_buckling;
      the same lb for both axes: alpha_cr is the frame's lowest mode, so N_cr is from below for either);
      k_aa <= C_m (1 + 0.6 n_a), k_bb <= C_m (1 + 0.6 n_b) (Table B.1's caps, elastic class 3); k_ab = k_bb,
      k_ba = 0.8 k_aa; C_m = 1 (Table B.3's largest); M_Rk = W_el fy (elastic: safe for class 1-2);
      M_Ed per plane = the largest proved |M| at the member's ends (nodal loads: linear along the member).
    (6.61): n_a + k_aa M_a/M_a,Rk + k_ab M_b/M_b,Rk <= 1;  (6.62): n_b + k_ba M_a/M_a,Rk + k_bb M_b/M_b,Rk <= 1
    (the M/M_Rk terms with gamma_M1). EARNED when both hold for every member in every case; OPEN otherwise.
    PREMISES (said): no lateral-torsional / torsional buckling (chi_LT = 1, members not susceptible to torsional
    deformation), class 1-3, no member loads (QLOAD refuses, as stability)."""
    from . import judge_ztl  # noqa: F401
    from .frame import CURVES, _curve_premises, _sqrt_down, _g_lower, _side_peak
    import zenergy as ZE
    # EN 5.3.2's global sway imperfection, +-phi along X and along Y, each case judged (2026-11-02: as the 2D frame's
    # judge_interaction; phi = 0 for the bare loads). The conservative side: four cases instead of one.
    phi = PHI0 if phi is None else F(phi)
    if phi:
        texti = with_imperfections(text, phi)
        if case is None:
            r = judge_interaction(texti, tol, fy, curve_z, curve_y, gamma_m1, None, 0)
        else:
            parts_ = [judge_interaction(texti, tol, fy, curve_z, curve_y, gamma_m1, f"{case}{t}{ax}", 0)
                      for ax in "XY" for t in "+-"]
            r = dict(parts_[0], members=[m for p_ in parts_ for m in p_["members"]],
                     verdict="EARNED" if all(p_["verdict"] == "EARNED" for p_ in parts_) else "OPEN",
                     utilisation_max=max(parts_, key=lambda p_: F(p_["utilisation_max"].split()[0]))["utilisation_max"])
        return dict(r, imperfection=f"EN 5.3.2 sway, +-{phi} along X and along Y (each judged)")
    for cv in (curve_z, curve_y):
        if cv not in CURVES:
            raise Frame3DError(f"{cv!r}: a buckling curve is one of {', '.join(CURVES)}")
    aa, ab = CURVES[curve_z], CURVES[curve_y]
    _curve_premises(aa); _curve_premises(ab)
    parts, fs, dof, emap = energy_system(text, tol)
    n = len(dof)
    names = list(fs) if case is None else [case]
    ks = sorted(emap)
    es, items, scale = [], [], []
    for k in ks:
        m = emap[k]
        pk, L = m["p"], m["L"]
        if not pk.tky or not pk.tkz:
            raise Frame3DError(f"member {k}: the interaction check needs TKY and TKZ")
        for plane, (bb, cc, I) in (("a", ("bz", "cz", pk.izz)), ("b", ("by", "cy", pk.iyy))):
            for end, sb in (("I", 1), ("J", -1)):
                e = [F(0)] * n
                for i_, v in m[bb].items():
                    e[i_] += I / L * v
                for i_, v in m[cc].items():
                    e[i_] += I / L * 3 * sb * v
                es.append(e); items.append((k, plane)); scale.append(m["part"])
    rs_all = ZE.certify_cases(parts, [fs[c] for c in names], es, n, scale=scale)
    rows, worst = [], F(0)
    for c, rs in zip(names, rs_all):
        st = stability_lower(text, tol, c)
        lam = st.get("lam_low")
        # MEMBER LOADS (2026-11-02, the 2D frame's way): first order, the moment along a member is EXACTLY the line
        # between its end moments plus kappa s (1 - s); each end moment = the K_E row + the clamped-beam moment, signed
        # as second_order_stress (-w L^2/12 in plane a = (v, th_z), +w L^2/12 in plane b — its outputs flipped), kappa
        # the opposite way (+w L^2/2, -w L^2/2: a clamped beam's +-w L^2/24 at midspan); the peak by _side_peak. An
        # axial member load bends nothing in first order (its N range is stability_lower's, widened).
        qmap = _qloads(text).get(c, {})
        ends = {}
        for (k, plane), r in zip(items, rs):
            ex = emap[k]["p"].ex
            ends.setdefault((k, plane), []).append(sorted([ex * r["lo"], ex * r["hi"]]))
        Mx = {}
        for (k, plane), (eI, eJ) in ends.items():
            xp_, yp_, zp_ = emap[k]["axes"]
            L_ = emap[k]["L"]
            qk = qmap.get(k)
            w = sum(qk[t] * (yp_ if plane == "a" else zp_)[t] for t in range(3)) if qk else F(0)
            mb = (-w if plane == "a" else w) * L_ * L_ / 12
            kap = (w if plane == "a" else -w) * L_ * L_ / 2
            Mx[(k, plane)] = _side_peak([eI[0] + mb, eI[1] + mb], [eJ[0] + mb, eJ[1] + mb], kap)
        for k in ks:
            nlo = st.get("Nlo", {}).get(k, F(0))
            if nlo >= 0:
                continue
            N = -nlo
            pk = emap[k]["p"]
            if not lam or lam <= 0:
                rows.append({"case": c, "member": k, "verdict": "OPEN", "why": "alpha_cr not proved positive"})
                continue
            lb = _sqrt_down(pk.area * F(fy) / (lam * N))
            Ha, Hb = lam * _g_lower(lb, aa), lam * _g_lower(lb, ab)
            if Ha <= 0 or Hb <= 0:
                rows.append({"case": c, "member": k, "verdict": "OPEN", "why": "no positive buckling resistance"})
                continue
            g = F(gamma_m1)
            na, nb = g / Ha, g / Hb
            kaa, kbb = 1 + F(3, 5) * na, 1 + F(3, 5) * nb
            kab, kba = kbb, F(4, 5) * kaa
            ma = Mx[(k, "a")] * g / ((pk.izz / (pk.tky / 2)) * F(fy))
            mb = Mx[(k, "b")] * g / ((pk.iyy / (pk.tkz / 2)) * F(fy))
            u1 = na + kaa * ma + kab * mb
            u2 = nb + kba * ma + kbb * mb
            u = max(u1, u2)
            worst = max(worst, u)
            rows.append({"case": c, "member": k, "N_Ed_max": _show(N, 1), "M_a_max": _show(Mx[(k, "a")], 1),
                         "M_b_max": _show(Mx[(k, "b")], 1), "u_6_61": _show(u1, 1), "u_6_62": _show(u2, 1),
                         "verdict": "EARNED" if u <= 1 else "OPEN"})
    vs = [r["verdict"] for r in rows]
    return {"verdict": "EARNED" if all(v == "EARNED" for v in vs) else "OPEN", "utilisation_max": _show(worst, 1),
            "members": rows, "path": "EN 1993-1-1 6.3.3 (6.61) and (6.62), Annex B Method 2, biaxial, C_m = 1",
            "premises": "no lateral-torsional / torsional buckling; class 1-3 (elastic resistance)"}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    text = open(argv[0], encoding="utf-8").read()
    tol = argv[argv.index("--tol") + 1] if "--tol" in argv else "0"
    target = argv[argv.index("--target") + 1]
    le = argv[argv.index("--le") + 1] if "--le" in argv else None
    ge = argv[argv.index("--ge") + 1] if "--ge" in argv else None
    print(json.dumps(judge(text, tol, target, le, ge), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
