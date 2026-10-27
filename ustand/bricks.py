"""Bricks: the stand's whole input, as JSON (format ztl-stand/1; bricks written as universal-stand/1 read the same).

    {
      "stand": "universal-stand/1",
      "quantities": {
        "Vin":  {"role": "given", "value": "5", "unit": "V", "ground": "psu"},
        "I":    {"role": "derived", "unit": "A"},
        "P1":   {"role": "derived", "unit": "W"}
      },
      "slots": {"R1": {"from": ["res_1pct_quarter_watt"]}},
      "laws": [{"zfl": "Vin - Vout == I*R1.R", "source": "Ohm's law"},
               {"zfl": "P1 == I*I*R1.R", "source": "Joule heating"}],
      "requirements": [{"quantity": "P1", "op": "<=", "value": "R1.P"}],
      "catalog": {
        "res_1pct_quarter_watt": {
          "series": "E24", "decades": [1000, 10000],
          "fields": {"R": {"series": true, "tolerance": "0.01", "unit": "ohm"},
                     "P": {"value": "0.25", "unit": "W"}},
          "ground": "datasheet"}
      }
    }

A SLOT is a place in the design (R1). An ITEM is a catalog row with several
FIELDS, each with its own nominal and tolerance (resistance 1k +-1%, power
rating 0.25 W, ...). Putting an item in a slot creates one quantity per field,
named slot.field (R1.R, R1.P). A catalog row is either generated from an E-series
(the field marked "series": true takes the series value) or listed in "items":
[{"R": {"value": "1000", "tolerance": "0.01"}, "P": {"value": "0.25"}}, ...].

Roles of the other quantities: "given" — fixed by the world, optionally with a
tolerance (the stand must hold for every value in it); "derived" — follows from
the laws. A requirement's value is a number, an interval (within), or the name
of a quantity (e.g. R1.P): then its least favourable value is used.
Numbers are strings read as exact fractions.
"""
from __future__ import annotations

import json
import re
from fractions import Fraction as F

E_SERIES = {
    "E12": [10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82],
    "E24": [10, 11, 12, 13, 15, 16, 18, 20, 22, 24, 27, 30,
            33, 36, 39, 43, 47, 51, 56, 62, 68, 75, 82, 91],
    "E3": [10, 22, 47],
    "E6": [10, 15, 22, 33, 47, 68],
}
# THREE-DIGIT series (blind test 2, c04 and c12, 2026-10-10: E96 missing, both authors typed it from memory).
# IEC 60063: round(10^(i/n) * 100), with the one listed exception of E192 (9.19 -> 9.20); generated, and
# cross-checked against the printed E96 table (all 96 equal) in tests/test_stand.py.
for _n in (48, 96, 192):
    _vals = [round(10 ** (_i / _n) * 100) for _i in range(_n)]
    if _n == 192:
        _vals[_vals.index(919)] = 920
    E_SERIES[f"E{_n}"] = _vals
