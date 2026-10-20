"""NETWORK bricks: branch currents of a scalar network (resistors, thermal conductances, diffusion) over the box of
its branch values — the curator's "да", 2026-10-12, to the shape:

    "network": {"branches": {"b1": {"from": "a", "to": "n1", "R": "R1"}, ...},
                "source":   {"from": "a", "to": "gnd", "V": "V"}},
    "requirements": [{"quantity": "I(b3)", "op": "<=", "value": "0.2", "unit": "A"}]

THE VERDICT is the network certificate's: netsearch.py SEARCHES (floating point, trusted for nothing), znet.py CHECKS
exactly by the kernel's rules — called HERE on every certificate, with the bound it must give. znet lives in the
stand, not in public ZTL (E3, Logik3); lean/ZNet.lean proves its algebra, the energy enclosure and the assembly
(zero axioms; Kirchhoff's law and the derivative-sign formulas are named premises): the output says so.

What it proves: the range of the current V * f(g), f = the current at V = 1, over every g in the box and V in its
range — f's upper and lower ends each certified (two searches per branch). A REFUTED needs a point where the
requirement fails PROVABLY: the search's best corner, enclosed exactly by a certificate on that single point.
--dev adds an independent check for small networks: every corner of the box solved exactly in fractions (Gaussian
elimination — a branch current is monotone in each conductance, a linear-fractional function, so its extremes over
the box sit at corners); the certified range must contain every corner's value.
"""
from __future__ import annotations

import itertools
import re
from fractions import Fraction as F

from . import bricks as B
from . import mode as MODE
from . import netsearch as NS
from . import units as U
from . import znet as Z

DEV_CORNERS = 1 << 10         # --dev solves every corner exactly up to 2^10 corners
OPS_NET = ("<=", ">=", "within")
_IREQ = re.compile(r"^I\((\w+)\)$")
_VREQ = re.compile(r"^V\((\w+)(?:\s*,\s*(\w+))?\)$")


class NetError(B.BrickError):
    pass


def _num(v, where):
    if not isinstance(v, str):
        raise NetError(f"{where}: a number written as a string, not {v!r}")
    try:
        return B.num(v)
    except (ValueError, ZeroDivisionError):
        raise NetError(f"{where}: {v!r} is not a number")


def _parse_unit(u):
    if not u:
        return F(1), None
    s, d = U.parse(u)
    return s, d


def _box(name, q):
    """A given quantity's box, in its own unit: (lo, hi)."""
    if not isinstance(q, dict) or q.get("role") != "given":
        raise NetError(f"network: {name!r} must be a given quantity")
    if "range" in q:
        r = q["range"]
        if not isinstance(r, list) or len(r) != 2:
            raise NetError(f"{name}: range must be [low, high]")
        lo, hi = _num(r[0], f"{name}.range"), _num(r[1], f"{name}.range")
    elif "value" in q:
        v = _num(q["value"], f"{name}.value")
        t = _num(q["tolerance"], f"{name}.tolerance") if "tolerance" in q else F(0)
        if t < 0:
            raise NetError(f"{name}: a negative tolerance")
        lo, hi = sorted((v * (1 - t), v * (1 + t)))
    else:
        raise NetError(f"{name}: a given quantity needs a value or a range")
    if lo > hi:
        raise NetError(f"{name}: range low above high")
    return lo, hi


def _value(spec, qs, where):
    """A branch value: a quantity name or a number written as a string -> (lo, hi) in SI, its dims (or None)."""
    if not isinstance(spec, str):
        raise NetError(f"{where}: a quantity name or a number written as a string")
    try:
        v = B.num(spec)
        return (v, v), None, F(1)
    except (ValueError, ZeroDivisionError):
        pass
    if spec not in qs:
        raise NetError(f"{where}: {spec!r} is not a quantity")
    sc, dim = _parse_unit(qs[spec].get("unit"))
    if isinstance(qs[spec], dict) and qs[spec].get("role") == "derived":
        # network + laws (v1, one way): a DERIVED input's range was proved by the laws first (derived_boxes)
        box = _DERIVED.get(spec)
        if box is None:
            raise NetError(f"{where}: {spec!r} is derived — give the brick the laws that define it")
        return (box[0] * sc, box[1] * sc), dim, sc
    lo, hi = _box(spec, qs[spec])
    return (lo * sc, hi * sc), dim, sc


