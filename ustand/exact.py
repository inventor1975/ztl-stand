"""EXACT per-design values: "where" (which combinations are designs at all) and "computed" (a value per design).

Blind test 2 (2026-10-10): three authors had to prepare the design space outside the stand — strings per
inverter input as ceil(NP / inputs) (c09), a per-system window of pipette volumes (c06), the stage pairs of a
gearbox inside a ratio window (c10: 54 000 combinations killed at 15 min). Both words read only EXACT values
(given quantities without tolerance, catalog fields without tolerance, labels, other computed values), so they
define the design space and never state anything about physics: no reading, no interval, no judge.

Names are read in SI, like laws. A bare number beside a quantity with a unit (VA.N <= 30 with N in mL) is
refused: 30 would be read as 30 m^3 — write the bound as a given quantity with its unit.
"""
from __future__ import annotations

import ast
import math
from fractions import Fraction as F

FUNCS = {"ceil": 1, "floor": 1, "abs": 1, "min": 2, "max": 2, "nominal": 1,
         "exp": 1, "ln": 1, "log10": 1, "sqrt": 1}
# exp ln log10 sqrt (J11, blind test 4, 2026-10-11: c07 could not pre-filter 331 128 designs, "`where` has no
# exp/ln"): their values are irrational, so they are read as an interval (mpmath, 200 bits, outward) and carried
# through the arithmetic exactly in fractions. A comparison those intervals do not decide — two sides within
# about 1e-55 — is said aloud (ExactError), never guessed: this word must stay exact.
TRANSCENDENTAL = {"exp", "ln", "log10", "sqrt"}


class _Iv:
    """A closed interval [lo, hi] of fractions holding an irrational value."""
    __slots__ = ("lo", "hi")

    def __init__(self, lo, hi):
        self.lo, self.hi = lo, hi

    @staticmethod
    def of(x):
        return x if isinstance(x, _Iv) else _Iv(x, x)

    def __add__(self, o):
        o = _Iv.of(o); return _Iv(self.lo + o.lo, self.hi + o.hi)
    __radd__ = __add__

    def __sub__(self, o):
        o = _Iv.of(o); return _Iv(self.lo - o.hi, self.hi - o.lo)

    def __rsub__(self, o):
        return _Iv.of(o) - self

    def __mul__(self, o):
        o = _Iv.of(o); p = [self.lo * o.lo, self.lo * o.hi, self.hi * o.lo, self.hi * o.hi]
        return _Iv(min(p), max(p))
    __rmul__ = __mul__

    def __truediv__(self, o):
        o = _Iv.of(o)
        if o.lo <= 0 <= o.hi:
            raise ZeroDivisionError
        return self * _Iv(1 / o.hi, 1 / o.lo)

    def __rtruediv__(self, o):
        return _Iv.of(o) / self

    def __neg__(self):
        return _Iv(-self.hi, -self.lo)

    def __abs__(self):
        if self.lo >= 0:
            return self
        if self.hi <= 0:
            return -self
        return _Iv(F(0), max(-self.lo, self.hi))


def _ends(r):
    """An mpmath interval's two ends, exactly, as fractions."""
    from mpmath.libmp import to_rational
    return tuple(F(*to_rational(e)) for e in r._mpi_)


def _transcendental(name, x, where):
    import mpmath
    iv = mpmath.iv
    iv.prec = 200
    x = _Iv.of(x)
    lo = iv.mpf(x.lo.numerator) / x.lo.denominator
    hi = iv.mpf(x.hi.numerator) / x.hi.denominator
    arg = iv.mpf([lo.a, hi.b])
    if name in ("ln", "log10") and not x.lo > 0:
        raise ExactError(f"{where}: {name} of a value that is not positive")
    if name == "sqrt" and x.lo < 0:
        raise ExactError(f"{where}: sqrt of a negative value")
    r = {"exp": iv.exp, "ln": iv.log, "sqrt": iv.sqrt,
         "log10": lambda v: iv.log(v) / iv.log(iv.mpf(10))}[name](arg)
    return _Iv(*_ends(r))


def _cmp(op, left, right, where):
    """A comparison where a side is an interval: decided only when the intervals do not touch."""
    L, R = _Iv.of(left), _Iv.of(right)
    if isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
        if isinstance(op, (ast.Gt, ast.GtE)):
            L, R = R, L                         # a > b  is  b < a
        if L.hi < R.lo:
            return True
        if L.lo > R.hi:
            return False
    elif isinstance(op, (ast.Eq, ast.NotEq)):
        if L.hi < R.lo or L.lo > R.hi:
            return isinstance(op, ast.NotEq)
    raise ExactError(f"{where}: a comparison with exp/ln/log10/sqrt too close to decide exactly (the two sides agree "
                     "to ~55 digits) — this word reads exact values only")
