# -*- coding: utf-8 -*-
"""ASSEMBLY — a plane linear elastic model stated ELEMENT BY ELEMENT, with proved ranges of its displacements and of
its members' forces.

SINCE 2026-11-14 it is also a SECTION OF A BRICK (`"assembly"`, BRICKS.md 7j; the end of this file): its stiffnesses
and loads name the brick's quantities, its results are quantities of the brick, and the stand solves it for every
design - so a catalogue is searched THROUGH the structure. `solve` below is the door to the kernel that section uses.

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


_KCTX = {}      # a structure's prepared stiffness (zenergy.fp_prepare_K), by a key the caller gives


def solve(spec, jobs=1, kkey=None):
    """The proved ranges of the outputs asked for. -> {"unknowns", "outputs": [{"output", "nominal", "lo", "hi"}]}
    `kkey`: a key of the STIFFNESS (nodes, supports, elements - not the loads). The load-independent half of the
    floating path - the factor and the proved smallest eigenvalue - is prepared once per solve (it was prepared
    twice: once for the displacements, once for the forces and flows) and, with a key, once for every load case of
    the same structure (MEASURED 2026-11-14: preparation was a third of a solve; modes are load cases)."""
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
    kctx = None
    try:
        if n > ZE.EXACT_UP_TO:
            held = _KCTX.get(kkey) if kkey is not None else None
            if held is not None:
                # the same structure under another load: zenergy ties a prepared stiffness to the very `parts` it was
                # made from, so those parts are used again (same key = same nodes, supports and elements; only f is new)
                kctx, parts, meta = held
            else:
                kctx = ZE.fp_prepare_K(parts, n)
                if kkey is not None:
                    if len(_KCTX) >= 4:
                        _KCTX.clear()
                    _KCTX[kkey] = (kctx, parts, meta)
        if plain:
            # MANY DISPLACEMENTS GO THROUGH THE BATCH (MEASURED 2026-11-13, 2542 unknowns, 1271 displacements: one by
            # one 30.0 s, in the batch 3.9 s; the ends of the proved ranges agree to 6e-13). zenergy's batch is the
            # path of SCALED outputs, p_k (e.u); scaled by a part whose factor is exactly 1 (tolerance 0) that IS e.u,
            # with the batch's rigorous rounding bounds - a range wider by about 1e-12, never narrower.
            zero = next((k for k, pt in enumerate(parts) if pt["t"] == 0), None)
            es = [e for _i, _l, e in plain]
            if zero is not None and len(es) >= ZE.BATCH_FROM and n > ZE.EXACT_UP_TO:
                rs = ZE.certify_many(parts, f, es, n, jobs=jobs, scale=[zero] * len(es), kctx=kctx)
            else:
                rs = ZE.certify_many(parts, f, es, n, jobs=jobs, kctx=kctx)
            for (i, label, _e), r in zip(plain, rs):
                out[i] = {"output": label, "nominal": r["nominal"], "lo": r["lo"], "hi": r["hi"]}
        if scaled:
            rs = ZE.certify_many(parts, f, [e for _i, _l, e, _p, _c in scaled], n, jobs=jobs, scale=[p for _i, _l, _e, p, _c in scaled], kctx=kctx)
            for (i, label, _e, _p, c), r in zip(scaled, rs):
                out[i] = {"output": label, "nominal": c * r["nominal"], "lo": c * r["lo"], "hi": c * r["hi"]}
    except AssemblyError:
        raise
    except Exception as e:                       # noqa: BLE001 — zenergy refuses a stiffness it cannot prove positive
        raise AssemblyError("the model could not be solved with a proof (" + str(e)[:160] + "): a mechanism - a part of "
                            "it that nothing restrains - or a stiffness range so wide that it is not decided") from None
    return {"unknowns": n, "elements": len(parts), "outputs": out}


# ---- THE BRICK SECTION (2026-11-14). `assembly` inside a brick: stiffnesses and loads NAME the brick's quantities
# (a given, a field of the item a slot holds, a computed value), the results are quantities of the brick, and the
# stand solves the structure for every design - so its catalogue search, its objective and its modes work through a
# structure whose parts act on one another.
# TWO FORMS of one section. ELEMENT BY ELEMENT: "nodes", "fixed", "elements", "loads", "outputs". BY RULES ON A GRID
# ("grid" present): a real roof is hundreds of nodes and nobody writes eight hundred elements - which cells have
# which shear stiffness ("panels" by box, "holes"), which grid lines carry bars and with what EA ("bars"), where the
# springs and supports are, how a load is spread (a point, a grid line by tributary length, the plan by tributary
# area), and outputs that may be the LARGEST magnitude over a zone. Both are laid out into the same thing: elements
# whose stiffness is a sum of (expression x exact factor), loads likewise, outputs read from the solver's.
_CACHE, _LAYOUTS = {}, {}
GRID_KINDS = {"u": "u", "max_u": "u", "flow": "flow", "max_flow": "flow", "max_bar_force": "force", "spring_force": "force"}


def _axis(spec, name):
    if isinstance(spec, dict):
        a, b, st = _q(spec.get("from", 0), f"grid {name} from"), _q(spec.get("to"), f"grid {name} to"), _q(spec.get("step"), f"grid {name} step")
        if st <= 0 or b <= a:
            raise AssemblyError(f"grid {name}: needs from < to and a positive step")
        out, x = [], a
        while x < b:
            out.append(x)
            x += st
        out.append(b)
    elif isinstance(spec, list) and len(spec) >= 2:
        out = sorted({_q(v, f"grid {name}") for v in spec})
    else:
        raise AssemblyError(f"grid {name}: a list of coordinates, or {{\"from\", \"to\", \"step\"}}")
    if len(out) < 2 or len(out) > 400:
        raise AssemblyError(f"grid {name}: between 2 and 400 lines")
    return out


def _expr(v, what):
    if not isinstance(v, str) or not v.strip():
        raise AssemblyError(f"{what}: an expression of the brick's quantities, written as a string (a given, a "
                            "slot.field, a computed value)")
    return v


def _lay_elements(sec):
    """the element-by-element form -> the layout"""
    nodes = {}
    for nid, xy in (sec.get("nodes") or {}).items():
        if not isinstance(xy, (list, tuple)) or len(xy) != 2:
            raise AssemblyError(f"node {nid}: coordinates are [x, y], numbers in the section's length_unit")
        nodes[str(nid)] = (_q(xy[0], f"node {nid}"), _q(xy[1], f"node {nid}"))
    elems, texts_ = [], []
    for i, e in enumerate(sec.get("elements") or []):
        if not isinstance(e, dict):
            raise AssemblyError(f"elements[{i}]: an object with id and type")
        key = "g" if e.get("type") == "panel" else "k"
        where = f"assembly.elements[{i}] ({e.get('id')}).{key}"
        texts_.append((where, _expr(e.get(key), where), "stiffness"))
        elems.append(({k: v for k, v in e.items() if k != key}, key, [(e[key], F(1))]))
    loads = {}
    for i, ld in enumerate(sec.get("loads") or []):
        if not isinstance(ld, (list, tuple)) or len(ld) != 3:
            raise AssemblyError(f"loads[{i}]: [node, \"X\" or \"Y\", force]")
        where = f"assembly.loads[{i}]"
        texts_.append((where, _expr(ld[2], where), "force"))
        loads.setdefault((str(ld[0]), str(ld[1]).upper()), []).append((ld[2], F(1)))
    outs, plan = [], {}
    for name, o in (sec.get("outputs") or {}).items():
        k = next((k for k in ("u", "force", "flow") if k in o), None)
        if k is None:
            raise AssemblyError(f"outputs.{name}: one of \"u\", \"force\", \"flow\"")
        outs.append({k: o[k]})
        plan[name] = (k, "one", [len(outs) - 1])
    return {"nodes": nodes, "fixed": list(sec.get("fixed") or []), "elems": elems, "loads": loads, "outs": outs,
            "plan": plan, "texts": texts_}


def _lay_grid(sec):
    """the grid rules -> the layout (coordinates in the section's length_unit; a bar's EA / L is a factor 1 / L)"""
    grid = sec.get("grid") or {}
    xs, ys = _axis(grid.get("x"), "x"), _axis(grid.get("y"), "y")
    ix, iy = {x: i for i, x in enumerate(xs)}, {y: j for j, y in enumerate(ys)}
    nid = lambda i, j: f"{i}_{j}"                           # noqa: E731
    texts_ = []

    def node_at(pt, what):
        if not isinstance(pt, (list, tuple)) or len(pt) != 2:
            raise AssemblyError(f"{what}: a point is [x, y]")
        x, y = _q(pt[0], what), _q(pt[1], what)
        if x not in ix or y not in iy:
            raise AssemblyError(f"{what}: [{float(x):g}, {float(y):g}] is not a crossing of the grid")
        return ix[x], iy[y]

    def box(bx, what):
        if bx is None:
            return xs[0], ys[0], xs[-1], ys[-1]
        if not isinstance(bx, (list, tuple)) or len(bx) != 4:
            raise AssemblyError(f"{what}: a box is [x0, y0, x1, y1]")
        x0, y0, x1, y1 = (_q(v, what) for v in bx)
        return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

    def lines(rule, what):
        along = str(rule.get("along") or "").lower()
        if along not in ("x", "y"):
            raise AssemblyError(f"{what}: along is \"x\" or \"y\"")
        across = ys if along == "x" else xs                 # a bar along x lies on a line y = const
        sel = rule.get("lines", "all")
        if sel == "all":
            cs = list(across)
        elif sel == "boundary":
            cs = [across[0], across[-1]]
        elif isinstance(sel, list) and sel:
            cs = [_q(v, what) for v in sel]
            bad = [c for c in cs if c not in across]
            if bad:
                raise AssemblyError(f"{what}: {float(bad[0]):g} is not a grid line across {along}")
        else:
            raise AssemblyError(f"{what}: lines is \"all\", \"boundary\" or a list of coordinates")
        return along, cs

    cells = {}
    for k, rule in enumerate(sec.get("panels") or []):
        if not isinstance(rule, dict):
            raise AssemblyError("panels: each rule is an object {g, box}")
        where = f"assembly.panels[{k}].g"
        g = _expr(rule.get("g"), where)
        texts_.append((where, g, "stiffness"))
        x0, y0, x1, y1 = box(rule.get("box"), f"assembly.panels[{k}]")
        for i in range(len(xs) - 1):
            for j in range(len(ys) - 1):
                if x0 <= xs[i] and xs[i + 1] <= x1 and y0 <= ys[j] and ys[j + 1] <= y1:
                    cells[(i, j)] = g                       # a later rule replaces an earlier one on the cells it covers
    for k, h in enumerate(sec.get("holes") or []):
        x0, y0, x1, y1 = box(h, f"assembly.holes[{k}]")
        for (i, j) in list(cells):
            if xs[i] < x1 and x0 < xs[i + 1] and ys[j] < y1 and y0 < ys[j + 1]:
                del cells[(i, j)]
    elems = [({"id": f"p{i}_{j}", "type": "panel", "nodes": [nid(i, j), nid(i + 1, j), nid(i + 1, j + 1), nid(i, j + 1)]}, "g", [(g, F(1))])
             for (i, j), g in sorted(cells.items())]
    bars = {}                                               # (along, i, j) -> [(EA expression, 1 / L)]: rules add up
    for k, rule in enumerate(sec.get("bars") or []):
        if not isinstance(rule, dict):
            raise AssemblyError("bars: each rule is an object {along, lines, EA}")
        where = f"assembly.bars[{k}].EA"
        ea = _expr(rule.get("EA"), where)
        texts_.append((where, ea, "force"))
        along, cs = lines(rule, f"assembly.bars[{k}]")
        for c in cs:
            if along == "x":
                for i in range(len(xs) - 1):
                    bars.setdefault(("x", i, iy[c]), []).append((ea, 1 / (xs[i + 1] - xs[i])))
            else:
                for j in range(len(ys) - 1):
                    bars.setdefault(("y", ix[c], j), []).append((ea, 1 / (ys[j + 1] - ys[j])))
    for (along, i, j), terms in sorted(bars.items()):
        a_, b_ = (nid(i, j), nid(i + 1, j)) if along == "x" else (nid(i, j), nid(i, j + 1))
        elems.append(({"id": f"b{along}{i}_{j}", "type": "bar", "a": a_, "b": b_}, "k", [(t, f_) for t, f_ in terms]))
    springs = {}
    for k, sp in enumerate(sec.get("springs") or []):
        if not isinstance(sp, dict):
            raise AssemblyError("springs: each is an object {at, dir, k}")
        i, j = node_at(sp.get("at"), f"assembly.springs[{k}]")
        d = str(sp.get("dir") or "").upper()
        if d not in ("X", "Y"):
            raise AssemblyError(f"assembly.springs[{k}]: dir is \"X\" or \"Y\"")
        where = f"assembly.springs[{k}].k"
        texts_.append((where, _expr(sp.get("k"), where), "stiffness"))
        springs.setdefault((i, j, d), []).append((sp["k"], F(1)))
    for (i, j, d), terms in sorted(springs.items()):
        elems.append(({"id": f"s{d}{i}_{j}", "type": "spring", "node": nid(i, j), "dir": d}, "k", terms))
    fixed = []
    for k, fx in enumerate(sec.get("fixed") or []):
        if not isinstance(fx, dict):
            raise AssemblyError("fixed: on a grid each is an object {at, dir}")
        i, j = node_at(fx.get("at"), f"assembly.fixed[{k}]")
        d = str(fx.get("dir") or "").upper()
        if d not in ("X", "Y"):
            raise AssemblyError(f"assembly.fixed[{k}]: dir is \"X\" or \"Y\"")
        fixed.append([nid(i, j), d])

    def trib(vals, k):
        return ((vals[k] - vals[k - 1]) if k > 0 else 0) / 2 + ((vals[k + 1] - vals[k]) if k < len(vals) - 1 else 0) / 2

    loads = {}
    for k, ld in enumerate(sec.get("loads") or []):
        if not isinstance(ld, dict):
            raise AssemblyError("loads: on a grid each is an object")
        d = str(ld.get("dir") or "").upper()
        if d not in ("X", "Y"):
            raise AssemblyError(f"assembly.loads[{k}]: dir is \"X\" or \"Y\"")
        sign = -1 if ld.get("sign") in (-1, "-1", "-") else 1
        if ld.get("on") == "area":
            where, text = f"assembly.loads[{k}].total", ld.get("total")
            area = (xs[-1] - xs[0]) * (ys[-1] - ys[0])
            share = {(i, j): trib(xs, i) * trib(ys, j) / area for i in range(len(xs)) for j in range(len(ys))}
        elif ld.get("on") == "line":
            where, text = f"assembly.loads[{k}].total", ld.get("total")
            if "x" in ld:
                c = _q(ld["x"], where)
                if c not in ix:
                    raise AssemblyError(f"assembly.loads[{k}]: x = {float(c):g} is not a grid line")
                share = {(ix[c], j): trib(ys, j) / (ys[-1] - ys[0]) for j in range(len(ys))}
            elif "y" in ld:
                c = _q(ld["y"], where)
                if c not in iy:
                    raise AssemblyError(f"assembly.loads[{k}]: y = {float(c):g} is not a grid line")
                share = {(i, iy[c]): trib(xs, i) / (xs[-1] - xs[0]) for i in range(len(xs))}
            else:
                raise AssemblyError(f"assembly.loads[{k}]: a line load names its line - \"x\": c or \"y\": c")
        else:
            where, text = f"assembly.loads[{k}].P", ld.get("P")
            share = {node_at(ld.get("at"), f"assembly.loads[{k}]"): F(1)}
        texts_.append((where, _expr(text, where), "force"))
        for (i, j), sh in share.items():
            if sh:
                loads.setdefault((nid(i, j), d), []).append((text, sign * sh))
    outs, plan = [], {}

    def ask(o):
        outs.append(o)
        return len(outs) - 1

    fx_set = {(n, d) for n, d in map(tuple, fixed)}
    for name, o in (sec.get("outputs") or {}).items():
        what = o.get("what")
        if what == "u":
            i, j = node_at(o.get("at"), f"outputs.{name}")
            plan[name] = ("u", "one", [ask({"u": [nid(i, j), str(o.get("dir") or "").upper()]})])
        elif what == "max_u":
            d = str(o.get("dir") or "").upper()
            if d not in ("X", "Y"):
                raise AssemblyError(f"outputs.{name}: dir is \"X\" or \"Y\"")
            x0, y0, x1, y1 = box(o.get("box"), f"outputs.{name}")
            pts = [(i, j) for i in range(len(xs)) for j in range(len(ys))
                   if (nid(i, j), d) not in fx_set and x0 <= xs[i] <= x1 and y0 <= ys[j] <= y1]
            if not pts:
                raise AssemblyError(f"outputs.{name}: no free node lies inside that box")
            plan[name] = ("u", "max", [ask({"u": [nid(i, j), d]}) for i, j in pts])
        elif what == "flow":
            pt = o.get("at")
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise AssemblyError(f"outputs.{name}: at is [x, y], a point inside the cell")
            x, y = _q(pt[0], name), _q(pt[1], name)
            hit = [(i, j) for (i, j) in sorted(cells) if xs[i] <= x <= xs[i + 1] and ys[j] <= y <= ys[j + 1]]
            if not hit:
                raise AssemblyError(f"outputs.{name}: no panel holds the point [{float(x):g}, {float(y):g}]")
            plan[name] = ("flow", "one", [ask({"flow": f"p{hit[0][0]}_{hit[0][1]}"})])
        elif what == "max_flow":
            x0, y0, x1, y1 = box(o.get("box"), f"outputs.{name}")
            ids = sorted((i, j) for (i, j) in cells if x0 <= xs[i] and xs[i + 1] <= x1 and y0 <= ys[j] and ys[j + 1] <= y1)
            if not ids:
                raise AssemblyError(f"outputs.{name}: no panel lies inside that box")
            plan[name] = ("flow", "max", [ask({"flow": f"p{i}_{j}"}) for i, j in ids])
        elif what == "max_bar_force":
            along, cs = lines(o, f"outputs.{name}")
            x0, y0, x1, y1 = box(o.get("box"), f"outputs.{name}")

            def inside(key):                                # both ends of the segment inside the box
                _a, i, j = key
                i2, j2 = (i + 1, j) if along == "x" else (i, j + 1)
                return x0 <= xs[i] and xs[i2] <= x1 and y0 <= ys[j] and ys[j2] <= y1
            keys = sorted(key for key in bars if key[0] == along and ((ys[key[2]] if along == "x" else xs[key[1]]) in cs) and inside(key))
            if not keys:
                raise AssemblyError(f"outputs.{name}: no bar lies on those lines" + (" inside that box" if o.get("box") else ""))
            plan[name] = ("force", "max", [ask({"force": f"b{a_}{i}_{j}"}) for a_, i, j in keys])
        elif what == "spring_force":
            i, j = node_at(o.get("at"), f"outputs.{name}")
            d = str(o.get("dir") or "").upper()
            if (i, j, d) not in springs:
                raise AssemblyError(f"outputs.{name}: no spring at that point in {d}")
            plan[name] = ("force", "one", [ask({"force": f"s{d}{i}_{j}"})])
        else:
            raise AssemblyError(f"outputs.{name}: what is one of {', '.join(GRID_KINDS)}")
    return {"nodes": {nid(i, j): (x, y) for x, i in ix.items() for y, j in iy.items()}, "fixed": fixed, "elems": elems,
            "loads": loads, "outs": outs, "plan": plan, "texts": texts_}


def layout(b):
    """the section laid out once per brick: geometry, which expression feeds which element with which factor, how
    each named output is read. It depends on the section alone (not on the design)."""
    import json
    sec = b.get("assembly") or {}
    key = json.dumps(sec, sort_keys=True, default=str)
    if key not in _LAYOUTS:
        if len(_LAYOUTS) > 16:
            _LAYOUTS.clear()
        if not isinstance(sec.get("outputs"), dict) or not sec["outputs"]:
            raise AssemblyError("outputs: an object of name: what to compute, each with its unit")
        _LAYOUTS[key] = _lay_grid(sec) if "grid" in sec else _lay_elements(sec)
    return _LAYOUTS[key]


def kinds(b):
    """{output name: (kind u | force | flow, how, unit)}"""
    lay, outs = layout(b), (b.get("assembly") or {}).get("outputs") or {}
    return {name: (k, how, (outs.get(name) or {}).get("unit", "")) for name, (k, how, _idx) in lay["plan"].items()}


def texts(b):
    """every expression of the section with what it must be: [(where, text, "stiffness" | "force")]"""
    return list(layout(b)["texts"])


def for_design(b, env, only=None):
    """The structure of this design, solved by ZTL (zenergy): -> {output name: (lo, hi)} in SI. `env`: the design's
    EXACT values in SI (stand.exact_env). `only`: the names to compute (the rest are not asked of the solver). Version 1: every stiffness and load is exact per design - a quantity with a
    tolerance or a range, or a derived one, has no exact value and is refused by name."""
    import ast
    import json
    from . import bricks as B, exact as X, units as U
    sec = b["assembly"]
    try:
        ls = U.parse(sec.get("length_unit", "m"))[0]
    except Exception as e:                       # noqa: BLE001
        raise AssemblyError(f"length_unit: {e}") from None
    lay, seen = layout(b), {}

    def val(text):
        if text in seen:
            return seen[text]
        code = B.compile_expr(text, b.get("define"))
        names = {n.id for n in ast.walk(ast.parse(code, mode="eval")) if isinstance(n, ast.Name)}
        missing = sorted(n for n in names if n not in env and n not in B.FUNCS)
        if missing:
            raise AssemblyError(f"{text!r}: {', '.join(m.replace('__', '.') for m in missing)} has no exact value for "
                                "this design - version 1 of the structure section reads exact values only (not a "
                                "tolerance, a range, or a derived quantity)")
        v = X.evaluate(X.parse(code), env, f"assembly: {text}")
        if isinstance(v, (X._Iv, str)):
            raise AssemblyError(f"{text!r}: not an exact number")
        seen[text] = F(v)
        return seen[text]

    want = [name for name in lay["plan"] if only is None or name in only]
    if not want:
        return {}
    # everything in SI: a coordinate x ls; a factor 1 / L (a bar's EA / L) is per section length -> / ls
    spec = {"nodes": {n: [str(x * ls), str(y * ls)] for n, (x, y) in lay["nodes"].items()}, "fixed": lay["fixed"],
            "elements": [], "loads": []}
    for e, key, terms in lay["elems"]:
        k = sum((val(t) * (f_ if f_ == 1 else f_ / ls) for t, f_ in terms), F(0))
        spec["elements"].append({**e, key: str(k)})
    kkey = json.dumps(spec, sort_keys=True)               # the stiffness alone: shared by every load case
    for (node, d), terms in sorted(lay["loads"].items()):
        p = sum((val(t) * f_ for t, f_ in terms), F(0))
        if p:
            spec["loads"].append([node, d, str(p)])
    ckey = kkey + json.dumps(spec["loads"])
    # THE RESULTS ARE KEPT BY NAME for this structure under this load: a later reader that wants fewer of them, or
    # other ones, is served from what is there and only the missing are solved for (MEASURED 2026-11-14: keyed by
    # the whole request, the confirmation of a refutation - one requirement - solved the same structure again)
    if ckey not in _CACHE:
        if len(_CACHE) > 256:
            _CACHE.clear()
        _CACHE[ckey] = {}
    have = _CACHE[ckey]
    missing = [name for name in want if name not in have]
    if missing:
        used = sorted({i for name in missing for i in lay["plan"][name][2]})
        at = {i: k for k, i in enumerate(used)}
        got = solve(dict(spec, outputs=[lay["outs"][i] for i in used]), kkey=kkey)["outputs"]
        for name in missing:
            _k, how, idx = lay["plan"][name]
            if how == "one":
                have[name] = (got[at[idx[0]]]["lo"], got[at[idx[0]]]["hi"])
            else:                                # the largest magnitude over several outputs: an enclosure of it
                lo = max((x["lo"] if x["lo"] > 0 else -x["hi"] if x["hi"] < 0 else F(0)) for x in (got[at[i]] for i in idx))
                hi = max(max(abs(x["lo"]), abs(x["hi"])) for x in (got[at[i]] for i in idx))
                have[name] = (lo, hi)
    return {name: have[name] for name in want}
