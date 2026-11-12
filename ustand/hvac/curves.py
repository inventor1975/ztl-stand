# -*- coding: utf-8 -*-
"""Layer 2: PERFORMANCE CURVES, ported from EnergyPlus 26.2.0 src/EnergyPlus/CurveManager.cc, Curve::value
(DESIGN-HVAC.md). Plus an IDF reader, so a curve is taken from the IDF text that states it (by code).

A brick declares its curves by name and calls them in any law, define, bound or objective:
    "curves": {"CAPFT": {"type": "Curve:Biquadratic", "coeffs": ["0.257896", "0.0389016", ...],
                         "x_min": "5", "x_max": "10", "y_min": "24", "y_max": "35", "out_min": ..., "out_max": ...,
                         "inputs": ["degC", "degC"], "output": ""}}
    "laws": [{"zfl": "Cap == Cap_ref*curve(CAPFT, Tchw, Tcond)", ...}]
`curve(NAME, args)` is expanded (expand_curves, before the brick is read) into EnergyPlus's own formula for that type:
every input CLAMPED to its limits first (V = max(min(V, max), min), as Curve::value does), the polynomial with the
coefficients inlined as exact decimals, the output clamped to its limits where they are given. `inputs` says what
each argument is in EnergyPlus's units: "degC" (a temperature — the argument, an absolute temperature in K in the
stand, enters as T/ep_K - 273.15, which is what EnergyPlus feeds a curve), or "" (a pure number: a ratio, a fraction).
The limits are in the same units as the inputs (as an IDF writes them).
Types: Linear, Quadratic, Cubic, Quartic, Exponent, Biquadratic, QuadraticLinear, CubicLinear, Bicubic,
Triquadratic, QuadLinear, QuintLinear, ChillerPartLoadWithLift, FanPressureRise, Sigmoid, RectangularHyperbola1/2,
ExponentialDecay, DoubleExponentialDecay. Not ported: ExponentialSkewNormal (erf, which the stand's laws do not have),
Table:Lookup (Btwxt interpolation) — refused aloud.

Layer 3 adds two types that are not Curve:* objects but are evaluated the same way — the user-defined coefficient
sets of a variable-speed cooling tower, CoolingTowerPerformance:CoolTools (35 coefficients) and :YorkCalc (27):
curve(NAME, FRW, FRA, Twb, Tr) = the approach (K), inputs water flow ratio, air flow ratio, inlet wet bulb ("degC"),
range ("dC": a temperature DIFFERENCE, K = deltaC), output "dC". The limits a spec states are applied as EnergyPlus's
checkModelBounds applies them (ustand/hvac/towers.py): z_min / z_max clamp the wet bulb, x_min / x_max the water flow
ratio (curve_from_idf writes those for CoolTools only — for YorkCalc EnergyPlus does not cap it); the range and
approach limits of the object are kept in the spec for the record (range_min, ...), EnergyPlus only warns on them.
"""
from __future__ import annotations

import re

