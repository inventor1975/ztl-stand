"""The only expressions the stand will evaluate with Python: arithmetic over numbers and names.

A brick is data, and it may come from anyone: a file someone sends, or a model that read a datasheet with hidden
instructions in it. Three places evaluate a brick's text with Python's eval (an objective or a part's price,
components.py; a law in the float witness, fwitness.py), and eval with empty __builtins__ is NOT a sandbox: attribute
access on any object reaches the interpreter's internals. So every such text is checked here first, and only this
shape passes:

    numbers, names (no __dunder__ names except the stand's own __if__), + - * / // % **, unary + -, comparisons,
    and / or / not, a if c else b, tuples and lists of those, and calls of a plain NAME (a function the caller
    provides, e.g. sqrt, min, __if__).

Everything else — attributes (x.y), subscripts (x[0]), comprehensions, lambdas, strings, f-strings, starred
arguments, walrus — is refused with UnsafeExpression before anything runs (2026-10-27, security review of the
public ZTL Engineer app that feeds bricks to this stand).
"""
from __future__ import annotations

import ast

ALLOWED_DUNDER = {"__if__"}

_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.Call, ast.Name,
          ast.Constant, ast.Tuple, ast.List, ast.keyword, ast.Load,
          ast.operator, ast.unaryop, ast.cmpop, ast.boolop)


class UnsafeExpression(ValueError):
    pass


def check(expr) -> ast.AST:
    """the parsed expression (text or an ast node), or UnsafeExpression naming what is not allowed"""
    tree = ast.parse(expr, mode="eval") if isinstance(expr, str) else expr
    for node in ast.walk(tree):
        if not isinstance(node, _NODES):
            raise UnsafeExpression(f"not allowed in an expression: {type(node).__name__}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float, complex)):
            raise UnsafeExpression(f"only numbers are allowed as constants, not {node.value!r}")
        if isinstance(node, ast.Name) and node.id.startswith("__") and node.id not in ALLOWED_DUNDER:
            raise UnsafeExpression(f"not allowed as a name: {node.id}")
        if isinstance(node, ast.Call) and not isinstance(node.func, ast.Name):
            raise UnsafeExpression("only a plain function name may be called")
    return tree


def compile_checked(expr, filename: str = "<expr>"):
    """check, then compile for eval"""
    tree = check(expr)
    if not isinstance(tree, ast.Expression):
        tree = ast.Expression(tree)
    return compile(tree, filename, "eval")