_DERIVED = {}       # name -> (lo, hi) in its own unit, set by derived_boxes() for one load


def _inputs(raw):
    """The quantity names the network reads: branch values, the source, its reference potential."""
    net = raw.get("network") or {}
    out = []
    for br in (net.get("branches") or {}).values():
        if isinstance(br, dict):
            out.append(br.get("R", br.get("G")))
    src = net.get("source") or {}
    out += [src.get("I", src.get("V")), src.get("at")]
    return [n for n in out if isinstance(n, str)]


def derived_boxes(raw):
    """NETWORK + LAWS, version 1 (the curator's "да", 2026-10-12; real round 3, n02: P = I_D^2 R_DS(on) into a thermal
    network). The laws are judged FIRST, as an ordinary brick whose only requirements are "within +-1e300" on each
    derived input of the network: the stand's (ZTL's) proved range of each becomes that input's box. One way: the
    network's outputs do not feed the laws back (a feedback is an implicit law — not in v1). -> ({name: (lo, hi)},
    a note on lost correlation or None)."""
    qs = raw.get("quantities") or {}
    der = sorted({n for n in _inputs(raw) if isinstance(qs.get(n), dict) and qs[n].get("role") == "derived"})
    if not der:
        return {}, None
    if not raw.get("laws"):
        raise NetError(f"network: {', '.join(der)} derived, but the brick has no laws to define them")
    sub = {k: v for k, v in raw.items() if k not in ("network", "find", "requirements")}
    sub.setdefault("slots", {})
    sub.setdefault("catalog", {})
    sub["requirements"] = [{"quantity": n, "op": "within", "value": ["-1e300", "1e300"],
                            **({"unit": qs[n]["unit"]} if qs[n].get("unit") else {})} for n in der]
    from . import stand as S
    r = S._run(sub, conflicts=False)
    if r.get("verdict") != "EARNED" or not r.get("guaranteed"):
        raise NetError(f"network + laws: the laws' ranges of {', '.join(der)} were not proved ({r.get('verdict')}: "
                       f"{str(r.get('why', ''))[:200]})")
    boxes = {}
    for n in der:
        lo, hi = r["guaranteed"][n]
        boxes[n] = (B.num(lo.split(" ")[0]), B.num(hi.split(" ")[0]))
    # which givens each network input rests on: a shared one means a correlation the boxes do not keep
    deps = {}
    law_names = []
    for l in raw.get("laws") or []:
        try:
            import ast as _ast
            law_names.append({x.id for x in _ast.walk(_ast.parse(B.compile_expr(l["zfl"], raw.get("define"))
                              .replace("==", "-(") + ")", mode="eval")) if isinstance(x, _ast.Name)})
        except Exception:                                    # noqa: BLE001 — a note, never the verdict
            law_names.append(set())

    def givens_of(n, seen=()):
        if n in seen:
            return set()
        q = qs.get(n) or {}
        if q.get("role") == "given" and ("tolerance" in q or "range" in q):
            return {n}
        out = set()
        for ns in law_names:
            if n in ns:
                for m in ns - {n}:
                    qm = qs.get(m) or {}
                    if qm.get("role") == "given" and ("tolerance" in qm or "range" in qm):
                        out.add(m)
                    elif qm.get("role") == "derived":
                        out |= givens_of(m, seen + (n,))
        return out
    for n in set(_inputs(raw)):
        deps[n] = givens_of(n)
    shared = sorted({g for a in deps for b in deps if a < b for g in deps[a] & deps[b]})
    note = (f"network + laws (one way): the inputs share the toleranced given(s) {', '.join(shared)} — each input's box "
            "is proved, the correlation between them is not kept: the bounds hold but may be wider") if shared else None
    return boxes, note


