"""A PLANE-STRESS PLATE (an ANSYS-style input deck, triangles) judged by ZTL zenergy (2026-11-01, after the frame:
the same energy path, a membrane element).

THE ELEMENT IS THE CONSTANT-STRAIN TRIANGLE (CST), whatever the ET label says. Nodes 1, 2, 3 at (x_i, y_i), ordered
counterclockwise here (a clockwise triangle is reordered; a degenerate one is refused):
    2A = (x2 - x1)(y3 - y1) - (x3 - x1)(y2 - y1) > 0
    b1 = y2 - y3, b2 = y3 - y1, b3 = y1 - y2,   c1 = x3 - x2, c2 = x1 - x3, c3 = x2 - x1
    eps = Bmat u, u = (u1, v1, u2, v2, u3, v3):
        eps_xx = sum b_i u_i / 2A,  eps_yy = sum c_i v_i / 2A,  gamma_xy = sum (c_i u_i + b_i v_i) / 2A
    D = E/(1 - nu^2) [[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu)/2]] = E D0          (plane stress)
    K_e = th A Bmat^T D Bmat = E (th A) Bmat^T D0 Bmat.
D0 is split by its own EXACT rational LDL^T, D0 = sum_k d_k l_k l_k^T (computed and checked in code, every d_k >= 0;
with nu in (-1, 1/2): d = (1/(1 - nu^2), 1, 1/(2(1 + nu))), l = ((1, nu, 0), (0, 1, 0), (0, 0, 1))), so
    K_e = E sum_k (th A d_k) g_k g_k^T,   g_k = Bmat^T l_k   (a rational row over the element's six displacements)
— THREE rank-one terms sharing ONE factor, the element's modulus: with E anywhere in E (1 +- t) the element is one
part of ZTL zenergy (lean/ZEnergy.lean `target_first_grouped`, as the frame's beam).

    python3 -m ustand.plate deck.txt --tol 0.5% --req "U(42,Y) >= -0.0251"     a requirement
    python3 -m ustand.plate deck.txt --tol 0.5% --range "U(42,Y)"               the proved enclosure (not exact)
            U(node,X|Y) a displacement
    python3 -m ustand.plate deck.txt --tol 0.5% --req "VM(17) <= 235e6"         a stress: S(k,XX|YY|XY) <=|>= v,
            or VM(k) <= v (von Mises), in element k

THE DECK (the subset read; anything else is REFUSED aloud):
    N, id, x, y                  a node
    E, i, j, k                   a triangle (one material, one real constant)
    MP, EX, 1, value             Young's modulus (nominal)
    MP, PRXY, 1, value           Poisson's ratio nu (needed; -1 < nu < 1/2)
    R, 1, thickness              the plate's thickness
    F, node, FX|FY, value        a nodal force
    D, node, UX|UY, 0            a support (zero displacement)
    /PREP7, ET (PLANE2 / PLANE42 / PLANE182 / 2 / 42 / 182 — read as a LABEL only: the element is the CST triangle
    above, not ANSYS's own quadratic triangle or quadrilateral), MAT, REAL, TYPE, comments (!) — read and skipped.
Coordinates, E, nu and thickness must be rational (decimals are read exactly).

WHAT IT DOES NOT DO, said: membrane (in-plane) action only — no bending, no plates in bending (Kirchhoff/Mindlin),
no shells, no 3D; no plane strain; no meshing or geometry beyond the structured rectangles of
examples/plate/gen_plate.py (the deck gives the triangles); one material, one thickness; stresses are the CST's
constant per-element values (S(k,XX|YY|XY), von Mises VM(k) by convexity over the 8 corners of the component box);
the box path (zlin) is not wired for plates — a requirement the energy path cannot
decide comes back OPEN, not guessed. The CST is the crudest membrane element: it passes the patch test (constant
strain is exact) but is stiff in bending-dominated fields — the stand proves the DISCRETE model's displacements, not
the continuum's (MEASURED, bench/stage0/plate_convergence: a clamped 4 x 1 m plate's tip is -45 % on 8 x 2
squares, -0.1 % on 256 x 64 — far beyond a +-0.5 % tolerance on coarse meshes).
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction as F

from . import bricks as B
from .spice import tolerance
from .truss import _num, _show

_ET_OK = ("PLANE2", "PLANE42", "PLANE182", "2", "42", "182")


class PlateError(B.BrickError):
    pass


def read_deck(text):
    nodes, elems, loads, supports = {}, [], {}, set()
    ex = nu = th = None
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.split("!")[0].strip()
        if not line or line.startswith("/"):
            continue
        f = [x.strip() for x in (line.split(",") if "," in line else line.split())]
        cmd, where = f[0].upper(), f"line {ln}"
        if cmd == "N":
            nodes[int(f[1])] = (_num(f[2], where), _num(f[3], where) if len(f) > 3 and f[3] else F(0))
            if len(f) > 4 and f[4] and _num(f[4], where) != 0:
                raise PlateError(f"{where}: a z coordinate — only a plane plate")
        elif cmd == "E":
            if len(f) != 4 or not all(f[1:]):
                raise PlateError(f"{where}: E needs exactly three nodes (a triangle: E, i, j, k)")
            elems.append((int(f[1]), int(f[2]), int(f[3])))
        elif cmd == "MP":
            prop = f[1].upper()
            if prop not in ("EX", "PRXY"):
                raise PlateError(f"{where}: MP {f[1]} — only EX and PRXY are read")
            if len(f) > 2 and f[2] not in ("1", ""):
                raise PlateError(f"{where}: MP for material {f[2]} — one material only (version 1)")
            v = _num(f[3], where)
            if prop == "EX":
                if ex is not None and v != ex:
                    raise PlateError(f"{where}: a second EX — one material only (version 1)")
                ex = v
            else:
                if nu is not None and v != nu:
                    raise PlateError(f"{where}: a second PRXY — one material only (version 1)")
                nu = v
        elif cmd == "R":
            if len(f) < 3:
                raise PlateError(f"{where}: R needs the thickness (R, 1, thickness)")
            if len(f) > 3 and any(x for x in f[3:]):
                raise PlateError(f"{where}: R with more than the thickness — not read (version 1)")
            v = _num(f[2], where)
            if th is not None and v != th:
                raise PlateError(f"{where}: a second real constant — one thickness only (version 1)")
            th = v
        elif cmd == "F":
            d = f[2].upper()
            if d not in ("FX", "FY"):
                raise PlateError(f"{where}: load {f[2]} — FX or FY only")
            k = (int(f[1]), d[1])
            loads[k] = loads.get(k, F(0)) + _num(f[3], where)
        elif cmd == "D":
            d = f[2].upper()
            if d not in ("UX", "UY"):
                raise PlateError(f"{where}: support {f[2]} — UX or UY only")
            if _num(f[3], where) != 0:
                raise PlateError(f"{where}: a prescribed nonzero displacement — not read (version 1)")
            supports.add((int(f[1]), d[1]))
        elif cmd == "ET":
            if len(f) < 3 or f[2].upper() not in _ET_OK:
                raise PlateError(f"{where}: element type {f[2] if len(f) > 2 else '?'} — only a plane label "
                                 f"({', '.join(_ET_OK)}), read as the CST triangle")
        elif cmd in ("MAT", "REAL", "TYPE"):
            if len(f) > 1 and f[1] not in ("1", ""):
                raise PlateError(f"{where}: {cmd},{f[1]} — one material and one real constant only")
        elif cmd == "TRAC":
            continue                                   # the continuum's load: ustand/hypercircle.py reads it
        else:
            raise PlateError(f"{where}: {f[0]} — not read (only N E MP R F D ET MAT REAL TYPE TRAC)")
    if not nodes or not elems:
        raise PlateError("no nodes or no elements")
    if ex is None or nu is None or th is None:
        raise PlateError("no MP,EX, no MP,PRXY or no R (the modulus, Poisson's ratio and the thickness are needed)")
    if ex <= 0 or th <= 0:
        raise PlateError("EX and the thickness must be positive")
    if not (-1 < nu < F(1, 2)):
        raise PlateError(f"PRXY {nu}: plane stress needs -1 < nu < 1/2")
    for el in elems:
        for n in el:
            if n not in nodes:
                raise PlateError(f"element {el}: node {n} does not exist")
    return nodes, elems, loads, supports, ex, nu, th


def d0_ldl(nu):
    """The exact LDL^T of D0 = 1/(1-nu^2) [[1,nu,0],[nu,1,0],[0,0,(1-nu)/2]]: [(d_k, l_k)], checked."""
    s = 1 / (1 - nu * nu)
    D0 = [[s, s * nu, F(0)], [s * nu, s, F(0)], [F(0), F(0), s * (1 - nu) / 2]]
    n = 3
    L = [[F(int(i == j)) for j in range(n)] for i in range(n)]
    d = [F(0)] * n
    for j in range(n):
        d[j] = D0[j][j] - sum(L[j][k] ** 2 * d[k] for k in range(j))
        if d[j] <= 0:
            raise PlateError(f"D0 not positive definite (nu = {nu}): pivot {j + 1} = {d[j]}")
        for i in range(j + 1, n):
            L[i][j] = (D0[i][j] - sum(L[i][k] * L[j][k] * d[k] for k in range(j))) / d[j]
    out = [(d[k], [L[i][k] for i in range(n)]) for k in range(n)]
    for i in range(n):
        for j in range(n):
            if sum(dk * lk[i] * lk[j] for dk, lk in out) != D0[i][j]:
                raise PlateError("internal: LDL^T of D0 does not reproduce D0 exactly")
    return out


def energy_system(text, tol):
    """K(p) = sum_e p_e (three rank-one terms of triangle e), p_e in [1 - t, 1 + t]; f the loads."""
    parts, f, dof, _, _ = energy_system_full(text, tol)
    return parts, f, dof


def energy_system_full(text, tol):
    """energy_system, plus for every element (1-based) its part index (None if every DOF is supported) and its
    strain rows over the free DOFs, and the deck's (E, nu) — what the stresses need (2026-11-01)."""
    nodes, elems, loads, supports, ex, nu, th = read_deck(text)
    t = F(0) if tol in (None, "0", 0) else tolerance(tol) if isinstance(tol, str) else F(tol)
    free = [(n, d) for n in sorted(nodes) for d in "XY" if (n, d) not in supports]
    dof = {nd: k for k, nd in enumerate(free)}
    ldl = [(dk, lk) for dk, lk in d0_ldl(nu) if dk != 0]
    parts = []
    emap = {}
    for k, (n1, n2, n3) in enumerate(elems, 1):
        (x1, y1), (x2, y2), (x3, y3) = nodes[n1], nodes[n2], nodes[n3]
        a2 = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        if a2 == 0:
            raise PlateError(f"element {k} ({n1}-{n2}-{n3}): degenerate (zero area)")
        if a2 < 0:                                     # clockwise: reorder counterclockwise
            n2, n3 = n3, n2
            (x2, y2), (x3, y3) = (x3, y3), (x2, y2)
            a2 = -a2
        b = (y2 - y3, y3 - y1, y1 - y2)
        c = (x3 - x2, x1 - x3, x2 - x1)
        ns = (n1, n2, n3)
        # the three rows of Bmat over (node, dir): eps_xx, eps_yy, gamma_xy
        rows = [[((ns[i], "X"), b[i] / a2) for i in range(3)],
                [((ns[i], "Y"), c[i] / a2) for i in range(3)],
                [((ns[i], "X"), c[i] / a2) for i in range(3)] + [((ns[i], "Y"), b[i] / a2) for i in range(3)]]
        area = a2 / 2
        emap[k] = {"part": None, "rows": [{dof[nd]: v for nd, v in r if v and nd in dof} for r in rows]}
        terms = []
        for dk, lk in ldl:
            g = {}
            for r, lr in enumerate(lk):
                if not lr:
                    continue
                for nd, v in rows[r]:
                    if v and nd in dof:
                        g[dof[nd]] = g.get(dof[nd], F(0)) + lr * v
            g = {i: v for i, v in g.items() if v}
            if g:
                terms.append((ex * th * area * dk, g))
        if terms:
            emap[k]["part"] = len(parts)
            parts.append({"t": t, "terms": terms})
    f = [F(0)] * len(free)
    for (n, d), v in loads.items():
        if n not in nodes:
            raise PlateError(f"a load at node {n}, which does not exist")
        if (n, d) in dof:
            f[dof[(n, d)]] += v
    for k in emap:
        emap[k]["t"] = t
    return parts, f, dof, emap, (ex, nu)


