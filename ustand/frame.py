"""A PLANE FRAME (an ANSYS input deck, BEAM3 elements) judged by ZTL zenergy (2026-11-01, the curator's plan: frames
after trusses, ZTL first).

A 2D Euler-Bernoulli beam element, nodes i, j, length L, direction (c, s), modulus E, area A, second moment I. Its
strain energy, in the element's own axes (axial u, transverse v, rotation th), is EXACTLY
    U = (E A / 2L)(u_j - u_i)^2 + (E I / 2L) [ (th_i - th_j)^2 + 3 (th_i + th_j - 2 (v_j - v_i)/L)^2 ]
(expand: 4 th_i^2 + 4 th_j^2 + 4 th_i th_j - 12 psi (th_i + th_j) + 12 psi^2, psi = (v_j - v_i)/L — the textbook
matrix (E I / L^3)[12 6L -12 6L; ...]). So the element stiffness is THREE rank-one terms that share ONE factor, E:
    (E A / L) a a^T,   (E I / L) b b^T,   (3 E I / L) c c^T
with a, b, c rational rows over the element's global displacements (u = c ux + s uy, v = -s ux + c uy). An element
with its modulus anywhere in E (1 +- t) is a part of three terms — the case lean/ZEnergy.lean's
`target_first_grouped` is for (ZTL), on top of ZNet's step 4.

    python3 -m ustand.frame deck.txt --tol 0.5% --req "U(12,Y) >= -0.0251"     a requirement
    python3 -m ustand.frame deck.txt --tol 0.5% --range "U(12,Y)"               the proved enclosure (not exact)
            U(node,X|Y) a displacement, ROT(node) a rotation

THE DECK (the subset read; anything else is REFUSED aloud):
    N, id, x, y                  a node
    E, i, j                      an element between nodes i and j (one material, one real constant)
    MP, EX, 1, value             Young's modulus (nominal)
    R, 1, area, izz              the section: area and second moment
    F, node, FX|FY|MZ, value     a nodal force or moment
    D, node, UX|UY|ROTZ, 0       a support (zero displacement or rotation)
    /PREP7, ET (BEAM3 / 3), MAT, REAL, TYPE, comments (!) — read and skipped.
Lengths must be rational (an irrational length is refused: the stiffness would not be exact).

WHAT IT DOES NOT DO (yet), said: the box path (zlin) is not wired for frames — a requirement the energy path cannot
decide comes back OPEN, not guessed; no shear deformation (Timoshenko), no second-order (P-delta) effects, no member
checks (stress, buckling) — displacements and rotations only.
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction as F

from . import bricks as B
from .spice import tolerance
from .truss import _num, _sqrt, _show


class FrameError(B.BrickError):
    pass


def read_deck(text):
    nodes, elems, loads, supports = {}, [], {}, set()
    ex = sec = None
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.split("!")[0].strip()
        if not line or line.startswith("/"):
            continue
        f = [x.strip() for x in (line.split(",") if "," in line else line.split())]
        cmd, where = f[0].upper(), f"line {ln}"
        if cmd == "N":
            nodes[int(f[1])] = (_num(f[2], where), _num(f[3], where) if len(f) > 3 and f[3] else F(0))
        elif cmd == "E":
            elems.append((int(f[1]), int(f[2])))
        elif cmd == "MP":
            if f[1].upper() != "EX":
                raise FrameError(f"{where}: MP {f[1]} — only EX is read")
            if ex is not None and _num(f[3], where) != ex:
                raise FrameError(f"{where}: a second material — one EX only (version 1)")
            ex = _num(f[3], where)
        elif cmd == "R":
            if len(f) < 4:
                raise FrameError(f"{where}: R needs the area and the second moment (R, 1, area, izz)")
            s = (_num(f[2], where), _num(f[3], where))
            if sec is not None and s != sec:
                raise FrameError(f"{where}: a second real constant — one section only (version 1)")
            sec = s
        elif cmd == "F":
            d = f[2].upper()
            if d not in ("FX", "FY", "MZ"):
                raise FrameError(f"{where}: load {f[2]} — FX, FY or MZ only")
            k = (int(f[1]), {"FX": "X", "FY": "Y", "MZ": "R"}[d])
            loads[k] = loads.get(k, F(0)) + _num(f[3], where)
        elif cmd == "D":
            d = f[2].upper()
            if d not in ("UX", "UY", "ROTZ"):
                raise FrameError(f"{where}: support {f[2]} — UX, UY or ROTZ only")
            if _num(f[3], where) != 0:
                raise FrameError(f"{where}: a prescribed nonzero displacement — not read (version 1)")
            supports.add((int(f[1]), {"UX": "X", "UY": "Y", "ROTZ": "R"}[d]))
        elif cmd == "ET":
            if f[2].upper() not in ("BEAM3", "3"):
                raise FrameError(f"{where}: element type {f[2]} — only BEAM3 (2D beam)")
        elif cmd in ("MAT", "REAL", "TYPE"):
            if len(f) > 1 and f[1] not in ("1", ""):
                raise FrameError(f"{where}: {cmd},{f[1]} — one material and one real constant only")
        else:
            raise FrameError(f"{where}: {f[0]} — not read (only N E MP R F D ET MAT REAL TYPE)")
    if not nodes or not elems:
        raise FrameError("no nodes or no elements")
    if ex is None or sec is None:
        raise FrameError("no MP,EX or no R (the modulus and the section are needed)")
    for i, j in elems:
        for n in (i, j):
            if n not in nodes:
                raise FrameError(f"element {i}-{j}: node {n} does not exist")
    return nodes, elems, loads, supports, ex, sec


def energy_system(text, tol):
    """K(p) = sum_e p_e (three rank-one terms of element e), p_e in [1 - t, 1 + t]; f the loads."""
    parts, f, dof, _, _ = energy_system_full(text, tol)
    return parts, f, dof


def read_height(text):
    """The section's HEIGHT, BEAM3's third real constant (R, 1, area, izz, height) — None if not given."""
    for raw in text.splitlines():
        line = raw.split("!")[0].strip()
        fl = [x.strip() for x in (line.split(",") if "," in line else line.split())]
        if fl and fl[0].upper() == "R" and len(fl) > 4 and fl[4]:
            return _num(fl[4], "R")
    return None


def energy_system_full(text, tol):
    """energy_system, plus per element its part index and rows (a, b, c) and length, and (E, A, I, h)."""
    nodes, elems, loads, supports, ex, (area, izz) = read_deck(text)
    t = F(0) if tol in (None, "0", 0) else tolerance(tol) if isinstance(tol, str) else F(tol)
    free = [(n, d) for n in sorted(nodes) for d in "XYR" if (n, d) not in supports]
    dof = {nd: k for k, nd in enumerate(free)}
    parts = []
    emap = {}
    for k, (i, j) in enumerate(elems, 1):
        dx, dy = nodes[j][0] - nodes[i][0], nodes[j][1] - nodes[i][1]
        L = _sqrt(dx * dx + dy * dy)
        if not L:
            raise FrameError(f"element {k} ({i}-{j}): its length is irrational or zero — not exact (version 1)")
        c, s = dx / L, dy / L

        def row(pairs):
            g = {}
            for (n, d), v in pairs:
                if v and (n, d) in dof:
                    g[dof[(n, d)]] = g.get(dof[(n, d)], F(0)) + v
            return g
        # u = c ux + s uy (axial), v = -s ux + c uy (transverse)
        a = row([((j, "X"), c), ((j, "Y"), s), ((i, "X"), -c), ((i, "Y"), -s)])
        b = row([((i, "R"), F(1)), ((j, "R"), F(-1))])
        cc = row([((i, "R"), F(1)), ((j, "R"), F(1)),
                  ((j, "X"), 2 * s / L), ((j, "Y"), -2 * c / L), ((i, "X"), -2 * s / L), ((i, "Y"), 2 * c / L)])
        emap[k] = {"part": len(parts), "a": a, "b": b, "c": cc, "L": L, "t": t}
        parts.append({"t": t, "terms": [(ex * area / L, a), (ex * izz / L, b), (3 * ex * izz / L, cc)]})
    f = [F(0)] * len(free)
    for (n, d), v in loads.items():
        if (n, d) in dof:
            f[dof[(n, d)]] += v
    return parts, f, dof, emap, (ex, area, izz, read_height(text))


# ----------------------------------------------------------------------------------------------------------------
# MEMBER STRESSES (2026-11-01). At an end of element k: N = (E A / L)(a.u) and the end moments
# M_i = (E I / L)((b + 3c).u), M_j = (E I / L)((-b + 3c).u) (the textbook 4th + 2th - 6psi: b = th_i - th_j,
# c = th_i + th_j - 2psi). An extreme fibre carries sigma = N/A +- M (h/2)/I = E p_k (g.u),
#   g = a/L +- (h/2)/L (+-b + 3c),
# an output scaled by the element's own factor — ZTL zenergy.certify_scaled. Both fibres at both ends are
# checked, so the sign convention of the moment does not matter. The check is EN 1993-1-1 6.2.1(7)'s elastic,
# conservative one: |sigma| <= fy / gamma_M0 at every fibre. NOT here: member buckling (6.3 needs buckling lengths
# from a stability analysis), shear, lateral-torsional buckling.

def fibre_vectors(emap, k, h):
    """The four fibre functionals of element k: (end, side, g) with sigma = E p_k (g.u)."""
    m = emap[k]
    L, a, b, c = m["L"], m["a"], m["b"], m["c"]
    out = []
    for end, sb in (("I", 1), ("J", -1)):
        for side, sg in (("TOP", 1), ("BOT", -1)):
            g = {}
            for i, v in a.items():
                g[i] = g.get(i, F(0)) + v / L
            for i, v in b.items():
                g[i] = g.get(i, F(0)) + sg * (h / 2) / L * sb * v
            for i, v in c.items():
                g[i] = g.get(i, F(0)) + sg * (h / 2) / L * 3 * v
            out.append((end, side, {i: v for i, v in g.items() if v}))
    return out


def fibre_ranges_many(text, tol, ks, ctx=None, jobs=1):
    """fibre_ranges for many elements at once: every fibre's output in ONE ZTL zenergy.certify_many call (the shared
    work once, the outputs over `jobs` processes) — results equal fibre_ranges' (2026-11-01)."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    parts, f, dof, emap, (ex, area, izz, h) = ctx or energy_system_full(text, tol)
    if h is None:
        raise FrameError("member stresses need the section height: R, 1, area, izz, height")
    n = len(dof)
    items, es = [], []
    for k in ks:
        if k not in emap:
            raise FrameError(f"SIG({k}): no element {k}")
        for end, side, g in fibre_vectors(emap, k, h):
            e = [F(0)] * n
            for i, v in g.items():
                e[i] = v
            items.append((k, end, side, e))
            if any(e):
                es.append(e)
    rs = iter(ZE.certify_many(parts, f, es, n, jobs=jobs))
    out = {k: [] for k in ks}
    for k, end, side, e in items:
        if not any(e):
            out[k].append({"end": end, "side": side, "lo": F(0), "hi": F(0), "nominal": F(0), "e": e, "sc": None})
            continue
        sc = ZE.scaled_from(next(rs), parts, emap[k]["part"])
        lo, hi = sorted([ex * sc["lo"], ex * sc["hi"]])
        out[k].append({"end": end, "side": side, "lo": lo, "hi": hi, "nominal": ex * sc["nominal"], "e": e, "sc": sc})
    return out


