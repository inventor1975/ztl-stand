"""Units: scale every value to SI, and check every law's dimensions (gap J5, 2026-10-09).

A unit string is a product/quotient of tokens, each an optional SI prefix and a
base unit, optionally raised to a power: "V", "ohm", "kohm", "nF",
"C/W", "1/C", "m*s^-2", "USD", "kEUR", "m^2.5/s", "m^(1/2)". Unknown tokens are refused aloud.

J7 (blind test 4, 2026-10-11): "year" (also "yr") is the JULIAN year, 365.25 days = 31 557 600 s
(the curator's decision; a life of 30 years x 8760 h is written as 8760 h, explicitly); a currency
takes the prefixes k and M (kEUR = 1000 EUR); a power may be a fraction (m^2.5, m^(5/2)) — empirical
coefficients carry such units, and sqrt of an odd power is now a half power instead of an error.

Temperature in "C" is treated as a temperature DIFFERENCE dimension (K) with no
offset: correct for laws that only add temperatures and differences (Tj = Ta +
P*R, R*(1 + a*(T - 25))); a law that multiplies absolute temperatures needs K.
Numbers in a law carry no unit: in a sum they take the unit of what they are
added to (the 25 in T - 25 is 25 C), in a product they are dimensionless.
"""
from __future__ import annotations

import ast
import re
from fractions import Fraction as F

# dimension vector over the SI bases, the amount of substance, and each CURRENCY apart (USD + EUR is
# a dimension error: exchange rates are quantities, not units)
CURRENCIES = ("USD", "EUR", "GBP", "ILS", "RUB", "JPY", "CHF", "CNY")
DIMS = ("m", "kg", "s", "A", "K", "mol") + CURRENCIES


def _d(**kw):
    return tuple(kw.get(k, 0) for k in DIMS)


BASE = {
    "": (F(1), _d()), "1": (F(1), _d()),
    "m": (F(1), _d(m=1)), "g": (F(1, 1000), _d(kg=1)), "s": (F(1), _d(s=1)),
    "A": (F(1), _d(A=1)), "K": (F(1), _d(K=1)), "C": (F(1), _d(K=1)),
    "V": (F(1), _d(m=2, kg=1, s=-3, A=-1)), "W": (F(1), _d(m=2, kg=1, s=-3)),
    "ohm": (F(1), _d(m=2, kg=1, s=-3, A=-2)), "F": (F(1), _d(m=-2, kg=-1, s=4, A=2)),
    "H": (F(1), _d(m=2, kg=1, s=-2, A=-2)), "Hz": (F(1), _d(s=-1)), "J": (F(1), _d(m=2, kg=1, s=-2)),
    "N": (F(1), _d(m=1, kg=1, s=-2)), "Pa": (F(1), _d(m=-1, kg=1, s=-2)),
    "ppm": (F(1, 10**6), _d()), "%": (F(1, 100), _d()),
    # added after the blind test (2026-10-10, G3): what twelve domains asked for
    "h": (F(3600), _d(s=1)), "min": (F(60), _d(s=1)), "day": (F(86400), _d(s=1)),
    "L": (F(1, 1000), _d(m=3)), "mol": (F(1), _d(mol=1)), "t": (F(1000), _d(kg=1)),
    "Ah": (F(3600), _d(s=1, A=1)), "Wh": (F(3600), _d(m=2, kg=1, s=-2)),
    "bar": (F(10**5), _d(m=-1, kg=1, s=-2)), "rpm": (F(1, 60), _d(s=-1)),
    "dB": (F(1), _d()), "dBA": (F(1), _d()), "rad": (F(1), _d()),
    "year": (F(31557600), _d(s=1)), "yr": (F(31557600), _d(s=1)),          # J7: the Julian year
    # blind test 5 (the curator's "да", 2026-10-11): dose, apparent and reactive power, the degree.
    # Gy and Sv are both J/kg — the check cannot tell absorbed from equivalent dose; VA and var are W —
    # nor apparent or reactive from active power: the names are for the reader.
    "Gy": (F(1), _d(m=2, s=-2)), "Sv": (F(1), _d(m=2, s=-2)),
    "VA": (F(1), _d(m=2, kg=1, s=-3)), "var": (F(1), _d(m=2, kg=1, s=-3)),
    # deg: pi/180 is irrational; this is pi/180 to 40 significant digits (relative error below 1e-40)
    "deg": (F("0.01745329251994329576923690768488612713443"), _d()),
    # real round 3 (the curator's "да", 2026-10-12): US customary, EXACT by definition — the inch is 0.0254 m, the
    # pound 0.45359237 kg (1959), the pound-force that pound under standard gravity 9.80665 m/s^2.
    # NOT added: degF (an offset scale, not a factor) and dBm (a logarithm) — a wrong guess there is costly.
    "in": (F("0.0254"), _d(m=1)), "ft": (F("0.3048"), _d(m=1)), "lb": (F("0.45359237"), _d(kg=1)),
    "lbf": (F("0.45359237") * F("9.80665"), _d(m=1, kg=1, s=-2)),
    "psi": (F("0.45359237") * F("9.80665") / F("0.0254") ** 2, _d(m=-1, kg=1, s=-2)),
    "ksi": (1000 * F("0.45359237") * F("9.80665") / F("0.0254") ** 2, _d(m=-1, kg=1, s=-2)),
    # real round 4 (2026-10-12, k05 k06): the avoirdupois ounce (1/16 lb), its force, the US liquid gallon
    # (231 cubic inches) and the gallon per minute — exact by the same definitions
    "oz": (F("0.45359237") / 16, _d(kg=1)), "ozf": (F("0.45359237") / 16 * F("9.80665"), _d(m=1, kg=1, s=-2)),
    "gal": (231 * F("0.0254") ** 3, _d(m=3)), "gpm": (231 * F("0.0254") ** 3 / 60, _d(m=3, s=-1)),
    "daN": (F(10), _d(m=1, kg=1, s=-2)),       # the decanewton of lashing tables (blind test 6, c09)
    **{c: (F(1), _d(**{c: 1})) for c in CURRENCIES},
}
PREFIX = {"p": F(1, 10**12), "n": F(1, 10**9), "u": F(1, 10**6), "m": F(1, 1000), "c": F(1, 100),
          "k": F(1000), "M": F(10**6), "G": F(10**9)}