# ----------------------------------------------------------------------------------------------------------------
# STRESSES (2026-11-01). In element k, sigma = E p_k D0 B u: the bracket is a LINEAR output of u (zenergy proves its
# range), times the element's own factor p_k in [1 - t, 1 + t] — an interval product, sound (it forgets that p_k
# also moves the bracket; that only widens). Von Mises: sigma_vm^2 = sx^2 - sx sy + sy^2 + 3 txy^2 is CONVEX in
# (sx, sy, txy), so over the box of the three components its maximum is at a corner — the 8 corners are checked
# exactly. (The joint box of the components forgets their correlation: sound, possibly wide.)

_COMP = {"XX": 0, "YY": 1, "XY": 2}


def _d0(nu):
    k = 1 / (1 - nu * nu)
    return [[k, k * nu, F(0)], [k * nu, k, F(0)], [F(0), F(0), k * (1 - nu) / 2]]


def stress_output(text, tol, k, comp, ctx=None):
    """[lo, hi] proved for sigma_comp of element k; nominal; and what a witness needs."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    parts, f, dof, emap, (ex, nu) = ctx or energy_system_full(text, tol)
    if k not in emap:
        raise PlateError(f"S({k},{comp}): no element {k}")
    n = len(dof)
    D0 = _d0(nu)
    c = _COMP[comp]
    e = [F(0)] * n
    for r in range(3):
        if D0[c][r]:
            for i, v in emap[k]["rows"][r].items():
                e[i] += D0[c][r] * v
    t = emap[k]["t"]
    if not any(e):
        z = F(0)
        return {"lo": z, "hi": z, "nominal": z, "w": None, "e": e}
    pk = emap[k]["part"]
    if pk is None:                                   # every DOF of the element supported: no stress moves
        w = ZE.certify(parts, f, e, n)
        cands = [ex * q * wv for q in (1 - t, 1 + t) for wv in (w["lo"], w["hi"])]
        return {"lo": min(cands), "hi": max(cands), "nominal": ex * w["nominal"], "w": w, "e": e}
    # the element's own factor merged into the exact first order (ZTL zenergy.certify_scaled, 2026-11-01)
    sc = ZE.certify_scaled(parts, f, e, n, pk)
    lo, hi = sorted([ex * sc["lo"], ex * sc["hi"]])
    return {"lo": lo, "hi": hi, "nominal": ex * sc["nominal"], "w": sc["base"], "e": e}


def _stress_target(text):
    import re
    m = re.match(r"^\s*S\(\s*(\d+)\s*,\s*(XX|YY|XY)\s*\)\s*$", text, re.I)
    if m:
        return ("S", int(m.group(1)), m.group(2).upper())
    m = re.match(r"^\s*VM\(\s*(\d+)\s*\)\s*$", text, re.I)
    if m:
        return ("VM", int(m.group(1)), None)
    return None


def judge_stress(text, tol, requirements):
    """Requirements on stresses: ("S", k, comp, op, v) or ("VM", k, None, "<=", v). EARNED when the proved range
    meets each; a component is REFUTED at the witness vertex of its bracket (solved exactly, or its floating
    enclosure wholly beyond); von Mises undecided stays OPEN — never guessed."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    ctx = energy_system_full(text, tol)
    parts, f, dof, emap, (ex, nu) = ctx
    n = len(dof)
    rows = []
    for kind, k, comp, op, v in requirements:
        if kind == "S":
            r = stress_output(text, tol, k, comp, ctx)
            row = {"requirement": f"S({k},{comp}) {op} {v}", "nominal": _show(r["nominal"]),
                   "proved_range": [_show(r["lo"], -1), _show(r["hi"], 1)]}
            if (r["hi"] <= v) if op == "<=" else (r["lo"] >= v):
                row["verdict"] = "EARNED"
            elif r["w"] is None:
                row["verdict"] = "REFUTED" if ((r["lo"] > v) if op == "<=" else (r["hi"] < v)) else "OPEN"
            else:
                up = op == "<="
                pk = emap[k]["part"]
                t = emap[k]["t"]
                # push the bracket w toward the violation, and the element's own factor too (sign of w at the end)
                ps = [1 + (pp["t"] if (sl > 0) == up and sl != 0 else -pp["t"] if sl != 0 else 0)
                      for pp, sl in zip(parts, r["w"]["slopes"])]
                if n <= ZE.EXACT_UP_TO:
                    wl = wh = ZE.value_at(parts, f, r["e"], n, ps)
                else:
                    wl, wh = ZE.value_enclosure_fp(parts, f, r["e"], n, ps)
                pkv = ps[pk] if pk is not None else F(1)
                sl, sh = sorted([ex * pkv * wl, ex * pkv * wh])
                row["witness_value"] = _show(sh if up else sl)
                row["verdict"] = "REFUTED" if ((sl > v) if up else (sh < v)) else "OPEN"
        else:
            comps = [stress_output(text, tol, k, c, ctx) for c in ("XX", "YY", "XY")]
            best = F(0)
            for sx in (comps[0]["lo"], comps[0]["hi"]):
                for sy in (comps[1]["lo"], comps[1]["hi"]):
                    for txy in (comps[2]["lo"], comps[2]["hi"]):
                        best = max(best, sx * sx - sx * sy + sy * sy + 3 * txy * txy)
            nom = [c["nominal"] for c in comps]
            vm2n = nom[0] ** 2 - nom[0] * nom[1] + nom[1] ** 2 + 3 * nom[2] ** 2
            row = {"requirement": f"VM({k}) <= {v}", "nominal_vm_squared": _show(vm2n),
                   "proved_max_vm_squared": _show(best, 1)}
            row["verdict"] = "EARNED" if (v >= 0 and best <= v * v) else ("REFUTED" if v < 0 else "OPEN")
        rows.append(row)
    vs = [r["verdict"] for r in rows]
    verdict = "REFUTED" if "REFUTED" in vs else "EARNED" if all(x == "EARNED" for x in vs) else "OPEN"
    return {"verdict": verdict, "path": "stresses: zenergy on the strain bracket, times the element's factor",
            "requirements": rows, "unknowns": n}