def fibre_ranges(text, tol, k, ctx=None):
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    parts, f, dof, emap, (ex, area, izz, h) = ctx or energy_system_full(text, tol)
    if h is None:
        raise FrameError("member stresses need the section height: R, 1, area, izz, height")
    if k not in emap:
        raise FrameError(f"SIG({k}): no element {k}")
    n = len(dof)
    res = []
    for end, side, g in fibre_vectors(emap, k, h):
        e = [F(0)] * n
        for i, v in g.items():
            e[i] = v
        if not any(e):
            res.append({"end": end, "side": side, "lo": F(0), "hi": F(0), "nominal": F(0), "e": e, "sc": None})
            continue
        sc = ZE.certify_scaled(parts, f, e, n, emap[k]["part"])
        lo, hi = sorted([ex * sc["lo"], ex * sc["hi"]])
        res.append({"end": end, "side": side, "lo": lo, "hi": hi, "nominal": ex * sc["nominal"], "e": e, "sc": sc})
    return res


def judge_members(text, tol, checks, jobs=1):
    """checks: [(k, limit)] — |sigma| <= limit at every extreme fibre of element k (EN 1993-1-1 6.2.1(7),
    limit = fy / gamma_M0). EARNED when every fibre's proved range is inside [-limit, limit]; REFUTED when a
    fibre's witness vertex (solved exactly, or its floating enclosure) is wholly outside; OPEN otherwise."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    ctx = energy_system_full(text, tol)
    parts, f, dof, emap, (ex, area, izz, h) = ctx
    n = len(dof)
    rows = []
    allfr = fibre_ranges_many(text, tol, [k for k, _ in checks], ctx, jobs)
    for k, lim in checks:
        fr = allfr[k]
        ok = all(-lim <= r["lo"] and r["hi"] <= lim for r in fr)
        row = {"check": f"|SIG({k})| <= {lim}", "fibres": [{"end": r["end"], "side": r["side"],
               "nominal": _show(r["nominal"]), "proved_range": [_show(r["lo"], -1), _show(r["hi"], 1)]} for r in fr]}
        if ok:
            row["verdict"] = "EARNED"
        else:
            row["verdict"] = "OPEN"
            worst = max((r for r in fr if r["sc"] is not None), key=lambda r: abs(r["nominal"]), default=None)
            if worst is not None:
                up = worst["nominal"] >= 0
                pk = emap[k]["part"]
                sl = worst["sc"]["base"]["slopes"]
                # push the bracket outward; the element's own factor up (|sigma| grows with p_k for this sign)
                ps = [1 + (pp["t"] if (s_ > 0) == up and s_ != 0 else -pp["t"] if s_ != 0 else 0)
                      for pp, s_ in zip(parts, sl)]
                ps[pk] = 1 + parts[pk]["t"]
                if n <= ZE.EXACT_UP_TO:
                    wl = wh = ZE.value_at(parts, f, worst["e"], n, ps)
                else:
                    wl, wh = ZE.value_enclosure_fp(parts, f, worst["e"], n, ps)
                lo_, hi_ = sorted([ex * ps[pk] * wl, ex * ps[pk] * wh])
                row["witness"] = {"end": worst["end"], "side": worst["side"], "value": _show(hi_ if up else lo_)}
                if (lo_ > lim) if up else (hi_ < -lim):
                    row["verdict"] = "REFUTED"
        rows.append(row)
    vs = [r["verdict"] for r in rows]
    verdict = "REFUTED" if "REFUTED" in vs else "EARNED" if all(x == "EARNED" for x in vs) else "OPEN"
    return {"verdict": verdict, "path": "member stresses: zenergy.certify_scaled on every extreme fibre",
            "checks": rows, "unknowns": n}


def _target(text):
    import re
    m = re.match(r"^\s*(?:U\(\s*(\d+)\s*,\s*([XYxy])\s*\)|ROT\(\s*(\d+)\s*\))\s*$", text)
    if not m:
        raise FrameError(f"{text!r}: a target is U(node,X), U(node,Y) or ROT(node)")
    return (int(m.group(1)), m.group(2).upper()) if m.group(1) else (int(m.group(3)), "R")


def _req(text):
    import re
    m = re.match(r"^\s*((?:U|ROT)\([^)]*\))\s*(<=|>=)\s*(\S+)\s*$", text)
    if not m:
        raise FrameError(f"{text!r}: a requirement is U(node,X|Y) or ROT(node), <= or >=, a value")
    n, d = _target(m.group(1))
    return n, d, m.group(2), _num(m.group(3), text)


def _name(n, d):
    return f"ROT({n})" if d == "R" else f"U({n},{d})"


def judge(text, tol, requirements):
    from . import judge_ztl  # noqa: F401  (puts ZTL on the path)
    import zenergy as ZE
    parts, f, dof = energy_system(text, tol)
    n = len(dof)
    rows = []
    for (nd, d, op, v) in requirements:
        if (nd, d) not in dof:
            raise FrameError(f"{_name(nd, d)}: not a free displacement of this frame")
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
            "requirements": rows, "unknowns": n, "elements": len(parts),
            "checked_by": "ZTL zenergy: exact solves up to ZTL zenergy.EXACT_UP_TO unknowns (120; residual checked); above them float solves with "
                          "exact residuals and lambda_min(K0) proved by a floating Cholesky — PREMISE: IEEE 754 "
                          "binary64 and LAPACK (Higham Thm 10.3, cited, not in Lean; ZTL KNOWN-LIMITS.md); the "
                          "bound's algebra is ZTL lean/ZNet.lean step 4 with lean/ZEnergy.lean target_first_grouped "
                          "(zero axioms); the floating path's error assembly is on paper (Lean next)"}


def range_of(text, tol, target):
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    parts, f, dof = energy_system(text, tol)
    nd, d = _target(target)
    e = [F(0)] * len(dof)
    e[dof[(nd, d)]] = F(1)
    r = ZE.certify(parts, f, e, len(dof))
    return {"target": target, "nominal": _show(r["nominal"]), "proved_range": [_show(r["lo"], -1), _show(r["hi"], 1)],
            "note": "an enclosure (first order exact + a proved rest), not the exact range"}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    try:
        text = open(argv[0], encoding="utf-8").read()
        tol = argv[argv.index("--tol") + 1] if "--tol" in argv else "0"
        import re as _re
        raw = [argv[i + 1] for i, a in enumerate(argv) if a == "--req"]
        sig = [x for x in raw if _re.match(r"^\s*SIG\(", x, _re.I)]
        if sig:                                       # member stress checks: SIG(k) <= limit
            checks = []
            for x in sig:
                m = _re.match(r"^\s*SIG\(\s*(\d+)\s*\)\s*<=\s*(\S+)\s*$", x, _re.I)
                if not m:
                    raise FrameError(f"{x!r}: a member check is SIG(element) <= limit (|sigma| at every fibre)")
                checks.append((int(m.group(1)), _num(m.group(2), x)))
            jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 1
            print(json.dumps(judge_members(text, tol, checks, jobs=jobs), indent=1, ensure_ascii=False))
            return 0
        reqs = [_req(x) for x in raw]
        ranges = [argv[i + 1] for i, a in enumerate(argv) if a == "--range"]
        out = {t: range_of(text, tol, t) for t in ranges} if ranges else judge(text, tol, reqs)
    except (B.BrickError, OSError, ValueError, IndexError) as e:
        out = {"verdict": "BRICK ERROR", "why": f"{e}"}
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