NO_PREFIX = {"", "1", "%", "ppm", "dB", "dBA", "rad", "min", "day", "h", "rpm", "year", "yr", "deg",
             "in", "ft", "lb", "lbf", "ksi", "oz", "ozf", "gal", "gpm", "daN"}
CURRENCY_PREFIX = {"k", "M"}          # J7: kEUR, MUSD — and no other (mEUR would be a typo)
NAME = re.compile(r"[A-Za-z%]+|1")
NUMBER = re.compile(r"\d+(?:\.\d+)?")      # a factor in a unit: kWh/100km (blind test 5, c08)


class UnitError(ValueError):
    pass


def _name(name):
    if name in BASE:
        return BASE[name]
    if len(name) > 1 and name[0] in PREFIX and name[1:] in BASE and name[1:] not in NO_PREFIX and \
            (name[1:] not in CURRENCIES or name[0] in CURRENCY_PREFIX):
        scale, dim = BASE[name[1:]]
        return PREFIX[name[0]] * scale, dim
    raise UnitError(f"unit {name!r} not known (known: {sorted(k for k in BASE if k)}; prefixes {sorted(PREFIX)})")


def parse(unit: str):
    """A unit string -> (scale to SI, dimension). Products `*`, quotients `/`, integer powers `^-2`
    and PARENTHESES (2026-10-10: `J/(kg*K)` met in the blind test). '' or None: dimensionless."""
    if not unit:
        return F(1), _d()
    if not isinstance(unit, str):       # the fuzz, 2026-10-12: a unit written as a number reached .replace
        raise UnitError(f"unit {unit!r}: write a unit as a string, e.g. \"ohm\"")
    text = unit.replace(" ", "")
    pos = [0]

    def peek():
        return text[pos[0]] if pos[0] < len(text) else ""

    def atom():
        if peek() == "(":
            pos[0] += 1
            v = expr()
            if peek() != ")":
                raise UnitError(f"unit {unit!r}: a parenthesis is not closed")
            pos[0] += 1
        else:
            num_m = NUMBER.match(text, pos[0])
            if num_m and num_m.group(0) != "1" or (num_m and NAME.match(text, num_m.end()) and
                                                   text[num_m.end():num_m.end() + 1].isalpha()):
                # a number, alone or written straight before a unit: 100km is 100 x km
                pos[0] = num_m.end()
                v = (F(num_m.group(0)), _d())
                if v[0] == 0:       # the fuzz, 2026-10-12: "1/0" as a unit divided by zero (a STAND ERROR)
                    raise UnitError(f"unit {unit!r}: a number in a unit must not be 0")
                nm = NAME.match(text, pos[0])
                if nm and nm.group(0) != "1":
                    pos[0] = nm.end()
                    s2, d2 = _name(nm.group(0))
                    v = (v[0] * s2, d2)
            else:
                m = NAME.match(text, pos[0])
                if not m:
                    raise UnitError(f"unit {unit!r}: cannot read at {text[pos[0]:]!r}")
                pos[0] = m.end()
                v = _name(m.group(0))
        if peek() == "^":
            m = re.compile(r"\^(?:\((-?\d+(?:\.\d+)?(?:/\d+)?)\)|(-?\d+(?:\.\d+)?))").match(text, pos[0])
            if not m:
                raise UnitError(f"unit {unit!r}: a power must be a number, e.g. ^2, ^-1, ^2.5 or ^(5/2)")
            pos[0] = m.end()
            k = F(m.group(1) or m.group(2))
            if k.denominator == 1:
                k = int(k)
                v = (v[0] ** k, tuple(k * x for x in v[1]))
            elif v[0] == 1:
                v = (v[0], tuple(k * x for x in v[1]))
            else:
                raise UnitError(f"unit {unit!r}: a fractional power of a scaled unit (its scale is irrational) — "
                                f"write the unit in SI first")
        return v

    def expr():
        scale, dim = atom()
        while peek() in ("*", "/"):
            op = text[pos[0]]
            pos[0] += 1
            s2, d2 = atom()
            if op == "*":
                scale, dim = scale * s2, tuple(a + b for a, b in zip(dim, d2))
            else:
                scale, dim = scale / s2, tuple(a - b for a, b in zip(dim, d2))
        return scale, dim

    out = expr()
    if pos[0] != len(text):
        raise UnitError(f"unit {unit!r}: cannot read at {text[pos[0]:]!r}")
    return out