def _target(text):
    import re
    m = re.match(r"^\s*U\(\s*(\d+)\s*,\s*([XYxy])\s*\)\s*$", text)
    if not m:
        raise PlateError(f"{text!r}: a target is U(node,X) or U(node,Y)")
    return int(m.group(1)), m.group(2).upper()


def _sreq(text):
    """A stress requirement: S(k,XX|YY|XY) <= | >= value, or VM(k) <= value; None if it is not one."""
    import re
    m = re.match(r"^\s*((?:S|VM)\([^)]*\))\s*(<=|>=)\s*(\S+)\s*$", text, re.I)
    if not m:
        return None
    t = _stress_target(m.group(1))
    if t is None:
        raise PlateError(f"{text!r}: a stress target is S(element,XX|YY|XY) or VM(element)")
    if t[0] == "VM" and m.group(2) != "<=":
        raise PlateError(f"{text!r}: von Mises takes an upper bound only (VM(k) <= value)")
    return t[0], t[1], t[2], m.group(2), _num(m.group(3), text)


def _req(text):
    import re
    m = re.match(r"^\s*(U\([^)]*\))\s*(<=|>=)\s*(\S+)\s*$", text)
    if not m:
        raise PlateError(f"{text!r}: a requirement is U(node,X|Y), <= or >=, a value")
    n, d = _target(m.group(1))
    return n, d, m.group(2), _num(m.group(3), text)


