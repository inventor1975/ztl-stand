"""--prove: the EARNED verdict's requirements as Lean THEOREMS on VR's continuum (ZTL tools/zbound2lean.py).

The curator, 2026-11-08: "важно, если стенд будет давать не только сертификат, но и доказательства".

For the design the stand EARNED, each requirement `q op c` on a quantity q the LINEAR laws determine is handed to
ZTL's translator: q's expression from the laws (ZTL's exact Cramer solution), the tolerance box rounded outward to
dyadics, the bound cleared to a polynomial, a cover tree proposed by ZBound.findV and CHECKED by the Lean kernel
(zero axioms). The verdict gets a `proof` field with every requirement's status and an honest count.

Said, not hidden (the `proof.rests_on` text):
  - the elimination laws => expression is Python's exact algebra, not proved in Lean; the theorem is about the
    expression;
  - the tolerances are the brick's data, taken as stated (the same credit the verdict rests on);
  - values are in SI (the stand's frame), the theorem's bound is the requirement converted to SI;
  - a quantity defined by a NONLINEAR law, an implicit quantity, a strict bound (< or >) and a bound written as an
    expression are not translated yet — they stay on the stand's certificate, and are counted as such.
"""
from __future__ import annotations

import ast
import hashlib
import os
import sys
import time
from fractions import Fraction as F

from . import bricks as B
from . import judge_ztl as J

PROVE = [False]
DEPTH = [0]         # stand.run's nesting depth, kept HERE so the two copies of ustand.stand share it (see stand._DEPTH)
LEVEL = [1]         # the run depth whose EARNED is proved: 1, or 2 for a find brick's decision (its own run)


def _zb():
    tools = os.path.join(J.ZTL_DIR, "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import zbound2lean
    return zbound2lean


def _ztl_text(node, defs, seen=()):
    """A definition's right side as ZTL's arithmetic (znumjudge._parse_arith: + - * /, pow(a, k), f(x)), every
    other definition it leans on inlined (a chain of definitions). None: a construct ZTL's reader lacks."""
    if isinstance(node, ast.Name):
        if node.id in defs:
            if node.id in seen:
                return None
            t = _ztl_text(defs[node.id], defs, seen + (node.id,))
            return None if t is None else f"({t})"
        return node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)) and not isinstance(node.value, bool):
        try:
            x = F(B.num(node.value))
        except (ValueError, ZeroDivisionError, TypeError):
            return None
        return f"({x.numerator}/{x.denominator})" if x.denominator != 1 else (f"({x})" if x < 0 else str(x))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        a = _ztl_text(node.operand, defs, seen)
        return None if a is None else f"(0 - {a})"
    if isinstance(node, ast.BinOp):
        a, b = _ztl_text(node.left, defs, seen), _ztl_text(node.right, defs, seen)
        if a is None or b is None:
            return None
        sym = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}.get(type(node.op))
        if sym:
            return f"({a} {sym} {b})"
        if isinstance(node.op, ast.Pow):
            return f"pow({a}, {b})"
        return None
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        args = [_ztl_text(x, defs, seen) for x in node.args]
        if any(x is None for x in args):
            return None
        return f"{node.func.id}({', '.join(args)})"
    return None


def _num(v, fixed):
    """A requirement's bound in SI as a Fraction: a number, or an expression of the design's FIXED data (a power
    rating `R1.P`) read exactly — or None."""
    try:
        return F(B.num(v))
    except (ValueError, ZeroDivisionError, TypeError):
        pass
    try:
        lo, hi = B._ival(ast.parse(str(v), mode="eval").body, {n: (x, x) for n, x in fixed.items()})
    except Exception:
        return None
    return F(lo) if lo == hi else None


def _bounds(r, fixed, defs):
    """[(op, value, strict)] of a requirement in SI — value a Fraction, or ZTL text of a bound that is an expression of
    toleranced data (`P1 <= R1.P` with the rating itself toleranced: proved as `P1 − R1.P <= 0`) — or a reason."""
    op, v = r["op"], r["value"]
    if op not in ("within", "<=", ">=", "<", ">"):
        return None, f"the requirement's op {op!r}"
    out = []
    for o, x in ([(">=", v[0]), ("<=", v[1])] if op == "within" else [(op, v)]):
        n = _num(x, fixed)
        if n is None:
            try:
                n = _ztl_text(ast.parse(str(x), mode="eval").body, defs)
            except SyntaxError:
                n = None
            if n is None:
                return None, "the bound is an expression ZTL's arithmetic reader lacks"
        out.append((o.rstrip("=") + "=" if o in ("<", ">") else o, n, o in ("<", ">")))
    return out, None


