# -*- coding: utf-8 -*-
"""HVAC plant models as LIBRARY FUNCTIONS of the brick language (DESIGN-HVAC.md, 2026-11-12).

Ported from EnergyPlus version 26.2.0 (github.com/NREL/EnergyPlus, tag v26.2.0); its copyright notice and licence are
in NOTICE-EnergyPlus.txt beside this file, as its clause (1) requires. The port is ours; EnergyPlus does not endorse it.

A law may call `ep_<name>(args)`. bricks.compile_expr expands the call into the function's TEMPLATE — a ZFL expression
over its parameters — before anything else reads the law; ZTL then proves the expanded law like any other. Each
template is the ONLY definition of its function: `evaluate` (for the tests against EnergyPlus's own values) reads the
same text. Arguments and results are SI with units: a template divides by the unit constants `ep_K`, `ep_Pa`, ... (given
quantities the stand adds when used, value 1 in their unit) so that exp / ln read pure numbers, and multiplies its
result by its unit. EnergyPlus works in deg C; the templates take absolute temperature in K (the stand's SI; a degC /
degF brick is translated to K first) and form Tc = T/ep_K - 273.15 where EnergyPlus writes T.
"""
from __future__ import annotations

import ast
import math
import re


# unit constants the templates use (value 1 in the unit)
UNIT_CONSTANTS = {"ep_K": "K", "ep_Pa": "Pa", "ep_J_kg": "J/kg", "ep_J_kgK": "J/(kg*K)", "ep_kg_m3": "kg/m^3",
                  "ep_m3_kg": "m^3/kg"}

LIBRARY: dict[str, dict] = {}


def register(name, args, expr, unit, source, note=""):
    LIBRARY[name] = {"args": list(args), "expr": re.sub(r"\s+", " ", expr).strip(), "unit": unit, "source": source,
                     "note": note}


from . import psychro  # noqa: E402,F401  (registers its functions)

CALL_RE = re.compile(r"(?<![\w.])(ep_[A-Za-z0-9_]+)\s*\(")


def uses_library(text):
    return any(m.group(1) in LIBRARY for m in CALL_RE.finditer(text))


def expand(text):
    """Every call of a library function replaced by its template, the arguments substituted in parentheses; nested
    calls (a template calling another, an argument calling one) expanded to a fixed point. -> (text, set of unit
    constants used). Raises ValueError on an unknown ep_ name or a wrong argument count."""
    used = set()
    for _ in range(32):
        m = None
        for mm in CALL_RE.finditer(text):
            m = mm
            break
        if m is None:
            break
        name = m.group(1)
        if name not in LIBRARY:
            if name in UNIT_CONSTANTS:
                continue
            raise ValueError(f"{name}: no such library function (known: {sorted(LIBRARY)})")
        # the argument list: up to the matching parenthesis
        i, depth = m.end(), 1
        while i < len(text) and depth:
            depth += {"(": 1, ")": -1}.get(text[i], 0)
            i += 1
        if depth:
            raise ValueError(f"{name}(: a parenthesis is not closed")
        inner = text[m.end():i - 1]
        args, depth, cur = [], 0, ""
        for ch in inner:
            if ch == "," and depth == 0:
                args.append(cur)
                cur = ""
                continue
            depth += {"(": 1, ")": -1}.get(ch, 0)
            cur += ch
        args.append(cur)
        args = [a.strip() for a in args if a.strip() or len(args) > 1]
        spec = LIBRARY[name]
        if len(args) != len(spec["args"]):
            raise ValueError(f"{name} takes {len(spec['args'])} arguments ({', '.join(spec['args'])}), not {len(args)}")
        body = spec["expr"]
        for p, a in zip(spec["args"], args):
            body = re.sub(rf"(?<![\w.]){re.escape(p)}(?![\w])", f"({a})", body)
        text = text[:m.start()] + f"({body})" + text[i:]
    else:
        raise ValueError("library expansion did not end (a function calls itself?)")
    used |= {c for c in UNIT_CONSTANTS if re.search(rf"(?<![\w.]){c}(?![\w])", text)}
    return text, used


# ---------------------------------------------------------------------------------------------------------- evaluate
def _ev(node, env):
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.UnaryOp):
        v = _ev(node.operand, env)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.BinOp):
        a, b = _ev(node.left, env), _ev(node.right, env)
        return {ast.Add: lambda: a + b, ast.Sub: lambda: a - b, ast.Mult: lambda: a * b, ast.Div: lambda: a / b,
                ast.Pow: lambda: a ** b}[type(node.op)]()
    if isinstance(node, ast.Compare):
        a, b = _ev(node.left, env), _ev(node.comparators[0], env)
        return {ast.Lt: a < b, ast.LtE: a <= b, ast.Gt: a > b, ast.GtE: a >= b}[type(node.ops[0])]
    if isinstance(node, ast.Call):
        f = node.func.id
        if f == "__if__":
            return _ev(node.args[1], env) if _ev(node.args[0], env) else _ev(node.args[2], env)
        a = [_ev(x, env) for x in node.args]
        return {"exp": math.exp, "ln": math.log, "log10": math.log10, "sqrt": math.sqrt, "pow": math.pow,
                "min": min, "max": max}[f](*a)
    raise ValueError(f"cannot evaluate {ast.dump(node)[:60]}")


def evaluate(name, *args):
    """The function in double precision, from its template (the tests compare it with EnergyPlus's own values).
    Arguments in SI numbers (K, Pa, kg/kg); the result in SI."""
    text, _ = expand(f"{name}({', '.join(f'__a{i}' for i in range(len(args)))})")
    env = {f"__a{i}": float(v) for i, v in enumerate(args)}
    env.update({c: 1.0 for c in UNIT_CONSTANTS})
    tree = ast.parse(re.sub(r"(?<![\w.])if\s*\(", "__if__(", text), mode="eval").body
    return _ev(tree, env)