def _name(n, d):
    return f"U({n},{d})"


def judge(text, tol, requirements):
    from . import judge_ztl  # noqa: F401  (puts ZTL on the path)
    import zenergy as ZE
    parts, f, dof = energy_system(text, tol)
    n = len(dof)
    rows = []
    for (nd, d, op, v) in requirements:
        if (nd, d) not in dof:
            raise PlateError(f"{_name(nd, d)}: not a free displacement of this plate")
        e = [F(0)] * n
        e[dof[(nd, d)]] = F(1)
        r = ZE.certify(parts, f, e, n)       # exact solves up to ZE.EXACT_UP_TO unknowns, the floating path above
        row = {"requirement": f"{_name(nd, d)} {op} {v}", "nominal": _show(r["nominal"]),
               "proved_range": [_show(r["lo"], -1), _show(r["hi"], 1)],
               "first_order": _show(r["first"]), "rest": _show(r["rest"])}
        if (r["hi"] <= v) if op == "<=" else (r["lo"] >= v):
            row["verdict"] = "EARNED"
        else:
            up = op == "<="
            ps = [1 + (p["t"] if (sl > 0) == up and sl != 0 else -p["t"] if sl != 0 else 0)
                  for p, sl in zip(parts, r["slopes"])]
            if n <= ZE.EXACT_UP_TO:
                w = wl = wh = ZE.value_at(parts, f, e, n, ps)
            else:                                     # the floating path at the vertex: its whole enclosure must cross
                wl, wh = ZE.value_enclosure_fp(parts, f, e, n, ps)
                w = wh if up else wl
            row["witness_value"] = _show(w)
            row["verdict"] = "REFUTED" if ((wl > v) if up else (wh < v)) else "OPEN"
        rows.append(row)
    vs = [r["verdict"] for r in rows]
    verdict = "REFUTED" if "REFUTED" in vs else "EARNED" if all(x == "EARNED" for x in vs) else "OPEN"
    return {"verdict": verdict, "path": "energy norm (ZTL zenergy): first order exact + a proved rest",
            "element": "CST (constant-strain triangle), plane stress",
            "requirements": rows, "unknowns": n, "elements": len(parts),
            "checked_by": "ZTL zenergy: exact solves up to ZTL zenergy.EXACT_UP_TO unknowns (120; residual checked); above them float solves with "
                          "exact residuals and lambda_min(K0) proved by a floating Cholesky — PREMISE: the machine obeys "
                          "IEEE 754's rounding model (Higham Thm 10.3, any summation order, proved in lean/ZHigham.lean); the "
                          "bound's algebra is ZTL lean/ZNet.lean step 4 with lean/ZEnergy.lean target_first_grouped "
                          "(zero axioms); the floating path's error assembly is lean/ZFloatPath.lean"}