def _split_implicit(text):
    """The ONE implicit root of a target text — `implicit(ph, g, lo, hi)` (ustand/bricks.implicit_laws) — as
    (ph, g, lo, hi, the text with the call replaced by ph), or None (none, or two different ones)."""
    calls, i = [], 0
    while True:
        j = text.find("implicit(", i)
        if j < 0:
            break
        dep, k = 0, j + len("implicit")
        for k in range(j + len("implicit"), len(text)):
            dep += 1 if text[k] == "(" else (-1 if text[k] == ")" else 0)
            if dep == 0:
                break
        calls.append(text[j:k + 1])
        i = k + 1
    if not calls or len(set(calls)) != 1:
        return None
    inner = calls[0][len("implicit("):-1]
    parts, dep, st = [], 0, 0
    for k, ch in enumerate(inner):
        dep += 1 if ch == "(" else (-1 if ch == ")" else 0)
        if ch == "," and dep == 0:
            parts.append(inner[st:k].strip()); st = k + 1
    parts.append(inner[st:].strip())
    if len(parts) != 4:
        return None
    ph, g, lo, hi = parts
    try:
        lo_f, hi_f = F(B.num(lo.replace(" ", "").strip("()"))), F(B.num(hi.replace(" ", "").strip("()")))
    except (ValueError, ZeroDivisionError, TypeError):
        return None
    return ph, g, lo_f, hi_f, text.replace(calls[0], ph)


def _strict_c(c, op):
    """A strict `q < c`: proved as `q <= c'` with c' = c − δ (δ = 2⁻²⁴·max(|c|, 1)), c' < c by arithmetic."""
    d = F(max(abs(c), 1)) / 2 ** 24
    return c - d if op == "<=" else c + d