def _s(x):
    from .stand import _s as s
    return s(x)


def load(raw):
    """The network part of a brick, checked: (Net, names, g boxes, V box, requirements, units note)."""
    net = raw.get("network")
    if not isinstance(net, dict) or not isinstance(net.get("branches"), dict) or not isinstance(net.get("source"), dict):
        raise NetError('network: needs {"branches": {name: {"from", "to", "R" or "G"}}, "source": {"from", "to", "V"}}')
    import copy as _copy
    raw = B._named_tolerances(_copy.deepcopy(raw))     # a tolerance may name a given quantity (find can search it)
    boxes, corr_note = derived_boxes(raw)
    _DERIVED.clear()
    _DERIVED.update(boxes)
    qs = raw.get("quantities") or {}
    src = net["source"]
    # a VOLTAGE source {"from", "to", "V"}: "from" held at V above "to", the reference; or (network v2) a CURRENT
    # source {"into", "from", "I"}: I injected into "into", drawn from "from", the reference. "at" (optional) is
    # the reference's own potential, a given quantity (an ambient temperature): V(n) of a single node adds it.
    current = "I" in src
    keys = ("into", "from", "I") if current else ("from", "to", "V")
    if current and "V" in src:
        raise NetError("network.source: a voltage source (V) or a current source (I), not both")
    for k in keys:
        if not isinstance(src.get(k), str):
            raise NetError(f"network.source: needs {k!r} ({'a current source' if current else 'a voltage source'})")
    hot, ref = (src["into"], src["from"]) if current else (src["from"], src["to"])
    if hot == ref:
        raise NetError("network.source: its two nodes are the same node")
    nodes = {hot: 0, ref: 1}
    names, edges, gbox, dims = [], [], [], []
    for bname, br in net["branches"].items():
        if not re.fullmatch(r"\w+", bname):
            raise NetError(f"network branch {bname!r}: a name of letters, digits and _")
        if not isinstance(br, dict) or not isinstance(br.get("from"), str) or not isinstance(br.get("to"), str):
            raise NetError(f"network branch {bname}: needs 'from' and 'to' nodes")
        if br["from"] == br["to"]:
            raise NetError(f"network branch {bname}: from and to are the same node")
        if ("R" in br) == ("G" in br):
            raise NetError(f"network branch {bname}: give exactly one of R (resistance) or G (conductance)")
        (lo, hi), dim, _ = _value(br.get("R", br.get("G")), qs, f"network branch {bname}")
        if lo <= 0:
            raise NetError(f"network branch {bname}: its value must be positive over its whole range")
        if "R" in br:
            lo, hi = 1 / hi, 1 / lo
            dim = tuple(-x for x in dim) if dim else None
        for x in (br["from"], br["to"]):
            nodes.setdefault(x, len(nodes))
        names.append(bname)
        edges.append((nodes[br["from"]], nodes[br["to"]]))
        gbox.append((lo, hi))
        dims.append(dim)
    if not names:
        raise NetError("network: no branches")
    (vlo, vhi), vdim, _ = _value(src["I" if current else "V"], qs, f"network.source.{'I' if current else 'V'}")
    at_box, at_dim = ((F(0), F(0)), None)
    if "at" in src:
        at_box, at_dim, _ = _value(src["at"], qs, "network.source.at")
    # connectivity: every node reaches the source's nodes through branches (else its potential is not fixed)
    adj = {}
    for (u, v) in edges:
        adj.setdefault(u, []).append(v)
        adj.setdefault(v, []).append(u)
    seen, stack = {0, 1}, [0, 1]
    while stack:
        for y in adj.get(stack.pop(), ()):
            if y not in seen:
                seen.add(y)
                stack.append(y)
    floating = [x for x, i in nodes.items() if i not in seen]
    if floating:
        raise NetError(f"network: node(s) {', '.join(floating)} reach no source node — their potential is not fixed")
    # units: every branch the same kind (conductance dims), the current = V x G
    known = [d for d in dims if d is not None]
    units_note = "not checked: some branch or the source has no unit"
    idim = pdim = None
    if known and len(known) == len(dims) and vdim is not None:
        if any(d != known[0] for d in known):
            raise U.UnitError("network: the branches are not all of one kind (their conductance units differ)")
        if current:
            idim, pdim = vdim, tuple(a - b for a, b in zip(vdim, known[0]))
            units_note = "checked: every branch one kind, a potential's unit = the source's / a conductance"
        else:
            idim, pdim = tuple(a + b for a, b in zip(vdim, known[0])), vdim
            units_note = "checked: every branch one kind, the current's unit = the source's x a conductance"
        if at_dim is not None and at_dim != pdim:
            raise U.UnitError(f"network.source.at: not a potential of this network ({U.unit_of(pdim)})")
    reqs = []
    if not isinstance(raw.get("requirements") or [], list):
        raise NetError("requirements: a list")
    for r in raw.get("requirements") or []:
        if not isinstance(r, dict):
            raise NetError("a requirement must be an object")
        q = str(r.get("quantity", ""))
        m, mv = _IREQ.match(q), _VREQ.match(q)
        if m and m.group(1) in names:
            kind, k, want = "I", names.index(m.group(1)) + 1, idim
        elif mv and mv.group(1) in nodes and (mv.group(2) is None or mv.group(2) in nodes):
            p_, q_ = nodes[mv.group(1)], nodes[mv.group(2)] if mv.group(2) else 1
            if p_ == q_:
                raise NetError(f"requirement on {q!r}: the same node twice")
            kind, k, want = ("V1" if mv.group(2) is None else "V2"), ("pair", p_, q_), pdim
        else:
            raise NetError(f"requirement on {q!r}: in a network brick, write I(<branch>), V(<node>) or "
                           "V(<node>, <node>)")
        if r.get("op") not in OPS_NET:
            raise NetError(f"requirement op must be one of {OPS_NET}")
        sc, d = _parse_unit(r.get("unit"))
        if want is not None and d is not None and d != want:
            raise U.UnitError(f"requirement on {r['quantity']}: unit {r.get('unit')!r} is not a "
                              f"{'current' if kind == 'I' else 'potential'} of this network ({U.unit_of(want)})")
        vals = r["value"] if r["op"] == "within" else [r.get("value")]
        if r["op"] == "within" and (not isinstance(vals, list) or len(vals) != 2):
            raise NetError(f"requirement on {r['quantity']}: within needs [low, high]")
        try:
            bounds = [_num(v, f"requirement on {r['quantity']}") * sc for v in vals]
        except TypeError:
            raise NetError(f"requirement on {r['quantity']}: the bound must be a number written as a string")
        reqs.append({"req": r, "k": k, "kind": kind, "bounds": bounds, "scale": sc})
    if not reqs:
        raise NetError("no requirements")
    # the source is branch 0 of the module's Net
    Znet = Z.Net(len(nodes), [(0, 1)] + edges, 0, current=current)
    glo = [F(1)] + [lo for lo, _ in gbox]
    ghi = [F(1)] + [hi for _, hi in gbox]
    Znet.at_box = at_box
    Znet.corr_note = corr_note
    Znet.law_boxes = {n: (_s(lo), _s(hi)) for n, (lo, hi) in boxes.items()}
    return Znet, names, nodes, glo, ghi, (vlo, vhi), reqs, units_note


