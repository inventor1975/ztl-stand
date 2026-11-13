# -*- coding: utf-8 -*-
"""ASSEMBLY — a plane linear elastic model stated ELEMENT BY ELEMENT, with proved ranges of its displacements and of
its members' forces.

WHY (2026-11-13). The stand had the solver and no door to it. ZTL's `zenergy` proves, for a stiffness that is a sum
of rank-one terms K(p) = sum_k p_k w_k g_k g_k^T with every p_k in [1 - t_k, 1 + t_k], a two-sided range of any
linear output of the solution of K u = f — exactly up to 120 unknowns, above that by a floating solve whose residual
and smallest eigenvalue are proved. `truss`, `frame` and `plate` build such terms from an ANSYS deck, one material
for all members, and are reached from a command line only. MEASURED on an engineering task: a roof diaphragm —
chords and collectors as axial bars, deck as shear panels, braced frames as springs — could not be stated to the
stand at all, and a model that had every input for it left the table of its results empty.

A bar, a spring to ground and a rectangular pure-shear panel are ONE rank-one term each:

    bar     a - b, axial stiffness k = EA / L          w = k,          g = c . (u_b - u_a), c the unit vector a -> b
    spring  a node's X or Y to ground, stiffness k     w = k,          g = that displacement
    panel   rectangle bl, br, tr, tl; shear stiffness  w = G' a b,     g = gamma, the panel's shear strain:
            G' (force per length; shear flow q = G' gamma)             gamma = [(u_tl - u_bl) + (u_tr - u_br)] / (2 b)
                                                                             + [(v_br - v_bl) + (v_tr - v_tl)] / (2 a)

(u along X, v along Y; a the panel's width in X, b its height in Y; the strain energy of the panel is G' a b gamma^2
/ 2, a constant shear flow over it.) Each element's stiffness is a number or a range [low, high]; a range is the
element's own tolerance, independent of every other element's.

    solve({"nodes": {"n1": [0, 0], ...}, "fixed": [["n1", "X"], ["n1", "Y"]],
           "elements": [{"id": "b1", "type": "bar", "a": "n1", "b": "n2", "k": "50"},
                        {"id": "s1", "type": "spring", "node": "n2", "dir": "X", "k": ["90", "110"]},
                        {"id": "p1", "type": "panel", "nodes": ["n1", "n2", "n3", "n4"], "g": "12"}],
           "loads": [["n2", "X", "10"]],
           "outputs": [{"u": ["n2", "X"]}, {"force": "b1"}, {"flow": "p1"}]})
    -> {"unknowns": n, "outputs": [{"output": ..., "nominal": Fraction, "lo": Fraction, "hi": Fraction}, ...]}

`force` of a bar is its tension (positive when it lengthens), of a spring the force it carries along its direction;
`flow` of a panel is its shear flow, in the units of G' (force per length). Units are the caller's: one consistent
system (the stand's unit layer is not involved here). Numbers are exact rationals; a bar's direction must be exact
(its length rational) — on a rectangular grid it always is.

MEASURED 2026-11-13 (tests/test_assembly.py's grid: 41 x 7 nodes, 574 unknowns, 790 elements, every panel's flow
asked): 0.6 s. With exact stiffnesses the answer is exact (lo = hi). With EVERY panel's G' in its own range the
proved range is the worst case over all of them at once and widens fast: +-1 % on each of 240 panels gives +-2.5 % on
the largest shear flow and +-0.8 % on the mid deflection; +-5 % gives +-14 % and +-4.4 %; +-10 % gives +-33 % and
+-9.6 %. Give a range only to what is really uncertain.

SCOPE, said plainly: first-order statics of the model AS STATED. Whether the model is the structure is not proved
here; a mechanism (no support, a node nothing holds) is refused, not solved.
"""
from __future__ import annotations

import math
from fractions import Fraction as F


class AssemblyError(ValueError):
    pass


def _q(x, what):
    if isinstance(x, bool) or x is None:
        raise AssemblyError(f"{what}: a number is needed, not {x!r}")
    try:
        return F(repr(x) if isinstance(x, float) else str(x).strip())
    except (ValueError, ZeroDivisionError):
        raise AssemblyError(f"{what}: {x!r} is not a number") from None


def _box(v, what):
    """a stiffness: a positive number, or [low, high] -> (nominal, t): the element's factor lies in [1 - t, 1 + t]"""
    if isinstance(v, (list, tuple)):
        if len(v) != 2:
            raise AssemblyError(f"{what}: a range is [low, high]")
        lo, hi = _q(v[0], what), _q(v[1], what)
        if not 0 < lo <= hi:
            raise AssemblyError(f"{what}: a stiffness range must be 0 < low <= high")
        return (lo + hi) / 2, (hi - lo) / (hi + lo)
    k = _q(v, what)
    if k <= 0:
        raise AssemblyError(f"{what}: a stiffness must be positive")
    return k, F(0)


def _sqrt(q):
    """the exact rational square root, or None"""
    if q < 0:
        return None
    a, b = math.isqrt(q.numerator), math.isqrt(q.denominator)
    return F(a, b) if a * a == q.numerator and b * b == q.denominator else None