def prove(laws, fixed, boxes, derived, grounds, reqs) -> dict:
    """reqs: the requirements in SI (the stand's run-time list)."""
    from . import forward as W
    linear, defs2 = W.split(laws, derived)
    lin_derived = [d for d in derived if d not in defs2]
    sheet = J.sheet(fixed, boxes, lin_derived, grounds)
    zb = _zb()
    items, proved = [], 0
    t0 = time.time()
    def one(target, pairs):
        key = "\n".join(linear) + "|" + sheet + "|" + target + "|" + repr(pairs)
        name = "ZStand_" + hashlib.sha1(key.encode()).hexdigest()[:12]
        imp = _split_implicit(target) if "implicit(" in target else None
        try:
            if imp is not None:            # a root of an implicit law: zimplicit's theorem + the bound at the root
                ph, g, lo_, hi_, tgt = imp
                st = zb.implicit_bound_to_lean(linear, lin_derived, sheet, tgt, ph, g, [lo_, hi_], pairs, name)
                return name, st
            st = zb.bound_to_lean(linear, lin_derived, sheet, target, pairs, name)
        except Exception as ex:                     # the translator's own failure: said, never a verdict
            st = {"status": "not translated", "why": f"translator error: {type(ex).__name__}: {ex}"}
        return name, st

    for r in reqs:
        q = r["quantity"]
        it = {"quantity": q, "op": r["op"], "value_si": r["value"]}
        bnds, why = _bounds(r, fixed, defs2)
        target = q if q in lin_derived else (_ztl_text(defs2[q], defs2) if q in defs2 else None)
        if bnds is None:
            it.update(status="not translated", why=why)
            items.append(it)
            continue
        if target is None:
            it.update(status="not translated",
                      why=("its definition holds a construct ZTL's arithmetic reader lacks" if q in defs2
                           else "not a derived quantity of the linear system"))
            items.append(it)
            continue
        if target != q:
            it["definition"] = f"{q} = {target} (the system's solutions substituted)"
        # the numeric bounds in one file; a bound that is an expression moves into the target: q − b {op} 0
        calls = []
        nums = [(o, _strict_c(c, o) if st_ else c) for o, c, st_ in bnds if isinstance(c, F)]
        if nums:
            calls.append((target, nums, " and ".join(f"{q} {o} {c}" for o, c in nums)))
        for o, c, st_ in bnds:
            if not isinstance(c, F):
                z = _strict_c(F(0), o) if st_ else F(0)
                calls.append((f"({target}) - ({c})", [(o, z)], f"{q} − ({c}) {o} {z}"))
        if any(st_ for _, _, st_ in bnds):
            it["strict"] = "a strict bound proved with a margin: q <= c' (or >=) with c' = c ∓ 2⁻²⁴·max(|c|, 1)"
        parts, ok = [], True
        for tgt, pairs, says in calls:
            name, st = one(tgt, pairs)
            part = {"status": st["status"], "reads": says}
            if st.get("about") == "tables":
                part["about"] = (f"MANY TABLES ({st['tables']}): each table's value a variable with a range proved on "
                                 "every branch of that table (ZBoundIf.bound_tabs); the requirement for every point of "
                                 "the box and every value of the tables' variables that is one of their branch values "
                                 "— the tables' dependence on one another unused (independent ranges); the expression "
                                 "from ZTL's exact elimination, Python")
            elif st.get("about") == "branches":
                part["about"] = (f"a TABLE, branch by branch ({st['branches']} branches): at every point of the box, "
                                 "WHICHEVER branch applies, the requirement holds (ZBoundIf — a branch's piece is "
                                 "proved or excluded by its own condition; that the branches cover the table is the "
                                 "table's reading); the expression from ZTL's exact elimination, Python")
            elif st.get("about") == "implicit":
                part["about"] = ("an IMPLICIT root: for every parameter vector the law's root in its bracket exists, "
                                 "is unique (zimplicit's verdict, a Lean theorem), and the requirement holds there "
                                 "(bounded over the whole bracket — the root's dependence on the parameters unused)")
            elif st.get("about"):
                part["about"] = ("the LAWS: for every point of the box and EVERY value of the unknowns satisfying the "
                                 "laws (rows + a cofactor certificate checked by the kernel — the elimination not "
                                 "trusted; theorems lawreq*)" if st["about"] == "laws" else
                                 "the EXPRESSION of the quantity from the laws (ZTL's exact elimination, Python)")
            if st["status"] == "theorem":
                k = len(pairs)
                part.update(file=st["file"],
                            theorems=(st["theorems"] if st.get("theorems") else
                                      [f"{name}.implreq{i}" for i in range(k)] + [f"{name}R.law_root"]
                                      if st.get("about") == "implicit" else
                                      [f"{name}.lawreq{i}" for i in range(k)] + [f"{name}.cl{i}" for i in range(k)]
                                      if st.get("factor") else
                                      ([f"{name}.lawreq{i}" for i in range(k)] + [f"{name}.law_val"]
                                       if st.get("about") == "laws" else [])
                                      + [f"{name}.req{i}" for i in range(k)] + [f"{name}.cleared{i}" for i in range(k)]
                                      + ([f"{name}.q_pos"] if st["quotient"] else [])),
                            **({"theorem_reads": f"{st['factor']}·({tgt}) — the target times {st['factor']} in the "
                                                 "scaled parameters (the factor clears its constants)"}
                               if st.get("factor") else {}),
                            params=st["params"],
                            theorem_vars=({p: f"var {i} = {st['scale'][p]}·{p}" for i, p in enumerate(st["params"])}
                                          if st.get("scale") else
                                          {p: f"var {i} = {p}" for i, p in enumerate(st["params"])}),
                            box={p: [str(a), str(b)] for p, (a, b) in st["box"].items()},
                            box_is=("exact: each parameter an integer multiple, an integer box" if st.get("scale")
                                    else "rounded outward to dyadics"))
            else:
                ok = False
                part["why"] = st.get("why") or (st.get("out") or "")[:300]
            parts.append(part)
        if ok:
            proved += 1
            it.update(status="theorem", axioms="none (each #print axioms: does not depend on any axioms)")
        else:
            bad = [x for x in parts if x["status"] != "theorem"]
            it.update(status=bad[0]["status"], why=bad[0].get("why", ""))
        if len(parts) == 1:
            it.update({k: v for k, v in parts[0].items() if k not in ("status", "why")})
        else:
            it["parts"] = parts
        items.append(it)
    return {"proved": proved, "of": len(reqs),
            "count": f"{proved} of {len(reqs)} requirement(s) proved as Lean theorems; "
                     f"{len(reqs) - proved} rest on ZTL's verdict alone (no Lean theorem)",
            "requirements": items,
            "seconds": round(time.time() - t0, 1),
            "check_again": f"cd {os.path.join(J.ZTL_DIR, 'lean')} && lake env lean --tstack=400000 <file>",
            "rests_on": ("each requirement says what its theorem is ABOUT: the LAWS (every value of the unknowns "
                         "satisfying them; each law read as a polynomial row — multiplied by its denominators, the "
                         "parameters scaled — Python, local per law; the elimination checked by the kernel), or the "
                         "EXPRESSION from ZTL's exact elimination (Python, not proved in Lean); the tolerances are the "
                         "brick's data, taken as stated; values in SI")}
