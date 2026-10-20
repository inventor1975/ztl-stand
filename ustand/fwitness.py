"""A WITNESS SEARCH IN FLOATS (2026-10-16, the curator's "делай"): before any certificate, look for a point of the
box where a requirement fails — every law evaluated in floats (an implicit law by a bracketed root), the worst corner
by the sign of each quantity's effect, flips one at a time, then a local search inside the box.

Trusted for NOTHING: a candidate is re-solved EXACTLY by the checker (checker.solve_at) and is a witness only if the
exact values fail a requirement there. Finding none proves nothing; the certificates come next as before.

Why: the four-unit motor with 28 uncertain data (per-segment batches) — the stand spent a whole certificate budget
(15 min, OPEN) on a design that FAILS before it ever looked for the failing point; an LLM with numpy found such
points in seconds (MEASURED 2026-10-16). The exact greedy walk (stand._greedy_corner) starts from all-low and
all-high corners and missed it.
"""
from __future__ import annotations

import ast
import math
from fractions import Fraction as F

from .lp import _FLOAT_FN

FN = dict(_FLOAT_FN, pi=math.pi)


def _compile(laws):
    """[(name, code | None, implicit spec | None)] from 'X == expr' laws; None when a law is not of that form."""
    out = []
    for law in laws:
        if law.count("==") != 1:
            return None
        lhs, rhs = (s.strip() for s in law.split("=="))
        if not lhs.isidentifier():
            return None
        try:
            tree = ast.parse(rhs, mode="eval").body
        except SyntaxError:
            return None
        if isinstance(tree, ast.Call) and getattr(tree.func, "id", None) == "implicit" and len(tree.args) == 4:
            ph = tree.args[0].id
            g = compile(ast.Expression(tree.args[1]), "<g>", "eval")
            lo = float(F(ast.unparse(tree.args[2]).replace(" ", "")))
            hi = float(F(ast.unparse(tree.args[3]).replace(" ", "")))
            out.append((lhs, None, (ph, g, lo, hi), _names(tree.args[1]) - {ph}))
        else:
            out.append((lhs, compile(ast.Expression(tree), "<law>", "eval"), None, _names(tree)))
    return out


def _names(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} - set(FN)


def _root(spec, env):
    ph, g, lo, hi = spec

    def f(x):
        return float(eval(g, {"__builtins__": {}, **FN}, dict(env, **{ph: x})))
    xs = [lo + (hi - lo) * k / 400 for k in range(401)]
    prev = None
    for x in xs:
        try:
            v = f(x)
        except (ArithmeticError, ValueError, TypeError):
            prev = None
            continue
        if v == 0:
            return x
        if prev is not None and (prev[1] < 0) != (v < 0):
            a, fa, b = prev[0], prev[1], x
            for _ in range(80):                         # bisection: robust, ~1e-16 relative
                m = (a + b) / 2
                fm = f(m)
                if (fa < 0) == (fm < 0):
                    a, fa = m, fm
                else:
                    b = m
            return (a + b) / 2
        prev = (x, v)
    return None


def _evaluate(comp, env):
    """Every derived value at one point (floats), or None."""
    env = dict(env)
    todo = list(comp)
    while todo:
        progress = False
        rest = []
        for name, code, spec, needs in todo:
            if not needs <= set(env):
                rest.append((name, code, spec, needs))
                continue
            try:
                v = _root(spec, env) if spec else float(eval(code, {"__builtins__": {}, **FN}, env))
            except (ArithmeticError, ValueError, TypeError, OverflowError):
                return None
            if v is None or v != v or abs(v) > 1e300:
                return None
            env[name] = v
            progress = True
        if not progress:
            return None
        todo = rest
    return env


RAN = [False]           # did the last find() evaluate the laws at all (False: the caller's exact walk instead)


def find(laws, fixed, boxes, derived, reqs, violation, req_at, solve_exact):
    """(point, exact values, hit) — a point the EXACT solution fails — or None. RAN[0] says whether the floats could
    read the laws (a law of another form, no value at the centre: they could not)."""
    RAN[0] = False
    try:
        return _find(laws, fixed, boxes, derived, reqs, violation, req_at, solve_exact)
    except Exception:                                   # noqa: BLE001 — a search aid: never a verdict, never a crash
        RAN[0] = False
        return None


def _find(laws, fixed, boxes, derived, reqs, violation, req_at, solve_exact):
    comp = _compile(laws)
    if comp is None:
        return None
    base = {n: float(v) for n, v in fixed.items()}
    wide = [n for n in sorted(boxes) if boxes[n][0] < boxes[n][1]]
    lo = {n: float(boxes[n][0]) for n in boxes}
    hi = {n: float(boxes[n][1]) for n in boxes}
    centre = {n: (lo[n] + hi[n]) / 2 for n in boxes}
    centre_exact = dict(fixed, **{n: (boxes[n][0] + boxes[n][1]) / 2 for n in boxes})
    tried = set()
    for r in reqs:
        try:
            a, c = req_at(r, centre_exact)
        except Exception:                               # noqa: BLE001 — a bound read at the point only: skip
            continue
        a = None if a is None else float(a)
        c = None if c is None else float(c)
        q = r["quantity"]

        def bad(pt):
            env = _evaluate(comp, dict(base, **pt))
            if env is None or q not in env:
                return None
            v = env[q]
            return max(([a - v] if a is not None else []) + ([v - c] if c is not None else []) or [None])

        b0 = bad(centre)
        if b0 is None:
            continue
        RAN[0] = True
        # each quantity to the end that makes this requirement worse (its effect over its whole width)
        pt = dict(centre)
        for n in wide:
            bl, bh = bad(dict(centre, **{n: lo[n]})), bad(dict(centre, **{n: hi[n]}))
            if bl is not None and bh is not None:
                pt[n] = hi[n] if bh >= bl else lo[n]
        cur = bad(pt)
        for _ in range(3):                              # flips, one quantity at a time
            better = False
            for n in wide:
                alt = dict(pt, **{n: lo[n] if pt[n] == hi[n] else hi[n]})
                v = bad(alt)
                if v is not None and cur is not None and v > cur:
                    pt, cur, better = alt, v, True
            if not better:
                break
        cands = [pt]
        if cur is None or cur <= 0:
            try:                                        # an extreme INSIDE the box
                from scipy.optimize import minimize
                x0 = [pt[n] for n in wide]
                res = minimize(lambda x: -(bad(dict(pt, **dict(zip(wide, x)))) or -1e30), x0, method="L-BFGS-B",
                               bounds=[(lo[n], hi[n]) for n in wide], options={"maxiter": 200})
                cands.append(dict(pt, **dict(zip(wide, res.x))))
            except Exception:                           # noqa: BLE001
                pass
        for cand in cands:
            v = bad(cand)
            if v is None or v <= 0:
                continue
            exact = {}
            for n in boxes:
                x = cand[n]
                if x == lo[n]:
                    exact[n] = boxes[n][0]
                elif x == hi[n]:
                    exact[n] = boxes[n][1]
                else:
                    fx = F(x).limit_denominator(10 ** 12)
                    exact[n] = min(max(fx, boxes[n][0]), boxes[n][1])
            key = tuple(sorted(exact.items()))
            if key in tried:
                continue
            tried.add(key)
            env = dict(fixed, **exact)
            try:
                vals = solve_exact(laws, env, derived)
            except Exception:                           # noqa: BLE001 — not solvable there: not a witness
                continue
            hit = violation(vals, env)
            if hit:
                return exact, vals, hit
    return None