SERIES_BASE = {name: (100 if vals[0] == 100 else 10) for name, vals in E_SERIES.items()}  # 1.00 or 1.0
OPS = ("within", "<=", ">=", "<", ">")         # strict < > since 2026-10-10 (law domains, G8)
DOTTED = re.compile(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\b")


class BrickError(ValueError):
    pass


def num(s) -> F:
    t = str(s)
    try:
        return F(t)
    except ValueError:
        # a quotient of decimals, "76.8/1000000" (real round 2, s05): exact as well
        a, sep, b = t.partition("/")
        if not sep or "/" in b:
            raise
        return F(a.strip()) / F(b.strip())


def ident(name: str) -> str:
    """slot.field -> slot__field: the form the judge and the checker read."""
    return name.replace(".", "__")


_SCI = re.compile(r"(?<![\w.])(?:\d+\.?\d*|\.\d+)[eE][+-]?\d+(?![\w.])")


def _sci_exact(m):
    """8.6541e-5 -> (86541/1000000000); a number past a float's range (1e999) is left alone — it still reads as
    infinite and is refused, said ("an infinite constant")."""
    try:
        if abs(float(m.group(0))) in (0.0, float("inf")) and F(m.group(0)) != 0:
            return m.group(0)
    except OverflowError:
        return m.group(0)
    v = F(m.group(0))
    return f"({v.numerator}/{v.denominator})"


_DEC = re.compile(r"(?<![\w.])(?:\d+\.\d*|\.\d+)(?![\w.])")


def _dec_exact(m):
    """0.000000001 -> (1/1000000000) when Python would print it in scientific notation (below 1e-4 or from 1e16):
    the laws are read through ast, whose unparse writes 1e-09 — ZTL's reader split it at the exponent's minus
    (the multi-node motor, 2026-10-16: STAND ERROR "unknown quantity or malformed arithmetic: '1e'"). Exact."""
    try:
        if "e" not in repr(float(m.group(0))):
            return m.group(0)
    except (OverflowError, ValueError):
        return m.group(0)
    v = F(m.group(0))
    return f"({v.numerator}/{v.denominator})"


def compile_expr(text: str, defines=None) -> str:
    """slot.field -> slot__field, and every DEFINE expanded in place (in parentheses).

    A define names an expression of given and catalog quantities only (gap G3,
    2026-10-09: R1T = R1.R*(1 + R1.a*(T - 25)) written as a derived quantity turned a
    parameter into an unknown and made Ohm's law nonlinear; expanded, it stays a
    coefficient and the system stays linear)."""
    defines = defines or {}
    # a number in SCIENTIFIC notation (8.6541e-5) as an exact fraction in parentheses: ZTL's reader splits at the
    # exponent's minus (blind test 6, c10: "unknown quantity or malformed arithmetic: '8.6541e'")
    text = _DEC.sub(_dec_exact, _SCI.sub(_sci_exact, text))
    defines = {k: _DEC.sub(_dec_exact, _SCI.sub(_sci_exact, v)) if isinstance(v, str) else v
               for k, v in defines.items()}
    for _ in range(len(defines) + 1):           # defines may use earlier defines
        before = text
        for name, expr in defines.items():
            # not after a dot either: a define named like a catalog FIELD (Uc vs HX.Uc) was substituted INSIDE
            # the field, and the error blamed an unrelated law (blind test 2, c01 and c08, 2026-10-10: ~8 runs lost)
            text = re.sub(rf"(?<!\.)\b{re.escape(name)}\b(?!\.)", f"({expr})", text)
        if text == before:
            break
    text = DOTTED.sub(r"\1__\2", text)
    has_if = bool(re.search(r"(?<![\w.])if\s*\(", text))
    if has_if:                                    # `if` is a Python keyword: renamed BEFORE the tables are read
        text = re.sub(r"(?<![\w.])if\s*\(", "__if__(", text)       # (real problems r04: table() inside if())
    if re.search(r"(?<![\w.])table\s*\(", text):
        text = _tables(text)
    if has_if:
        text = _branches(text)
    # J11 (blind test 4, 2026-10-11, the curator's "да"): x^n is x**n (a power, never a bitwise xor); abs(x) is
    # if(x > 0, x, -x) — the one branch every reader knows (an author wrote it by a sign trick)
    if "^" in text:
        text = text.replace("^", "**")
    if "**" in text or re.search(r"(?<![\w.])abs\s*\(", text):     # a ** b -> pow(a, b): one spelling for every reader
        import ast as _ast

        class _Pow(_ast.NodeTransformer):
            def visit_BinOp(self, node):
                self.generic_visit(node)
                if isinstance(node.op, _ast.Pow):
                    return _ast.Call(func=_ast.Name(id="pow", ctx=_ast.Load()), args=[node.left, node.right], keywords=[])
                return node

            def visit_Call(self, node):
                self.generic_visit(node)
                if isinstance(node.func, _ast.Name) and node.func.id == "abs":
                    if len(node.args) != 1:
                        raise BrickError(f"abs(...) takes one value — in {text!r}")
                    x = node.args[0]
                    return _ast.Call(func=_ast.Name(id="ifpos", ctx=_ast.Load()),
                                     args=[x, x, _ast.UnaryOp(op=_ast.USub(), operand=x)], keywords=[])
                return node
        try:
            text = _ast.unparse(_Pow().visit(_ast.parse(text, mode="eval")))
        except SyntaxError:
            pass                                  # the shape check names the bad expression
    return text


def _branches(text):
    """if(A > B, a, b) -> ifpos(A - B, a, b), the one branch every reader knows (blind test 2, 2026-10-10:
    Euler or Johnson by slenderness, eps-NTU at Cr = 1). < <= > >= only; >= and <= swap the branches so the
    boundary goes where the author put it."""
    import ast as _ast
    try:
        tree = _ast.parse(re.sub(r"(?<![\w.])if\s*\(", "__if__(", text), mode="eval")
    except SyntaxError:
        raise BrickError(f"{text!r} is not a readable expression")

    class _If(_ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            if not (isinstance(node.func, _ast.Name) and node.func.id == "__if__"):
                return node
            if len(node.args) != 3 or not (isinstance(node.args[0], _ast.Compare) and len(node.args[0].ops) == 1):
                raise BrickError(f"if(...) takes a comparison and two values: if(A > B, a, b) — in {text!r}")
            c, a, b = node.args
            lhs, op, rhs = c.left, c.ops[0], c.comparators[0]
            sub = lambda x, y: _ast.BinOp(left=x, op=_ast.Sub(), right=y)
            if isinstance(op, _ast.Gt):
                x, yes, no = sub(lhs, rhs), a, b
            elif isinstance(op, _ast.Lt):
                x, yes, no = sub(rhs, lhs), a, b
            elif isinstance(op, _ast.GtE):          # A >= B  is  not (B - A > 0)
                x, yes, no = sub(rhs, lhs), b, a
            elif isinstance(op, _ast.LtE):          # A <= B  is  not (A - B > 0)
                x, yes, no = sub(lhs, rhs), b, a
            else:
                raise BrickError(f"if(...) compares with < <= > >= only — in {text!r}")
            return _ast.Call(func=_ast.Name(id="ifpos", ctx=_ast.Load()), args=[x, yes, no], keywords=[])
    return _ast.unparse(_If().visit(tree))


def _tables(text):
    """table(x, x0, y0, x1, y1, ...) — a piecewise-linear table (blind test 4, J5, 2026-10-11: four authors typed
    their tables as 5-9 deep nested if chains by hand). Linear between the knots, the end value held beyond them;
    compiled to a chain of ifpos, so ZTL and the checker read it as the branches they already know. The knots may
    be numbers or expressions (a catalog field as a value); numeric x-knots must increase."""
    import ast as _ast
    from fractions import Fraction as _F
    try:
        tree = _ast.parse(text, mode="eval")
    except SyntaxError:
        raise BrickError(f"{text!r} is not a readable expression")

    def num_or_none(node):
        try:
            return _F(_ast.unparse(node).replace(" ", ""))
        except (ValueError, ZeroDivisionError):
            return None

    class _T(_ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            if not (isinstance(node.func, _ast.Name) and node.func.id == "table"):
                return node
            args = node.args
            if len(args) < 5 or len(args) % 2 == 0:
                raise BrickError("table(x, x0, y0, x1, y1, ...) takes x and at least two (x, y) knots — in "
                                 f"{text!r}")
            x, knots = args[0], args[1:]
            xs, ys = knots[0::2], knots[1::2]
            nums = [num_or_none(k) for k in xs]
            if all(v is not None for v in nums) and any(b <= a for a, b in zip(nums, nums[1:])):
                raise BrickError(f"table(...): the x-knots must increase — in {text!r}")
            sub = lambda a, b: _ast.BinOp(left=a, op=_ast.Sub(), right=b)

            def seg(k):                         # y_k + (y_{k+1} - y_k) * (x - x_k) / (x_{k+1} - x_k)
                return _ast.BinOp(left=ys[k], op=_ast.Add(), right=_ast.BinOp(
                    left=_ast.BinOp(left=sub(ys[k + 1], ys[k]), op=_ast.Mult(), right=sub(x, xs[k])),
                    op=_ast.Div(), right=sub(xs[k + 1], xs[k])))
            ifpos = lambda c, a, b: _ast.Call(func=_ast.Name(id="ifpos", ctx=_ast.Load()), args=[c, a, b],
                                              keywords=[])
            n = len(xs) - 1
            above = ys[n]                       # x > x_n: the last value held
            for k in range(n - 1, -1, -1):      # x > x_k: on segment k up to x_{k+1}, above it the rest
                above = ifpos(sub(x, xs[k + 1]), above, seg(k))
            return ifpos(sub(x, xs[0]), above, ys[0])     # x <= x_0: the first value held
    return _ast.unparse(_T().visit(tree))


# FUNCTIONS (blind test G1, 2026-10-10): ZTL reads them with proved brackets (ZTL zfunc.py);
# the checker with mpmath's interval arithmetic — a different implementation.
FUNCS = {"exp": 1, "ln": 1, "log10": 1, "atan": 1, "tan": 1, "sin": 1, "cos": 1, "sqrt": 1, "pow": 2, "min": 2, "max": 2,
         "ifpos": 3}                 # ifpos: what if(A > B, a, b) compiles to (_branches)


def field(v):
    """A field or given value -> (nominal, relative tolerance) or ("range", lo, hi).

    "1000" | {"value": "1000", "tolerance": "0.01"} | {"range": ["-1/10000", "1/10000"]}.
    A RANGE is absolute (2026-10-09, gap G1: an ambient 20..45 C, a TCR of +-100 ppm
    around zero cannot be written as nominal +- percent)."""
    if isinstance(v, dict) and "range" in v:
        lo, hi = num(v["range"][0]), num(v["range"][1])
        if lo > hi:
            raise BrickError(f"range {v['range']}: low end above high end")
        return ("range", lo, hi)
    if isinstance(v, dict):
        return (num(v["value"]), num(v.get("tolerance", "0")))
    try:
        return (num(v), F(0))
    except (ValueError, ZeroDivisionError):
        return ("label", str(v))     # gap G4: a non-numeric field ("grade": "fine") is a label, not a quantity


def items(cat: dict):
    """[{field: (nominal, tolerance)}] — every row of one catalog."""
    fields = cat.get("fields") or {}
    if "integers" in cat:                       # gap J6: an integer choice without listing it
        spec = cat["integers"]
        lo, hi = int(num(spec["from"])), int(num(spec["to"]))
        if lo > hi:
            raise BrickError(f"integers: from {lo} above to {hi}")
        return [{spec["field"]: (F(k), F(0))} for k in range(lo, hi + 1)]
    if "continuous" in cat:                     # blind test 3: any amount in a range (ustand/lp.py)
        spec = cat["continuous"]
        return [{spec["field"]: ("range", num(spec["from"]), num(spec["to"]))}]
    if "items" in cat:
        out = []
        for row in cat["items"]:
            out.append({f: field(v) for f, v in row.items()})
        return out
    series = E_SERIES.get(cat.get("series"))
    if series is None:
        raise BrickError(f"unknown series {cat.get('series')!r}")
    sfield = [f for f, d in fields.items() if d.get("series")]
    if len(sfield) != 1:
        raise BrickError("a series catalog needs exactly one field with \"series\": true")
    out = []
    for d in cat["decades"]:
        for v in series:
            row = {}
            for f, spec in fields.items():
                if spec.get("series"):
                    row[f] = (F(v) * num(d) / SERIES_BASE[cat["series"]], num(spec.get("tolerance", "0")))
                else:
                    row[f] = field(spec)
            out.append(row)
    return out


def field_units(cat: dict) -> dict:
    """{field: unit string} declared for a catalog (series or listed items alike)."""
    out = {f: spec.get("unit") for f, spec in (cat.get("fields") or {}).items() if isinstance(spec, dict)}
    if "integers" in cat:
        out[cat["integers"]["field"]] = cat["integers"].get("unit", "")
    if "continuous" in cat:
        out[cat["continuous"]["field"]] = cat["continuous"].get("unit", "")
    return out


def _shape(b):
    """THE SHAPE OF A BRICK, checked before anything reads it (2026-10-10: the blind test and a
    fuzz of every example found ~25 places where a wrong TYPE — a string for an object, a missing
    key, an unreadable number — escaped as a Python traceback). Every message names the place."""
    def need(cond, where, what):
        if not cond:
            raise BrickError(f"{where}: {what}")

    def number(v, where):
        need(isinstance(v, (str, int)) and not isinstance(v, bool), where, f"a number written as a string, not {v!r}")
        try:
            x = num(v)
        except (ValueError, ZeroDivisionError, OverflowError):
            raise BrickError(f"{where}: {v!r} is not a number (write e.g. \"0.01\" or \"1/3\")")
        need(abs(x) < F(10) ** 60 and (x == 0 or abs(x) > F(1, 10 ** 60)), where,
             f"{v!r} is outside 1e-60..1e60 — not a physical quantity in these units (and past float range downstream)")
        return x

    def value_spec(v, where, allow_label=False):
        if isinstance(v, dict):
            if "range" in v:
                r = v["range"]
                need(isinstance(r, list) and len(r) == 2, where, "range must be [low, high]")
                lo, hi = number(r[0], where + ".range[0]"), number(r[1], where + ".range[1]")
                need(lo <= hi, where, f"range {r}: low end above high end")
            elif "value" in v:
                number(v["value"], where + ".value")
                if "tolerance" in v:
                    t = number(v["tolerance"], where + ".tolerance")
                    need(t >= 0, where, "tolerance must not be negative")
            else:
                need(False, where, "an object here needs \"value\" (with an optional \"tolerance\") or \"range\"")
        elif allow_label and isinstance(v, str):
            pass                                      # a label ("grade": "fine") or a plain number
        else:
            number(v, where)

    need(isinstance(b, dict), "brick", "must be a JSON object")
    qs = b.get("quantities")
    need(isinstance(qs, dict) and qs, "quantities", "must be a non-empty object of named quantities")
    for n, q in qs.items():
        need(isinstance(q, dict), f"quantities.{n}", "must be an object")
        need(isinstance(q.get("unit", ""), str), f"quantities.{n}.unit", "must be a string")
        need(isinstance(q.get("ground", ""), str), f"quantities.{n}.ground", "must be a string")
        if q.get("role") == "given":
            if "range" in q:
                value_spec({"range": q["range"]}, f"quantities.{n}")
            elif "value" in q:
                value_spec({k: q[k] for k in ("value", "tolerance") if k in q}, f"quantities.{n}")
        if "search" in q:
            need(q.get("role") == "derived", f"quantities.{n}.search", "only a derived quantity is searched for")
            sr = q["search"]
            need(isinstance(sr, list) and len(sr) == 2, f"quantities.{n}.search", "must be [low, high]")
            need(number(sr[0], f"quantities.{n}.search[0]") < number(sr[1], f"quantities.{n}.search[1]"),
                 f"quantities.{n}.search", "the low end must be below the high end")
    slots = b.get("slots") or {}
    need(isinstance(slots, dict), "slots", "must be an object")
    for sn, sp in slots.items():
        need(isinstance(sp, dict) and isinstance(sp.get("from"), list) and all(isinstance(c, str) for c in sp["from"]),
             f"slots.{sn}", "must be {\"from\": [catalog names]}")
    cat = b.get("catalog") or {}
    need(isinstance(cat, dict), "catalog", "must be an object")
    for cn, c in cat.items():
        w = f"catalog.{cn}"
        need(isinstance(c, dict), w, "must be an object")
        need(isinstance(c.get("ground", ""), str), w + ".ground", "must be a string")
        need(isinstance(c.get("series", ""), str), w + ".series", "must be a name such as \"E24\"")
        fields = c.get("fields", {})
        need(isinstance(fields, dict) and all(isinstance(fv, dict) for fv in fields.values()), w + ".fields",
             "must be an object of field objects")
        for f, fv in fields.items():
            need(isinstance(fv.get("unit", ""), str), f"{w}.fields.{f}.unit", "must be a string")
        if "integers" in c:
            spec = c["integers"]
            need(isinstance(spec, dict) and isinstance(spec.get("field"), str), w + ".integers", "needs \"field\", \"from\", \"to\"")
            need(isinstance(spec.get("unit", ""), str), w + ".integers.unit", "must be a string")
            number(spec.get("from"), w + ".integers.from"); number(spec.get("to"), w + ".integers.to")
        elif "continuous" in c:
            spec = c["continuous"]
            need(isinstance(spec, dict) and isinstance(spec.get("field"), str), w + ".continuous",
                 "needs \"field\", \"from\", \"to\"")
            need(isinstance(spec.get("unit", ""), str), w + ".continuous.unit", "must be a string")
            need(number(spec.get("from"), w + ".continuous.from") <= number(spec.get("to"), w + ".continuous.to"),
                 w + ".continuous", "from must not be above to")
        elif "items" in c:
            need(isinstance(c["items"], list) and c["items"], w + ".items", "must be a non-empty list")
            for i, row in enumerate(c["items"]):
                need(isinstance(row, dict) and row, f"{w}.items[{i}]", "must be an object of fields")
                for f, v in row.items():
                    value_spec(v, f"{w}.items[{i}].{f}", allow_label=True)
        else:
            need(isinstance(c.get("decades"), list) and c["decades"], w, "a series catalog needs \"decades\": [...]")
            for d in c["decades"]:
                number(d, w + ".decades")
            for f, spec in fields.items():
                if not spec.get("series"):
                    need("value" in spec or "range" in spec, f"{w}.fields.{f}", "needs a value or a range (or \"series\": true)")
                    value_spec({k: spec[k] for k in ("value", "tolerance", "range") if k in spec}, f"{w}.fields.{f}")
                elif "tolerance" in spec:
                    number(spec["tolerance"], f"{w}.fields.{f}.tolerance")
    laws = b.get("laws")
    need(isinstance(laws, list) and laws, "laws", "must be a non-empty list")
    seen_laws = {}
    for i, l in enumerate(laws):
        need(isinstance(l, dict) and isinstance(l.get("zfl"), str), f"laws[{i}]", "must be {\"zfl\": \"lhs == rhs\", \"source\": ...}")
        key = re.sub(r"\s+", "", l["zfl"])
        need(key not in seen_laws, f"laws[{i}]", f"repeats laws[{seen_laws.get(key)}] — a law written twice makes the system "
             "look over-determined; write it once")
        seen_laws[key] = i
    defines = b.get("define") or {}
    need(isinstance(defines, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in defines.items()),
         "define", "must be an object of name: expression strings")
    for key in ("requirements",):
        rs = b.get(key) or []
        need(isinstance(rs, list), key, "must be a list")
    _cf = b.get("conflicts")
    need(_cf in (None, True, False, "all") or (isinstance(_cf, int) and not isinstance(_cf, bool) and _cf >= 0),
         "conflicts", 'true, false (no minimal_conflicts), "all" (every subset) or a number of subset runs')
    modes = b.get("modes")
    if modes is not None:
        need(isinstance(modes, dict) and modes, "modes", "must be a non-empty object of named modes")
        for m, sp in modes.items():
            need(isinstance(sp, dict), f"modes.{m}", "must be an object")
            need(isinstance(sp.get("quantities", {}), dict), f"modes.{m}.quantities", "must be an object")
            for q, ov in (sp.get("quantities") or {}).items():
                need(isinstance(ov, dict), f"modes.{m}.quantities.{q}", "must be an object")
                if "range" in ov:
                    value_spec({"range": ov["range"]}, f"modes.{m}.quantities.{q}")
                elif "value" in ov:
                    value_spec({k: ov[k] for k in ("value", "tolerance") if k in ov}, f"modes.{m}.quantities.{q}")
            need(isinstance(sp.get("requirements", []), list), f"modes.{m}.requirements", "must be a list")
            need(isinstance(sp.get("define", {}), dict) and all(isinstance(k, str) and isinstance(v, str)
                                                                 for k, v in (sp.get("define") or {}).items()),
                 f"modes.{m}.define", "must be an object of name: expression strings")
            need(isinstance(sp.get("laws", []), list) and all(isinstance(l, dict) and isinstance(l.get("zfl"), str)
                                                               for l in (sp.get("laws") or [])),
                 f"modes.{m}.laws", "must be a list of {\"zfl\": ...}")
    all_reqs = list(b.get("requirements") or []) + [r for sp in (modes or {}).values() if isinstance(sp, dict)
                                                       for r in (sp.get("requirements") or [])]
    for i, r in enumerate(all_reqs):
        need(isinstance(r, dict) and isinstance(r.get("quantity"), str), f"requirement {i}", "must be {\"quantity\", \"op\", \"value\"}")
        if r.get("op") == "within":
            need(isinstance(r.get("value"), list) and len(r["value"]) == 2
                 and all(isinstance(v, (str, int)) and not isinstance(v, bool) for v in r["value"]),
                 f"requirement on {r['quantity']}", "\"within\" needs a value [low, high] of numbers or names")
        else:
            need(isinstance(r.get("value"), (str, int)) and not isinstance(r.get("value"), bool),
                 f"requirement on {r['quantity']}", "the bound must be a number, a given quantity or a slot.field")
    obj = b.get("objective")
    if obj is not None:
        need(isinstance(obj, dict) and isinstance(obj.get("minimize"), str), "objective", "must be {\"minimize\": \"expression\"}")
    # THE EXPRESSIONS: readable, and every name in them known (a quantity, a define, or a
    # slot.field of a declared slot) — else ZTL's reader or Python's parser raised (fuzz, 2026-10-10)
    import ast as _ast
    # "where" and "computed" (blind test 2, 2026-10-10): exact per-design words, ustand/exact.py
    from . import exact as _X
    comp = b.get("computed") or {}
    need(isinstance(comp, dict), "computed", "must be an object of name: expression (or {\"value\", \"unit\"})")
    for cn, cv in comp.items():
        need(isinstance(cn, str) and re.fullmatch(r"[A-Za-z_]\w*", cn or "") and "__" not in cn, f"computed.{cn}",
             "must be a plain name")
        need(cn not in qs and cn not in defines, f"computed.{cn}", "clashes with a quantity or a define")
        text = cv if isinstance(cv, str) else (cv.get("value") if isinstance(cv, dict) else None)
        need(isinstance(text, str), f"computed.{cn}", "must be an expression string or {\"value\": \"...\", \"unit\": \"...\"}")
        need(isinstance(cv, str) or isinstance(cv.get("unit", ""), str), f"computed.{cn}.unit", "must be a string")
    wh = b.get("where") or []
    need(isinstance(wh, list) and all(isinstance(w, str) for w in wh), "where", "must be a list of condition strings")
    for i, text in enumerate(list(wh) + [cv if isinstance(cv, str) else cv["value"] for cv in comp.values()]):
        label = f"where[{i}]" if i < len(wh) else "computed"
        try:
            node = _X.parse(compile_expr(text))
            _X.check_shape(node, label)
        except _X.ExactError as e:
            raise BrickError(str(e))
        for n in _X.names(node):
            if "__" in n:
                need(n.split("__")[0] in slots, label, f"{n.replace('__', '.')!r}: no such slot")
            else:
                need(n in qs or n in comp, label, f"{n!r} is not a quantity or a computed name")
    known = set(qs) | set(defines) | set(comp)
    def names_ok(text, where):
        try:
            tree = _ast.parse(compile_expr(text, defines), mode="eval")
        except SyntaxError:
            raise BrickError(f"{where}: {text!r} is not a readable expression")
        func_names = set()
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Call):
                need(isinstance(node.func, _ast.Name) and node.func.id in FUNCS and not node.keywords, where,
                     f"only these functions exist: {', '.join(sorted(FUNCS))}")
                need(len(node.args) == FUNCS[node.func.id], where,
                     f"{node.func.id} takes {FUNCS[node.func.id]} argument(s)")
                func_names.add(id(node.func))
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Name) and id(node) in func_names:
                continue
            if isinstance(node, _ast.Call):
                continue
            if isinstance(node, _ast.Name):
                n = node.id
                if "__" in n:
                    slot = n.split("__")[0]
                    need(slot in slots, where, f"{n.replace('__', '.')!r}: no slot called {slot!r}")
                else:
                    need(n in known, where, f"{n!r} is not a quantity, a define or a slot.field")
            elif isinstance(node, _ast.Constant):
                v = node.value
                need(isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf"),
                     where, f"the constant {v!r} is not a finite number")
            elif not isinstance(node, (_ast.Expression, _ast.Compare, _ast.Eq, _ast.BinOp, _ast.UnaryOp,
                                       _ast.Add, _ast.Sub, _ast.Mult, _ast.Div, _ast.USub, _ast.UAdd, _ast.Load)):
                raise BrickError(f"{where}: {type(node).__name__} is not allowed here (+ - * / **, parentheses and "
                                 f"the functions {', '.join(sorted(FUNCS))})")
    # EVERY slot.field USED must exist in EVERY item the slot can take (fuzz, 2026-10-10: an item
    # missing a field reached ZTL as an unknown name)
    used_fields = set()
    for t in [l["zfl"] for l in laws] + list(defines.values()) + ([obj["minimize"]] if obj is not None else []):
        used_fields |= set(DOTTED.findall(t))
    for sl, f in sorted(used_fields):
        if sl not in slots:
            continue
        for cn in slots[sl]["from"]:
            c = cat.get(cn) or {}
            if "items" in c:
                for i, row in enumerate(c["items"]):
                    need(isinstance(row, dict) and f in row, f"catalog.{cn}.items[{i}]",
                         f"has no field {f!r}, used as {sl}.{f}")
                    need(field(row[f])[0] != "label", f"catalog.{cn}.items[{i}].{f}",
                         f"{row[f]!r} is a label (not a number), but {sl}.{f} is used as a quantity")
            elif "integers" in c:
                need(c["integers"].get("field") == f, f"catalog.{cn}", f"an integer catalog gives only {c['integers'].get('field')!r}, not {f!r}")
            elif "continuous" in c:
                need(c["continuous"].get("field") == f, f"catalog.{cn}",
                     f"a continuous catalog gives only {c['continuous'].get('field')!r}, not {f!r}")
            else:
                need(f in (c.get("fields") or {}), f"catalog.{cn}.fields", f"has no field {f!r}, used as {sl}.{f}")
    for i, l in enumerate(laws):
        names_ok(l["zfl"], f"laws[{i}]")
    for k, v in defines.items():
        names_ok(v, f"define.{k}")
    if obj is not None:
        names_ok(obj["minimize"], "objective")
        need(obj.get("case", "nominal") in ("nominal", "worst"), "objective.case", "must be \"nominal\" or \"worst\"")
        need(isinstance(obj.get("unit", ""), str), "objective.unit", "must be a unit string")
        used = set(re.findall(r"(?<![.\w])([A-Za-z_]\w*)(?![\w.(])", compile_expr(obj["minimize"], defines)))
        derived_used = sorted(n for n in used if qs.get(n, {}).get("role") == "derived")
        if obj.get("case", "nominal") == "nominal":
            pass        # derived quantities allowed since 2026-10-10 (I3): read at the nominal point by the laws
        else:
            need(not modes, "objective.case", "\"worst\" together with modes is not supported yet")


# BUILT-IN CONSTANTS (blind test G7, 2026-10-10: four of twelve authors wrote pi or g0 by hand).
# Added as GIVEN quantities only where a brick uses the name without declaring it; a brick's own
# quantity of that name always wins. pi is irrational, so it is a bracket of rationals 1e-15 wide
# (the stand computes in exact fractions); the others are exact by the definition of the SI.
CONSTANTS = {
    "pi": {"role": "given", "range": ["3141592653589793/1000000000000000", "3141592653589794/1000000000000000"],
           "unit": "", "ground": "built-in constant (a rational bracket of pi)"},
    "g0": {"role": "given", "value": "9.80665", "unit": "m/s^2", "ground": "built-in constant (standard gravity, exact)"},
    "R_gas": {"role": "given", "value": "8.314462618", "unit": "J/(mol*K)", "ground": "built-in constant (molar gas constant, exact in the SI)"},
    "c0": {"role": "given", "value": "299792458", "unit": "m/s", "ground": "built-in constant (speed of light, exact)"},
}


def _named_tolerances(b):
    """`"tolerance": "tol"` naming a GIVEN dimensionless quantity (real round 3, n01; the curator's "да", 2026-10-12):
    the box is value * (1 +- t) for the worst t in tol's own box — so `find` can search a tolerance ("the largest
    tolerance that still works": find over tol, each tried range [0, a] gives value * (1 +- a)). Resolved in place
    to the number; the quantity keeps `_tolerance_of` for the output. Idempotent."""
    qs = b.get("quantities") if isinstance(b, dict) else None
    if not isinstance(qs, dict):
        return b
    for n, q in qs.items():
        t = q.get("tolerance") if isinstance(q, dict) else None
        if not isinstance(t, str) or t not in qs:
            continue
        tq = qs[t]
        if not isinstance(tq, dict) or tq.get("role") != "given":
            raise BrickError(f"{n}.tolerance names {t!r}, which must be a given quantity")
        if tq.get("unit") not in (None, ""):
            raise BrickError(f"{n}.tolerance names {t!r}, which must be dimensionless (a fraction: 0.01 is 1 %)")
        if isinstance(tq.get("tolerance"), str) and tq["tolerance"] in qs:
            raise BrickError(f"{n}.tolerance names {t!r}, whose own tolerance names another quantity: one step only")
        try:
            if "range" in tq:
                lo, hi = num(tq["range"][0]), num(tq["range"][1])
            else:
                v = num(tq["value"])
                w = abs(v) * num(tq.get("tolerance", "0"))
                lo, hi = v - w, v + w
        except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError):
            raise BrickError(f"{n}.tolerance names {t!r}, whose value or range is not readable")
        worst = max(abs(lo), abs(hi))
        q["tolerance"] = str(worst.numerator) if worst.denominator == 1 else f"{worst.numerator}/{worst.denominator}"
        q["_tolerance_of"] = t
    return b