# type -> (number of inputs, number of coefficients, formula over V1..Vn and c0..ck)
TYPES = {
    "Curve:Linear": (1, 2, "c0 + V1*c1"),
    "Curve:Quadratic": (1, 3, "c0 + V1*(c1 + V1*c2)"),
    "Curve:Cubic": (1, 4, "c0 + V1*(c1 + V1*(c2 + V1*c3))"),
    "Curve:Quartic": (1, 5, "c0 + V1*(c1 + V1*(c2 + V1*(c3 + V1*c4)))"),
    "Curve:Exponent": (1, 3, "c0 + c1*pow(V1, c2)"),
    "Curve:Sigmoid": (1, 5, "c0 + c1/pow(1 + exp((c2 - V1)/c3), c4)"),
    "Curve:RectangularHyperbola1": (1, 3, "(c0*V1)/(c1 + V1) + c2"),
    "Curve:RectangularHyperbola2": (1, 3, "(c0*V1)/(c1 + V1) + c2*V1"),
    "Curve:ExponentialDecay": (1, 3, "c0 + c1*exp(c2*V1)"),
    "Curve:DoubleExponentialDecay": (1, 5, "c0 + c1*exp(c2*V1) + c3*exp(c4*V1)"),
    "Curve:Biquadratic": (2, 6, "c0 + V1*(c1 + V1*c2) + V2*(c3 + V2*c4) + V1*V2*c5"),
    "Curve:QuadraticLinear": (2, 6, "(c0 + V1*(c1 + V1*c2)) + (c3 + V1*(c4 + V1*c5))*V2"),
    "Curve:CubicLinear": (2, 6, "(c0 + V1*(c1 + V1*(c2 + V1*c3))) + (c4 + V1*c5)*V2"),
    "Curve:Bicubic": (2, 10, "c0 + V1*c1 + V1*V1*c2 + V2*c3 + V2*V2*c4 + V1*V2*c5 + V1*V1*V1*c6 + V2*V2*V2*c7 + "
                            "V1*V1*V2*c8 + V1*V2*V2*c9"),
    "Curve:FanPressureRise": (2, 4, "V1*(c0*V1 + c1 + c2*sqrt(V2)) + c3*V2"),
    "Curve:ChillerPartLoadWithLift": (3, 12, "c0 + c1*V1 + c2*V1*V1 + c3*V2 + c4*V2*V2 + c5*V1*V2 + c6*V1*V1*V1 + "
                                             "c7*V2*V2*V2 + c8*V1*V1*V2 + c9*V1*V2*V2 + c10*V1*V1*V2*V2 + c11*V3*V2*V2*V2"),
    "Curve:Triquadratic": (3, 27, "c0 + c1*V1*V1 + c2*V1 + c3*V2*V2 + c4*V2 + c5*V3*V3 + c6*V3 + c7*V1*V1*V2*V2 + "
                                  "c8*V1*V2 + c9*V1*V2*V2 + c10*V1*V1*V2 + c11*V1*V1*V3*V3 + c12*V1*V3 + c13*V1*V3*V3 + "
                                  "c14*V1*V1*V3 + c15*V2*V2*V3*V3 + c16*V2*V3 + c17*V2*V3*V3 + c18*V2*V2*V3 + "
                                  "c19*V1*V1*V2*V2*V3*V3 + c20*V1*V1*V2*V2*V3 + c21*V1*V1*V2*V3*V3 + c22*V1*V2*V2*V3*V3 + "
                                  "c23*V1*V1*V2*V3 + c24*V1*V2*V2*V3 + c25*V1*V2*V3*V3 + c26*V1*V2*V3"),
    "Curve:QuadLinear": (4, 5, "c0 + V1*c1 + V2*c2 + V3*c3 + V4*c4"),
    "Curve:QuintLinear": (5, 6, "c0 + V1*c1 + V2*c2 + V3*c3 + V4*c4 + V5*c5"),
}
from .towers import COOLTOOLS_TERMS as _CT_T, YORKCALC_TERMS as _YC_T, polynomial as _poly   # noqa: E402

_TOWER_SYM = {"A": "V2*V2*V2", "W": "V1", "T": "V3", "R": "V4", "F": "V1/V2"}
TYPES["CoolingTowerPerformance:CoolTools"] = (4, 35, _poly(_CT_T, [f"c{i}" for i in range(35)], _TOWER_SYM))
TYPES["CoolingTowerPerformance:YorkCalc"] = (4, 27, _poly(_YC_T, [f"c{i}" for i in range(27)], _TOWER_SYM))
TOWER_TYPES = {"CoolingTowerPerformance:CoolTools": 8, "CoolingTowerPerformance:YorkCalc": 9}   # limit fields first
REFUSED = {"Curve:ExponentialSkewNormal": "uses erf, which the stand's laws do not have",
           "Table:Lookup": "Btwxt table interpolation is not ported (write the table as a table() or a fitted curve)"}
LIM = ("x", "y", "z", "w", "v")          # Curve:* limit fields: Minimum Value of x / y / z / w / v
CALL_RE = re.compile(r"(?<![\w.])curve\s*\(")


class CurveError(ValueError):
    pass


def _num(v):
    s = str(v).strip()
    float(s)                                 # refuse what is not a number
    return f"({s})"


