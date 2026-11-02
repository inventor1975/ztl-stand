"""frame3d — SPACE FRAMES (the stand's 3D phase, track 2, version 1, 2026-11-02): ANSYS-style BEAM4 decks, every
displacement as a PROVED range for every modulus in the tolerance box (first order), judged by ZTL zenergy — the 2D
frame's energy path one dimension up.

    python3 -m ustand.frame3d deck.txt --tol 0.5% --target "U(5,Z)" [--le 0.012]

Deck (version 1):
    ET, 1, BEAM4
    MP, EX, 1, 210e9          MP, PRXY, 1, 0.3          (G = E / (2 (1 + nu)))
    R, 1, AREA, IZZ, IYY, TKZ, TKY, THETA, ISTRN, IXX    (IXX = the torsion constant J; THETA 0 or 90 only)
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


def read_deck(text):
    nodes, elems, loads, supports = {}, [], {}, set()
    ex = nu = sec = None
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
            elems.append((int(f[1]), int(f[2])))
        elif cmd == "MP":
            prop, v = f[1].upper(), _num(f[3], where)
            if prop == "EX":
                if ex is not None and v != ex:
                    raise Frame3DError(f"{where}: a second EX — one material only (version 1)")
                ex = v
            elif prop in ("PRXY", "NUXY"):
                nu = v
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
            s = (area, izz, iyy, tkz, tky, theta, ixx)
            if sec is not None and s != sec:
                raise Frame3DError(f"{where}: a second real constant — one section only (version 1)")
            sec = s
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
        elif cmd == "ET":
            if f[2].upper() not in ("BEAM4", "4"):
                raise Frame3DError(f"{where}: element type {f[2]} — only BEAM4 (3D beam)")
        elif cmd in ("MAT", "REAL", "TYPE"):
            if len(f) > 1 and f[1] not in ("1", ""):
                raise Frame3DError(f"{where}: {cmd},{f[1]} — one material and one real constant only")
        else:
            raise Frame3DError(f"{where}: {f[0]} — not read (only N E MP R F D ET MAT REAL TYPE)")
    if not nodes or not elems:
        raise Frame3DError("no nodes or no elements")
    if ex is None or sec is None or nu is None:
        raise Frame3DError("MP,EX, MP,PRXY and R are needed (modulus, Poisson ratio, section)")
    for i, j in elems:
        for n in (i, j):
            if n not in nodes:
                raise Frame3DError(f"element {i}-{j}: node {n} does not exist")
    return nodes, elems, loads, supports, ex, nu, sec


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
    nodes, elems, loads, supports, ex, nu, (area, izz, iyy, tkz, tky, theta, ixx) = read_deck(text)
    t = F(0) if tol in (None, "0", 0) else tolerance(tol) if isinstance(tol, str) else F(tol)
    G = ex / (2 * (1 + nu))
    free = [(n, d) for n in sorted(nodes) for d in DIRS if (n, d) not in supports]
    dof = {nd: k for k, nd in enumerate(free)}
    parts, emap = [], {}
    for k, (i, j) in enumerate(elems, 1):
        L, xp, yp, zp = _axes(nodes[i], nodes[j], theta)

        def row(pairs):
            g = {}
            for (n, dd), v in pairs:
                if v and (n, dd) in dof:
                    g[dof[(n, dd)]] = g.get(dof[(n, dd)], F(0)) + v
            return g

        def proj(n, axis, rot):                        # local component along `axis` of node n's displacement/rotation
            names = ("RX", "RY", "RZ") if rot else ("X", "Y", "Z")
            return [((n, names[q]), axis[q]) for q in range(3)]

        def neg(lst):
            return [(key, -v) for key, v in lst]

        def sc(lst, s):
            return [(key, s * v) for key, v in lst]
        a = row(proj(j, xp, False) + neg(proj(i, xp, False)))
        tt = row(proj(j, xp, True) + neg(proj(i, xp, True)))
        bz = row(proj(i, zp, True) + neg(proj(j, zp, True)))
        cz = row(proj(i, zp, True) + proj(j, zp, True) + sc(proj(j, yp, False), -2 / L) + sc(proj(i, yp, False), 2 / L))
        by = row(proj(i, yp, True) + neg(proj(j, yp, True)))
        cy = row(proj(i, yp, True) + proj(j, yp, True) + sc(proj(j, zp, False), 2 / L) + sc(proj(i, zp, False), -2 / L))
        emap[k] = {"part": len(parts), "L": L, "a": a, "t": tt, "bz": bz, "cz": cz, "by": by, "cy": cy}
        parts.append({"t": t, "terms": [(ex * area / L, a), (G * ixx / L, tt), (ex * izz / L, bz),
                                        (3 * ex * izz / L, cz), (ex * iyy / L, by), (3 * ex * iyy / L, cy)]})
    f = [F(0)] * len(free)
    for (n, d), v in loads.items():
        if (n, d) in dof:
            f[dof[(n, d)]] += v
    return parts, f, dof, emap


def _target(s):
    s = s.strip().upper()
    if not (s.startswith("U(") and s.endswith(")")):
        raise Frame3DError(f"target {s}: write U(node,X|Y|Z|RX|RY|RZ)")
    n, d = s[2:-1].split(",")
    d = d.strip()
    if d not in DIRS:
        raise Frame3DError(f"target {s}: direction X Y Z RX RY RZ")
    return int(n), d


def range_of(text, tol, target):
    """A proved range of one displacement for every modulus in the box (first order)."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    parts, f, dof, _ = energy_system(text, tol)
    nd, d = _target(target)
    if (nd, d) not in dof:
        return {"target": target, "nominal": "0", "proved_range": ["0", "0"], "note": "a supported direction"}
    e = [F(0)] * len(dof)
    e[dof[(nd, d)]] = F(1)
    r = ZE.certify(parts, f, e, len(dof))
    return {"target": target, "nominal": _show(r["nominal"]), "lo": r["lo"], "hi": r["hi"],
            "proved_range": [_show(r["lo"], -1), _show(r["hi"], 1)],
            "note": "FIRST ORDER (version 1): an enclosure for every modulus in the box"}


def judge(text, tol, target, le=None, ge=None):
    """A displacement requirement judged by ZTL over the proved range."""
    from . import judge_ztl as J  # noqa: F401
    from znumjudge import parse_quantities, judge_sheet_claim
    r = range_of(text, tol, target)
    lo, hi = r.get("lo", F(0)), r.get("hi", F(0))
    fr = lambda x: f"{x.numerator}/{x.denominator}"
    q, m = parse_quantities(f"u=[{fr(lo)},{fr(hi)}] earned:frame3d-energy-path")
    claims = []
    if le is not None:
        claims.append(f"u <= {fr(F(le))}")
    if ge is not None:
        claims.append(f"u >= {fr(F(ge))}")
    out = dict(r)
    out.pop("lo", None); out.pop("hi", None)
    if claims:
        res = judge_sheet_claim(" & ".join(claims), q, m)
        out["verdict"] = res["disposition"] + (f" ({res['polarity']})" if res.get("polarity") else "")
    return out


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