def _add_constants(b):
    if not isinstance(b, dict) or not isinstance(b.get("quantities"), dict):
        return
    texts = [l.get("zfl", "") for l in (b["laws"] if isinstance(b.get("laws"), list) else []) if isinstance(l, dict)]
    texts += [v for v in (b.get("define") or {}).values() if isinstance(v, str)] if isinstance(b.get("define"), dict) else []
    obj = b.get("objective")
    if isinstance(obj, dict) and isinstance(obj.get("minimize"), str):
        texts.append(obj["minimize"])
    reqs = list(b.get("requirements") or []) if isinstance(b.get("requirements"), list) else []
    for m in (b.get("modes") or {}).values() if isinstance(b.get("modes"), dict) else []:
        if isinstance(m, dict) and isinstance(m.get("requirements"), list):
            reqs += m["requirements"]
    for r in reqs:
        if isinstance(r, dict):
            vals = r.get("value") if isinstance(r.get("value"), list) else [r.get("value")]
            texts += [v for v in vals if isinstance(v, str)]
    used = {n for t in texts if isinstance(t, str) for n in re.findall(r"(?<![.\w])([A-Za-z_]\w*)", t)}
    for name, spec in CONSTANTS.items():
        if name in used and name not in b["quantities"]:
            b["quantities"][name] = dict(spec)