def range_of(text, tol, target):
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    parts, f, dof = energy_system(text, tol)
    nd, d = _target(target)
    if (nd, d) not in dof:
        raise PlateError(f"{target}: not a free displacement of this plate")
    e = [F(0)] * len(dof)
    e[dof[(nd, d)]] = F(1)
    r = ZE.certify(parts, f, e, len(dof))
    return {"target": target, "nominal": _show(r["nominal"]), "proved_range": [_show(r["lo"], -1), _show(r["hi"], 1)],
            "unknowns": len(dof),
            "note": "an enclosure (first order exact + a proved rest), not the exact range"}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    try:
        text = open(argv[0], encoding="utf-8").read()
        tol = argv[argv.index("--tol") + 1] if "--tol" in argv else "0"
        raw = [argv[i + 1] for i, a in enumerate(argv) if a == "--req"]
        sreqs = [r for r in (_sreq(x) for x in raw) if r is not None]
        reqs = [_req(x) for x in raw if _sreq(x) is None]
        ranges = [argv[i + 1] for i, a in enumerate(argv) if a == "--range"]
        if ranges:
            out = {}
            for t in ranges:
                st = _stress_target(t)
                if st and st[0] == "S":
                    r = stress_output(text, tol, st[1], st[2])
                    out[t] = {"nominal": _show(r["nominal"]), "proved_range": [_show(r["lo"], -1), _show(r["hi"], 1)]}
                else:
                    out[t] = range_of(text, tol, t)
        elif sreqs and not reqs:
            out = judge_stress(text, tol, sreqs)
        else:
            out = judge(text, tol, reqs)
            if sreqs:
                so = judge_stress(text, tol, sreqs)
                out["requirements"] += so["requirements"]
                vs = [r["verdict"] for r in out["requirements"]]
                out["verdict"] = "REFUTED" if "REFUTED" in vs else "EARNED" if all(x == "EARNED" for x in vs) else "OPEN"
    except (B.BrickError, OSError, ValueError, IndexError) as e:
        out = {"verdict": "BRICK ERROR", "why": f"{e}"}
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