# nominal(e): e read at the NOMINAL point — every toleranced given and field at its nominal value (a value
# with a tolerance: the value; a range: its middle). Blind test 3 (c02, c04; c02 and c05 of round 2): the
# cost needed nominal values of toleranced data, and the authors typed exact duplicates by hand.


class ExactError(ValueError):
    pass


def parse(text):
    try:
        return ast.parse(text, mode="eval").body
    except SyntaxError:
        raise ExactError(f"{text!r} is not a readable expression")


def names(node):
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            continue
        if isinstance(n, ast.Name):
            out.add(n.id)
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            out.discard(n.func.id)
    return out


def check_shape(node, where):
    """Only arithmetic, comparisons, and/or/not, strings (labels) and the functions in FUNCS."""
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            if not (isinstance(n.func, ast.Name) and n.func.id in FUNCS and not n.keywords
                    and len(n.args) == FUNCS[n.func.id]):
                raise ExactError(f"{where}: only these functions exist here: "
                                 + ", ".join(f"{k}({'x' if v == 1 else 'x, y'})" for k, v in FUNCS.items()))
        elif isinstance(n, ast.Constant):
            if isinstance(n.value, bool) or not isinstance(n.value, (int, float, str)):
                raise ExactError(f"{where}: the constant {n.value!r} is not a number or a label")
        elif not isinstance(n, (ast.Name, ast.Load, ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp,
                                ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd, ast.Not,
                                ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
            raise ExactError(f"{where}: {type(n).__name__} is not allowed here")


def evaluate(node, env, where):
    """Exact value: Fraction, a label string, or a bool."""
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else F(str(node.value))
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise ExactError(f"{where}: {node.id.replace('__', '.')} has no exact value here (a tolerance, a "
                             "range or a derived quantity) — this word reads exact values only")
        return env[node.id]
    if isinstance(node, ast.UnaryOp):
        v = evaluate(node.operand, env, where)
        if isinstance(node.op, ast.Not):
            return not v
        if isinstance(v, str):
            raise ExactError(f"{where}: arithmetic on a label")
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.BinOp):
        a, b = evaluate(node.left, env, where), evaluate(node.right, env, where)
        if isinstance(a, (str, bool)) or isinstance(b, (str, bool)):
            raise ExactError(f"{where}: arithmetic on a label or a condition")
        if isinstance(node.op, ast.Add): return a + b
        if isinstance(node.op, ast.Sub): return a - b
        if isinstance(node.op, ast.Mult): return a * b
        if (b == 0) if not isinstance(b, _Iv) else (b.lo <= 0 <= b.hi):
            raise ExactError(f"{where}: division by zero")
        return a / b
    if isinstance(node, ast.BoolOp):
        vals = [evaluate(v, env, where) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.Compare):
        left = evaluate(node.left, env, where)
        for op, comp in zip(node.ops, node.comparators):
            right = evaluate(comp, env, where)
            if isinstance(left, str) != isinstance(right, str) and not isinstance(op, (ast.Eq, ast.NotEq)):
                raise ExactError(f"{where}: a label compared by size")
            if isinstance(left, _Iv) or isinstance(right, _Iv):
                if not _cmp(op, left, right, where):
                    return False
                left = right
                continue
            ok = {ast.Eq: left == right, ast.NotEq: left != right}.get(type(op))
            if ok is None:
                ok = {ast.Lt: left < right, ast.LtE: left <= right,
                      ast.Gt: left > right, ast.GtE: left >= right}[type(op)]
            if not ok:
                return False
            left = right
        return True
    if isinstance(node, ast.Call) and node.func.id == "nominal":
        nom = env.get("__nominal__")
        if nom is None:
            raise ExactError(f"{where}: nominal() has no nominal point here")
        try:
            return evaluate(node.args[0], nom, where)
        except ExactError as e:
            raise ExactError(f"{where}: nominal() reads given and catalog quantities (a derived one at its nominal "
                             f"value belongs in the objective): {e}")
    if isinstance(node, ast.Call):
        args = [evaluate(a, env, where) for a in node.args]
        if any(isinstance(a, (str, bool)) for a in args):
            raise ExactError(f"{where}: {node.func.id} of a label or a condition")
        name = node.func.id
        if name in TRANSCENDENTAL:
            return _transcendental(name, args[0], where)
        if any(isinstance(a, _Iv) for a in args):
            if name == "abs":
                return abs(args[0])
            if name in ("ceil", "floor"):
                f = math.ceil if name == "ceil" else math.floor
                a = args[0]
                if f(a.lo) != f(a.hi):
                    raise ExactError(f"{where}: {name} of a value with exp/ln too close to an integer to decide")
                return F(f(a.lo))
            a, b = (_Iv.of(x) for x in args)
            return _Iv(min(a.lo, b.lo), min(a.hi, b.hi)) if name == "min" else _Iv(max(a.lo, b.lo), max(a.hi, b.hi))
        if name == "ceil": return F(math.ceil(args[0]))
        if name == "floor": return F(math.floor(args[0]))
        if name == "abs": return abs(args[0])
        if name == "min": return min(args)
        if name == "max": return max(args)
    raise ExactError(f"{where}: cannot evaluate {ast.dump(node)[:60]}")


def dims(node, dimof, where, show):
    """Dimension of an expression (a tuple), None for a bare number; labels and conditions -> 'label'/'bool'.
    STRICT: a bare number beside a quantity with a unit is refused (it would be read in SI)."""
    nonzero = lambda d: d is not None and d not in ("label", "bool") and any(d)
    if isinstance(node, ast.Constant):
        return "label" if isinstance(node.value, str) else None
    if isinstance(node, ast.Name):
        return dimof(node.id)
    if isinstance(node, ast.UnaryOp):
        d = dims(node.operand, dimof, where, show)
        return "bool" if isinstance(node.op, ast.Not) else d
    if isinstance(node, ast.BoolOp):
        for v in node.values:
            dims(v, dimof, where, show)
        return "bool"
    if isinstance(node, (ast.BinOp, ast.Compare)):
        if isinstance(node, ast.BinOp):
            parts = [node.left, node.right]
            op = node.op
        else:
            parts = [node.left] + list(node.comparators)
            op = None
        ds = [dims(p, dimof, where, show) for p in parts]
        if op is None or isinstance(op, (ast.Add, ast.Sub)):
            real = [d for d in ds if d is not None]
            if any(nonzero(d) for d in real) and any(d is None for d in ds):
                raise ExactError(f"{where}: a bare number beside a quantity with a unit — it would be read in SI; "
                                 "write it as a given quantity with its unit")
            if len({d for d in real if d not in ("label",)}) > 1 or ("label" in real and len(set(real)) > 1):
                raise ExactError(f"{where}: comparing or adding different units ({', '.join(show(d) if isinstance(d, tuple) else str(d) for d in real)})")
            if op is None:
                return "bool"
            return real[0] if real else None
        a, b = [d if isinstance(d, tuple) else (None if d is None else d) for d in ds]
        if a in ("label", "bool") or b in ("label", "bool"):
            raise ExactError(f"{where}: arithmetic on a label or a condition")
        a = a or tuple(0 for _ in range(len(b))) if b else a
        b = b or tuple(0 for _ in range(len(a))) if a else b
        if a is None and b is None:
            return None
        if isinstance(op, ast.Mult):
            return tuple(x + y for x, y in zip(a, b))
        return tuple(x - y for x, y in zip(a, b))
    if isinstance(node, ast.Call):
        ds = [dims(a, dimof, where, show) for a in node.args]
        if node.func.id == "nominal":
            return ds[0]
        if node.func.id in ("ceil", "floor"):
            if nonzero(ds[0]):
                raise ExactError(f"{where}: {node.func.id} of a quantity with a unit ({show(ds[0])}) — round a ratio")
            return None
        if node.func.id in ("exp", "ln", "log10"):
            if nonzero(ds[0]):
                raise ExactError(f"{where}: {node.func.id} of a quantity with a unit ({show(ds[0])}) — divide by a unit first")
            return None
        if node.func.id == "sqrt":
            return tuple(F(x) / 2 for x in ds[0]) if isinstance(ds[0], tuple) else ds[0]
        if node.func.id in ("min", "max"):
            real = [d for d in ds if d is not None]
            if len(set(real)) > 1 or (real and nonzero(real[0]) and len(real) < len(ds)):
                raise ExactError(f"{where}: {node.func.id} of different units")
            return real[0] if real else None
        return ds[0]
    raise ExactError(f"{where}: cannot read units of {ast.dump(node)[:60]}")