_VALID = re.compile(r"^(.*?)(<=|>=|<|>)(.*)$")


def _add_domains(b):
    """A LAW'S DOMAIN (blind test G8, 2026-10-10: an M/M/1 latency formula used where mu < lambda
    gave a design with a negative latency). `"valid": "mu > lam"` on a law makes the model's
    domain a REQUIREMENT: a quantity valid_<i> == mu - lam, required > 0. A design whose box
    leaves the domain anywhere is refused, and says the law did not hold — the stand never
    vouches for a formula outside the region it was given for."""
    if not isinstance(b, dict) or not isinstance(b.get("laws"), list) or not isinstance(b.get("quantities"), dict):
        return
    for i, law in enumerate(b["laws"]):
        if not (isinstance(law, dict) and isinstance(law.get("valid"), str)):
            continue
        m = _VALID.match(law["valid"].strip())
        if not m or "=" in m.group(1)[-1:] or "=" in m.group(3)[:1]:
            raise BrickError(f"laws[{i}].valid: write one comparison, e.g. \"mu > lam\" (not {law['valid']!r})")
        lhs, op, rhs = m.group(1).strip(), m.group(2), m.group(3).strip()
        name = f"valid_{i}"
        if name in b["quantities"]:
            continue                        # already added (a mode's brick is loaded again: idempotent)
        b["quantities"][name] = {"role": "derived", "unit": _infer_unit(b, f"({lhs}) - ({rhs})"),
                                 "why": f"the domain of laws[{i}]"}
        b["laws"].append({"zfl": f"{name} == ({lhs}) - ({rhs})", "source": f"the domain of laws[{i}]: {law['valid']}"})
        b.setdefault("requirements", [])
        if not isinstance(b["requirements"], list):
            return                          # the shape check names the broken requirements
        b["requirements"].append({"quantity": name, "op": op, "value": "0",
                                  "why": f"laws[{i}] ({law.get('zfl', '')}) holds only where {law['valid']}"})


