"""COMPONENTS — assume–guarantee contracts (2026-10-12, the curator's "да"; his example: a 220 V socket — a 5 V
adapter — a phone's charging board — a battery: four devices, each proved once and reused).

A COMPONENT is an ordinary brick with an INTERFACE:

    "interface": {"inputs":  {"Vin": {"assume": ["200", "250"], "bands": ["200", "230", "250"]}},
                  "outputs": ["Vout"]}

  inputs:  given quantities of the brick; `assume` the range the component is proved for (in the quantity's unit);
           `bands` (optional) cut it into pieces, each proved on its own — the contract is then a TABLE
           "input band -> output range", which keeps much of the dependence a single range loses;
  outputs: derived quantities whose ranges the stand proves (the GUARANTEE).
The contract: for every band (several inputs: every combination of their bands) the brick is judged with each input
given that band's range; its own requirements (ratings) must be EARNED there, and each output gets the stand's proved
range. A band that is not earned has no guarantee.

A SYSTEM is a brick with
    "components": {"AD": {"brick": {...}} | {"file": "adapter.json"}, ...},
    "connect":    {"AD.Vin": "Vmains", "CH.Vin": "AD.Vout", ...}
and its laws, requirements, objective may name a component's output as `AD.Vout`. The stand, in the order the
connections give (an upstream component first):
  1. the range ARRIVING at each input: a system given's own range, or the upstream output's guaranteed range;
  2. it must lie inside the input's `assume` — else that component's contract does not cover it and the system is
     OPEN (an arriving range is an enclosure, maybe wider than the truth: leaving `assume` is not a refutation);
  3. the bands it touches are used; each output's range is the hull of their guarantees — and must be guaranteed
     in every one of them (a touched band without a guarantee: OPEN, with the component's own reason);
  4. the system is judged as an ordinary brick, each component output a GIVEN with that range (named AD_Vout).
     EARNED is sound (every range encloses). A REFUTED at a point is NOT: the point may lie in an enclosure where no
     component can be — the system answers OPEN then, and says where it failed; unless a requirement fails at EVERY
     point of the ranges (its negation EARNED on the flat brick): then the true system fails it too — REFUTED
     (audit 2026-10-13, cx1).
The component's inside is not recomputed: its contract is proved once per (brick, band) — cached by the content's
sha256 — and reused. RECURSION: a system with an `interface` is itself a component (its contract is judged by
expanding its own components). CHOICE: a component may be {"choose": [candidates]}, each with exact `fields` (a price) the system names
as COMPONENT.field; every combination is judged, cheapest first when the objective reads only such numbers, and the
first EARNED is the answer — `optimal` only when nothing cheaper is left OPEN (a system refutes only everywhere). A choice
inside a component that is itself a system is refused (its contract must be ONE device's).
A cycle in the hierarchy (a component containing itself) is a BRICK ERROR, and so is
a feedback between siblings (an input fed, through the connections, by its own component's output) — version 1.

What is lost, said plainly: between components only RANGES travel. Two outputs of one component, or two components
fed by one source, are given independent ranges in the system — a correlation a flat brick would keep (bands keep
part of it). The answer is sound (every range encloses), maybe wider than the flat brick's.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import os
import re
from fractions import Fraction as F

from . import bricks as B
from . import safeexpr as SX
from . import units as U

_CACHE = {}      # sha256 of (component brick, input ranges) -> the stand's answer, reduced
_STACK = []      # sha256 of the component bricks being contracted now: a repeat is a cycle


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _fr(x: F) -> str:
    return f"{x.numerator}/{x.denominator}"


def _given_range(q: dict, name: str):
    try:
        f = B.field(q)
    except (ValueError, ZeroDivisionError, TypeError, KeyError, AttributeError):
        raise B.BrickError(f"connect: the given {name} has no readable value, tolerance or range")
    if f[0] == "label":
        raise B.BrickError(f"connect: {name} is a label, not a quantity")
    if f[0] == "range":
        return f[1], f[2]
    nom, tol = f
    a, b = nom * (1 - tol), nom * (1 + tol)
    return min(a, b), max(a, b)


def _shape(raw, where):
    """The fields this module reads before the stand checks the brick: their shape, or a BRICK ERROR."""
    if not isinstance(raw, dict):
        raise B.BrickError(f"{where}: a brick is a JSON object")
    qs = raw.get("quantities")
    if not isinstance(qs, dict) or not all(isinstance(k, str) and isinstance(v, dict) for k, v in qs.items()):
        raise B.BrickError(f"{where}: quantities must be an object of objects")
    laws = raw.get("laws", [])
    if not isinstance(laws, list) or not all(isinstance(l, dict) and isinstance(l.get("zfl"), str) for l in laws):
        raise B.BrickError(f"{where}: laws must be a list of {{\"zfl\": \"...\"}}")
    reqs = raw.get("requirements", [])
    if not isinstance(reqs, list) or not all(isinstance(r, dict) for r in reqs):
        raise B.BrickError(f"{where}: requirements must be a list of objects")
    d = raw.get("define")
    if d is not None and (not isinstance(d, dict) or not all(isinstance(v, str) for v in d.values())):
        raise B.BrickError(f"{where}: define must be an object of expressions")
    o = raw.get("objective")
    if o is not None and not isinstance(o, dict):
        raise B.BrickError(f"{where}: objective must be an object")


CHOICES_MAX = 2000      # combinations of chosen components judged (each one a whole system run)


FAMILY_MAX = 500        # a component's own designs expanded into candidates


def _alternatives(cname, spec, base):
    """A component's candidates: [{"label", "brick", "base", "fields": {name: (value, unit)}}] — one for a fixed
    component, several for {"choose": [...]}, and — PARAMETERS (2026-10-12, the curator's "да", v1) — one per design
    of a candidate whose brick has its own slots (a resistor from E24): each design is pinned into ONE device (a
    contract is one device's; judged per band, a free slot would pick another part in every band), and the brick's
    own objective, read at that design, is its field `cost`. A candidate's FIELDS (a price, a mass) are exact numbers
    the system may name as COMPONENT.field (version 1: exact, no tolerance)."""
    if not isinstance(spec, dict):
        raise B.BrickError(f"component {cname}: an object, {{\"file\": ...}} or {{\"choose\": [...]}}")
    cands = spec["choose"] if "choose" in spec else [spec]
    if not isinstance(cands, list) or not cands or not all(isinstance(x, dict) for x in cands):
        raise B.BrickError(f"component {cname}: choose is a non-empty list of candidates")
    out = []
    for i, cand in enumerate(cands):
        fields = {}
        fs = cand.get("fields") or {}
        if not isinstance(fs, dict):
            raise B.BrickError(f"component {cname}: fields must be an object")
        for k, v in fs.items():
            if not re.fullmatch(r"[A-Za-z_]\w*", str(k)):
                raise B.BrickError(f"component {cname}: field {k!r} is not a name")
            try:
                val, unit = (v.get("value"), v.get("unit", "")) if isinstance(v, dict) else (v, "")
                fields[k] = (B.num(val), unit if isinstance(unit, str) else "")
            except (ValueError, ZeroDivisionError, TypeError):
                raise B.BrickError(f"component {cname}: field {k} must be an exact number (version 1)")
        label = str(cand.get("label", os.path.basename(cand["file"]) if isinstance(cand.get("file"), str)
                             else f"#{i + 1}"))
        brick, cbase = _brick_of(cand, base, cname)
        if isinstance(brick, dict) and brick.get("slots") and not brick.get("components"):
            fam = _family(brick, cname)
            for flab, pinned, cost, pfields in fam:
                pfields = dict(pfields)
                cost_why = pfields.pop("__cost_why", None)
                f2 = dict(fields, **pfields)
                if cost is not None:
                    if "cost" in f2:
                        raise B.BrickError(f"component {cname}: a field named cost and the brick's own objective")
                    f2["cost"] = cost
                out.append({"label": flab if len(cands) == 1 else f"{label}: {flab}", "brick": pinned,
                            "base": cbase, "fields": f2, "cost_why": cost_why})
        else:
            out.append({"label": label, "brick": brick, "base": cbase, "fields": fields})
    if len(out) > 1 and len({x["label"] for x in out}) != len(out):
        raise B.BrickError(f"component {cname}: two candidates with one label")
    return out


_FAMILY = {}


def _family(brick, cname):
    """[(label, pinned brick, (cost, unit) or None)] — every design of the component's own slots, each pinned
    (cached by content: a system's every combination asks again)."""
    key = _sha(brick)
    if key not in _FAMILY:
        _FAMILY[key] = _family_build(brick, cname)
    return _FAMILY[key]


def _family_build(brick, cname):
    from . import stand as S
    _shape(brick, f"component {cname}")
    sub = {k: v for k, v in brick.items() if k != "interface"}
    itf = brick.get("interface")
    outs = itf.get("outputs") if isinstance(itf, dict) and isinstance(itf.get("outputs"), list) else []
    sub["requirements"] = list(sub.get("requirements") or []) + [
        {"quantity": o, "op": "within", "value": ["-1e300", "1e300"]} for o in outs if isinstance(o, str)]
    sub.setdefault("catalog", {})
    b = B.load(sub)
    obj = (brick.get("objective") or {}) if isinstance(brick.get("objective"), dict) else {}
    out = []
    for d in S.designs(b):
        if len(out) >= FAMILY_MAX:
            raise B.BrickError(f"component {cname}: more than {FAMILY_MAX} designs of its own slots (version 1)")
        pinned = copy.deepcopy(brick)
        labels, env, part_fields = [], {}, {}
        for s_, (cat, item) in d.items():
            # the LOADED brick's catalog: an optional slot's "none" catalog exists only there (blind test 6, c03:
            # KeyError 'HT_none', a STAND ERROR)
            rawcat = (brick.get("catalog") or {}).get(cat) or b["catalog"][cat]
            if "continuous" in rawcat:
                raise B.BrickError(f"component {cname}: a continuous slot inside a component (version 1: discrete "
                                   f"parameters only)")
            parsed = B.items(rawcat)
            idx = next(k for k, it in enumerate(parsed) if it == item)
            if "integers" in rawcat:
                spec = rawcat["integers"]
                v = int(B.num(spec["from"])) + idx
                newcat = {"integers": dict(spec, **{"from": str(v), "to": str(v)})}
                labels.append(f"{s_}.{spec['field']}={v}")
            else:
                rawit = rawcat["items"][idx]
                newcat = {"items": [rawit], **({"fields": rawcat["fields"]} if "fields" in rawcat else {})}
                nm = rawit.get("name") or rawit.get("id") or rawit.get("label") if isinstance(rawit, dict) else None
                labels.append(f"{s_}={nm or '#' + str(idx + 1)}")
            pinned["catalog"][f"__pin_{s_}"] = newcat
            pinned["slots"][s_] = {"from": [f"__pin_{s_}"]}
            fu = B.field_units(rawcat)
            for f, val in item.items():
                if val[0] == "label":
                    continue
                if val[0] != "range" and val[1] == 0:
                    env[B.ident(f"{s_}.{f}")] = val[0]
                # the chosen part's fields reach the system as COMPONENT.slot.field (real round 4, k05: the ratio of
                # the gearhead picked travelled only as its `cost`); a toleranced one as its own toleranced given —
                # sound, but not tied to the component's inside (an independent copy of the same tolerance)
                part_fields[f"{s_}.{f}"] = (val, fu.get(f) or "")
        cost = None
        itf_in = set(((brick.get("interface") or {}).get("inputs") or {}).keys()) \
            if isinstance(brick.get("interface"), dict) else set()
        obj_names = set(re.findall(r"[A-Za-z_]\w*", B.compile_expr(obj["minimize"], brick.get("define")))) \
            if isinstance(obj.get("minimize"), str) else set()
        derived_n = {n for n, q in (brick.get("quantities") or {}).items() if isinstance(q, dict) and q.get("role") == "derived"}
        if obj_names & (itf_in | derived_n):
            # the component's price reads an INPUT the system decides (blind test 6, c02: a cable's price x its
            # length, the length a system quantity — `cost` came out at the placeholder length, 2068 EUR instead of
            # 2825.5, no warning): no `cost` field then; the system prices it from the part's fields itself
            obj = {}
            cost_why = (f"its objective reads {sorted(obj_names & (itf_in | derived_n))}, decided by the system — "
                        f"price it in the system's objective from the part's fields (e.g. AD.slot.price)")
        else:
            cost_why = None
        if isinstance(obj.get("minimize"), str):
            try:
                for n, q in (brick.get("quantities") or {}).items():
                    if q.get("role") == "given" and "range" not in q and B.num(q.get("tolerance", "0")) == 0:
                        env.setdefault(n, B.num(q["value"]))
                text = B.compile_expr(obj["minimize"], brick.get("define"))
                cost = (F(eval(SX.compile_checked(text, "<cost>"), {"__builtins__": {}}, env)),
                        obj.get("unit", "") if isinstance(obj.get("unit", ""), str) else "")
            except Exception:                            # noqa: BLE001 — no cost field, said by its absence
                cost = None
        out.append((", ".join(labels), pinned, cost, dict(part_fields, **({"__cost_why": cost_why} if cost_why else {}))))
    if not out:
        raise B.BrickError(f"component {cname}: no design of its own slots passes its `where`")
    return out


def absolutize(raw, base):
    """A copy of the system whose component files are absolute paths (2026-10-12: `find` judges copies of the brick
    as dicts, and a dict has no directory of its own to read relative files from)."""
    if not isinstance(raw, dict) or not isinstance(raw.get("components"), dict):
        return raw
    out = copy.deepcopy(raw)
    for spec in out["components"].values():
        cands = spec.get("choose") if isinstance(spec, dict) else None
        for cand in (cands if isinstance(cands, list) else [spec]):
            if isinstance(cand, dict) and isinstance(cand.get("file"), str):
                cand["file"] = os.path.normpath(os.path.join(base, cand["file"]))
    return out


def _brick_of(spec, base, cname):
    if isinstance(spec, dict) and isinstance(spec.get("brick"), dict):
        return spec["brick"], base
    if isinstance(spec, dict) and isinstance(spec.get("file"), str):
        path = os.path.join(base, spec["file"])
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh), os.path.dirname(path)
        except (OSError, ValueError) as e:
            raise B.BrickError(f"component {cname}: cannot read {spec['file']}: {e}")
    raise B.BrickError(f"component {cname}: give {{\"brick\": {{...}}}} or {{\"file\": \"path\"}}")


def _interface(brick, cname):
    _shape(brick, f"component {cname}")
    itf = brick.get("interface")
    if not isinstance(itf, dict) or not isinstance(itf.get("inputs"), dict) or not itf.get("outputs"):
        raise B.BrickError(f"component {cname}: its brick needs \"interface\": {{\"inputs\": {{...}}, "
                           f"\"outputs\": [...]}}")
    qs = brick.get("quantities") or {}
    if not isinstance(itf["outputs"], list) or not all(isinstance(x, str) for x in itf["outputs"]):
        raise B.BrickError(f"component {cname}: interface outputs must be a list of names")
    ins = {}
    for n, spec in itf["inputs"].items():
        if (qs.get(n) or {}).get("role") != "given":
            raise B.BrickError(f"component {cname}: interface input {n} must be a given quantity of its brick")
        arriving_bands = isinstance(spec, dict) and spec.get("bands") == "arriving"
        try:
            lo, hi = B.num(spec["assume"][0]), B.num(spec["assume"][1])
            cuts = [B.num(x) for x in (None if arriving_bands else spec.get("bands"))
                    or [spec["assume"][0], spec["assume"][1]]]
        except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError, AttributeError):
            raise B.BrickError(f"component {cname}: input {n} needs \"assume\": [low, high] (and optional "
                               f"\"bands\": [cut, ...])")
        if not lo <= hi or cuts[0] != lo or cuts[-1] != hi or any(a >= b for a, b in zip(cuts, cuts[1:])):
            raise B.BrickError(f"component {cname}: input {n}: assume [low, high] with bands rising from low "
                               f"to high")
        ins[n] = {"assume": (lo, hi), "bands": list(zip(cuts, cuts[1:])) or [(lo, hi)], "unit": qs[n].get("unit", ""),
                  "arriving": arriving_bands}
    outs = list(itf["outputs"])
    for n in outs:
        if (qs.get(n) or {}).get("role") != "derived":
            raise B.BrickError(f"component {cname}: interface output {n} must be a derived quantity of its brick")
    return ins, outs


def _dims(unit):
    try:
        return U.parse(unit or "")
    except (U.UnitError, ValueError, KeyError):
        return None


def _with_inputs(brick, values):
    """The brick with each input a range (a, b) or a point (a, a)."""
    sub = copy.deepcopy(brick)
    sub.pop("interface", None)
    for n, (a, b) in values.items():
        q = sub["quantities"][n]
        sub["quantities"][n] = {k: v for k, v in q.items() if k not in ("value", "tolerance", "range")}
        if a == b:
            sub["quantities"][n]["value"] = _fr(a)
        else:
            sub["quantities"][n]["range"] = [_fr(a), _fr(b)]
    sub.setdefault("slots", {})
    sub.setdefault("catalog", {})
    sub["conflicts"] = False
    return sub


TIGHT_TRIES = (F(1, 10 ** 6), F(1, 10 ** 4), F(1, 100))   # the margins tried past an attained extreme
CORNERS_MAX = 10                                            # toleranced quantities read at every corner


def _attained(sub, names):
    """{name: (min, max)} of values the brick ATTAINS (in each quantity's own unit) — at every corner of its box (up to
    2^10) and its middle, each solved exactly by the checker. Search side: these are real values, so a proved bound
    can never be tighter than them; None when the laws cannot be solved at a point."""
    from . import stand as S
    from . import checker as C
    try:
        b = B.load(sub)
        d = next(iter(S.designs(b)), None)
        if d is None:
            return None
        fixed, boxes, derived, _g = S.frame(b, d)
        laws = B.implicit_laws(b, [B.compile_expr(l["zfl"], b.get("define")) for l in b["laws"]])
        keys = sorted(boxes)
        if len(keys) > CORNERS_MAX:
            return None
        pts = [dict(zip(keys, c)) for c in itertools.product(*[boxes[k] for k in keys])]
        pts.append({k: (boxes[k][0] + boxes[k][1]) / 2 for k in keys})
        scale = {n: U.parse(b["quantities"][n].get("unit") or "")[0] for n in names}
        got = {}
        for pt in pts:
            vals = C.solve_at(laws, dict(fixed, **pt), derived)
            for n in names:
                v = vals[n] / scale[n]
                lo, hi = got.get(n, (v, v))
                got[n] = (min(lo, v), max(hi, v))
        return got
    except Exception:                                    # noqa: BLE001 — a search aid, never a verdict
        return None


def _tighten(sub, base, n, outer, attained):
    """The proved range of n made TIGHT (2026-10-12, real round 4: a contract was the stand's OUTER reading — a name
    that appears twice did not cancel, k01's remainder +-0.19 V against +-0.02 V true): the bound just past the attained
    extreme, proved as an ordinary requirement (a certificate, ZTL checks it); widened if not proved, never past the
    outer one. -> (lo, hi), each end proved."""
    lo_o, hi_o = outer
    a_lo, a_hi = attained
    span = max(abs(a_hi - a_lo), abs(a_lo), abs(a_hi), F(1, 10 ** 12))
    res = [lo_o, hi_o]
    from .stopflag import check as _stop_check
    for side, op in ((0, ">="), (1, "<=")):
        a = a_lo if side == 0 else a_hi
        for m in TIGHT_TRIES:
            _stop_check()
            c = a - m * span if side == 0 else a + m * span
            if (side == 0 and c <= lo_o) or (side == 1 and c >= hi_o):
                break
            t = copy.deepcopy(sub)
            t["requirements"] = [r for r in (t.get("requirements") or []) if r.get("value") != ["-1e300", "1e300"]] \
                + [{"quantity": n, "op": op, "value": _fr(c)}]
            r = run_brick(t, base)
            if r.get("verdict") == "EARNED":
                res[side] = c
                break                              # REFUTED: the extreme lies inside, past the corners — wider
    return tuple(res)


def _judge_band(brick, base, ins, outs, band):
    """The component's brick with each input given its band: its ratings judged, each output's range proved, and —
    AFFINE CONTRACTS (2026-10-12, the curator's "да") — for an output of the same dimension as every input, a slope
    k per input and the proved range of the remainder e = out - sum k*in over the band. The slope is the search's
    (two point runs per input); ANY slope keeps the remainder's range true, a good one keeps it narrow.
    -> {"earned", "outputs": {n: (lo, hi)}, "affine": {n: ({input: k}, (e_lo, e_hi))}, "why"}; cached by content."""
    key = _sha({"brick": brick, "band": {n: [_fr(a), _fr(b)] for n, (a, b) in band.items()}, "v": 3})
    if key in _CACHE:
        return _CACHE[key]
    qs = brick["quantities"]
    dims = {n: _dims(qs[n].get("unit")) for n in list(band) + list(outs)}
    aff_outs = [o for o in outs if dims[o] is not None and all(dims[n] is not None and dims[n][1] == dims[o][1]
                                                               for n in band)]
    ks = {o: {} for o in aff_outs}
    for n, (a, b) in band.items():
        if not aff_outs or a == b:
            continue
        mids = []
        for x in (a, b):
            sub = _with_inputs(brick, dict(band, **{n: (x, x)}))
            sub["requirements"] = list(sub.get("requirements") or []) + [
                {"quantity": o, "op": "within", "value": ["-1e300", "1e300"]} for o in aff_outs]
            r = run_brick(sub, base)
            if r.get("verdict") != "EARNED" or not r.get("guaranteed"):
                mids = None
                break
            mids.append({o: sum(B.num(v.split(" ")[0]) for v in r["guaranteed"][o]) / 2 for o in aff_outs})
        for o in aff_outs:
            if mids is None:
                ks[o] = None
            elif ks[o] is not None:
                k = (mids[1][o] - mids[0][o]) / (b - a)
                ks[o][n] = F(k).limit_denominator(10 ** 9)
    aff_outs = [o for o in aff_outs if ks[o] is not None]
    sub = _with_inputs(brick, band)
    res_name = {}
    for o in aff_outs:
        nm = f"zres_{o}"
        while nm in sub["quantities"]:
            nm = "z" + nm
        res_name[o] = nm
        sub["quantities"][nm] = {"role": "derived", "unit": qs[o].get("unit", "")}
        terms = " ".join(f"- ({_fr(k)})*{n}" for n, k in sorted(ks[o].items()))
        sub["laws"] = list(sub.get("laws") or []) + [{"zfl": f"{nm} == {o} {terms}".strip()}]
    sub["requirements"] = list(sub.get("requirements") or []) + [
        {"quantity": n, "op": "within", "value": ["-1e300", "1e300"]} for n in list(outs) + list(res_name.values())]
    r = run_brick(sub, base)
    if r.get("verdict") == "EARNED" and r.get("guaranteed"):
        got = {"earned": True, "why": None, "outputs": {}, "affine": {}}
        rd = lambda n: tuple(B.num(x.split(" ")[0]) for x in r["guaranteed"][n])
        att = _attained(sub, list(outs) + list(res_name.values())) if not brick.get("components") else None
        tight = lambda n: _tighten(sub, base, n, rd(n), att[n]) if att and n in att else rd(n)
        for n in outs:
            got["outputs"][n] = tight(n)
        for o, nm in res_name.items():
            if nm in r["guaranteed"]:
                got["affine"][o] = (dict(ks[o]), tight(nm))
        got["how"] = {n: (r.get("how") or {}).get(n) for n in outs}
        if r.get("design"):
            got["design"] = r["design"]
    else:
        got = {"earned": False, "outputs": {}, "affine": {},
               "why": f"{r.get('verdict')}: {str(r.get('why') or r.get('fails') or '')[:300]}"}
    _CACHE[key] = got
    return got


def contract(brick, base, cname="the component"):
    """The whole table: every band combination -> its judgement. (Also what a system's report shows.)"""
    ins, outs = _interface(brick, cname)
    names = sorted(ins)
    rows = []
    for combo in itertools.product(*[ins[n]["bands"] for n in names]):
        band = dict(zip(names, combo))
        rows.append((band, _judge_band(brick, base, ins, outs, band)))
    return ins, outs, rows


def _order(comps, connect):
    """Components in the order the connections give; a feedback between siblings is refused (version 1)."""
    deps = {c: set() for c in comps}
    for dst, src in connect.items():
        c_dst = dst.split(".")[0]
        if "." in src and src.split(".")[0] in comps:
            deps[c_dst].add(src.split(".")[0])
    done, order = set(), []
    while len(order) < len(comps):
        ready = sorted(c for c in comps if c not in done and deps[c] <= done)
        if not ready:
            raise B.BrickError(f"connect: a feedback between components ({', '.join(sorted(set(comps) - done))}) — "
                               f"not in version 1")
        for c in ready:
            done.add(c)
            order.append(c)
    return order


def expand(raw, base, pick=None):
    """The system brick -> (a flat brick with every component output a given range, the components' report, a reason
    the system cannot be judged or None). pick: {component: candidate index} for chosen components."""
    _shape(raw, "the system")
    comps = raw.get("components")
    connect = raw.get("connect") or {}
    if not isinstance(comps, dict) or not comps:
        raise B.BrickError("components: give at least one {\"name\": {\"brick\": ...}}")
    if not isinstance(connect, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                                for k, v in connect.items()):
        raise B.BrickError("connect: {\"COMPONENT.input\": \"source\", ...} — names as strings")
    for c in comps:
        if not re.fullmatch(r"[A-Za-z_]\w*", c):
            raise B.BrickError(f"components: {c!r} is not a name")
    qs = raw.get("quantities") or {}
    alts = {c: _alternatives(c, spec, base) for c, spec in comps.items()}
    chosen = {c: alts[c][(pick or {}).get(c, 0)] for c in comps}
    loaded = {c: (chosen[c]["brick"], chosen[c]["base"]) for c in comps}
    for dst, src in connect.items():
        if dst.count(".") != 1 or dst.split(".")[0] not in comps:
            raise B.BrickError(f"connect: {dst!r} is not COMPONENT.input")
    arriving_out = {}            # "C.out" -> (lo, hi) in that output's own unit
    out_unit = {}                # "C.out" -> its unit
    affine = {}                  # "C.out" -> ({source: k in SI}, (e_lo, e_hi) in the output's unit)
    report, blocked = {}, None
    for c in _order(comps, connect):
        brick, cbase = loaded[c]
        h = _sha(brick)
        if h in _STACK:
            raise B.BrickError(f"component {c}: it contains itself (a cycle in the hierarchy)")
        ins, outs = _interface(brick, c)
        rep = {"inputs": {}, "bands_used": None, "outputs": {}}
        arriving = {}
        srcs = {}
        for n in ins:
            src = connect.get(f"{c}.{n}")
            if src is None:
                raise B.BrickError(f"connect: {c}.{n} is not connected")
            if src in arriving_out:
                got_r, src_unit = arriving_out[src], out_unit[src]
            elif (qs.get(src) or {}).get("role") == "given":
                got_r, src_unit = _given_range(qs[src], src), qs[src].get("unit", "")
            else:
                raise B.BrickError(f"connect: {c}.{n} <- {src}: a system GIVEN or an upstream COMPONENT.output "
                                   f"(version 1)")
            # the arriving range in the INPUT's unit, through SI (2026-10-12: a source in kV fed an input in V)
            d_src, d_in = _dims(src_unit), _dims(ins[n]["unit"])
            if d_src is None or d_in is None or d_src[1] != d_in[1]:
                raise B.BrickError(f"connect: {c}.{n} ({ins[n]['unit'] or 'dimensionless'}) <- {src} "
                                   f"({src_unit or 'dimensionless'}): the units' dimensions differ")
            arriving[n] = (got_r[0] * d_src[0] / d_in[0], got_r[1] * d_src[0] / d_in[0])
            srcs[n] = src
            lo, hi = arriving[n]
            a_lo, a_hi = ins[n]["assume"]
            rep["inputs"][n] = {"from": src, "arrives": [_fr(lo), _fr(hi)], "assume": [_fr(a_lo), _fr(a_hi)],
                                "inside": a_lo <= lo and hi <= a_hi}
            if not rep["inputs"][n]["inside"] and blocked is None:
                blocked = (f"{c}.{n}: the range arriving from {src}, [{float(lo):.6g}, {float(hi):.6g}], leaves the "
                           f"component's assume [{float(a_lo):.6g}, {float(a_hi):.6g}] — its contract does not cover "
                           f"it (an arriving range encloses, so this is not a refutation)")
        report[c] = rep
        if blocked:
            break
        # a band is touched when it OVERLAPS what arrives (positive length) — one sharing only an edge is not
        # (real round 4, k01 k03 k05: it added a band and lost the affine form); a point arriving: the first band
        # holding it
        touched = {}
        for n in ins:
            lo_a, hi_a = arriving[n]
            if ins[n].get("arriving"):
                # "bands": "arriving" (real round 4, k01 k04 k06: bands were cut by hand and the answer depended on the
                # cut): the contract is judged on what arrives itself — the tightest; a new range costs a new
                # judgement (cached by content)
                touched[n] = [(lo_a, hi_a)]
            elif lo_a == hi_a:
                touched[n] = [next(bd for bd in ins[n]["bands"] if bd[0] <= lo_a <= bd[1])]
            else:
                touched[n] = [bd for bd in ins[n]["bands"] if bd[0] < hi_a and lo_a < bd[1]]
        names = sorted(ins)
        _STACK.append(h)
        try:
            judged = [(dict(zip(names, combo)), _judge_band(brick, cbase, ins, outs, dict(zip(names, combo))))
                      for combo in itertools.product(*[touched[n] for n in names])]
        finally:
            _STACK.pop()
        rep["bands_used"] = [{"band": {n: [_fr(a), _fr(b)] for n, (a, b) in bd.items()},
                              "earned": j["earned"], **({"why": j["why"]} if not j["earned"] else
                                                        {"outputs": {o: [_fr(x), _fr(y)] for o, (x, y) in
                                                                     j["outputs"].items()}})}
                             for bd, j in judged]
        bad = [j for _bd, j in judged if not j["earned"]]
        if bad:
            blocked = f"component {c}: a band its input touches has no guarantee ({bad[0]['why']})"
            break
        cq = brick.get("quantities") or {}
        for o in outs:
            lo = min(j["outputs"][o][0] for _bd, j in judged)
            hi = max(j["outputs"][o][1] for _bd, j in judged)
            arriving_out[f"{c}.{o}"] = (lo, hi)
            out_unit[f"{c}.{o}"] = cq[o].get("unit", "")
            rep["outputs"][o] = [_fr(lo), _fr(hi)]
            # ONE band touched per input and an affine contract there: the output keeps its source
            if len(judged) == 1 and o in judged[0][1].get("affine", {}) and raw.get("contracts") != "ranges":
                ks, (e_lo, e_hi) = judged[0][1]["affine"][o]
                d_o = _dims(cq[o].get("unit", ""))
                # slopes of inputs wired to ONE source ADD (audit 2026-10-13, cx1: a dict keyed by source let the
                # second slope overwrite the first — G*(S - S) became G*S, a false EARNED)
                k_si = {}
                for n, k in ks.items():
                    k_si[srcs[n]] = k_si.get(srcs[n], 0) + k * d_o[0] / _dims(ins[n]["unit"])[0]
                affine[f"{c}.{o}"] = (k_si, (e_lo, e_hi))
                rep["outputs_affine"] = dict(rep.get("outputs_affine") or {}, **{o: {
                    "slope": {n: _fr(k) for n, k in ks.items()}, "remainder": [_fr(e_lo), _fr(e_hi)]}})
    if blocked:
        # outputs not reached get PLACEHOLDER ranges — only so the flat brick is whole for a shape and units check
        # (_validate); a blocked system is never judged
        for c in comps:
            itf = loaded[c][0].get("interface") if isinstance(loaded[c][0], dict) else None
            for o in (itf.get("outputs") if isinstance(itf, dict) and isinstance(itf.get("outputs"), list) else []):
                if isinstance(o, str):
                    arriving_out.setdefault(f"{c}.{o}", (F(0), F(0)))
                    q_o = (loaded[c][0].get("quantities") or {}).get(o)
                    out_unit.setdefault(f"{c}.{o}", q_o.get("unit", "") if isinstance(q_o, dict) else "")
    flat = {k: v for k, v in raw.items() if k not in ("components", "connect", "interface")}
    flat["quantities"] = dict(qs)
    names = {}
    for ref in arriving_out:
        c, o = ref.split(".")
        nm = f"{c}_{o}"           # not C__o: in a brick X__y already means slot X's field y
        if nm in flat["quantities"] or (ref in affine and f"{nm}_e" in flat["quantities"]):
            raise B.BrickError(f"components: the name {nm} (for {ref}) is taken in the system")
        names[ref] = nm
    extra_laws = []
    for ref, (lo, hi) in arriving_out.items():
        c, o = ref.split(".")
        nm, unit = names[ref], out_unit.get(ref, "")
        if ref in affine and not blocked:
            k_si, (e_lo, e_hi) = affine[ref]
            flat["quantities"][nm] = {"role": "derived", "unit": unit,
                                      "why": f"component {c}'s output {o}: slope x source + a proved remainder"}
            flat["quantities"][f"{nm}_e"] = {"role": "given", "range": [_fr(e_lo), _fr(e_hi)], "unit": unit,
                                             "why": f"component {c}'s proved remainder of {o} (affine contract)"}
            terms = " + ".join(f"({_fr(k)})*{names.get(sref, sref)}" for sref, k in sorted(k_si.items()))
            extra_laws.append({"zfl": f"{nm} == {nm}_e" + (f" + {terms}" if terms else "")})
        else:
            flat["quantities"][nm] = {"role": "given", "range": [_fr(lo), _fr(hi)], "unit": unit,
                                      "why": f"component {c}'s guaranteed output {o}"}

    for c in comps:
        for k, (val, unit) in chosen[c]["fields"].items():
            nm = f"{c}_{k.replace('.', '_')}"
            if nm in flat["quantities"] or f"{c}.{k}" in names:
                raise B.BrickError(f"components: the name {nm} (for {c}.{k}) is taken")
            why = f"component {c}'s field {k} ({chosen[c]['label']})"
            if isinstance(val, tuple) and val[0] == "range":
                flat["quantities"][nm] = {"role": "given", "range": [_fr(val[1]), _fr(val[2])], "unit": unit, "why": why}
            elif isinstance(val, tuple):
                flat["quantities"][nm] = {"role": "given", "value": _fr(val[0]), "tolerance": _fr(val[1]),
                                          "unit": unit, "why": why}
            else:
                flat["quantities"][nm] = {"role": "given", "value": _fr(val), "unit": unit, "why": why}
            names[f"{c}.{k}"] = nm

    def sub(text):
        for ref, nm in sorted(names.items(), key=lambda kv: -len(kv[0])):     # AD.R1.R before AD.R1
            text = re.sub(rf"\b{re.escape(ref)}\b", nm, text)
        return text
    flat["laws"] = [dict(l, zfl=sub(l["zfl"]), **({"valid": sub(l["valid"])} if isinstance(l.get("valid"), str) else {}))
                    for l in flat.get("laws") or []] + extra_laws         # `valid` too (blind test 6, c03)
    if isinstance(flat.get("define"), dict):
        flat["define"] = {k: sub(v) for k, v in flat["define"].items()}
    if isinstance(flat.get("objective"), dict) and isinstance(flat["objective"].get("minimize"), str):
        flat["objective"] = dict(flat["objective"], minimize=sub(flat["objective"]["minimize"]))
    reqs = []
    for r in flat.get("requirements") or []:
        r = dict(r)
        if isinstance(r.get("quantity"), str) and r["quantity"] in names:
            r["quantity"] = names[r["quantity"]]
        reqs.append(r)
    flat["requirements"] = reqs
    texts = [l["zfl"] for l in flat["laws"]] + list((flat.get("define") or {}).values()) + \
        [(flat.get("objective") or {}).get("minimize") or ""]
    for t in texts:
        if not isinstance(t, str):
            continue
        for m in re.finditer(r"\b([A-Za-z_]\w*)\.([A-Za-z_][\w.]*)", t):
            if m.group(1) in comps:
                if m.group(2) == "cost" and chosen[m.group(1)].get("cost_why"):
                    raise B.BrickError(f"components: {m.group(0)} is not given — {chosen[m.group(1)]['cost_why']}")
                raise B.BrickError(f"components: {m.group(0)} is neither an output (interface) nor a field of the "
                                   f"chosen part of component {m.group(1)}")
    return flat, report, blocked


def run_brick(raw, base):
    """A brick that may itself be a system (recursion): expanded, then judged."""
    from . import stand as S
    if isinstance(raw, dict) and raw.get("components"):
        if _has_choice(raw, base):
            # a contract is ONE device's: a choice inside could pick another candidate in every band (version 1)
            raise B.BrickError("components: a component that is itself a system may not CHOOSE among candidates "
                               "(its contract would be another device in every band) — choose at the top")
        return _run_one(raw, base)
    return S._run(raw, conflicts=False)


def _validate(brick, outs=None):
    """A shape and units check of a brick WITHOUT judging it (a candidate, a flat system): its errors are said even
    when the candidate's combination stops before its contract is computed. Raises BrickError / UnitError."""
    from . import stand as S
    sub = {k: v for k, v in brick.items() if k not in ("interface", "components", "connect")}
    if outs is not None:
        sub["requirements"] = list(sub.get("requirements") or []) + [
            {"quantity": n, "op": "within", "value": ["-1e300", "1e300"]} for n in outs]
    sub.setdefault("slots", {})
    sub.setdefault("catalog", {})
    b = B.load(sub)
    laws = B.implicit_laws(b, [B.compile_expr(l["zfl"], b.get("define")) for l in b["laws"]])
    d = next(iter(S.designs(b)), None)
    if d is not None:
        S.unit_check(b, d, laws)


def _cost(flat):
    """The objective at the flat brick's exact givens (a candidate's price, a fixed number) — None when it names
    anything else (a range, a derived quantity): then no ordering, every combination is judged."""
    obj = (flat.get("objective") or {}).get("minimize")
    if not isinstance(obj, str):
        return None
    try:
        text = B.compile_expr(obj, flat.get("define"))
        env = {}
        for n, q in flat["quantities"].items():
            if q.get("role") == "given" and "range" not in q and B.num(q.get("tolerance", "0")) == 0:
                env[n] = B.num(q["value"])
        import ast as _ast
        names = {x.id for x in _ast.walk(_ast.parse(text, mode="eval")) if isinstance(x, _ast.Name)}
        if not names <= set(env):
            return None
        return F(eval(SX.compile_checked(text, "<objective>"), {"__builtins__": {}}, env))
    except Exception:                                    # noqa: BLE001 — an ordering, never a verdict
        return None


def _has_choice(raw, base):
    comps = raw.get("components")
    if not isinstance(comps, dict):
        return False
    _shape(raw, "the system")
    return any(len(_alternatives(c, spec, base)) > 1 for c, spec in comps.items())


def run_system(raw, base):
    if _has_choice(raw, base):
        return _run_choice(raw, base)
    return _run_one(raw, base)


def _run_choice(raw, base):
    """CHOSEN components (version 1): every combination of candidates, cheapest first when the objective reads only
    exact numbers (the candidates' fields); the first EARNED is the answer. A system refutes only where a requirement
    fails at every point of its ranges (they enclose), so a cheaper combination left OPEN makes `optimal` false."""
    _shape(raw, "the system")
    comps = raw["components"]
    for c in comps:
        if not re.fullmatch(r"[A-Za-z_]\w*", str(c)):
            raise B.BrickError(f"components: {c!r} is not a name")
    alts = {c: _alternatives(c, spec, base) for c, spec in comps.items()}
    names = sorted(comps)
    combos = list(itertools.product(*[range(len(alts[c])) for c in names]))
    if len(combos) > CHOICES_MAX:
        raise B.BrickError(f"components: {len(combos)} combinations of candidates — at most {CHOICES_MAX} "
                           f"(version 1)")
    for c in names:                          # every candidate's own brick: shape and units, before any judging
        for alt in alts[c]:
            brick = alt["brick"]
            _ins, outs = _interface(brick, c)
            if not brick.get("components"):
                try:
                    _validate(brick, outs)
                except (B.BrickError, U.UnitError) as e:
                    raise B.BrickError(f"component {c}, candidate {alt['label']}: {e}")
    rows = []
    for combo in combos:
        pick = dict(zip(names, combo))
        flat, _rep, blocked = expand(raw, base, pick)
        if blocked:
            try:
                _validate(flat)                  # its run will stop early: its errors are said here
            except (B.BrickError, U.UnitError) as e:
                raise B.BrickError(f"components, with {dict((c, alts[c][pick[c]]['label']) for c in names)}: {e}")
        rows.append({"pick": pick, "cost": _cost(flat)})     # the fields are in the flat brick even when blocked
    ordered = all(r["cost"] is not None for r in rows) and bool(raw.get("objective"))
    if ordered:
        rows.sort(key=lambda r: (r["cost"], [r["pick"][c] for c in names]))
    tried, best = [], None
    for r in rows:
        out = _run_one(raw, base, r["pick"])
        design = {c: alts[c][r["pick"][c]]["label"] for c in names}
        if out.get("verdict") in ("BRICK ERROR", "STAND ERROR"):
            # a malformed candidate is the brick's error, not a design that failed: said, never skipped
            return dict(out, why=f"components, with {design}: {out.get('why')}")
        cost = r["cost"]
        if cost is None and out.get("verdict") == "EARNED" and (out.get("objective") or {}).get("value"):
            try:
                cost = B.num(str(out["objective"]["value"]).split(" ")[0].lstrip("~"))
            except (ValueError, ZeroDivisionError):
                cost = None
        tried.append({"design": design, "verdict": out.get("verdict"), "cost": cost,
                      **({"why": str(out.get("why"))[:900]} if out.get("verdict") != "EARNED" else {})})
        if out.get("verdict") == "EARNED" and (best is None or (cost is not None and best[1] is not None
                                                                 and cost < best[1])):
            best = (out, cost, design)
            if ordered:
                break                        # cheapest first: nothing later is cheaper
    listing = [dict(t, cost=None if t["cost"] is None else f"{_fr(t['cost'])} (~{float(t['cost']):.6g})")
               for t in tried][:50]
    if best is None:
        if tried and all(t["verdict"] == "REFUTED" for t in tried):
            return {"verdict": "REFUTED", "why": f"components: every one of the {len(tried)} combinations of candidates "
                                                f"fails a requirement at every point of its guaranteed ranges",
                    "combinations": listing}
        return {"verdict": "OPEN", "why": f"components: none of the {len(tried)} combinations of candidates was earned "
                                         f"(a system refutes only where a requirement fails at every point of its "
                                         f"ranges)", "combinations": listing}
    out, cost, design = best
    out = dict(out)
    out["design"] = dict(out.get("design") or {}, **{f"component {c}": lab for c, lab in design.items()})
    cheaper_open = [t for t in tried if t["verdict"] not in ("EARNED", "REFUTED") and (not ordered or t is not tried[-1])]
    if raw.get("objective"):
        obj = {k: v for k, v in (out.get("objective") or {}).items() if k != "note"}   # the flat run's note is
        obj["minimize"] = raw["objective"].get("minimize", obj.get("minimize"))       # about ITS designs, not these
        out["objective"] = dict(obj, optimal=bool(ordered and not cheaper_open),
                                optimal_means=("among the candidates: true only when no cheaper combination is left "
                                               "undecided — a system refutes only where a requirement fails at every "
                                               "point of its ranges, so a cheaper one may stay OPEN"))
    out["combinations"] = listing
    out["combinations_judged"] = f"{len(tried)} of {len(combos)}" + (" (cheapest first; stopped at the first EARNED)"
                                                                      if ordered else "")
    return out


_NEG = {"<=": ">", ">=": "<", "<": ">=", ">": "<="}


def _fails_everywhere(flat):
    """A REFUTATION THROUGH ENCLOSURES (audit 2026-10-13, cx1; the curator 2026-10-15): a failing point of the
    components' ranges may be one no component produces — but when a requirement fails at EVERY point of those ranges,
    the true system (inside them) fails it too. Proved, not sampled: the requirement's negation is judged on the flat
    brick alone and must be EARNED. Only a brick with one design (no slots, modes or totals: there "every design fails"
    would need the negation for every design, which one EARNED does not say). -> (requirement, negation, run) or None."""
    if flat.get("slots") or flat.get("modes") or flat.get("totals"):
        return None
    from . import stand as S
    for r in flat.get("requirements") or []:
        if not isinstance(r, dict):
            continue
        if r.get("op") in _NEG:
            tries = [dict(r, op=_NEG[r["op"]])]
        elif r.get("op") == "within" and isinstance(r.get("value"), list) and len(r["value"]) == 2:
            tries = [dict(r, op="<", value=r["value"][0]), dict(r, op=">", value=r["value"][1])]
        else:
            continue
        for t in tries:
            nb = copy.deepcopy(flat)
            nb["requirements"] = [t]
            nb.pop("objective", None)
            try:
                got = S._run(nb, conflicts=False)
            except (B.BrickError, U.UnitError):
                continue
            if got.get("verdict") == "EARNED":
                return r, t, got
    return None


LIFT_CORNERS_MAX = 10       # a component's own box read at every corner (and its middle) up to 2^10 points


def _lift(raw, base, flat, out, pick=None):
    """WITNESS LIFTING (2026-10-18, the duel: a chain the SMT solvers refuted at once stayed OPEN here). The flat run
    failed at a point W of the components' ranges — maybe a point no component produces. Lift it: component by
    component in the connections' order, at its REAL input (a system given at W, or the output already lifted
    upstream), the component's own box is read at every corner and its middle (search side) and the point whose
    output lies closest to the one W needs is taken; its outputs are solved EXACTLY by the checker. Then the flat brick
    with every component output PINNED to those exact values and every system given to W is judged by the stand: a
    REFUTED there is a real state of the system — each component inside its own box, at its own input — that fails.
    An output that is irrational at its point (a function: an interval, not a number) stops the lift (no exact pin).
    -> (the refutation, the lifted states) or None."""
    from . import stand as S
    from . import checker as C
    try:
        comps, connect = raw["components"], raw.get("connect") or {}
        qs = raw.get("quantities") or {}
        alts = {c: _alternatives(c, spec, base) for c, spec in comps.items()}
        chosen = {c: alts[c][(pick or {}).get(c, 0)] for c in comps}
        W = {k.replace(".", "__"): B.num(str(v).split(" ")[0]) for k, v in (out.get("its_violating_point") or {}).items()}
        fb = B.load(flat)
        d0 = next(iter(S.designs(fb)), None)
        if d0 is None or fb.get("slots"):
            return None
        fx, bx, dv, _g = S.frame(fb, d0)
        wsi = dict(fx)
        for n in bx:
            if n not in W:
                return None
            wsi[n] = W[n] * U.parse(fb["quantities"][n].get("unit") or "")[0]
        flaws = B.implicit_laws(fb, [B.compile_expr(l["zfl"], fb.get("define")) for l in fb["laws"]])
        target = C.solve_at(flaws, wsi, dv)            # every flat value at W (SI): what each output must be
        real = {}                                      # "C.out" -> (value in SI, unit)
        states = {}
        for c in _order(comps, connect):
            brick = chosen[c]["brick"]
            if brick.get("components") or brick.get("slots"):
                return None                            # version 1: a plain component
            ins, outs = _interface(brick, c)
            cq = brick["quantities"]
            xin = {}
            for n in ins:
                src = connect[f"{c}.{n}"]
                if src in real:
                    v_si = real[src][0]
                elif src in qs:
                    v_si = wsi[src]
                else:
                    return None
                xin[n] = v_si / U.parse(ins[n]["unit"] or "")[0]
            sub = _with_inputs(brick, {n: (x, x) for n, x in xin.items()})
            sub["requirements"] = [{"quantity": o, "op": "within", "value": ["-1e300", "1e300"]} for o in outs]
            cb = B.load(sub)
            cd = next(iter(S.designs(cb)), None)
            cfx, cbx, cdv, _ = S.frame(cb, cd)
            claws = B.implicit_laws(cb, [B.compile_expr(l["zfl"], cb.get("define")) for l in cb["laws"]])
            keys = sorted(cbx)
            if len(keys) > LIFT_CORNERS_MAX:
                return None
            pts = [{k: (cbx[k][0] + cbx[k][1]) / 2 for k in keys}]
            pts += [dict(zip(keys, cr)) for cr in itertools.product(*[cbx[k] for k in keys])]
            want = {o: target.get(f"{c}_{o}") for o in outs}
            if any(isinstance(w, tuple) or w is None for w in want.values()):
                return None
            best = None
            for pt in pts:
                vals = C.solve_at(claws, dict(cfx, **pt), cdv)
                ys = {o: vals[o] for o in outs}
                if any(isinstance(y, tuple) for y in ys.values()):
                    continue                           # irrational there: no exact pin
                dist = max(abs(ys[o] - want[o]) / max(abs(want[o]), F(1, 10 ** 12)) for o in outs)
                if best is None or dist < best[0]:
                    best = (dist, pt, ys)
            if best is None:
                return None
            for o in outs:
                real[f"{c}.{o}"] = (best[2][o], cq[o].get("unit", ""))
            states[c] = {"input": {n: _fr(x) for n, x in xin.items()},
                         "own_point": {k.replace("__", "."): _fr(v / U.parse(cb["quantities"][k].get("unit") or "")[0])
                                       if k in cb["quantities"] else _fr(v) for k, v in best[1].items()},
                         "output": {o: _fr(best[2][o] / U.parse(cq[o].get("unit") or "")[0]) for o in outs}}
        pinned = copy.deepcopy(flat)
        pq = pinned["quantities"]
        drop_laws = set()
        for ref, (v_si, unit) in real.items():
            c, o = ref.split(".")
            nm = f"{c}_{o}"
            pq[nm] = {"role": "given", "value": _fr(v_si / U.parse(unit or "")[0]), "unit": unit,
                      "why": f"component {c}'s output {o}, lifted (exact)"}
            if f"{nm}_e" in pq:
                del pq[f"{nm}_e"]
                drop_laws.add(nm)
        pinned["laws"] = [l for l in pinned.get("laws") or []
                          if not any(l["zfl"].startswith(f"{nm} == {nm}_e") for nm in drop_laws)]
        for n, q in list(pq.items()):
            if q.get("role") == "given" and n in W and ("range" in q or q.get("tolerance") not in (None, "0", 0)):
                pq[n] = {k: v for k, v in q.items() if k not in ("range", "tolerance", "value")}
                pq[n]["value"] = _fr(W[n])
        got = S._run(pinned, conflicts=False)
        if got.get("verdict") == "REFUTED":
            return got, states
        return None
    except Exception:                                  # noqa: BLE001 — a search aid: no lift, the OPEN stands
        return None


def _run_one(raw, base, pick=None):
    flat, report, blocked = expand(raw, base, pick)
    if blocked:
        return {"verdict": "OPEN", "why": f"components: {blocked}", "components": report}
    from . import stand as S
    out = S._run(flat, conflicts=raw.get("conflicts", True) is not False)
    every = _fails_everywhere(flat) if out.get("verdict") == "REFUTED" else None
    lifted = _lift(raw, base, flat, out, pick) if out.get("verdict") == "REFUTED" and not every else None
    if every:
        r, t, _got = every
        out = {"verdict": "REFUTED",
               "why": (f"components: the requirement {r['quantity']} {r['op']} {r['value']} fails at EVERY point of the "
                       f"components' guaranteed ranges — the stand proved {t['quantity']} {t['op']} {t['value']} over "
                       f"all of them (EARNED); the ranges enclose what the components produce, so the system fails it"),
               "fails_everywhere": {"requirement": {k: r.get(k) for k in ("quantity", "op", "value")},
                                    "proved_instead": {k: t.get(k) for k in ("quantity", "op", "value")}},
               "refuted_inside_the_enclosures": {k: out.get(k) for k in ("fails", "its_violating_point", "by_at_witness")
                                                 if out.get(k) is not None}}
    elif lifted:
        got, states = lifted
        out = {"verdict": "REFUTED",
               "why": ("components: the failing point was LIFTED to a real state of the system — each component at "
                       "its real input, its own parameters inside its own box, its outputs solved exactly — and the "
                       "system fails there: " + str(got.get("why") or got.get("fails") or "")[:200]),
               "requirement": got.get("requirement"), "overshoot": got.get("overshoot"),
               "its_violating_point": got.get("its_violating_point"), "value_there": got.get("value_there"),
               "lifted_states": states}
    elif out.get("verdict") == "REFUTED":
        # a component's output is a GIVEN range here only because it ENCLOSES what the component does: a failing point
        # of that range may be one no component can produce — so the system's refutation is not one (EARNED is sound)
        out = {"verdict": "OPEN",
               "why": ("components: the system fails at a point of the components' guaranteed ranges, but those "
                       "ranges enclose (they may be wider than what the components can produce): not a refutation. "
                       "Finer bands, or the chain as one flat brick, decide it. The flat run said: "
                       + str(out.get("why") or out.get("fails") or "")[:300]),
               "refuted_inside_the_enclosures": {k: out.get(k) for k in ("fails", "its_violating_point", "by_at_witness")
                                                 if out.get(k) is not None}}
    out["components"] = report
    out["components_note"] = ("each component judged once per input band (its ratings EARNED there, its outputs' "
                              "ranges proved); between components only ranges travel — a correlation through a "
                              "shared source is not kept (sound, maybe wider than one flat brick)")
    return out
