"""The judge: ZTL's numeric floor (ZTL/znumsolve.py), called as it is.

The bricks of one design are compiled into a ZFL sheet (quantities with their
provenance) and a claim (the laws joined by &). ZTL narrows every derived
quantity and says HOW: "exact at the corners" when the system lies in its exact
class (linear in the derived quantities, each toleranced quantity entering to
the first power with rank one), otherwise an outer range or nothing. The stand
only uses a range as decisive when ZTL itself calls it exact. Whatever new
mathematics ZTL learns, this adapter passes through unchanged.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from fractions import Fraction as F

ZTL_DIR = os.environ.get("USTAND_ZTL", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "ZTL"))   # ZTL cloned beside this repo, or USTAND_ZTL
ZTL_DIR = os.path.normpath(ZTL_DIR)
if not os.path.exists(os.path.join(ZTL_DIR, "znumsolve.py")):
    sys.exit(f"ztl-stand needs ZTL, the judge: not found at {ZTL_DIR}. Clone https://github.com/inventor1975/ZTL "
             f"beside this repository (../ZTL), or set USTAND_ZTL to its path.")
if ZTL_DIR not in sys.path:
    sys.path.insert(0, ZTL_DIR)

from znumjudge import parse_quantities  # noqa: E402
from znumsolve import solve_claim        # noqa: E402

EXACT_MARK = "by the system over its parameters, exact at the corners"
EXACT_MARK_MLIN = "multilinear, exact at the corners"     # ZTL's _mlin_eq step (gap Z2, 2026-10-09)


def ztl_commit() -> str:
    try:
        return subprocess.run(["git", "-C", ZTL_DIR, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _f(x: F) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def sheet(fixed: dict, boxes: dict, derived, grounds: dict):
    """ZFL quantity text. fixed: name -> exact value; boxes: name -> (lo, hi)."""
    parts = []
    for n, v in fixed.items():
        g = grounds.get(n)
        # the ground is a free text in the brick ("datasheet p.3 (rev/2)"); ZTL's sheet reads it as
        # one token, and a "/" or "(" there was read as a UNIT (blind test, 2026-10-10) — so a token
        parts.append(f"{n}={_f(v)} " + (f"earned:{re.sub(r'[^A-Za-z0-9_.-]+', '_', g).strip('_') or 'ground'}" if g else "credit"))
    for n, (lo, hi) in boxes.items():
        parts.append(f"{n}=[{_f(lo)},{_f(hi)}] credit")      # a tolerance is the datasheet's word
    parts += [f"{n}=? credit" for n in derived]
    return ", ".join(parts)


def judge(laws, fixed, boxes, derived, grounds):
    """{name: (lo, hi, exact)} for every derived quantity ZTL narrowed, plus its log."""
    if not laws:                    # every law a definition (2026-10-10): nothing for the linear judge
        return {}, [], None
    claim = " & ".join(f"({law})" for law in laws)
    try:
        r = solve_claim(claim, *parse_quantities(sheet(fixed, boxes, derived, grounds)))
    except ValueError as e:
        # a law left to ZTL names a quantity that has no range yet (blind test 6, c03: a stalled pack's sqrt of a
        # negative number left Vt unbounded, the laws using Vt came here and ZTL's reader stopped on 'Vt' — a STAND
        # ERROR): nothing is narrowed, said in the log; the stand then treats those quantities as unbounded
        return {}, [f"ZTL could not read these laws: {e}"], None
    log = r.get("log") or []
    lines = log if isinstance(log, list) else [str(log)]
    partial = any("exact over the linear rows only" in l for l in lines)
    out = {}
    for n in derived:
        q = r["narrowed"].get(n) or {}
        lo, hi = q.get("lo"), q.get("hi")
        if lo is None or hi is None or abs(float(lo)) == float("inf") or abs(float(hi)) == float("inf"):
            continue            # ZTL left it unbounded: the stand says so, it does not crash (gap Z2, 2026-10-09)
        mine = [l for l in lines if l.startswith(f"{n} -> ")]
        if partial or not any(EXACT_MARK in l or EXACT_MARK_MLIN in l for l in mine):
            exact = False
        elif any("critical points" in l for l in mine):
            exact = "critical"      # exact, but an extreme may sit INSIDE the box (ZTL _solve_rank_many)
        else:
            exact = "corners"       # exact, attained at corners of the box
        out[n] = (F(lo), F(hi), exact)
    return out, lines, r.get("disposition")


def implicit(law_rhs, fixed, boxes, grounds, goal=None, tighten=0):
    """An IMPLICIT quantity's range, from ZTL (gap G6, 2026-10-10). law_rhs is the compiled
    `implicit(_root_Q, g, lo, hi)` (ustand/bricks.implicit_laws). The SEARCH for a certificate is
    zimplicit.search_certificate — outside the kernel by the decision of 2026-10-09; the kernel's
    zimplicit.check_implicit checks every statement in it. -> ((lo, hi), how, cert) or (None, why, None)."""
    import ast
    import zimplicit
    from znumjudge import _parse_arith
    call = ast.parse(law_rhs, mode="eval").body
    ph = call.args[0].id
    lo, hi = (F(ast.unparse(a).replace(" ", "")) for a in call.args[2:4])
    qs = parse_quantities(sheet(fixed, boxes, [ph], grounds))[0]
    try:
        g = _parse_arith(ast.unparse(call.args[1]), qs)
    except Exception as e:                  # ZTL's reader refused the law: said, not crashed
        return None, f"ZTL could not read the implicit law: {e}", None
    from .stopflag import interruptible
    with interruptible():                   # a stop from outside ends ZTL's search at once (stopflag.py)
        cert = zimplicit.search_certificate(g, ph, qs, [str(lo), str(hi)], goal=goal, tighten=tighten)
    if cert is None:
        return None, "the search found no certificate within its piece limit", None
    res = zimplicit.check_implicit(g, ph, qs, cert)
    if not res[0]:
        return None, f"ZTL refused the certificate: {res[1]}", None
    if res[1] is None:
        # the range said (blind test 4, c10: read as a property of the design when the range was too narrow)
        return None, (f"no root in the search range [{float(lo):g}, {float(hi):g}] for any value of the box — "
                      "widen `search` if a root may lie outside it"), None
    return res[1], res[2], cert

