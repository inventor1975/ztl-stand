# -*- coding: utf-8 -*-
"""ABSOLUTE TEMPERATURE SCALES: degC and degF (2026-11-12; the PLE cooling-tower task writes wet bulbs in deg F).

Until now the stand knew "C" only as a temperature DIFFERENCE dimension with no offset (units.py, 2026-10-09), and
degF was left out on purpose ("an offset scale, not a factor — a wrong guess there is costly", real round 3). This
module adds the two offset scales WITHOUT touching the core: a brick that writes a quantity in degC or degF is
TRANSLATED before the stand reads it, exactly, into kelvin, and the output gets the converted values back beside the
stand's own (which stay in K and say so).

    K = C + 273.15           K = (F + 459.67) * 5/9          (exact rationals: 27315/100, 45967/100)

The rules, each a place where a silent wrong answer was possible:
  1. degC / degF only as the WHOLE unit of a quantity or a catalog field. Inside a compound unit ("degF/h") the
     offset has no meaning — refused; a rate or a difference is written with the DIFFERENCE units dC (= 1 K) and dF
     (= 5/9 K), which units.py knows as plain factors. (Also degR, the Rankine, 5/9 K, no offset.)
  2. No relative TOLERANCE on an absolute temperature: +-1 % of 78 F is not +-1 % of 298.7 K. Refused; write a range.
  3. No NUMBER added to or subtracted from an absolute temperature in a law, a define or a requirement bound
     ("CWS == Twb + 7"). Numbers in laws are SI (BRICKS.md §4), so the 7 would be read as 7 K, while whoever wrote
     degF meant 7 F. Refused; write the difference as a given quantity in dF.
  4. The legacy "C" (a difference without offset) and the absolute scales in ONE brick: refused — 25 "C" next to
     25 degC would mean two different temperatures with no way to tell.
Values, ranges, `search` intervals, catalog fields and requirement bounds written as numbers are converted; a bound
that names quantities is already in SI (K) by the stand's own convention.
"""
from fractions import Fraction as F
import ast
import copy
import json

SCALES = {"degC": (F(1), F(27315, 100)), "degF": (F(5, 9), F(45967, 100))}     # K = (x + offset) * factor
LEGACY = "C"


class TemperatureError(ValueError):
    pass


def to_k(x, unit):
    f, off = SCALES[unit]
    return (F(x) + off) * f


def from_k(k, unit):
    f, off = SCALES[unit]
    return F(k) / f - off