def _infer_unit(b, text):
    """The unit of an expression from the brick's own units; None when any name has none."""
    try:
        import ast as _ast
        from . import units as _U
        dims = {}
        for n, q in b["quantities"].items():
            if isinstance(q, dict) and isinstance(q.get("unit"), str):
                dims[n] = _U.parse(q["unit"])[1]
        for sn, sp in (b.get("slots") or {}).items():
            cat = (b.get("catalog") or {}).get((sp.get("from") or [None])[0]) or {}
            for f, u in field_units(cat).items():
                if isinstance(u, str):
                    dims[f"{sn}__{f}"] = _U.parse(u)[1]
        d = _U._dim(_ast.parse(compile_expr(text, b.get("define")), mode="eval").body, dims, "valid")
        return _U.unit_of(d) if d is not None else ""
    except Exception:                       # noqa: BLE001 — no unit then: "units: not checked" says so
        return None


ROOT = "_root_"          # the placeholder of an implicit quantity inside its own law


def implicit_laws(b, laws):
    """IMPLICIT LAWS (blind test G6, 2026-10-10: a fan's or a pump's operating point, where two
    curves meet). A derived quantity with "search": [lo, hi] is fixed by the ONE law in which it
    appears that does not define another quantity; that law, g == 0 with lhs - rhs, is rewritten
    as a definition:  Q == implicit(_root_Q, g with Q renamed _root_Q, lo, hi)  (lo, hi in SI).
    So every reader handles it as a definition: chains, units, the checker's classes. What it
    MEANS — every root of g in [lo, hi] — is read by ZTL (zimplicit: a root-exclusion certificate)
    and, independently, by the checker. Version 1: the law may use only given and catalog
    quantities besides Q (other derived quantities may use Q freely)."""
    import ast as _ast
    from . import units as _U
    qs = b["quantities"]
    search = {n: q["search"] for n, q in qs.items() if q.get("role") == "derived" and "search" in q}
    if not search:
        return laws
    derived = {n for n, q in qs.items() if q.get("role") == "derived"}
    out = list(laws)
    for q, (lo, hi) in search.items():
        sc = _U.parse(qs[q].get("unit") or "")[0]
        lo, hi = num(lo) * sc, num(hi) * sc
        own = []
        for i, law in enumerate(out):
            tree = _ast.parse(law, mode="eval").body
            names = {x.id for x in _ast.walk(tree) if isinstance(x, _ast.Name)}
            if q not in names:
                continue
            lhs, rhs = tree.left, tree.comparators[0]
            defines_other = isinstance(lhs, _ast.Name) and lhs.id in derived and lhs.id != q \
                and lhs.id not in {x.id for x in _ast.walk(rhs) if isinstance(x, _ast.Name)}
            if isinstance(lhs, _ast.Name) and lhs.id == q and q not in \
                    {x.id for x in _ast.walk(rhs) if isinstance(x, _ast.Name)}:
                raise BrickError(f"{q}: has an explicit law ({law!r}) — drop \"search\", it is not implicit")
            if not defines_other:
                own.append((i, tree, names))
        if len(own) != 1:
            raise BrickError(f"{q}: \"search\" needs exactly ONE law fixing it implicitly (one in which it appears "
                             f"and that defines no other quantity); found {len(own)}")
        i, tree, names = own[0]
        others = sorted((names & derived) - {q})
        if others:
            raise BrickError(f"{q}: its implicit law uses the derived {', '.join(others)} — version 1 reads an "
                             "implicit law over given and catalog quantities only (write them in, or use define)")
        ph = ROOT + q
        g = _ast.parse(f"({_ast.unparse(tree.left)}) - ({_ast.unparse(tree.comparators[0])})", mode="eval").body
        for x in _ast.walk(g):
            if isinstance(x, _ast.Name) and x.id == q:
                x.id = ph
        out[i] = f"{q} == implicit({ph}, {_ast.unparse(g)}, {lo.numerator}/{lo.denominator}, " \
                 f"{hi.numerator}/{hi.denominator})"
    return out