def _pw(p):
    p = F(p)
    return str(p.numerator) if p.denominator == 1 else f"({p.numerator}/{p.denominator})"


def show(dim) -> str:
    parts = [f"{n}^{_pw(p)}" if p != 1 else n for n, p in zip(DIMS, dim) if p]
    return "*".join(parts) or "dimensionless"


def _const(node):
    """The exact value of an expression of numbers only (+ - * / and unary minus), or None."""
    if isinstance(node, ast.Constant) and not isinstance(node.value, bool) and isinstance(node.value, (int, float)):
        return F(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _const(node.operand)
        return None if v is None else (-v if isinstance(node.op, ast.USub) else v)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        a, b = _const(node.left), _const(node.right)
        if a is None or b is None or (isinstance(node.op, ast.Div) and b == 0):
            return None
        return {ast.Add: a + b, ast.Sub: a - b, ast.Mult: a * b}.get(type(node.op)) if not isinstance(node.op, ast.Div) \
            else a / b
    return None


def _dim(node, dims, where):
    """Dimension of an expression; None = a bare number (takes its partner's unit in a sum)."""
    if isinstance(node, ast.Constant):
        return None
    if isinstance(node, ast.Name):
        if node.id not in dims:
            raise UnitError(f"{where}: {node.id} has no unit")
        return dims[node.id]
    if isinstance(node, ast.Call):
        name = node.func.id
        if name == "ifpos":                     # a branch: the condition's own terms agree, the branches share a unit
            _dim(node.args[0], dims, where)
            a, b = _dim(node.args[1], dims, where), _dim(node.args[2], dims, where)
            if a is not None and b is not None and a != b:
                raise UnitError(f"{where}: the two branches of if(...) have different units ({show(a)}, {show(b)})")
            return a if a is not None else b
        if name == "implicit":                  # Q == implicit(_root_Q, g, lo, hi): g's terms must agree,
            _dim(node.args[1], dims, where)     # and the value has the unit of Q (bricks.implicit_laws)
            return _dim(node.args[0], dims, where)
        ds = [_dim(a, dims, where) for a in node.args]
        if name in ("min", "max"):
            a, b = ds
            if a is not None and b is not None and a != b:
                raise UnitError(f"{where}: {name} of {show(a)} and {show(b)}")
            return a if a is not None else b
        if name == "sqrt":                      # J7: an odd power gives a half power (m^2.5/s and kin)
            a = ds[0] or _d()
            return tuple(F(x) / 2 if x % 2 else x // 2 for x in a)
        if name == "pow":
            a, b = ds[0] or _d(), ds[1] or _d()
            if any(b):
                raise UnitError(f"{where}: an exponent with a unit ({show(b)})")
            if not any(a):
                return a
            k = _const(node.args[1])            # a number, or arithmetic of numbers: pow(x, 2/3) (blind test 5, c04)
            if k is None:
                raise UnitError(f"{where}: {show(a)} to a power that is not a constant")
            return tuple(k * x if (k * x).denominator != 1 else int(k * x) for x in a)
        a = ds[0]
        if a is not None and any(a):
            raise UnitError(f"{where}: {name} of {show(a)} — a transcendental function reads a dimensionless argument")
        return None
    if isinstance(node, ast.UnaryOp):
        return _dim(node.operand, dims, where)
    if isinstance(node, ast.BinOp):
        a, b = _dim(node.left, dims, where), _dim(node.right, dims, where)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            if a is not None and b is not None and a != b:
                raise UnitError(f"{where}: adding {show(a)} to {show(b)}")
            return a if a is not None else b
        if isinstance(node.op, ast.Mult):
            a, b = a or _d(), b or _d()
            return tuple(x + y for x, y in zip(a, b))
        if isinstance(node.op, ast.Div):
            a, b = a or _d(), b or _d()
            return tuple(x - y for x, y in zip(a, b))
    raise UnitError(f"{where}: cannot check {ast.dump(node)[:50]}")


def check_law(law: str, dims: dict, label: str):
    tree = ast.parse(law, mode="eval").body
    l, r = _dim(tree.left, dims, label), _dim(tree.comparators[0], dims, label)
    if l is not None and r is not None and l != r:
        raise UnitError(f"{label}: left side is {show(l)}, right side is {show(r)}")


def unit_of(dim) -> str:
    """A dimension back to a unit string `parse` reads (SI bases: m kg s A K mol, currencies)."""
    parts = []
    for name, p in zip(DIMS, dim):
        if p:
            parts.append(name if p == 1 else f"{name}^{_pw(p)}")
    return "*".join(parts)