def _s(x):
    x = F(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def _units_in(b):
    out = []
    qs = b.get("quantities")
    for n, q in (qs.items() if isinstance(qs, dict) else []):
        if isinstance(q, dict):
            out.append((f"quantities.{n}", q.get("unit", "")))
    cats = b.get("catalog")
    for cn, cat in (cats.items() if isinstance(cats, dict) else []):
        fields = cat.get("fields") if isinstance(cat, dict) else None
        for fn, fs in (fields.items() if isinstance(fields, dict) else []):
            if isinstance(fs, dict):
                out.append((f"catalog.{cn}.fields.{fn}", fs.get("unit", "")))
    obj = b.get("objective")
    if isinstance(obj, dict) and obj.get("unit"):
        out.append(("objective", obj["unit"]))
    return out


def uses_scales(b):
    """True when some unit string names degC / degF. Never raises: a malformed brick (a unit written as a number,
    quantities not an object — the stand's fuzz tests) is not ours to judge; the stand reports it (MEASURED
    2026-11-12: the first version raised TypeError on "unit": 5 and ended test_stand without its summary)."""
    try:
        if not isinstance(b, dict):
            return False
        return any(isinstance(u, str) and any(s in u for s in SCALES) for _, u in _units_in(b))
    except (AttributeError, TypeError):
        return False


def _conv_value_spec(spec, unit, where):
    """a quantity's / a field's value in a scale -> the same in K."""
    if isinstance(spec, dict):
        if "tolerance" in spec and F(str(spec["tolerance"])) != 0:
            raise TemperatureError(f"{where}: a relative tolerance on an absolute temperature ({unit}) is not "
                                   f"defined — write a range")
        if "range" in spec:
            return dict(spec, range=[_s(to_k(F(str(x)), unit)) for x in spec["range"]])
        if "value" in spec:
            out = {k: v for k, v in spec.items() if k != "tolerance"}
            out["value"] = _s(to_k(F(str(spec["value"])), unit))
            return out
        return spec
    return _s(to_k(F(str(spec)), unit))


def _additive_literal(node, hot):
    """True if a number is added to / subtracted from an expression that reads an absolute temperature."""
    for x in ast.walk(node):
        if isinstance(x, ast.BinOp) and isinstance(x.op, (ast.Add, ast.Sub)):
            for a, b in ((x.left, x.right), (x.right, x.left)):
                if _is_number(a) and _reads(b, hot):
                    return True
    return False


def _is_number(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
        return True
    if isinstance(n, ast.UnaryOp):
        return _is_number(n.operand)
    if isinstance(n, ast.BinOp):
        return _is_number(n.left) and _is_number(n.right)
    return False


def _reads(node, hot):
    for x in ast.walk(node):
        if isinstance(x, ast.Name) and x.id in hot:
            return True
        if isinstance(x, ast.Attribute):
            full = []
            y = x
            while isinstance(y, ast.Attribute):
                full.append(y.attr)
                y = y.value
            if isinstance(y, ast.Name):
                full.append(y.id)
                if ".".join(reversed(full)) in hot:
                    return True
    return False


def _parse(expr):
    try:
        return ast.parse(expr, mode="eval").body
    except SyntaxError:
        return None


def translate(raw):
    """-> (the brick in K, info) — or (raw, None) when it writes no absolute scale. Raises TemperatureError."""
    if not uses_scales(raw):
        return raw, None
    b = copy.deepcopy(raw)
    if b.get("components") or b.get("kind") == "stocks" or "network" in b:
        raise TemperatureError("degC / degF: version 1 translates plain bricks (quantities, laws, requirements, "
                               "catalog, modes, find); not components, stocks or networks — write those in K")
    units = _units_in(b)
    for where, u in units:
        u = u or ""
        if u in SCALES:
            continue
        for s in SCALES:
            if s in u:
                raise TemperatureError(f"{where}: '{u}' — an absolute scale ({s}) inside a compound unit has no "
                                       f"meaning; write differences and rates with dC / dF")
    if any(u == LEGACY for _, u in units):
        raise TemperatureError("the legacy unit \"C\" (a difference, no offset) and an absolute scale (degC / degF) "
                               "in one brick: write differences as dC, absolute temperatures as degC")
    info = {"quantities": {}, "fields": {}}
    hot = set()
    for n, q in (b.get("quantities") or {}).items():
        u = q.get("unit", "")
        if u not in SCALES:
            continue
        hot.add(n)
        info["quantities"][n] = u
        where = f"quantities.{n}"
        if "tolerance" in q and F(str(q["tolerance"])) != 0:
            raise TemperatureError(f"{where}: a relative tolerance on an absolute temperature ({u}) is not defined "
                                   f"— write a range")
        if "range" in q:
            q["range"] = [_s(to_k(F(str(x)), u)) for x in q["range"]]
        elif "value" in q:
            q["value"] = _conv_value_spec(q["value"], u, where) if isinstance(q["value"], dict) else \
                _s(to_k(F(str(q["value"])), u))
            q.pop("tolerance", None)
        if "search" in q:
            q["search"] = [_s(to_k(F(str(x)), u)) for x in q["search"]]
        q["unit"] = "K"
    for cn, cat in (b.get("catalog") or {}).items():
        fields = cat.get("fields") or {}
        hot_f = {fn: fs["unit"] for fn, fs in fields.items() if isinstance(fs, dict) and fs.get("unit") in SCALES}
        if not hot_f:
            continue
        for fn, u in hot_f.items():
            info["fields"][f"{cn}.{fn}"] = u
            fields[fn]["unit"] = "K"
            for slot, sp in (b.get("slots") or {}).items():
                if cn in (sp.get("from") or []):
                    hot.add(f"{slot}.{fn}")
        for i, row in enumerate(cat.get("items") or []):
            for fn, u in hot_f.items():
                if fn in row:
                    row[fn] = _conv_value_spec(row[fn], u, f"catalog.{cn}.items[{i}].{fn}")
    for i, law in enumerate(b.get("laws") or []):
        t = _parse(law.get("zfl", "")) if isinstance(law, dict) else None
        if t is not None and _additive_literal(t, hot):
            raise TemperatureError(f"laws[{i}] {law['zfl']!r}: a number added to an absolute temperature — numbers in "
                                   f"laws are SI (K); write the difference as a given quantity in dF / dC")
    for name, expr in (b.get("define") or {}).items():
        t = _parse(expr) if isinstance(expr, str) else None
        if t is not None and _additive_literal(t, hot):
            raise TemperatureError(f"define.{name}: a number added to an absolute temperature")
    for i, r in enumerate(b.get("requirements") or []):
        qn = r.get("quantity")
        if qn not in info["quantities"]:
            continue
        u = info["quantities"][qn]

        def conv(v, where):
            if isinstance(v, str):
                t = _parse(v)
                if t is not None and _is_number(t):
                    return _s(to_k(F(v), u))
                if t is not None and _additive_literal(t, hot):
                    raise TemperatureError(f"{where} {v!r}: a number added to an absolute temperature")
                return v                                   # names: SI (K) already
            if isinstance(v, (int, float)):
                return _s(to_k(F(str(v)), u))
            return v
        if isinstance(r.get("value"), list):
            r["value"] = [conv(v, f"requirements[{i}].value") for v in r["value"]]
        else:
            r["value"] = conv(r.get("value"), f"requirements[{i}].value")
    return b, info


def _num(v):
    """the stand prints exact values as '54167/180 (~300.928)': the exact part"""
    return F(str(v).split(" (", 1)[0].strip())


def annotate(out, info):
    """Beside the stand's own values (in K, labelled K), the same values in the scale each quantity was written in:
    out["in_written_scales"]. Nothing the stand printed is changed."""
    if not info or not isinstance(out, dict):
        return out
    scales = info["quantities"]

    def back(d):
        res = {}
        for n, v in (d or {}).items():
            u = scales.get(n)
            if u is None:
                continue
            try:
                if isinstance(v, list):
                    res[n] = [_s(from_k(_num(x), u)) for x in v]
                else:
                    res[n] = _s(from_k(_num(v), u))
            except (ValueError, ZeroDivisionError, TypeError):
                pass
        return res
    conv = {}
    for key in ("guaranteed", "its_violating_point", "value_there"):
        if isinstance(out.get(key), dict):
            c = back(out[key])
            if c:
                conv[key] = c
    req = out.get("requirement") or {}
    if req.get("quantity") in scales and out.get("overshoot") is not None:
        f, _ = SCALES[scales[req["quantity"]]]
        try:
            conv["overshoot"] = _s(_num(out["overshoot"]) / f)      # a DIFFERENCE: the factor only
        except (ValueError, ZeroDivisionError):
            pass
    out["in_written_scales"] = {"scales": scales, **conv,
                                "note": "the stand worked in K (every value above is in K, labelled so); these are "
                                        "the same values in the scale each quantity was written in, converted exactly "
                                        "(K = C + 273.15; K = (F + 459.67)*5/9); an overshoot is a difference"}
    return out


if __name__ == "__main__":
    import sys
    print(json.dumps(translate(json.load(open(sys.argv[1])))[0], indent=1))