def _expand_defines(text, defines):
    """Every define expanded in place (in parentheses), as compile_expr does — without the other rewritings."""
    for _ in range(len(defines) + 1):
        before = text
        for name, expr in defines.items():
            text = re.sub(rf"(?<!\.)\b{re.escape(name)}\b(?!\.)", f"({expr})", text)
        if text == before:
            break
    return text


def joint_totals(raw) -> dict:
    """TOTALS OVER MODES (J8, blind test 4, 2026-10-11, the curator's "да"): annual energy over flow bins, wet + dry
    life. Each mode carries a "weight" (a number or an expression of givens: a share of the year, hours); the brick's
    "totals" name sums: {"Eyear": {"sum": "P*h", "unit": "MWh"}} is the sum over the modes of weight * (P*h) read in
    that mode. The brick is judged as ONE brick: every derived quantity, and every given a mode overrides, gets a
    copy per mode (P_in_wet); a given no mode overrides is the SAME value in every mode (one physical part — to let
    it differ, override it in each mode). A mode's requirements go on its copies; a requirement on a total, once."""
    import copy as _copy
    b = _copy.deepcopy(raw)
    modes, totals = b.get("modes"), b.get("totals")
    if not isinstance(modes, dict) or not modes:
        raise BrickError("totals: need \"modes\" — a total sums a quantity over the modes")
    if not isinstance(totals, dict) or not totals:
        raise BrickError("totals: must be an object of name: {\"sum\": expression, \"unit\": ...}")
    qs = b.get("quantities") or {}
    derived = [n for n, q in qs.items() if isinstance(q, dict) and q.get("role") == "derived"]
    for t, ts in totals.items():
        if not isinstance(ts, dict) or not isinstance(ts.get("sum"), str):
            raise BrickError(f"totals.{t}: must be {{\"sum\": expression, \"unit\": ...}}")
        if t in qs:
            raise BrickError(f"totals.{t}: the name is already a quantity")
    base_defs = b.get("define") or {}
    out_q = {n: q for n, q in qs.items() if n not in derived}
    out_laws, out_reqs, parts = [], [], {t: [] for t in totals}
    for m, sp in modes.items():
        if not re.fullmatch(r"[A-Za-z]\w*", m):
            raise BrickError(f"modes.{m}: with totals a mode's name must be a plain name (letters, digits, _)")
        if not isinstance(sp, dict) or not isinstance(sp.get("weight"), str):
            raise BrickError(f"modes.{m}: with totals every mode needs a \"weight\" (a number or an expression, as "
                             "a string)")
        over = sp.get("quantities") or {}
        for g in over:
            if g not in qs or qs[g].get("role") != "given":
                raise BrickError(f"modes.{m}: {g!r} is not a given quantity of the brick (a mode overrides givens only)")
        # a given whose tolerance NAMES a given this mode overrides has its own box in the mode (audit 2026-10-13, cx2:
        # it stayed one quantity with the base tolerance — a false EARNED)
        tol_of = {n: (q.get("_tolerance_of") or q.get("tolerance")) for n, q in qs.items()
                  if isinstance(q, dict) and q.get("role") == "given" and n not in over}
        dep = {n: t for n, t in tol_of.items() if isinstance(t, str) and t in over}
        ren = set(derived) | set(over) | set(dep)
        defs = dict(base_defs, **(sp.get("define") or {}))

        def rn(text, m=m, ren=ren, defs=defs):
            text = _expand_defines(text, defs)
            for n in sorted(ren, key=len, reverse=True):
                text = re.sub(rf"(?<![\w.]){re.escape(n)}\b(?!\.)", f"{n}_in_{m}", text)
            return text
        for n in derived:
            new = f"{n}_in_{m}"
            if new in qs or new in totals:
                raise BrickError(f"{new}: the per-mode copy's name is taken — rename the quantity or the mode")
            out_q[new] = _copy.deepcopy(qs[n])
        for g, ov in over.items():
            base = {k: v for k, v in qs[g].items() if k not in ("value", "tolerance", "range")}
            base.update(ov)
            out_q[f"{g}_in_{m}"] = base
        for n, t in dep.items():
            if f"{n}_in_{m}" in qs or f"{n}_in_{m}" in totals:
                raise BrickError(f"{n}_in_{m}: the per-mode copy's name is taken — rename the quantity or the mode")
            cp = {k: v for k, v in qs[n].items() if k != "_tolerance_of"}
            cp["tolerance"] = f"{t}_in_{m}"
            out_q[f"{n}_in_{m}"] = cp
        for l in list(b.get("laws") or []) + list(sp.get("laws") or []):
            # `valid` read in the mode too (audit 2026-10-13, cx3: it kept the base givens — a false EARNED)
            out_laws.append(dict(l, zfl=rn(l["zfl"]), source=f"[{m}] " + str(l.get("source", "")),
                                 **({"valid": rn(l["valid"])} if isinstance(l.get("valid"), str) else {})))
        for r in list(b.get("requirements") or []) + list(sp.get("requirements") or []):
            if r.get("quantity") in totals:
                continue
            r2 = dict(r, quantity=f"{r['quantity']}_in_{m}" if r.get("quantity") in ren else r.get("quantity"),
                      why=f"[{m}] " + str(r.get("why", "")))
            if isinstance(r.get("value"), str):
                r2["value"] = rn(r["value"])
            elif isinstance(r.get("value"), list):
                r2["value"] = [rn(v) if isinstance(v, str) else v for v in r["value"]]
            out_reqs.append(r2)
        for t, ts in totals.items():
            parts[t].append(f"({rn(sp['weight'])})*({rn(ts['sum'])})")
    for t, ts in totals.items():
        out_q[t] = {"role": "derived", "unit": ts.get("unit", ""), "why": f"the total over the modes of {ts['sum']}"}
        out_laws.append({"zfl": f"{t} == " + " + ".join(parts[t]), "source": f"totals.{t}: the weighted sum over the modes"})
    out_reqs += [r for r in (b.get("requirements") or []) if r.get("quantity") in totals]
    obj = b.get("objective")
    if obj and isinstance(obj.get("minimize"), str):
        used = {x for x in re.findall(r"(?<![\w.])([A-Za-z_]\w*)\b(?!\.)", _expand_defines(obj["minimize"], base_defs))}
        bad = sorted(used & set(derived))
        if bad:
            raise BrickError(f"objective: {', '.join(bad)} has a value in every mode — minimize a total instead")
    b["quantities"], b["laws"], b["requirements"] = out_q, out_laws, out_reqs
    for k in ("modes", "totals"):
        b.pop(k, None)
    b["_joined_modes"] = list(modes)
    return b