def template(spec):
    """the curve's formula, its inputs V1..Vn left as parameters _V1.._Vn (already in EnergyPlus's units)"""
    t = spec.get("type", "")
    if t in REFUSED:
        raise CurveError(f"{t}: not ported — {REFUSED[t]}")
    if t not in TYPES:
        raise CurveError(f"curve type {t!r} unknown (known: {sorted(TYPES)})")
    n, k, f = TYPES[t]
    co = list(spec.get("coeffs") or [])
    if len(co) != k:
        raise CurveError(f"{t} takes {k} coefficients, not {len(co)}")
    body = f
    for i in reversed(range(k)):              # c10 before c1
        body = re.sub(rf"\bc{i}\b", _num(co[i]), body)
    for j in range(n):
        lo, hi = spec.get(f"{LIM[j]}_min"), spec.get(f"{LIM[j]}_max")
        v = f"_V{j + 1}"
        if hi is not None:
            v = f"min({v}, {_num(hi)})"
        if lo is not None:
            v = f"max({v}, {_num(lo)})"
        body = re.sub(rf"\bV{j + 1}\b", f"({v})", body)
    body = f"({body})"
    if spec.get("out_max") is not None:
        body = f"min({body}, {_num(spec['out_max'])})"
    if spec.get("out_min") is not None:
        body = f"max({body}, {_num(spec['out_min'])})"
    return n, body


def call_text(spec, args):
    """curve(NAME, a1..an) -> the expression: each argument converted to EnergyPlus's unit, then the template"""
    n, body = template(spec)
    if len(args) != n:
        raise CurveError(f"{spec.get('type')} takes {n} inputs, not {len(args)}")
    units = list(spec.get("inputs") or [""] * n)
    for j, a in enumerate(args):
        u = units[j] if j < len(units) else ""
        if u in ("degC", "C", "Temperature"):
            a = f"(({a})/ep_K - 273.15)"
        elif u in ("dC", "deltaC", "dK"):          # a temperature DIFFERENCE: K = deltaC, no offset
            a = f"(({a})/ep_K)"
        elif u not in ("", "1", "Dimensionless", "dimensionless"):
            raise CurveError(f"curve input unit {u!r}: degC (a temperature), dC (a difference) or '' (a pure number)")
        body = re.sub(rf"(?<![\w]){re.escape(f'_V{j + 1}')}(?![\w])", lambda _m, _a=a: f"({_a})", body)
    out = spec.get("output") or ""
    if out in ("dC", "deltaC", "dK"):
        body = f"(({body})*ep_K)"
    elif out not in ("", "1", "Dimensionless", "dimensionless"):
        raise CurveError(f"curve output unit {out!r}: dC (a temperature difference) or '' (a pure number)")
    return body


def _split_args(inner):
    args, depth, cur = [], 0, ""
    for ch in inner:
        if ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
            continue
        depth += {"(": 1, ")": -1}.get(ch, 0)
        cur += ch
    args.append(cur.strip())
    return args


def expand_text(text, curves):
    for _ in range(64):
        m = CALL_RE.search(text)
        if not m:
            return text
        i, depth = m.end(), 1
        while i < len(text) and depth:
            depth += {"(": 1, ")": -1}.get(text[i], 0)
            i += 1
        if depth:
            raise CurveError("curve(: a parenthesis is not closed")
        args = _split_args(text[m.end():i - 1])
        name = args[0].strip().strip("'\"")
        if name not in curves:
            raise CurveError(f"curve {name!r} is not declared in \"curves\" (declared: {sorted(curves)})")
        text = text[:m.start()] + f"({call_text(curves[name], args[1:])})" + text[i:]
    raise CurveError("curve expansion did not end")


def expand_curves(b):
    """In place: every curve(NAME, ...) in laws, defines, requirement bounds and the objective expanded; the "curves"
    block kept for the record. Raises CurveError (a BRICK ERROR) on an unknown name, type, or a wrong count."""
    curves = b.get("curves") or {}
    if not isinstance(curves, dict):
        raise CurveError("curves: an object of named curves")
    if not curves and not any("curve(" in str(x) for x in (b.get("laws"), b.get("define"))):
        return b
    for law in b.get("laws") or []:
        if isinstance(law, dict) and isinstance(law.get("zfl"), str):
            law["zfl"] = expand_text(law["zfl"], curves)
    for k, v in list((b.get("define") or {}).items()):
        if isinstance(v, str):
            b["define"][k] = expand_text(v, curves)
    for r in b.get("requirements") or []:
        if isinstance(r, dict):
            if isinstance(r.get("value"), str):
                r["value"] = expand_text(r["value"], curves)
            elif isinstance(r.get("value"), list):
                r["value"] = [expand_text(x, curves) if isinstance(x, str) else x for x in r["value"]]
    obj = b.get("objective")
    if isinstance(obj, dict) and isinstance(obj.get("minimize"), str):
        obj["minimize"] = expand_text(obj["minimize"], curves)
    return b