def build(spec):
    """-> (parts, f, dof, meta): zenergy's parts and load vector, the free displacements, and for every element its
    part index, weight, row and kind."""
    if not isinstance(spec, dict):
        raise AssemblyError("the model is an object with nodes, fixed, elements, loads, outputs")
    nodes = {}
    for nid, xy in (spec.get("nodes") or {}).items():
        if not isinstance(xy, (list, tuple)) or len(xy) != 2:
            raise AssemblyError(f"node {nid}: coordinates are [x, y]")
        nodes[str(nid)] = (_q(xy[0], f"node {nid}"), _q(xy[1], f"node {nid}"))
    if not nodes:
        raise AssemblyError("no nodes")
    fixed = set()
    for item in spec.get("fixed") or []:
        if not isinstance(item, (list, tuple)) or len(item) != 2 or str(item[0]) not in nodes or str(item[1]).upper() not in ("X", "Y"):
            raise AssemblyError(f"fixed {item!r}: each is [node, \"X\" or \"Y\"] of a node of the model")
        fixed.add((str(item[0]), str(item[1]).upper()))
    free = [(n, d) for n in nodes for d in "XY" if (n, d) not in fixed]
    dof = {nd: i for i, nd in enumerate(free)}
    parts, meta = [], {}

    def add(row, where):
        g = {}
        for (n, d), c in row:
            if n not in nodes:
                raise AssemblyError(f"{where}: {n!r} is not a node of the model")
            if (n, d) in dof and c != 0:
                g[dof[(n, d)]] = g.get(dof[(n, d)], F(0)) + c
        g = {i: c for i, c in g.items() if c != 0}
        if not g:
            raise AssemblyError(f"{where}: every displacement it joins is fixed - it carries nothing in this model")
        return g

    for el in spec.get("elements") or []:
        if not isinstance(el, dict) or not str(el.get("id") or "").strip():
            raise AssemblyError("each element is an object with an id")
        eid, kind = str(el["id"]), el.get("type")
        if eid in meta:
            raise AssemblyError(f"element {eid}: the id is used twice")
        if kind == "bar":
            a, b = str(el.get("a")), str(el.get("b"))
            if a not in nodes or b not in nodes or a == b:
                raise AssemblyError(f"bar {eid}: a and b are two different nodes of the model")
            dx, dy = nodes[b][0] - nodes[a][0], nodes[b][1] - nodes[a][1]
            L = _sqrt(dx * dx + dy * dy)
            if not L:
                raise AssemblyError(f"bar {eid}: its length is zero or irrational - its direction is not exact")
            k, t = _box(el.get("k"), f"bar {eid}, k")
            g = add([((b, "X"), dx / L), ((b, "Y"), dy / L), ((a, "X"), -dx / L), ((a, "Y"), -dy / L)], f"bar {eid}")
            meta[eid] = {"kind": "bar", "w": k, "scale": F(1)}
        elif kind == "spring":
            n, d = str(el.get("node")), str(el.get("dir") or "").upper()
            if n not in nodes or d not in ("X", "Y"):
                raise AssemblyError(f"spring {eid}: node is a node of the model and dir is \"X\" or \"Y\"")
            k, t = _box(el.get("k"), f"spring {eid}, k")
            g = add([((n, d), F(1))], f"spring {eid}")
            meta[eid] = {"kind": "spring", "w": k, "scale": F(1)}
        elif kind == "panel":
            ns = [str(x) for x in (el.get("nodes") or [])]
            if len(ns) != 4 or any(x not in nodes for x in ns) or len(set(ns)) != 4:
                raise AssemblyError(f"panel {eid}: nodes are four different nodes of the model: [bl, br, tr, tl]")
            bl, br, tr, tl = (nodes[x] for x in ns)
            a, b = br[0] - bl[0], tl[1] - bl[1]
            if not (a > 0 and b > 0 and br[1] == bl[1] and tl[0] == bl[0] and tr == (br[0], tl[1])):
                raise AssemblyError(f"panel {eid}: its nodes must be the corners of a rectangle along the axes, in the "
                                    "order bottom-left, bottom-right, top-right, top-left")
            gp, t = _box(el.get("g"), f"panel {eid}, g")
            k = gp * a * b
            g = add([((ns[3], "X"), 1 / (2 * b)), ((ns[2], "X"), 1 / (2 * b)), ((ns[0], "X"), -1 / (2 * b)), ((ns[1], "X"), -1 / (2 * b)),
                     ((ns[1], "Y"), 1 / (2 * a)), ((ns[2], "Y"), 1 / (2 * a)), ((ns[0], "Y"), -1 / (2 * a)), ((ns[3], "Y"), -1 / (2 * a))],
                    f"panel {eid}")
            meta[eid] = {"kind": "panel", "w": k, "scale": 1 / (a * b)}      # flow = G' gamma = w gamma / (a b)
        else:
            raise AssemblyError(f"element {eid}: type is \"bar\", \"spring\" or \"panel\"")
        meta[eid].update(part=len(parts), row=g)
        parts.append({"t": t, "terms": [(k, g)]})
    if not parts:
        raise AssemblyError("no elements")
    f = [F(0)] * len(free)
    for item in spec.get("loads") or []:
        if not isinstance(item, (list, tuple)) or len(item) != 3 or str(item[0]) not in nodes or str(item[1]).upper() not in ("X", "Y"):
            raise AssemblyError(f"load {item!r}: each is [node, \"X\" or \"Y\", force]")
        nd = (str(item[0]), str(item[1]).upper())
        if nd not in dof:
            raise AssemblyError(f"load on {nd[0]} {nd[1]}: that displacement is fixed - the support takes it")
        f[dof[nd]] += _q(item[2], f"load on {nd[0]} {nd[1]}")
    held = {i for p in parts for (_w, g) in p["terms"] for i in g}
    loose = [f"{n} {d}" for (n, d), i in dof.items() if i not in held]
    if loose:
        raise AssemblyError("a mechanism: nothing holds " + ", ".join(loose[:8]) + (" ..." if len(loose) > 8 else "")
                            + " - fix it or join it with an element")
    return parts, f, dof, meta