def _direct_requirements(b):
    """A requirement directly on a GIVEN quantity or a catalog FIELD (blind test 5, c06 and c09, the curator's "да",
    2026-10-11: "B <= 2.0 m" on a catalog width needed a dummy derived quantity). The stand makes the dummy itself:
    a derived `<name>_req` with the law `<name>_req == <name>`, in the same unit."""
    qs = b.get("quantities") or {}
    reqs = list(b.get("requirements") or [])
    for sp in (b.get("modes") or {}).values() if isinstance(b.get("modes"), dict) else []:
        if isinstance(sp, dict):
            reqs += list(sp.get("requirements") or [])
    made = {}
    for r in reqs:
        if not isinstance(r, dict) or not isinstance(r.get("quantity"), str):
            continue
        q = r["quantity"]
        if q in made:
            r["quantity"] = made[q]
            continue
        unit = None
        if isinstance(qs.get(q), dict) and qs[q].get("role") == "given":
            unit = qs[q].get("unit")
        elif re.fullmatch(r"[A-Za-z_]\w*\.[A-Za-z_]\w*", q):
            slot, f = q.split(".")
            spec = (b.get("slots") or {}).get(slot)
            if not isinstance(spec, dict):
                continue
            us = [field_units((b.get("catalog") or {}).get(c) or {}).get(f) for c in spec.get("from") or []]
            unit = next((u for u in us if u), None)
        else:
            continue
        name = re.sub(r"\W", "_", q) + "_req"
        if name in qs:
            raise BrickError(f"requirement on {q!r}: the stand's name {name!r} for it is taken")
        qs[name] = {"role": "derived", "unit": unit or "", "why": f"{q}, so a requirement can name it"}
        b.setdefault("laws", []).append({"zfl": f"{name} == {q}", "source": f"the requirement on {q} (made by the stand)"})
        r.setdefault("why", f"{q} {r.get('op')} {r.get('value')}")
        r["quantity"] = made[q] = name
    b["quantities"] = qs


def _optional_slots(b):
    """A slot with "optional": true may stay EMPTY (J11, blind test 4, 2026-10-11, the curator's "да"): a catalog
    `<slot>_none` with one item "none" is added to it — every numeric field 0 (price 0, power 0, count 0), every
    label "none". What an author typed by hand. A law that divides by such a field cannot read the empty choice:
    write it so that 0 means "absent" (a conductance, not a resistance)."""
    cat = b.get("catalog") or {}
    for s, spec in (b.get("slots") or {}).items():
        if not isinstance(spec, dict) or not spec.get("optional"):
            continue
        if spec["optional"] is not True:
            raise BrickError(f"slots.{s}.optional: true or absent, not {spec['optional']!r}")
        name = f"{s}_none"
        if name in cat and name in (spec.get("from") or []) and \
                (cat[name].get("ground") or "").startswith(f"slot {s} left empty"):
            continue        # loaded once already (a mode's brick is loaded again — blind test 5, c10: BRICK ERROR)
        if name in cat:
            raise BrickError(f"slots.{s}.optional: the catalog name {name!r} is taken")
        fields, units = {}, {}
        for c in spec.get("from") or []:
            src = cat.get(c) or {}
            for f, u in field_units(src).items():
                fields.setdefault(f, "0")
                if u is not None:
                    units.setdefault(f, u)
            for it in src.get("items") or []:
                for f, v in it.items():
                    numeric = isinstance(v, dict)
                    if not numeric:
                        try:
                            num(v); numeric = True
                        except (ValueError, ZeroDivisionError, TypeError):
                            numeric = False
                    if fields.get(f) != "0":
                        fields[f] = "0" if numeric else "none"
        fields["name"] = "none"
        cat[name] = {"items": [fields], "fields": {f: {"unit": u} for f, u in units.items()},
                     "ground": f"slot {s} left empty (optional)"}
        spec["from"] = list(spec.get("from") or []) + [name]
    b["catalog"] = cat


def _safe_texts(b):
    """every law and objective a brick brings must be arithmetic over names before anything reads it: some of them
    are later evaluated with Python (components.py, fwitness.py), and a brick may come from anyone (safeexpr.py)"""
    from . import safeexpr as SX
    texts = [("law", t) for t in (b.get("laws") or []) if isinstance(t, str)]
    texts += [("define " + k, v) for k, v in (b.get("define") or {}).items() if isinstance(v, str)]
    obj = (b.get("objective") or {}).get("minimize")
    if isinstance(obj, str):
        texts.append(("objective", obj))
    for what, t in texts:
        try:
            SX.check(compile_expr(t, b.get("define")))
        except SX.UnsafeExpression as e:
            raise BrickError(f"{what} {t[:120]!r}: {e} — a brick's expressions are arithmetic over names only")
        except SyntaxError:
            pass                                    # unreadable text is the readers' own error, said there


def load(path_or_dict) -> dict:
    import copy as _copy
    b = _copy.deepcopy(path_or_dict) if isinstance(path_or_dict, dict) \
        else json.load(open(path_or_dict, encoding="utf-8"))          # never edit the caller's brick
    _named_tolerances(b)
    _add_constants(b)
    _add_domains(b)
    _shape(b)
    _optional_slots(b)
    _direct_requirements(b)
    _safe_texts(b)
    qs = b.get("quantities") or {}
    cat = b.get("catalog") or {}
    for name, q in qs.items():
        if q.get("role") not in ("given", "derived"):
            raise BrickError(f"{name}: role must be given or derived (choices are slots), not {q.get('role')!r}")
        if q["role"] == "given" and "value" not in q and "range" not in q:
            raise BrickError(f"{name}: a given quantity needs a value or a range")
    for s, spec in (b.get("slots") or {}).items():
        if not spec.get("from"):
            raise BrickError(f"slot {s}: needs 'from' (catalog names)")
        for c in spec["from"]:
            if c not in cat:
                raise BrickError(f"slot {s}: catalog {c!r} not defined")
    if not b.get("laws"):
        raise BrickError("no laws")
    mode_reqs = [r for m in (b.get("modes") or {}).values() if isinstance(m, dict) for r in (m.get("requirements") or [])]
    if not b.get("requirements") and not mode_reqs:
        raise BrickError("no requirements")         # with modes, requirements may live in the modes only
    for r in list(b.get("requirements") or []) + mode_reqs:
        if r.get("op") not in OPS:
            raise BrickError(f"requirement op must be one of {OPS}")
        if qs.get(r.get("quantity"), {}).get("role") != "derived":
            raise BrickError(f"requirement on {r.get('quantity')!r}: must be a derived quantity")
        vals = r.get("value") if isinstance(r.get("value"), list) else [r.get("value")]
        for v in vals:
            if not isinstance(v, str):
                continue
            try:
                num(v)
                continue                                      # a plain number
            except (ValueError, ZeroDivisionError):
                pass
            # a name or an EXPRESSION (blind test G4, 2026-10-10: L/300, 15*g0, savings - fee)
            try:
                tree = __import__("ast").parse(compile_expr(v, b.get("define")), mode="eval").body
            except SyntaxError:
                raise BrickError(f"requirement on {r['quantity']!r}: the bound {v!r} is not a number, a name or "
                                 "a readable expression")
            # a FUNCTION's name is not a quantity: the bound reader (_ival) reads sqrt, min, exp, ... (found
            # 2026-10-20 by the bridge girder: "min" in an EN 1993 buckling bound was refused here, read fine there)
            calls = {id(c.func) for c in __import__("ast").walk(tree)
                     if type(c).__name__ == "Call" and type(c.func).__name__ == "Name" and c.func.id in FUNCS}
            for node in __import__("ast").walk(tree):
                if type(node).__name__ == "Name" and id(node) not in calls:
                    n = node.id
                    if "__" in n:
                        if n.split("__")[0] not in (b.get("slots") or {}):
                            raise BrickError(f"requirement on {r['quantity']!r}: {n.replace('__', '.')!r} — no such slot")
                    elif n not in qs:
                        raise BrickError(f"requirement on {r['quantity']!r}: {n!r} in the bound is not a quantity")
                    elif qs[n].get("role") == "derived":
                        raise BrickError(f"requirement on {r['quantity']!r}: the bound uses {n!r}, a derived quantity — "
                                         "a bound is built from numbers, given quantities and slot.fields; for a "
                                         "derived bound write the difference as its own derived quantity, bound by 0")
    return b