def _certified_f(net, glo, ghi, k, direction):
    """max over the box of direction * f (f the current at V = 1): the search's certificate, CHECKED here by znet."""
    cert, U_ = NS.search(net, glo, ghi, 1, k, direction)
    if cert is None:
        return None, f"no certificate found: {U_}"
    ok = Z.check(net, glo, ghi, 1, k, direction, U_, cert)
    if not ok[0]:
        return None, f"the certificate did not check: {ok[1]}"
    return ok[1], ok[2]


def _point_f(net, g, k):
    """f at ONE conductance vector, enclosed exactly: [lo, hi] (two certificates on a point box)."""
    out = []
    for d in (1, -1):
        U_, info = _certified_f(net, g, g, k, d)
        if U_ is None:
            return None
        out.append(U_)
    return -out[1], out[0]


def _exact_f(net, g, k):
    """f at one conductance vector, EXACTLY (Gaussian elimination in fractions) — the --dev check's own means."""
    m = len(net.free)
    A = [[F(0)] * m for _ in range(m)]
    c = net.rhs_source(g, 1)
    for j in net.res:
        u, v = net.edges[j]
        for x, y in ((u, v), (v, u)):
            if x in net.idx:
                A[net.idx[x]][net.idx[x]] += g[j]
                if y in net.idx:
                    A[net.idx[x]][net.idx[y]] -= g[j]
    rhs = list(c)
    for i in range(m):
        p = next(r for r in range(i, m) if A[r][i] != 0)
        A[i], A[p], rhs[i], rhs[p] = A[p], A[i], rhs[p], rhs[i]
        for r in range(i + 1, m):
            if A[r][i]:
                q = A[r][i] / A[i][i]
                for col in range(i, m):
                    A[r][col] -= q * A[i][col]
                rhs[r] -= q * rhs[i]
    x = [F(0)] * m
    for i in reversed(range(m)):
        x[i] = (rhs[i] - sum(A[i][col] * x[col] for col in range(i + 1, m))) / A[i][i]
    p = net.pots(x, 1)
    if isinstance(k, tuple):
        return p[k[1]] - p[k[2]]
    u, v = net.edges[k]
    return g[k] * (p[u] - p[v])