def solve(spec, jobs=1):
    """The proved ranges of the outputs asked for. -> {"unknowns", "outputs": [{"output", "nominal", "lo", "hi"}]}"""
    from . import judge_ztl  # noqa: F401  (puts ZTL on the path)
    import zenergy as ZE
    parts, f, dof, meta = build(spec)
    n = len(dof)
    asked = spec.get("outputs") or []
    if not asked:
        raise AssemblyError("no outputs: ask for {\"u\": [node, dir]}, {\"force\": element} or {\"flow\": panel}")
    plain, scaled = [], []                       # (index in asked, label, e) and (index, label, e, part, factor)
    for i, o in enumerate(asked):
        if isinstance(o, dict) and "u" in o:
            nd = (str(o["u"][0]), str(o["u"][1]).upper()) if isinstance(o["u"], (list, tuple)) and len(o["u"]) == 2 else None
            if nd is None or nd[1] not in ("X", "Y"):
                raise AssemblyError(f"output {o!r}: u is [node, \"X\" or \"Y\"]")
            if nd not in dof:
                raise AssemblyError(f"output u of {nd[0]} {nd[1]}: not a free displacement of the model (fixed, or no such node)")
            plain.append((i, f"u({nd[0]},{nd[1]})", {dof[nd]: F(1)}))
        elif isinstance(o, dict) and ("force" in o or "flow" in o):
            key = "force" if "force" in o else "flow"
            eid = str(o[key])
            if eid not in meta:
                raise AssemblyError(f"output {key} of {eid!r}: no such element")
            m = meta[eid]
            if (key == "flow") != (m["kind"] == "panel"):
                raise AssemblyError(f"output {key} of {eid}: a panel has a flow, a bar and a spring have a force")
            scaled.append((i, f"{key}({eid})", m["row"], m["part"], m["w"] * m["scale"]))
        else:
            raise AssemblyError(f"output {o!r}: one of {{\"u\": [node, dir]}}, {{\"force\": element}}, {{\"flow\": panel}}")
    out = [None] * len(asked)
    try:
        if plain:
            # MANY DISPLACEMENTS GO THROUGH THE BATCH (MEASURED 2026-11-13, 2542 unknowns, 1271 displacements: one by
            # one 30.0 s, in the batch 3.9 s; the ends of the proved ranges agree to 6e-13). zenergy's batch is the
            # path of SCALED outputs, p_k (e.u); scaled by a part whose factor is exactly 1 (tolerance 0) that IS e.u,
            # with the batch's rigorous rounding bounds - a range wider by about 1e-12, never narrower.
            zero = next((k for k, pt in enumerate(parts) if pt["t"] == 0), None)
            es = [e for _i, _l, e in plain]
            if zero is not None and len(es) >= ZE.BATCH_FROM and n > ZE.EXACT_UP_TO:
                rs = ZE.certify_many(parts, f, es, n, jobs=jobs, scale=[zero] * len(es))
            else:
                rs = ZE.certify_many(parts, f, es, n, jobs=jobs)
            for (i, label, _e), r in zip(plain, rs):
                out[i] = {"output": label, "nominal": r["nominal"], "lo": r["lo"], "hi": r["hi"]}
        if scaled:
            rs = ZE.certify_many(parts, f, [e for _i, _l, e, _p, _c in scaled], n, jobs=jobs, scale=[p for _i, _l, _e, p, _c in scaled])
            for (i, label, _e, _p, c), r in zip(scaled, rs):
                out[i] = {"output": label, "nominal": c * r["nominal"], "lo": c * r["lo"], "hi": c * r["hi"]}
    except AssemblyError:
        raise
    except Exception as e:                       # noqa: BLE001 — zenergy refuses a stiffness it cannot prove positive
        raise AssemblyError("the model could not be solved with a proof (" + str(e)[:160] + "): a mechanism - a part of "
                            "it that nothing restrains - or a stiffness range so wide that it is not decided") from None
    return {"unknowns": n, "elements": len(parts), "outputs": out}