def _ival(node, env):
    """Sound interval of a bound expression (the stand's own small reader; names -> (lo, hi))."""
    import ast as _ast
    if isinstance(node, _ast.Constant):
        x = num(node.value)
        return x, x
    if isinstance(node, _ast.Name):
        return env[node.id]
    if isinstance(node, _ast.Call):
        from . import judge_ztl  # noqa: F401  (ZTL on the path)
        import zfunc
        args = [_ival(a, env) for a in node.args]
        name = node.func.id
        try:
            if name == "sqrt":
                if args[0][0] < 0:
                    raise BrickError("a bound takes the root of a range below zero")
                import znum
                return znum._iv_sqrt(args[0])
            r = zfunc.UNARY[name](args[0]) if name in zfunc.UNARY else zfunc.BINARY[name](*args)
        except zfunc.NoReadings as why:
            raise BrickError(f"a requirement bound: {why}")
        if r is None:
            raise BrickError(f"a requirement bound: {name} is undefined somewhere on its range")
        return r
    if isinstance(node, _ast.UnaryOp):
        lo, hi = _ival(node.operand, env)
        return (-hi, -lo) if isinstance(node.op, _ast.USub) else (lo, hi)
    a, b = _ival(node.left, env), _ival(node.right, env)
    if isinstance(node.op, _ast.Add):
        return a[0] + b[0], a[1] + b[1]
    if isinstance(node.op, _ast.Sub):
        return a[0] - b[1], a[1] - b[0]
    if isinstance(node.op, _ast.Mult):
        ps = [x * y for x in a for y in b]
        return min(ps), max(ps)
    if b[0] <= 0 <= b[1]:
        raise BrickError("a requirement bound divides by a range that contains zero")
    ps = [x / y for x in a for y in b]
    return min(ps), max(ps)


def bound_value(v, boxes, fixed, side):
    """A requirement bound: a number, a quantity, or an expression of given / catalog quantities —
    at its LEAST FAVOURABLE end over the box (sound: an interval reading; at a point, exact)."""
    if not isinstance(v, str):
        return num(v)
    try:
        return num(v)
    except (ValueError, ZeroDivisionError):
        pass
    import ast as _ast
    tree = _ast.parse(v.replace(".", "__") if DOTTED.fullmatch(v) else v, mode="eval").body
    env = {n: (x, x) for n, x in fixed.items()}
    env.update(boxes)
    lo, hi = _ival(tree, env)
    # SPLIT WHAT VARIES (2026-10-20, the bridge girder: an EN 1993 buckling bound reads one toleranced modulus a dozen
    # times through lambda, phi and chi; read once over E +-0.5 % it widened enough to leave two verticals OPEN that
    # hold at every point). With one or two names varying, each interval is cut into pieces and the bound read on
    # every piece — the union covers the box, so the ends stay sound, and the widening shrinks with the pieces.
    vary = sorted(n for n in {x.id for x in _ast.walk(tree) if isinstance(x, _ast.Name)}
                  if n in env and env[n][0] != env[n][1])
    if 1 <= len(vary) <= 2:
        k = BOUND_PIECES if len(vary) == 1 else 8
        cuts = {n: [env[n][0] + (env[n][1] - env[n][0]) * i / k for i in range(k + 1)] for n in vary}
        los, his = [], []
        for idx in __import__("itertools").product(range(k), repeat=len(vary)):
            sub = dict(env, **{n: (cuts[n][i], cuts[n][i + 1]) for n, i in zip(vary, idx)})
            a, b = _ival(tree, sub)
            los.append(a)
            his.append(b)
        lo, hi = max(lo, min(los)), min(hi, max(his))
    return lo if side == "upper" else hi


BOUND_PIECES = 32       # pieces of ONE varying name in a requirement's bound (see bound_value)


class Win(tuple):
    """A requirement's window (low, high) that also remembers whether each end is STRICT. It
    unpacks like the pair it always was (`a, c = iv`), so every reader of a window keeps working."""
    def __new__(cls, a, c, strict_lo=False, strict_hi=False):
        w = tuple.__new__(cls, (a, c))
        w.strict_lo, w.strict_hi = strict_lo, strict_hi
        return w


def req_interval(r, boxes=None, fixed=None):
    boxes, fixed = boxes or {}, fixed or {}
    if r["op"] == "within":
        return Win(bound_value(r["value"][0], boxes, fixed, "lower"), bound_value(r["value"][1], boxes, fixed, "upper"))
    if r["op"] in ("<=", "<"):
        return Win(None, bound_value(r["value"], boxes, fixed, "upper"), False, r["op"] == "<")
    return Win(bound_value(r["value"], boxes, fixed, "lower"), None, r["op"] == ">", False)



def merge_windows(w1, w2):
    """Two requirements on ONE quantity: the window both ask for — the higher low end, the lower high end, a tie
    strict if either is (2026-10-11: windows were kept in a dict by quantity, the second overwrote the first, and
    a design was EARNED against one requirement only — order-dependent, a FALSE EARNED)."""
    if w1 is None:
        return w2
    (a1, c1), (a2, c2) = w1, w2
    s1l, s1h = getattr(w1, "strict_lo", False), getattr(w1, "strict_hi", False)
    s2l, s2h = getattr(w2, "strict_lo", False), getattr(w2, "strict_hi", False)
    if a1 is None or (a2 is not None and a2 > a1):
        a, sl = a2, s2l
    elif a2 is None or a1 > a2:
        a, sl = a1, s1l
    else:
        a, sl = a1, s1l or s2l
    if c1 is None or (c2 is not None and c2 < c1):
        c, sh = c2, s2h
    elif c2 is None or c1 < c2:
        c, sh = c1, s1h
    else:
        c, sh = c1, s1h or s2h
    return Win(a, c, sl, sh)


def windows(reqs, boxes=None, fixed=None):
    """{quantity: the merged window of every requirement on it}."""
    out = {}
    for r in reqs:
        out[r["quantity"]] = merge_windows(out.get(r["quantity"]), req_interval(r, boxes, fixed))
    return out

def inside(lo, hi, iv) -> bool:
    a, b = iv
    sl, sh = getattr(iv, "strict_lo", False), getattr(iv, "strict_hi", False)
    return (a is None or (lo > a if sl else lo >= a)) and (b is None or (hi < b if sh else hi <= b))


def violates(v, iv) -> bool:
    """v a number, or an interval (lo, hi) — a value with a function in it, read at a point. An
    interval violates only when ALL of it is past the bound (a witness must be certain)."""
    a, b = iv
    lo, hi = v if isinstance(v, tuple) and not isinstance(v, Win) else (v, v)
    sl, sh = getattr(iv, "strict_lo", False), getattr(iv, "strict_hi", False)
    return (a is not None and (hi <= a if sl else hi < a)) or (b is not None and (lo >= b if sh else lo > b))