def _hull(vbox, fbox):
    ps = [v * f for v in vbox for f in fbox]
    return min(ps), max(ps)


def _corner_ascent(net, glo, ghi, k, direction):
    """The search's best corner for direction * f (floating point, trusted for nothing): the conductance vector."""
    g = [(a + b) / 2 for a, b in zip(glo, ghi)]
    g = [glo[j] if glo[j] == ghi[j] else g[j] for j in range(len(g))]
    best = direction * NS._float_current(net, g, 1, k)
    for _ in range(3):
        for j in net.res:
            if glo[j] == ghi[j]:
                continue
            for end in (glo[j], ghi[j]):
                g2 = list(g)
                g2[j] = end
                v = direction * NS._float_current(net, g2, 1, k)
                if v > best:
                    best, g = v, g2
    # a corner: any coordinate left at the centre goes to the end the float reading prefers
    for j in net.res:
        if glo[j] < g[j] < ghi[j]:
            ends = []
            for end in (glo[j], ghi[j]):
                g2 = list(g)
                g2[j] = end
                ends.append((direction * NS._float_current(net, g2, 1, k), end))
            g[j] = max(ends)[1]
    return g


def run_network(raw) -> dict:
    try:
        net, names, nodes, glo, ghi, vbox, reqs, units_note = load(raw)
    except (B.BrickError, U.UnitError):
        raise
    except (ValueError, TypeError, AttributeError, KeyError, IndexError, ZeroDivisionError) as e:
        # load() only READS the brick: anything it trips on is a malformed brick (the fuzz, 2026-10-12)
        raise NetError(f"network brick malformed: {type(e).__name__}: {str(e)[:200]}")
    qs = raw.get("quantities") or {}
    out_reqs, verdicts = [], []
    for rq in reqs:
        k, r = rq["k"], rq["req"]
        label = r.get("quantity")
        # V(n) of a single node is relative to the reference, whose own potential is `at` (0 when not given)
        at_lo, at_hi = net.at_box if rq["kind"] == "V1" else (F(0), F(0))
        if isinstance(k, tuple) and k[1] not in net.idx and k[2] not in net.idx:
            # both nodes are the voltage source's: the value is exact (V or 0) — no certificate to read
            fixed = lambda n: F(1) if n == net.a else F(0)
            f0 = fixed(k[1]) - fixed(k[2])
            up, up_info, dn, dn_info = f0, "exact: both nodes are the source's", -f0, "exact"
        else:
            up, up_info = _certified_f(net, glo, ghi, k, 1)
            dn, dn_info = _certified_f(net, glo, ghi, k, -1)
        unit_sc = rq["scale"]
        row = {"requirement": r}
        if up is None or dn is None:
            row.update(verdict="OPEN", why=f"{label}: {up_info if up is None else dn_info}")
            out_reqs.append(row)
            verdicts.append("OPEN")
            continue
        lo_I, hi_I = _hull(vbox, (-dn, up))
        lo_I, hi_I = lo_I + at_lo, hi_I + at_hi
        row["proved_range"] = [_s(lo_I / unit_sc), _s(hi_I / unit_sc)]
        row["certificate"] = {"max": _s(up_info), "min": _s(dn_info)}
        lo_b, hi_b = (rq["bounds"][0], rq["bounds"][1]) if r["op"] == "within" else \
            ((None, rq["bounds"][0]) if r["op"] == "<=" else (rq["bounds"][0], None))
        holds = (hi_b is None or hi_I <= hi_b) and (lo_b is None or lo_I >= lo_b)
        if holds:
            row["verdict"] = "EARNED"
        else:
            # a failing point, PROVED: the search's best corner for the violated side, enclosed exactly
            side = 1 if (hi_b is not None and hi_I > hi_b) else -1
            refuted = None
            if isinstance(k, tuple) and k[1] not in net.idx and k[2] not in net.idx:
                # an exact target: the violating end of the source's (and the reference's) range is the witness
                at_end = at_hi if side > 0 else at_lo
                vend = max(vbox, key=lambda v: side * v * up)
                val = vend * up + at_end
                refuted = (list(glo), vend, val, val, at_end)
            for vend in ([] if refuted else vbox):
                d = side if vend >= 0 else -side
                g = _corner_ascent(net, glo, ghi, k, d)
                enc = _point_f(net, g, k)
                if enc is None:
                    continue
                Ilo, Ihi = _hull((vend,), enc)
                at_end = at_hi if side > 0 else at_lo
                Ilo, Ihi = Ilo + at_end, Ihi + at_end
                if side > 0 and Ilo > hi_b or side < 0 and Ihi < lo_b:
                    refuted = (g, vend, Ilo, Ihi, at_end)
                    break
            if refuted:
                g, vend, Ilo, Ihi, at_end = refuted
                point = {}
                for j, bn in enumerate(names, start=1):
                    br = raw["network"]["branches"][bn]
                    spec = br.get("R", br.get("G"))
                    if spec in qs and glo[j] < ghi[j]:
                        sc = _parse_unit(qs[spec].get("unit"))[0]
                        val = (1 / g[j] if "R" in br else g[j]) / sc
                        point[spec] = _s(val)
                src = raw["network"]["source"]
                src_v = src.get("I", src.get("V"))
                if src_v in qs and vbox[0] < vbox[1]:
                    point[src_v] = _s(vend / _parse_unit(qs[src_v].get("unit"))[0])
                if rq["kind"] == "V1" and src.get("at") in qs and net.at_box[0] < net.at_box[1]:
                    point[src["at"]] = _s(at_end / _parse_unit(qs[src["at"]].get("unit"))[0])
                row.update(verdict="REFUTED", its_violating_point=point,
                           value_there=[_s(Ilo / unit_sc), _s(Ihi / unit_sc)],
                           value_there_is=f"{label} at that point, enclosed exactly (two certificates on the point)")
            else:
                row.update(verdict="OPEN",
                           why="the proved range crosses the bound, and no corner the search found fails provably — "
                               "the certificate may be loose (the gap below)")
        # the value the search reached inside the box, for the gap
        found = []
        for d in (1, -1):
            g = _corner_ascent(net, glo, ghi, k, d)
            found.append(NS._float_current(net, g, 1, k))
        lo_f, hi_f = _hull([float(v) for v in vbox], (min(found), max(found)))
        lo_f, hi_f = lo_f + float(at_lo), hi_f + float(at_hi)
        row["found_inside"] = [f"{lo_f / float(unit_sc):.9g}", f"{hi_f / float(unit_sc):.9g}"]
        row["found_inside_is"] = "the range the search reached at corners (floating point): the proved range's tightness"
        if MODE.DEV[0]:
            row["dev_check"] = _dev_check(net, glo, ghi, vbox, k, lo_I - at_lo, hi_I - at_hi, unit_sc)
            if row["dev_check"].startswith("FAULT"):
                row["verdict"] = "STAND FAULT"
        out_reqs.append(row)
        verdicts.append(row["verdict"])
    if "STAND FAULT" in verdicts:
        verdict = "STAND FAULT"
    elif "REFUTED" in verdicts:
        verdict = "REFUTED"
    elif "OPEN" in verdicts:
        verdict = "OPEN"
    else:
        verdict = "EARNED"
    from .judge_ztl import ztl_commit
    return {"stand": "ztl-stand/1", "judge": f"ZTL {ztl_commit()} + the network certificate (ustand/znet.py)",
            "verdict": verdict, "network": {"nodes": len(nodes), "branches": len(names),
                                            "free_branches": sum(1 for j in net.res if glo[j] < ghi[j])},
            "units": units_note, "requirements": out_reqs,
            **({"inputs_from_laws": {n: list(v) for n, v in net.law_boxes.items()},
                "inputs_from_laws_are": "each derived input's range PROVED from the laws first (one way: the network "
                                        "does not feed back into the laws)"} if net.law_boxes else {}),
            **({"correlation_note": net.corr_note} if net.corr_note else {}),
            "rests_on": ("the network certificate: znet.py checks every certificate exactly by the kernel's rules; "
                         "it is in the stand, not in public ZTL; lean/ZNet.lean proves its algebra, the energy enclosure and "
                         "the assembly with zero axioms (Kirchhoff's law and the derivative signs are named premises)"),
            "checked_by": ("the network certificate + exact corner enumeration (dev mode)" if MODE.DEV[0] else
                           "the network certificate (work mode; --dev adds every corner solved exactly, small "
                           "networks)")}


def _dev_check(net, glo, ghi, vbox, k, lo_I, hi_I, sc):
    free = [j for j in net.res if glo[j] < ghi[j]]
    if (1 << len(free)) > DEV_CORNERS:
        return f"skipped: {len(free)} free branches, {1 << len(free)} corners (limit {DEV_CORNERS})"
    vals = []
    for ends in itertools.product(*[(glo[j], ghi[j]) for j in free]):
        g = list(glo)
        for j, e in zip(free, ends):
            g[j] = e
        f = _exact_f(net, g, k)
        vals.extend(v * f for v in vbox)
    lo_c, hi_c = min(vals), max(vals)
    if lo_c < lo_I or hi_c > hi_I:
        return (f"FAULT: a corner's exact current [{float(lo_c / sc):.9g}, {float(hi_c / sc):.9g}] lies outside the "
                f"proved range [{float(lo_I / sc):.9g}, {float(hi_I / sc):.9g}]")
    return (f"agrees: every one of {1 << len(free)} corners solved exactly lies in the proved range; the corners' "
            f"exact extremes [{_s(lo_c / sc)}, {_s(hi_c / sc)}] in the requirement's unit (the true extremes: a current is monotone in each conductance)")