def evaluate(spec, *args):
    """the curve in double precision from its template (inputs in EnergyPlus's units), for the tests"""
    from . import _ev
    import ast
    _, body = template(spec)
    env = {f"_V{j + 1}": float(a) for j, a in enumerate(args)}
    return _ev(ast.parse(body, mode="eval").body, env)


# ------------------------------------------------------------------------------------------------------------- IDF
def idf_objects(text):
    """an IDF text -> [(class, [fields])]: '!' starts a comment, ',' separates fields, ';' ends an object"""
    text = re.sub(r"!.*", "", text)
    out = []
    for chunk in text.split(";"):
        fields = [f.strip() for f in chunk.split(",")]
        if fields and fields[0]:
            out.append((fields[0], fields[1:]))
    return out


def curve_from_idf(cls, fields):
    """an IDF Curve:* object -> the brick's curve spec (the IDF's field order: name, coefficients, then the min / max of
    each input, then the optional output min / max and the unit types, as EnergyPlus's IDD lays them out)"""
    t = next((k for k in list(TYPES) + list(REFUSED) if k.lower() == cls.lower()), None)
    if t is None:
        raise CurveError(f"{cls}: not a curve type")
    n, k, _ = TYPES.get(t, (1, 0, ""))
    name, rest = fields[0], fields[1:]
    if t in TOWER_TYPES:
        # CoolingTowerPerformance:*: min/max inlet wet bulb, range, approach, water flow ratio (YorkCalc: + the
        # maximum liquid-to-gas ratio), then the coefficients (GetTowerInput: NumArray2(1..8/9), then Coeff)
        m = TOWER_TYPES[t]
        lim, co = rest[:m], rest[m:m + k]
        if len(lim) < m or len(co) != k or any(not x for x in lim + co):
            raise CurveError(f"{cls} {name!r}: {m} limits and {k} coefficients expected")
        spec = {"type": t, "coeffs": co, "z_min": lim[0], "z_max": lim[1], "range_min": lim[2], "range_max": lim[3],
                "approach_min": lim[4], "approach_max": lim[5], "frw_min": lim[6], "frw_max": lim[7],
                "inputs": ["", "", "degC", "dC"], "output": "dC"}
        if t.endswith("CoolTools"):
            spec["x_min"], spec["x_max"] = lim[6], lim[7]      # capped by checkModelBounds (CoolTools only)
        else:
            spec["lg_max"] = lim[8]
        return name, spec
    spec = {"type": t, "coeffs": rest[:k]}
    lims = rest[k:k + 2 * n]
    for j in range(n):
        lo = lims[2 * j] if 2 * j < len(lims) else ""
        hi = lims[2 * j + 1] if 2 * j + 1 < len(lims) else ""
        if lo:
            spec[f"{LIM[j]}_min"] = lo
        if hi:
            spec[f"{LIM[j]}_max"] = hi
    after = rest[k + 2 * n:]
    if len(after) >= 1 and after[0]:
        spec["out_min"] = after[0]
    if len(after) >= 2 and after[1]:
        spec["out_max"] = after[1]
    unit_types = after[2:2 + n]
    spec["inputs"] = ["degC" if u.lower() == "temperature" else "" for u in unit_types] + [""] * (n - len(unit_types))
    return name, spec


def curves_from_idf(text):
    out = {}
    for cls, fields in idf_objects(text):
        if cls.lower().startswith(("curve:", "coolingtowerperformance:")):
            try:
                name, spec = curve_from_idf(cls, fields)
                out[name] = spec
            except CurveError:
                continue
    return out
