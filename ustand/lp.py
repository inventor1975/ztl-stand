"""CONTINUOUS CHOICES — a slot that takes any amount in a range, and an optimum ZTL can check.

Blind test 3 (c06 concrete, c12 feed): the authors chose amounts with an LP outside the stand; the stand only
verified their candidates, and "no cheaper mix exists" rested on that LP. Approved by the curator 2026-10-10.

    "catalog": {"maize": {"continuous": {"field": "x", "from": "45", "to": "70", "unit": ""}}}

When every requirement's quantity and the objective are AFFINE in the continuous choices (with coefficients
from given and catalog quantities, toleranced or not), per combination of the discrete slots:
  1. ZTL's kernel derives each coefficient from the laws itself and checks affinity (zlp.affine);
  2. an LP solver (scipy, outside, untrusted) finds the cheapest mix of the ROBUST problem (every requirement
     for every value of the box; amounts >= 0, so a ">=" row takes the lower end of each coefficient);
  3. that mix, rationalised, is judged by the ordinary stand — EARNED or not, with the usual proofs;
  4. the solver's multipliers go to ZTL's zlp.lower_bound, which proves: no mix in the box costs less than L;
  5. where the robust LP finds no mix, a phase-1 LP's multipliers go to zlp.infeasible (Farkas): proved, no mix
     in the box meets the requirements — that combination is REFUTED, not left open (2026-10-10).
The answer: the mix, its cost C, the proved bound L and the gap C - L. Modes: each mode's rows over its own box,
in one LP (2026-10-10). Version 1: amounts >= 0;
explicit laws; numeric requirement bounds; a nominal objective.
"""
from __future__ import annotations

import ast
import re
import copy
import itertools
from fractions import Fraction as F

from . import bricks as B
from . import certify as K
from . import forward as W
from . import judge_ztl as J
from . import units as U

import zlp                                  # noqa: E402  (ZTL is on the path through judge_ztl)
from znumjudge import _parse_arith, parse_quantities   # noqa: E402


def _scale(unit):
    return U.parse(unit)[0] if unit else F(1)


def continuous_slots(b):
    out = {}
    for s, spec in (b.get("slots") or {}).items():
        cats = [c for c in spec["from"] if "continuous" in b["catalog"][c]]
        if cats:
            if len(spec["from"]) != 1:
                raise B.BrickError(f"slot {s}: a continuous catalog stands alone in its slot")
            out[s] = cats[0]
    return out


def _pinned(b, values):
    """The brick with each continuous slot reduced to one listed item at its chosen amount."""
    out = copy.deepcopy(b)
    for s, (cat, fld, v) in values.items():
        spec = b["catalog"][cat]["continuous"]
        name = f"__mix_{s}"
        out["catalog"][name] = {"items": [{fld: f"{v.numerator}/{v.denominator}"}],
                                "fields": {fld: {"unit": spec.get("unit", "")}}}
        out["slots"][s] = {"from": [name]}
    return out


def _hard_points(cert_cons, qs_con, xs, at, fast=False):
    """Each constraint read at ONE point of its box — the end of each parameter that makes it hardest at the mix
    `at` (search side; the kernel checks the point lies in the box, and any point keeps the certificate sound)."""
    import zcertify as ZC
    pts = []
    at_mix = {n: (v, v) for n, v in at.items()}
    for i, (node, op, _b) in enumerate(cert_cons):
        qs = zlp._qs_for(qs_con, i)
        pt = {}
        for pname in sorted(ZC._names(node)):
            if pname in xs or pname not in qs or qs[pname]["lo"] == qs[pname]["hi"]:
                continue
            lo_p, hi_p = qs[pname]["lo"], qs[pname]["hi"]
            plain = {"cases": False, "affine": False} if fast else {}
            r_lo = ZC._reading(node, qs, dict(at_mix, **{pname: (lo_p, lo_p)}), **plain)
            r_hi = ZC._reading(node, qs, dict(at_mix, **{pname: (hi_p, hi_p)}), **plain)
            if r_lo is None or r_hi is None:
                continue
            if op == ">=":
                pt[pname] = lo_p if r_lo[1] <= r_hi[1] else hi_p
            else:
                pt[pname] = hi_p if r_hi[0] >= r_lo[0] else lo_p
        pts.append(pt)
    return pts


def _hard_points_f(cert_cons, qs_con, xs, at, texts):
    """_hard_points in FLOATS (2026-10-20, c11: the exact readings choosing these points were 358 of 848 s under a
    profile). The same choice — each parameter at the end that makes its row hardest at the mix, the others at their
    middle — read by the row's float text; a row the floats cannot read falls back to the exact choice. Search side:
    any point of the box keeps a certificate sound (the kernel checks the point lies in the box)."""
    import zcertify as ZC
    pts = []
    atf = {n: float(v) for n, v in at.items()}
    for i, (node, op, _b) in enumerate(cert_cons):
        qs = zlp._qs_for(qs_con, i)
        f = _float_fn(texts[i], qs) if texts and texts[i] is not None else None
        pt, fell = {}, f is None
        for pname in sorted(ZC._names(node)):
            if fell:
                break
            if pname in xs or pname not in qs or qs[pname]["lo"] == qs[pname]["hi"]:
                continue
            lo_p, hi_p = qs[pname]["lo"], qs[pname]["hi"]
            v_lo, v_hi = f(dict(atf, **{pname: float(lo_p)})), f(dict(atf, **{pname: float(hi_p)}))
            if v_lo is None or v_hi is None:
                fell = True
                break
            pt[pname] = (lo_p if v_lo <= v_hi else hi_p) if op == ">=" else (hi_p if v_hi >= v_lo else lo_p)
        if fell:
            pt = _hard_points([(node, op, _b)], [qs], xs, at)[0]
        pts.append(pt)
    return pts


def _no_mix(cert_rows, cert_cons, qs_con, xs, names):
    """The robust LP found no mix: try to PROVE none exists. Phase 1 (solver, outside): min t with every robust
    row relaxed by t; t* > 0 and its multipliers (sum 1) are a Farkas certificate the kernel checks
    (zlp.infeasible). Returns (True, M) — proved, M < 0 the box-maximum of sum y*h — or (False, why)."""
    from scipy.optimize import linprog
    A = [row + [-1.0] for row, _ in cert_rows]
    b = [rhs for _, rhs in cert_rows]
    res = linprog([0.0] * len(names) + [1.0], A_ub=A, b_ub=b,
                  bounds=[(float(xs[n][0]), float(xs[n][1])) for n in names] + [(None, None)], method="highs")
    if not res.success or res.fun <= 1e-9:
        return False, "phase 1 found no violation to certify"
    ys = [F(str(round(max(0.0, -float(m)), 12))).limit_denominator(10 ** 12) for m in res.ineqlin.marginals]
    at = {n: min(max(F(str(round(float(v), 9))).limit_denominator(10 ** 7), xs[n][0]), xs[n][1])
          for n, v in zip(names, res.x)}
    ok, M = zlp.infeasible(cert_cons, qs_con, xs, ys, _hard_points(cert_cons, qs_con, xs, at))
    if not ok:
        ok, M = zlp.infeasible(cert_cons, qs_con, xs, ys)
    return ok, M, ys


def _core_of(entry, rowreq, parts):
    """A combination proved to have no mix: the requirements its proof uses (indices into the part's requirements) —
    only with ONE part (no modes: a mode's rows would need the mode named too)."""
    rows = entry.pop("none_rows", None)
    if rows is not None and "none" in entry and len(parts) == 1:
        entry["none_reqs"] = sorted({rowreq[i] for i in rows})
    return entry


def _tree_rows(tree):
    """Every row a zmin tree's failing leaves name (the fallback core: their union)."""
    out = set()
    if isinstance(tree, dict):
        if tree.get("leaf") == "fails" and isinstance(tree.get("row"), int):
            out.add(tree["row"])
        for v in tree.values():
            out |= _tree_rows(v)
    elif isinstance(tree, (list, tuple)):
        for v in tree:
            out |= _tree_rows(v)
    return out


def _rows(bm, design, reqs_given, laws, qscale, frame):
    """One part's requirements (the brick's, or one mode's) as [(text, op, bound)] over its own box, and that
    box; None when a derived quantity is not explicit (not this path)."""
    fixed, boxes, derived, grounds = frame(bm, design)
    linear, defs = W.split(laws, derived)
    explicit = dict(W.explicit(linear, set(derived)), **defs)
    qs_part = parse_quantities(J.sheet(fixed, boxes, [], grounds))[0]
    rows = []
    for j_req, r in enumerate(reqs_given):
        q = r["quantity"]
        text, left = K.expression(q, explicit, set(derived)) if q in explicit else (q, {q})
        node = None
        if left:
            # LINEAR UNKNOWNS (c06, 2026-10-12): the requirement leans on quantities a linear SYSTEM fixes. The
            # search reads the stand's own solution (sympy, untrusted); the KERNEL's node is ZTL's own Cramer solution
            # of the same laws (zcertify.solve_system) — what zmin and zlp read is the kernel's, not the stand's
            got = _system_row(text, left, explicit, linear, derived, qs_part)
            if got is None:
                return None
            text, node = got
        sc = qscale[q]
        vals = r["value"] if isinstance(r["value"], list) else [r["value"]]
        nums = []
        for v in vals:
            try:
                nums.append(B.num(v) * sc)
                continue
            except (ValueError, ZeroDivisionError, TypeError):
                pass
            # a bound with NAMES (real round 4, k03: a part's own limit DEV.Tc): an expression in SI, read at this
            # combination's EXACT values — a name that is toleranced, derived or an amount is still refused
            try:
                btext = B.compile_expr(v, bm.get("define"))
                names = {n.id for n in ast.walk(ast.parse(btext, mode="eval")) if isinstance(n, ast.Name)}
                if not names <= set(fixed):
                    raise ValueError(sorted(names - set(fixed)))
                nums.append(F(eval(compile(btext, "<bound>", "eval"), {"__builtins__": {}},
                                   {n: fixed[n] for n in names})))
            except (ValueError, ZeroDivisionError, TypeError, SyntaxError, KeyError) as e:
                raise B.BrickError(f"requirement on {q}: in continuous choices a bound is a number or an expression "
                                   f"of exact values of the combination (version 1): {v!r} ({e})")
        if r["op"] == "within" and nums[0] == nums[1]:
            rows.append((text, "==", nums[0], node, j_req))       # an equality (a batch that sums to 100 %)
        elif r["op"] == "within":
            rows += [(text, ">=", nums[0], node, j_req), (text, "<=", nums[1], node, j_req)]
        elif r["op"] in (">=", ">"):
            rows.append((text, ">=", nums[0], node, j_req))
        else:
            rows.append((text, "<=", nums[0], node, j_req))
    return rows, qs_part


def _system_row(text, left, explicit, linear, derived, qs):
    """(search text, kernel node) for a requirement whose expression keeps linear unknowns, or None."""
    import zcertify as ZC
    core_u = sorted(u for u in derived if u not in explicit)
    if not set(left) <= set(core_u):
        return None
    core_laws = []
    for law in linear:
        l, rr = law.split("==")
        if l.strip() in explicit and l.strip() not in rr:
            continue                    # it IS an explicit definition
        lt, _ = K.expression("_lhs", dict(explicit, _lhs=ast.parse(l.strip(), mode="eval").body), set(derived))
        rt, _ = K.expression("_rhs", dict(explicit, _rhs=ast.parse(rr.strip(), mode="eval").body), set(derived))
        core_laws.append(f"{lt} == {rt}")
    # only the CONNECTED part of the system the requirement leans on (c06: two impurities, two independent 3x3
    # systems — one 6x6 made Cramer's expressions too large to read fast; a block's solution is the same)
    names_of = [set(re.findall(r"[A-Za-z_]\w*", l)) & set(core_u) for l in core_laws]
    need, laws_in = set(left), set()
    grew = True
    while grew:
        grew = False
        for i, ns in enumerate(names_of):
            if i not in laws_in and ns & need:
                laws_in.add(i)
                if not ns <= need:
                    need |= ns
                grew = True
    core_laws = [core_laws[i] for i in sorted(laws_in)]
    core_u = sorted(need)
    # the unknowns are names to the reader only while parsing: the kernel's solution replaces every one of them
    proto = next(iter(qs.values()))
    qs_u = dict(qs, **{u: dict(proto, lo=F(0), hi=F(0)) for u in core_u if u not in qs})
    try:
        sol_k = ZC.solve_system(core_laws, core_u, qs_u)            # the KERNEL's own solution (Cramer)
        node = ZC._subst(_parse_arith(text, qs_u), sol_k)
    except (ZC.SystemError_, ValueError, KeyError):
        return None
    if ZC._names(node) & set(core_u):
        return None
    sol = K.solve_linear(core_laws, core_u)                         # the search's (sympy)
    if sol is None or set(left) - set(sol):
        return None
    for u, t in sol.items():
        text = re.sub(rf"\b{re.escape(u)}\b", f"({t})", text)
    return K.simplify(text), node


def _design_brick(b, design, cont):
    """The brick with this combination's DISCRETE slots pinned, the continuous catalogs kept (blind test 6, c10,
    2026-10-12: only the continuous slots were pinned, so a mix found for one combination was judged over EVERY
    discrete design and the first that passed — another combination — lent its EARNED to this one: a false EARNED,
    DR6 without a fan at 44.02 kEUR where only DR8 at 51.669 holds)."""
    from .stand import _pinned as _pin_design
    out = _pin_design(b, {s: d for s, d in design.items() if s not in cont})
    for s, cat in cont.items():
        out["catalog"][cat] = b["catalog"][cat]
    return out


def _make_mix_of(b, names, xs, xnames, eqs, run_plain):
    """mix_of(res): the solver's amounts (res.x) rationalised, the equalities made exact again, judged by the
    ordinary stand over the whole box -> (xstar, values, verdict). `b` must have its discrete slots PINNED to the
    combination the mix is for (_design_brick)."""
    def mix_of(res):
        xstar = {}
        for n, v in zip(names, res.x):
            lo, hi = xs[n]
            fv = F(str(round(float(v), 9))).limit_denominator(10 ** 7)
            xstar[n] = min(max(fv, lo), hi)
        # equalities made EXACT again after the rounding: one variable per equality absorbs the residue
        used = set()
        for _n, (c_, k_), b_ in eqs:
            resid = b_ - c_[0] - sum(k_[n][0] * xstar[n] for n in names)
            for n in sorted(names, key=lambda m: -(xs[m][1] - xs[m][0])):
                a = k_[n][0]
                if a != 0 and n not in used:
                    v = xstar[n] + resid / a
                    if xs[n][0] <= v <= xs[n][1]:
                        xstar[n] = v
                        used.add(n)
                        break
        values = {xnames[n][0]: (xnames[n][1], xnames[n][2], xstar[n] / xnames[n][3]) for n in names}
        return xstar, values, run_plain(_pinned(b, values))
    return mix_of


def run_continuous(b, parts, run_plain):
    """parts: [(brick, its requirements, its laws)] — the brick itself, or one per MODE (each mode its own box of
    data and its own requirements; every mode's rows go into ONE LP, each row certified over its own box)."""
    from .stand import frame, designs, _s, _label, _design_out
    if not b.get("objective") or (b["objective"].get("case") == "worst"):
        raise B.BrickError("continuous choices need a nominal objective (the cheapest mix)")
    cont = continuous_slots(b)
    xs, xnames = {}, {}
    for s, cat in cont.items():
        spec = b["catalog"][cat]["continuous"]
        sc = _scale(spec.get("unit"))
        lo, hi = B.num(spec["from"]) * sc, B.num(spec["to"]) * sc
        if lo < 0 or lo > hi:
            raise B.BrickError(f"slot {s}: a continuous range must lie at or above 0 (version 1), low below high")
        name = B.ident(f"{s}.{spec['field']}")
        xs[name] = (lo, hi)
        xnames[name] = (s, cat, spec["field"], sc)
    qscale = {n: _scale(q.get("unit")) for n, q in b["quantities"].items()}
    obj_text = B.compile_expr(b["objective"]["minimize"], b.get("define"))
    base_laws = B.implicit_laws(b, [B.compile_expr(l["zfl"], b.get("define")) for l in b["laws"]])
    results = []
    # EXISTENCE ONLY (2026-10-18): a conflict-search subset asks only "is there a mix?" — no bound is proved and the
    # first EARNED combination ends the search (c07: {R2, R4} was 637 of 640 s proving a bound nobody reads)
    exist_only = bool(b.get("_existence_only"))
    search_only = bool(b.get("_search_only"))
    if exist_only and not search_only:
        # SEARCH FIRST (2026-10-18, c07 {R2, R4}: 635 s proving O80 has no mix — unproved — before O100 gave one at
        # once): every combination's mix searched, no proof; a proof only when no combination yields a mix
        first = run_continuous(dict(b, _search_only=True), parts, run_plain)
        if first is None or any(e.get("verdict", {}).get("verdict") == "EARNED" for e in first):
            return first
    for design in designs(b):
        if exist_only and any(e.get("verdict", {}).get("verdict") == "EARNED" for e in results):
            break
        # the objective: the brick's own (nominal) values, its own laws
        fixed, boxes, derived, grounds = frame(b, design)
        linear, defs = W.split(base_laws, derived)
        explicit = dict(W.explicit(linear, set(derived)), **defs)
        names_obj = {n.id for n in ast.walk(ast.parse(obj_text, mode="eval").body) if isinstance(n, ast.Name)}
        otext = obj_text
        if names_obj & set(derived):
            for d_ in sorted(names_obj & set(derived)):
                t, left = K.expression(d_, explicit, set(derived))
                if left:
                    return None
                otext = otext.replace(d_, f"({t})")
        nominal_fixed = dict(fixed, **{n: (lo + hi) / 2 for n, (lo, hi) in boxes.items() if n not in xs})
        qs_obj = parse_quantities(J.sheet(nominal_fixed, {n: xs[n] for n in xs}, [], grounds))[0]
        allc, qrow, alltext, rowreq = [], [], [], []
        try:
            obj_node = _parse_arith(otext, qs_obj)
            for bm, reqs_m, laws_m in parts:
                got = _rows(bm, design, reqs_m, laws_m, qscale, frame)
                if got is None:
                    return None
                rows_m, qs_m = got
                allc += [(nd if nd is not None else _parse_arith(t, qs_m), op, bnd) for t, op, bnd, nd, _j in rows_m]
                qrow += [qs_m] * len(rows_m)
                alltext += [t for t, _op, _bnd, _nd, _j in rows_m]
                rowreq += [_j for _t, _op, _bnd, _nd, _j in rows_m]
        except B.BrickError:
            raise
        except (ValueError, KeyError) as e:
            raise B.BrickError(f"continuous choices: a requirement or the objective is unreadable: {e}")
        try:
            c0, cx = zlp.affine(obj_node, xs, qs_obj)
            alla = [zlp.affine(n, xs, q_) for (n, _, _), q_ in zip(allc, qrow)]
        except zlp.NotAffine:
            # J3 (2026-10-12, the curator's "да"): NOT affine in the amounts — the nonlinear path
            names = sorted(xs)
            eqs = []
            for (n_, op, b_), q_ in zip(allc, qrow):
                if op != "==":
                    continue
                try:
                    a_ = zlp.affine(n_, xs, q_)
                except zlp.NotAffine as e:
                    raise B.BrickError(f"continuous choices: an equality must be affine in the amounts (version 1): "
                                       f"{e}")
                if a_[0][0] != a_[0][1] or any(v[0] != v[1] for v in a_[1].values()):
                    raise B.BrickError("an equality with uncertain coefficients cannot hold for every value of "
                                       "the box")
                eqs.append((n_, a_, b_))
            entry = {"design": design, "label": _label({k: v for k, v in design.items() if k not in cont})}
            mix_of = _make_mix_of(_design_brick(b, design, cont), names, xs, xnames, eqs, run_plain)
            inc = min((e["cost"] for e in results if e.get("verdict", {}).get("verdict") == "EARNED"
                       and e.get("cost") is not None), default=None)
            entry.update(_nonlinear(allc, qrow, alltext, xs, names, obj_node, qs_obj, otext, mix_of, qscale, inc,
                                    exist_only, search_only))
            results.append(_core_of(entry, rowreq, parts))
            continue
        names = sorted(xs)
        eqs = [(n_, a_, b_) for (n_, op, b_), a_ in zip(allc, alla) if op == "=="]
        q_ineq = [q_ for (n_, op, b_), q_ in zip(allc, qrow) if op != "=="]
        t_ineq = [t_ for t_, (n_, op, b_) in zip(alltext, allc) if op != "=="]      # float texts, search side
        t_eq = [t_ for t_, (n_, op, b_) in zip(alltext, allc) if op == "=="]
        q_eq = [q_ for (n_, op, b_), q_ in zip(allc, qrow) if op == "=="]
        qs_con = q_ineq + q_eq + q_eq            # one box per certificate row, in cert_cons order
        for _n, (c_, k_), _b in eqs:
            if c_[0] != c_[1] or any(v[0] != v[1] for v in k_.values()):
                raise B.BrickError("an equality with uncertain coefficients cannot hold for every value of the box")
        cons = [(n_, op, b_) for n_, op, b_ in allc if op != "=="]
        aff = [a_ for (n_, op, b_), a_ in zip(allc, alla) if op != "=="]
        # an equality is two inequalities for the CERTIFICATE (each with its own multiplier)
        cert_cons = list(cons) + [(n_, ">=", b_) for n_, _a, b_ in eqs] + [(n_, "<=", b_) for n_, _a, b_ in eqs]
        # the robust LP (search side): amounts >= 0, so a ">=" row uses each coefficient's lower end
        A, ub = [], []
        for (const, coefs), (_, op, bnd) in zip(aff, cons):
            if op == ">=":
                A.append([-float(coefs[n][0]) for n in names]); ub.append(-float(bnd - const[0]))
            else:
                A.append([float(coefs[n][1]) for n in names]); ub.append(float(bnd - const[1]))
        Aeq = [[float(k_[n][0]) for n in names] for _n, (c_, k_), _b in eqs]
        beq = [float(b_ - c_[0]) for _n, (c_, k_), b_ in eqs]
        from scipy.optimize import linprog
        cvec = [float((cx[n][0] + cx[n][1]) / 2) for n in names]
        # a hair inside, so the rounded mix stays feasible — scaled by the row's size (blind test 4, c12, 2026-10-11:
        # a binding R2 margin at the LP vertex came out -1.7e-7 after rounding the mix; a fixed 1e-7 was too thin)
        rownorm = [sum(abs(a) * float(xs[n][1] - xs[n][0]) for a, n in zip(row, names)) for row in A]

        def solve(fac):
            slack = [fac * 1e-7 * max(1.0, abs(v), rn) for v, rn in zip(ub, rownorm)]
            return linprog(cvec, A_ub=A or None, b_ub=[u - e for u, e in zip(ub, slack)] or None,
                           A_eq=Aeq or None, b_eq=beq or None,
                           bounds=[(float(xs[n][0]), float(xs[n][1])) for n in names], method="highs")

        mix_of = _make_mix_of(_design_brick(b, design, cont), names, xs, xnames, eqs, run_plain)

        res = solve(1.0)
        entry = {"design": design, "label": _label({k: v for k, v in design.items() if k not in cont})}
        if not res.success:
            # SCENARIO CUTS first (2026-10-12, blind test 5 c11): the box LP takes each coefficient's worst case on
            # its own; when the coefficients share an uncertain parameter (one spot rate in three of them) that
            # relaxation-in-reverse finds NO mix although one exists. The robust problem relaxed to finitely many
            # data points is a true relaxation: its optimum is a lower bound, its infeasibility a proof.
            sc_entry = _scenario_cuts(b, cons, q_ineq, eqs, q_eq, Aeq, beq, xs, names, cvec, obj_node, qs_obj,
                                      mix_of, xnames, qscale, t_ineq)
            if sc_entry is not None:
                entry.update(sc_entry)
                results.append(_core_of(entry, rowreq, parts))
                continue
            # the certificate's rows, robust, in cert_cons order (an equality: its two halves)
            rows_c = [(list(r_), u_) for r_, u_ in zip(A, ub)]
            rows_c += [([-v for v in r_], -u_) for r_, u_ in zip(Aeq, beq)] + [(list(r_), u_) for r_, u_ in zip(Aeq, beq)]
            okN, M, ysN = _no_mix(rows_c, cert_cons, qs_con, xs, names)
            if okN:
                # the core: the rows with a nonzero multiplier, back to their requirements (cert_cons order)
                cmap = [i for i, (_n, op, _b) in enumerate(allc) if op != "=="]
                cmap += [i for i, (_n, op, _b) in enumerate(allc) if op == "=="] * 2
                entry["none_rows"] = sorted({cmap[k] for k, y in enumerate(ysN) if y != 0})
                entry["none"] = (f"proved by ZTL (zlp, Farkas): no mix in the box meets every requirement for every "
                                 f"value of the data — the weighted sum of the requirements' margins is at most "
                                 f"{float(M):.6g} < 0 over the whole box")
            else:
                entry["lp"] = ("the robust LP found no mix (it is conservative: this is not a proof that none "
                               f"exists; ZTL's Farkas check: {M})")
            results.append(_core_of(entry, rowreq, parts))
            continue
        xstar, values, verdict = mix_of(res)
        # the mix missed (a tight vertex and the rounding): retry a little further inside — search side only
        for fac in (1e2, 1e4):
            if verdict.get("verdict") == "EARNED":
                break
            res2 = solve(fac)
            if not res2.success:
                break
            x2, v2, d2 = mix_of(res2)
            res, xstar, values, verdict = res2, x2, v2, d2
        ys = [F(str(round(max(0.0, -float(m)), 12))).limit_denominator(10 ** 12)
              for m in (res.ineqlin.marginals if cons else [])]
        em = list(res.eqlin.marginals) if eqs else []
        # an equality's multiplier m: m > 0 on its ">=" half, -m on its "<=" half (scipy: d cost / d b_eq)
        ys += [F(str(round(max(0.0, float(m)), 12))).limit_denominator(10 ** 12) for m in em]
        ys += [F(str(round(max(0.0, -float(m)), 12))).limit_denominator(10 ** 12) for m in em]
        okL, L = zlp.lower_bound(obj_node, qs_obj, cert_cons, qs_con, xs, ys)
        # a sharper bound: each constraint read at ONE point of its box — the end of each parameter that makes
        # it hardest at the mix found (search side; the kernel checks the point lies in the box, and any point
        # gives a sound bound). The better of the two proved bounds is kept.
        pts = _hard_points_f(cert_cons, qs_con, xs, xstar, t_ineq + t_eq + t_eq)
        okP, LP_ = zlp.lower_bound(obj_node, qs_obj, cert_cons, qs_con, xs, ys, pts)
        if okP and (not okL or LP_ > L):
            okL, L = True, LP_
        cost = c0[0] + sum(((cx[n][0] + cx[n][1]) / 2) * xstar[n] for n in names)
        entry.update(values=values, verdict=verdict, cost=cost, L=L if okL else None,
                     L_why=None if okL else L)
        results.append(_core_of(entry, rowreq, parts))
    return results

SCENARIO_ROUNDS = 40


def _row_params(node, q, xs):
    import zcertify as ZC
    return sorted(n for n in ZC._names(node) if n in q and n not in xs and q[n]["lo"] != q[n]["hi"])


def _worst_point(node, op, q, xs, xstar, start, fval=None):
    """The data point where the row is hardest at the mix — SEARCH side, trusted for nothing (any point of the box
    is a sound scenario): coordinate sweeps over a grid of each parameter, then golden-section refinement around the
    best (the worst of a row with a min/max often sits at a kink inside the box: c11's 1/min(S, K)).
    fval: the row as a FLOAT function (2026-10-13, speed-up lever 2, the curator's "да": "deterministic anyway, just
    less precise"). The exact reading cost c10 ~40 % of its time (exp / ln brackets in rationals) for a point nothing
    trusts; a float point is as sound a scenario. Used when it evaluates at the start point, else the exact reading."""
    import zcertify as ZC
    ps = _row_params(node, q, xs)
    if not ps:
        return None
    mix = {n: (v, v) for n, v in xstar.items()}
    mixf = {n: float(v) for n, v in xstar.items()}

    def val_exact(pt):
        r = ZC._reading(node, q, dict(mix, **{p: (v, v) for p, v in pt.items()}), cases=False, affine=False)
        if r is None:
            return None
        v = (r[0] + r[1]) / 2
        return v if op == ">=" else -v              # minimise: the row's margin

    def val_float(pt):
        try:
            v = fval(dict(mixf, **{p: float(c) for p, c in pt.items()}))
        except Exception:                           # noqa: BLE001 — a name the float text lacks: fall back
            return None
        if v is None:
            return None
        return v if op == ">=" else -v
    pt = {p: start.get(p, (q[p]["lo"] + q[p]["hi"]) / 2) for p in ps}
    val = val_float if fval is not None and val_float(pt) is not None else val_exact
    best = val(pt)
    if best is None:
        return None
    for _ in range(3):
        for p in ps:
            lo, hi = q[p]["lo"], q[p]["hi"]
            for k in range(33):
                c = lo + (hi - lo) * F(k, 32)
                v = val(dict(pt, **{p: c}))
                if v is not None and v < best:
                    best, pt = v, dict(pt, **{p: c})
            fa, fb = float(max(lo, pt[p] - (hi - lo) / 32)), float(min(hi, pt[p] + (hi - lo) / 32))
            g = 0.6180339887498949
            for _ in range(40):
                c1, c2 = fb - g * (fb - fa), fa + g * (fb - fa)
                v1 = val(dict(pt, **{p: F(c1).limit_denominator(10 ** 9)}))
                v2 = val(dict(pt, **{p: F(c2).limit_denominator(10 ** 9)}))
                if v1 is None or v2 is None:
                    break
                if v1 < v2:
                    fb = c2
                else:
                    fa = c1
            c = min(max(F((fa + fb) / 2).limit_denominator(10 ** 9), lo), hi)
            v = val(dict(pt, **{p: c}))
            if v is not None and v < best:
                best, pt = v, dict(pt, **{p: c})
    return pt


def _scenario_cuts(b, cons, q_ineq, eqs, q_eq, Aeq, beq, xs, names, cvec, obj_node, qs_obj, mix_of, xnames, qscale,
                   texts=None):
    """THE ROBUST LP BY SCENARIO CUTS (Kelley). Every inequality row is read at finitely many data points (its
    coefficients then exact, by the kernel: zlp.affine at the point); the LP over them is a RELAXATION of the robust
    problem. Its mix is judged by the ordinary stand over the WHOLE box: EARNED — done, and the relaxation's
    multipliers give ZTL a lower bound (zlp.lower_bound with the points: each requirement holds at each of its
    points); refuted or open — the failing point and the rows' hardest corners at the mix are added, and again.
    An infeasible relaxation is a Farkas proof that no mix exists (zlp.infeasible with the points).
    -> an entry for run_continuous, or None when it decides nothing."""
    from scipy.optimize import linprog
    scen = []                      # [(row index, point)]
    seen = set()

    def add(i, pt):
        key = (i, tuple(sorted(pt.items())))
        if key in seen:
            return False
        seen.add(key)
        scen.append((i, dict(pt)))
        return True
    for i, (node, op, bnd) in enumerate(cons):
        q = q_ineq[i]
        add(i, {p: (q[p]["lo"] + q[p]["hi"]) / 2 for p in _row_params(node, q, xs)})
    from .stopflag import check as _stop_check
    for rnd in range(SCENARIO_ROUNDS):
        _stop_check()
        A, ub = [], []
        for i, pt in scen:
            node, op, bnd = cons[i]
            c, k = zlp.affine(node, xs, q_ineq[i], {p: (v, v) for p, v in pt.items()})
            if op == ">=":
                A.append([-float(k[n][0]) for n in names]); ub.append(-float(bnd - c[0]))
            else:
                A.append([float(k[n][1]) for n in names]); ub.append(float(bnd - c[1]))
        rownorm = [sum(abs(a) * float(xs[n][1] - xs[n][0]) for a, n in zip(row, names)) for row in A]

        def solve(fac):
            slack = [fac * 1e-7 * max(1.0, abs(v), rn) for v, rn in zip(ub, rownorm)]
            return linprog(cvec, A_ub=A or None, b_ub=[u - e for u, e in zip(ub, slack)] or None,
                           A_eq=Aeq or None, b_eq=beq or None,
                           bounds=[(float(xs[n][0]), float(xs[n][1])) for n in names], method="highs")
        rows = [cons[i] for i, _ in scen]
        qs_rows = [q_ineq[i] for i, _ in scen]
        pts = [pt for _, pt in scen]
        res = solve(1.0)
        if not res.success:
            # phase 1 on the relaxation: a Farkas certificate, checked by the kernel at the same points
            Ap = [row + [-1.0] for row in A]
            r1 = linprog([0.0] * len(names) + [1.0], A_ub=Ap or None, b_ub=ub or None,
                         bounds=[(float(xs[n][0]), float(xs[n][1])) for n in names] + [(None, None)], method="highs")
            if r1.success and r1.fun > 1e-9:
                ys = [F(str(round(max(0.0, -float(m)), 12))).limit_denominator(10 ** 12) for m in r1.ineqlin.marginals]
                ok, M = zlp.infeasible(rows, qs_rows, xs, ys, pts)
                if ok:
                    return {"none": (f"proved by ZTL (zlp, Farkas, scenario cuts): the requirements read at "
                                     f"{len(scen)} data points of the box already admit no mix — the weighted sum "
                                     f"of their margins is at most {float(M):.6g} < 0"), "scenarios": len(scen)}
            return None
        xstar, values, verdict = mix_of(res)
        for fac in (1e2, 1e4, 1e5):
            if verdict.get("verdict") == "EARNED":
                break
            res2 = solve(fac)
            if not res2.success:
                break
            x2, v2, d2 = mix_of(res2)
            res, xstar, values, verdict = res2, x2, v2, d2
        if verdict.get("verdict") == "EARNED":
            ys = [F(str(round(max(0.0, -float(m)), 12))).limit_denominator(10 ** 12) for m in res.ineqlin.marginals]
            cert_rows, cert_qs, cert_pts = list(rows), list(qs_rows), list(pts)
            em = list(res.eqlin.marginals) if eqs else []
            for (n_, (c_, k_), b_), m, qe in zip(eqs, em, q_eq):
                cert_rows += [(n_, ">=", b_), (n_, "<=", b_)]
                cert_qs += [qe, qe]
                cert_pts += [None, None]
                ys += [F(str(round(max(0.0, float(m)), 12))).limit_denominator(10 ** 12),
                       F(str(round(max(0.0, -float(m)), 12))).limit_denominator(10 ** 12)]
            okL, L = zlp.lower_bound(obj_node, qs_obj, cert_rows, cert_qs, xs, ys, cert_pts)
            c0, cx = zlp.affine(obj_node, xs, qs_obj)
            cost = c0[0] + sum(((cx[n][0] + cx[n][1]) / 2) * xstar[n] for n in names)
            return {"values": values, "verdict": verdict, "cost": cost, "L": L if okL else None,
                    "L_why": None if okL else L, "scenarios": len(scen),
                    "method": f"scenario cuts: {len(scen)} data points, {rnd + 1} round(s)"}
        # not earned: the failing point, and every row's hardest corner at this mix
        new = False
        pt_w = verdict.get("its_violating_point") or {}
        wpt = {}
        for k_, v_ in pt_w.items():
            try:
                n = B.ident(k_)
                wpt[n] = B.num(str(v_).split(" ")[0]) * qscale.get(n, F(1))
            except (ValueError, ZeroDivisionError):
                continue
        for i, (node, op, bnd) in enumerate(cons):
            ps = _row_params(node, q_ineq[i], xs)
            if ps and all(p in wpt for p in ps):
                pt = {p: min(max(wpt[p], q_ineq[i][p]["lo"]), q_ineq[i][p]["hi"]) for p in ps}
                new |= add(i, pt)
        hard = _hard_points_f(cons, q_ineq, xs, xstar, texts) if texts else _hard_points(cons, q_ineq, xs, xstar)
        for i, pt in enumerate(hard):
            ps = _row_params(cons[i][0], q_ineq[i], xs)
            if ps and all(p in pt for p in ps):
                new |= add(i, pt)
            wp = _worst_point(cons[i][0], cons[i][1], q_ineq[i], xs, xstar, pt,
                              _float_fn(texts[i], q_ineq[i]) if texts else None)
            if wp is not None:
                new |= add(i, wp)
        if not new:
            return None
    return None



# ── NONLINEAR AMOUNTS (J3, 2026-10-12, the curator's "да") ─────────────────────────────────────────────────────────
# A requirement or the objective NOT affine in the amounts (a purge fraction inside a ratio, a surcharge under a
# log10, a mass in an exponent). Per combination of the discrete slots:
#   1. the mix: a local solver (scipy SLSQP, outside, untrusted) over the requirements read at finitely many DATA
#      POINTS — the same scenario loop as the LP's (Kelley): the mix is judged by the ordinary stand over the WHOLE
#      box; a failing point and each row's hardest point at the mix are added, and again;
#   2. the bound: a split of the AMOUNTS' box, every piece either "the objective is >= L here" or "requirement i
#      fails here at one point of its data" — searched here, checked by ZTL (zmin.check_lower_bound, each leaf by
#      zcertify.check). No piece left: L is proved for every robust mix; every piece failing: no mix exists.
# Without the bound the mix is still EARNED, its optimality not shown (no gap).
NL_ROUNDS = 30
NL_PIECES = 20000          # the bound's SEARCH budget (outside the kernel): past it the open pieces become cost leaves
NL_PRUNE_PIECES = 400     # a combination's proof that it cannot beat the cheapest mix so far: a small budget
NL_TOL = F(1, 10 ** 5)     # a piece whose objective reads within this share of the mix's cost is closed

_FLOAT_FN = {"exp": __import__("math").exp, "ln": __import__("math").log, "log10": __import__("math").log10,
             "atan": __import__("math").atan, "tan": __import__("math").tan, "sqrt": __import__("math").sqrt,
             "sin": __import__("math").sin, "cos": __import__("math").cos,
             "pow": lambda a, c: a ** c, "min": min, "max": max, "ifpos": lambda c, a, d: a if c > 0 else d}


def _float_fn(text, qs):
    """The text as a float function of {name: value} (search side only), the other names at their box's middle."""
    code = compile(text, "<row>", "eval")
    base = {n: float((q["lo"] + q["hi"]) / 2) for n, q in qs.items()
            if not isinstance(q["lo"], float) and not isinstance(q["hi"], float)}

    def f(vals):
        try:
            v = eval(code, {"__builtins__": {}, **_FLOAT_FN}, dict(base, **vals))
            v = float(v)
            return v if v == v and abs(v) < 1e300 else None
        except (ArithmeticError, ValueError, TypeError):
            return None
    return f


def _nlp(obj_f, rows_f, scen, xs, names, eqs, starts, fac):
    """The cheapest mix over the scenario rows (search side): SLSQP from each start, the best that meets them all.
    SCALED (c06, 2026-10-12: a cost of ~1e5 against concentrations of ~1e-3 left SLSQP at the box's edge, 382 500
    where 137 804 was possible): the amounts on [0, 1], the objective by its size, each row by its bound's. With at
    most 3 amounts a grid of feasible points seeds the starts (and stands in when SLSQP finds nothing better)."""
    from scipy.optimize import minimize
    import itertools as _it
    lo = [float(xs[n][0]) for n in names]
    hi = [float(xs[n][1]) for n in names]
    span = [(c - a) or 1.0 for a, c in zip(lo, hi)]

    def unpack(u):
        return {n: a + v * w for n, a, v, w in zip(names, lo, u, span)}
    mid_u = [0.5] * len(names)
    o_mid = obj_f(unpack(mid_u))
    oscale = max(1.0, abs(o_mid)) if o_mid is not None else 1.0

    def obj(u):
        v = obj_f(unpack(u))
        return 1e30 if v is None else v / oscale
    cons = []
    probes = [mid_u, [0.0] * len(names), [1.0] * len(names)]
    for i, pt in scen:
        f, op, bnd = rows_f[i]
        bf = float(bnd)
        p_ = {k: float(v) for k, v in pt.items()}
        v_mid = f(dict(unpack(mid_u), **p_))
        # A ROW THE AMOUNTS DO NOT MOVE (2026-10-19, c07 {R2, R4}: "PL.d >= 80" for the 80 mm plate is 0.08 >= 0.08 at
        # every mix; the slack "a hair inside" below made it unmeetable, and a plate WITH robust mixes (A = 500 m^2
        # EARNED) was searched as having none): read at the centre and two corners; equal there and met, it is no
        # constraint of the search (the stand judges the mix exactly anyway); missed, it stays (the proof refutes).
        vals = [f(dict(unpack(u_), **p_)) for u_ in probes]
        if None not in vals and len(set(vals)) == 1 and ((vals[0] >= bf) if op == ">=" else (vals[0] <= bf)):
            continue
        rs = max(abs(bf), abs(v_mid) if v_mid is not None else 0.0, 1e-300)
        sl = fac * 1e-7

        def g(u, f=f, op=op, bf=bf, sl=sl, p_=p_, rs=rs):
            v = f(dict(unpack(u), **p_))
            if v is None:
                return -1e9
            return ((v - bf) if op == ">=" else (bf - v)) / rs - sl
        cons.append({"type": "ineq", "fun": g})
    for _n, (c_, k_), b_ in eqs:
        cf, kf, bf = float(c_[0]), {n: float(k_[n][0]) for n in names}, float(b_)
        es = max(1.0, abs(bf))
        cons.append({"type": "eq", "fun": lambda u, cf=cf, kf=kf, bf=bf, es=es:
                     (cf + sum(kf[n] * x for n, x in unpack(u).items()) - bf) / es})
    n_in = len(scen)

    def viol(u):
        return max([0.0] + [-c["fun"](u) for c in cons[:n_in]] + [abs(c["fun"](u)) for c in cons[n_in:]])
    starts_u = [[(x - a) / w for x, a, w in zip(z, lo, span)] for z in starts]
    best = None
    if not eqs and 1 <= len(names) <= 3:
        k = {1: 129, 2: 33, 3: 9}[len(names)]
        grid = [g_ for g_ in _it.product(*[[j / (k - 1) for j in range(k)]] * len(names))]
        feas = sorted((obj(list(u)), list(u)) for u in grid if viol(list(u)) <= 0)
        if feas:
            best = feas[0]
            starts_u = [u for _o, u in feas[:3]] + starts_u
    for u0 in starts_u:
        try:
            res = minimize(obj, u0, method="SLSQP", bounds=[(0.0, 1.0)] * len(names), constraints=cons,
                           options={"maxiter": 300, "ftol": 1e-12})
        except (ValueError, ArithmeticError):
            continue
        u = [min(max(v, 0.0), 1.0) for v in res.x]
        if viol(u) <= 1e-9 and (best is None or obj(u) < best[0]):
            best = (obj(u), u)
    if best is None:
        return None
    z = unpack(best[1])
    return [z[n] for n in names]


def _split(piece, names, width0):
    """The search's split of a piece: the widest amount (relative to the box), at a short dyadic point.
    -> (name, point, low piece, high piece) or None when nothing can be cut."""
    cut = [n for n in names if piece[n][0] < piece[n][1]]
    if not cut:
        return None
    n = max(cut, key=lambda m: (piece[m][1] - piece[m][0]) / width0[m])
    lo, hi = piece[n]
    at = K._dyadic(lo, hi)
    return n, at, dict(piece, **{n: (lo, at)}), dict(piece, **{n: (at, hi)})


SPEC_AHEAD = 2      # speculate on the descendants of the top (jobs x SPEC_AHEAD) pieces of the heap ...
SPEC_DEPTH = 1      # ... down to this many splits (children first, then grandchildren)


def _spec_worker(piece):
    from . import parallel as PAR
    return PAR.STATE["bb_value"](piece)


class _Speculation:
    """SPECULATIVE VISITS (2026-10-13, the curator's "да" to parallel continuous search; capacity bench: c06 and c10
    spend ~80 % in _bb, ~0.15-0.19 s per visit, and --jobs gave x1.0). The search loop is NOT changed: it pops,
    splits and visits in its own order, exactly as with one process. What runs in parallel is `value(piece)` — a pure
    function of the piece — for the children of the pieces at the top of the heap, computed AHEAD by worker processes
    (fork). A visit takes the worker's answer if one was started for that piece, otherwise computes it here. The
    answers are the same values the loop would compute, so the tree, the bound and the verdict are byte-identical
    for any number of jobs; a wrong guess costs only a worker's time. With JOBS == 1 nothing changes at all."""

    def __init__(self, value, names, width0):
        from . import parallel as PAR
        self.value_here, self.names, self.width0 = value, names, width0
        self.pending, self.pool, self.done = {}, None, set()
        if PAR.JOBS[0] > 1:
            import multiprocessing as mp
            PAR.STATE["bb_value"] = value
            self.pool = mp.get_context("fork").Pool(PAR.JOBS[0], initializer=PAR._init)
            self.n = PAR.JOBS[0] * SPEC_AHEAD

    @staticmethod
    def key(piece):
        return tuple(sorted(piece.items()))

    def ahead(self, heap):
        if self.pool is None:
            return
        import heapq
        level = [piece for _lb, _k, piece, _node in heapq.nsmallest(self.n, heap)]
        for _ in range(SPEC_DEPTH):
            nxt = []
            for piece in level:
                got = _split(piece, self.names, self.width0)
                if got is None:
                    continue
                for child in got[2:]:
                    kc = self.key(child)
                    if kc not in self.pending and kc not in self.done:
                        self.pending[kc] = self.pool.apply_async(_spec_worker, (child,))
                    nxt.append(child)
            level = nxt

    def value(self, piece):
        if self.pool is None:
            return self.value_here(piece)
        kp = self.key(piece)
        self.done.add(kp)                       # never speculated again once visited
        r = self.pending.pop(kp, None)
        return r.get() if r is not None else self.value_here(piece)

    def close(self):
        if self.pool is not None:
            self.pool.terminate()
            self.pool.join()
            self.pool = None


PROOF_FIRST_PIECES = 64  # the cheap proof tried before a combination's mix is searched (2026-10-19)
HC4 = [True]          # zmin's search tries a contraction where no reading fails a piece (2026-10-19)
FLOAT_SKIP_REL = 1e-9   # a row met at a sample by more than this (relative) cannot be failed by the exact reading


def _bb(obj_node, qs_obj, rows, xs, pts, C, budget, ftexts=None):
    """The bound's search: best-first over pieces of the amounts' box. -> (tree, L, counts) or None.
    rows: [(node, op, b, qs)]; pts[i]: data points tried for row i; C: the mix's cost (None: only failures close a
    piece — the search for "no mix exists")."""
    import heapq
    import zcertify as ZC
    names = sorted(xs)
    width0 = {n: (xs[n][1] - xs[n][0]) or F(1) for n in names}
    tol = None if C is None else NL_TOL * max(F(1), abs(C))

    def on(qs, piece):
        q2 = dict(qs)
        for n, (lo, hi) in piece.items():
            if n in q2:
                q2[n] = dict(q2[n], lo=lo, hi=hi)
        return q2

    def fails(piece):
        return _first_fail(piece)

    # FLOAT GUIDANCE (2026-10-18, c07: ~72 exact readings per piece, 3.6 ms each): the search reads each row in machine
    # floats first. A row MET at a point of the piece (its centre, the data point) by a clear margin cannot be failed
    # by the exact reading there — its lower end is at most that value — so the exact reading is skipped: a skip is
    # always sound (a certificate is made only of exact failures), it only saves time. The hardest data point is
    # chosen in floats too (search side: any point of the box keeps the certificate sound). Equalities: no skip.
    frows = [_float_fn(t, q_) for t, (_n, _op, _b, q_) in zip(ftexts, rows)] if ftexts else None
    fnames = [sorted(p for p in ZC._names(node) if p not in xs and p in qs and qs[p]["lo"] != qs[p]["hi"])
              for node, _op, _b, qs in rows] if frows else None

    def _met(i, op, b, at):
        if frows is None or op == "==":
            return False
        v = frows[i]({k: float(x) for k, x in at.items()})
        if v is None:
            return False
        m = FLOAT_SKIP_REL * max(1.0, abs(float(b)), abs(v))
        return v <= float(b) - m if op == "<=" else v >= float(b) + m

    def _hard_float(i, op, qs, centre):
        f, pt = frows[i], {}
        base = {k: float(x) for k, x in centre.items()}
        for pn in fnames[i]:
            lo_p, hi_p = qs[pn]["lo"], qs[pn]["hi"]
            v_lo, v_hi = f(dict(base, **{pn: float(lo_p)})), f(dict(base, **{pn: float(hi_p)}))
            if v_lo is None or v_hi is None:
                continue
            pt[pn] = (lo_p if v_lo <= v_hi else hi_p) if op == ">=" else (hi_p if v_hi >= v_lo else lo_p)
        return pt

    def _first_fail(piece, only=None):
        centre = {n: (lo + hi) / 2 for n, (lo, hi) in piece.items()}
        for i, (node, op, b, qs) in enumerate(rows):
            if only is not None and i != only:
                continue
            extra = []
            if op != "==":
                # the data point hardest at this piece's centre: a piece the scenario points cannot fail often fails
                # there (c <= 0.008 with g and r toleranced: the middle data fail p < 0.075 only, the worst p < 0.0975)
                hp = _hard_float(i, op, qs, centre) if frows else \
                    _hard_points([(node, op, b)], [qs], xs, centre, fast=True)[0]
                if hp and hp not in pts[i]:
                    extra.append(hp)
            for pt in pts[i] + extra:
                if _met(i, op, b, dict(centre, **pt)):
                    continue
                r = ZC._reading(node, on(qs, dict(piece, **{d: (v, v) for d, v in pt.items()})), {})
                if r is None:
                    continue
                if op in (">=", "==") and r[1] < b:
                    return {"leaf": "fails", "row": i, "at": {d: _fr(v) for d, v in pt.items()},
                            "bound": _fr(r[1]), "cert": {"leaf": "interval"}}
                if op in ("<=", "==") and r[0] > b:
                    return {"leaf": "fails", "row": i, "at": {d: _fr(v) for d, v in pt.items()},
                            "bound": _fr(r[0]), "cert": {"leaf": "interval"}}
        # CONTRACTION (2026-10-19, ZTL zcontract / lean ZContract): no reading failed the piece — the requirement MET,
        # contracted over it at its hardest data point, may still leave nothing (the reading's dependency problem).
        # Tried only where floats see the row missed at the centre (met there, a contraction cannot empty the box).
        if HC4[0]:
            import zcontract as ZK
            for i, (node, op, b, qs) in enumerate(rows):
                if only is not None and i != only:
                    continue
                if op == "==":
                    continue
                pt = (_hard_float(i, op, qs, centre) if frows else (pts[i][0] if pts[i] else {})) or {}
                if _met(i, op, b, dict(centre, **pt)):
                    continue
                if ZK.empty(node, op, b, on(qs, dict(piece, **{d: (v, v) for d, v in pt.items()}))):
                    return {"leaf": "fails", "row": i, "at": {d: _fr(v) for d, v in pt.items()},
                            "cert": {"leaf": "hc4"}}
        return None

    def reading(piece):
        return ZC._reading(obj_node, on(qs_obj, piece), {})

    def low(piece):
        r = reading(piece)
        return None if r is None else r[0]
    root = {}
    heap, k, count = [], 0, {"pieces": 0, "cost": 0, "fails": 0}
    closed_lb = []

    def value(piece):
        """What a visit computes about a piece — a PURE function of the piece (the rows, data points and objective
        are fixed for this search), so a worker may compute it ahead (SPECULATION below)."""
        fl = fails(piece)
        return fl, (None if fl is not None else reading(piece))

    spec = _Speculation(value, names, width0)

    def visit(piece, node):
        nonlocal k
        count["pieces"] += 1
        fl, r = spec.value(piece)
        if fl is not None:
            node.update(fl)
            count["fails"] += 1
            return
        lb = None if r is None else r[0]
        # closed by its cost: above the mix's (less the tolerance) — or the objective varies by less than the
        # tolerance on it: a feasible piece cheaper than the mix (the mix sits a hair above the optimum) cannot be
        # failed and splitting it only narrows a reading already that tight; it bounds L by its own lower end
        if C is not None and r is not None and (lb >= C - tol or r[1] - r[0] <= tol):
            node.update({"leaf": "cost", "cert": {"leaf": "interval"}})
            closed_lb.append(lb)
            count["cost"] += 1
            return
        k += 1
        heapq.heappush(heap, (float(lb) if lb is not None else -1e300, k, piece, node))
    visit(dict(xs), root)
    from .stopflag import check as _stop_check
    try:
        while heap and count["pieces"] < budget:
            _stop_check()           # a stop asked from outside (blind test 6: `timeout` ran on past 900 s in here)
            spec.ahead(heap)
            _lb, _k, piece, node = heapq.heappop(heap)
            got = _split(piece, names, width0)
            if got is None:
                heapq.heappush(heap, (_lb, _k, piece, node))
                break
            n, at, lo_piece, hi_piece = got
            node.update({"split": n, "at": _fr(at), "lo": {}, "hi": {}})
            visit(lo_piece, node["lo"])
            visit(hi_piece, node["hi"])
    finally:
        spec.close()
    # what is left open becomes a cost leaf with its own reading — a sound, maybe weaker, bound
    for _lb, _k, piece, node in heap:
        lb = low(piece)
        if C is None or lb is None:
            return None, None, dict(count, open=len(heap))
        node.update({"leaf": "cost", "cert": {"leaf": "interval"}})
        closed_lb.append(lb)
        count["cost"] += 1
    L = min(closed_lb) if closed_lb else None
    if C is None and count["cost"] == 0:
        # THE CORE, a pass over the FINISHED tree (2026-10-18, c07: the first failing row of each leaf made it 7 of
        # 10): leaves in the tree's order; a leaf that fails a row already in the core is RELABELLED to it, else its
        # own row joins. Sequential and deterministic — the search itself (and its speculation) is untouched; the
        # relabelled tree is what zmin checks (lean/ZConflict.lean, no_mix_core).
        core = set()

        def walk(node, piece):
            if "split" in node:
                n_, at_ = node["split"], F(node["at"])
                walk(node["lo"], dict(piece, **{n_: (piece[n_][0], at_)}))
                walk(node["hi"], dict(piece, **{n_: (at_, piece[n_][1])}))
            elif node.get("leaf") == "fails":
                if node["row"] in core:
                    return
                for j in sorted(core):
                    got = _first_fail(piece, only=j)
                    if got is not None:
                        # RELABELLED in the tree itself: zmin then checks the leaf as it is now, so the core is
                        # exactly the rows of a CHECKED tree (ZConflict.no_mix_core: LeavesIn core)
                        node.clear()
                        node.update(got)
                        return
                core.add(node["row"])
        walk(root, dict(xs))
        count["core_rows"] = sorted(core)
    return root, L, dict(count, open=len(heap))


def _fr(x):
    x = F(x)
    return f"{x.numerator}/{x.denominator}"


def _nonlinear(allc, qrow, alltext, xs, names, obj_node, qs_obj, otext, mix_of, qscale, incumbent=None,
               exist_only=False, search_only=False):
    """One combination with amounts NOT affine: -> an entry (values, verdict, cost, L | none | lp).
    incumbent: the cheapest earned mix of the combinations judged before — a combination PROVED not to beat it (the
    same split, closed at that cost) needs no mix searched; its bound still goes to ZTL."""
    import zmin
    rows = [(n_, op, b_, q_) for (n_, op, b_), q_ in zip(allc, qrow)]
    if incumbent is not None:
        pts0 = []
        for n_, op, b_, q_ in rows:
            pts0.append([{p: (q_[p]["lo"] + q_[p]["hi"]) / 2 for p in _row_params(n_, q_, xs)}] if op != "==" else [{}])
        tree, L0, cnt = _bb(obj_node, qs_obj, rows, xs, pts0, incumbent, NL_PRUNE_PIECES, alltext)
        if tree is not None and (cnt["cost"] == 0 or (L0 is not None and L0 >= incumbent - NL_TOL * max(F(1), abs(incumbent)))):
            ok, info = zmin.check_lower_bound(obj_node, qs_obj, rows, xs, L0 if cnt["cost"] else 0, tree)
            if ok and cnt["cost"] == 0:
                return {"none": (f"proved by ZTL (zmin): the amounts' box split in {info['pieces']} pieces, each "
                                 f"failing a requirement at one point of its data — no mix exists"),
                        "none_rows": cnt.get("core_rows") or sorted(_tree_rows(tree))}
            if ok:
                return {"L": L0, "pruned": True, "zmin": info}
    if not search_only:
        # A CHEAP PROOF FIRST (2026-10-19, c07: every combination's mix searched — 1.9 s of a 7.9 s profile — before
        # "no mix" was proved): a split of at most PROOF_FIRST_PIECES, the readings, the float skip and contraction;
        # closed, the combination has no mix and no search is spent on it. Open, nothing is lost but those pieces.
        pts_q = [[{p: (q_[p]["lo"] + q_[p]["hi"]) / 2 for p in _row_params(n_, q_, xs)}] if op != "==" else [{}]
                 for n_, op, b_, q_ in rows]
        tree, _L, cnt = _bb(obj_node, qs_obj, rows, xs, pts_q, None, PROOF_FIRST_PIECES, alltext)
        if tree is not None and cnt["cost"] == 0:
            ok, info = zmin.check_lower_bound(obj_node, qs_obj, rows, xs, 0, tree)
            if ok:
                return {"none": (f"proved by ZTL (zmin): the amounts' box split in {info['pieces']} pieces, each "
                                 f"failing a requirement at one point of its data — no mix exists"),
                        "none_rows": cnt.get("core_rows") or sorted(_tree_rows(tree))}
    rows_f = [(_float_fn(t, q_), op, b_) for t, (n_, op, b_), q_ in zip(alltext, allc, qrow)]
    obj_f = _float_fn(otext, qs_obj)
    ineq = [i for i, (_n, op, _b, _q) in enumerate(rows) if op != "=="]
    eq_rows = [i for i, (_n, op, _b, _q) in enumerate(rows) if op == "=="]
    eqs_aff = []
    for i in eq_rows:
        n_, op, b_, q_ = rows[i]
        eqs_aff.append((n_, zlp.affine(n_, xs, q_), b_))
    scen, seen = [], set()

    def add(i, pt):
        key = (i, tuple(sorted(pt.items())))
        if key in seen:
            return False
        seen.add(key)
        scen.append((i, dict(pt)))
        return True
    for i in ineq:
        n_, op, b_, q_ = rows[i]
        add(i, {p: (q_[p]["lo"] + q_[p]["hi"]) / 2 for p in _row_params(n_, q_, xs)})
    mid = [float((xs[n][0] + xs[n][1]) / 2) for n in names]
    starts = [mid, [float(xs[n][1]) for n in names], [float(xs[n][0] + (xs[n][1] - xs[n][0]) / 4) for n in names],
              [float(xs[n][0] + 3 * (xs[n][1] - xs[n][0]) / 4) for n in names]]
    found = None
    rounds = 0
    from .stopflag import check as _stop_check
    for rnd in range(NL_ROUNDS):
        _stop_check()
        rounds = rnd + 1
        verdict = None
        for fac in (1.0, 1e2, 1e4, 1e5):
            z = _nlp(obj_f, rows_f, scen, xs, names, eqs_aff, starts, fac)
            if z is None:
                break
            xstar, values, verdict = mix_of(type("R", (), {"x": z})())
            if verdict.get("verdict") == "EARNED":
                found = (xstar, values, verdict)
                break
        if found or verdict is None:
            break
        starts = [[float(xstar[n]) for n in names]] + starts[:4]
        new = False
        pt_w = verdict.get("its_violating_point") or {}
        wpt = {}
        for k_, v_ in pt_w.items():
            try:
                n = B.ident(k_)
                wpt[n] = B.num(str(v_).split(" ")[0]) * qscale.get(n, F(1))
            except (ValueError, ZeroDivisionError):
                continue
        for i in ineq:
            n_, op, b_, q_ = rows[i]
            ps = _row_params(n_, q_, xs)
            if ps and all(p in wpt for p in ps):
                new |= add(i, {p: min(max(wpt[p], q_[p]["lo"]), q_[p]["hi"]) for p in ps})
            hard = _hard_points([(n_, op, b_)], [q_], xs, xstar)[0]
            if ps and all(p in hard for p in ps):
                new |= add(i, hard)
            wp = _worst_point(n_, op, q_, xs, xstar, hard, rows_f[i][0])
            if wp is not None:
                new |= add(i, wp)
        if not new:
            break
    method = f"nonlinear amounts: a local solver over {len(scen)} data points, {rounds} round(s)"
    pts = [[pt for j, pt in scen if j == i] or [{}] for i in range(len(rows))]
    if found is None and search_only:
        return {"lp": f"search only: no earned mix found ({method}); no proof attempted"}
    if found is None:
        tree, _L, cnt = _bb(obj_node, qs_obj, rows, xs, pts, None, NL_PIECES, alltext)
        if tree is not None and cnt["cost"] == 0:
            ok, info = zmin.check_lower_bound(obj_node, qs_obj, rows, xs, 0, tree)
            if ok:
                return {"none": (f"proved by ZTL (zmin): the amounts' box split in {info['pieces']} pieces, each "
                                 f"failing a requirement at one point of its data — no mix exists"),
                        "method": method, "none_rows": cnt.get("core_rows") or sorted(_tree_rows(tree))}
        return {"lp": f"the local solver found no earned mix ({method}), and no proof that none exists"}
    xstar, values, verdict = found
    import zcertify as ZC
    r = ZC._reading(obj_node, {**qs_obj, **{n: dict(qs_obj[n], lo=v, hi=v) for n, v in xstar.items()}}, {})
    cost = (r[0] + r[1]) / 2 if r is not None else None
    if cost is None:
        return {"values": values, "verdict": verdict, "cost": None, "L": None,
                "L_why": "the objective has no reading at the mix", "method": method}
    if exist_only:
        return {"values": values, "verdict": verdict, "cost": cost, "L": None,
                "L_why": "existence only (a conflict-search subset): no bound proved", "method": method}
    tree, L, cnt = _bb(obj_node, qs_obj, rows, xs, pts, cost, NL_PIECES, alltext)
    if tree is None or L is None:
        return {"values": values, "verdict": verdict, "cost": cost, "L": None,
                "L_why": "the bound's search left a piece with no reading of the objective", "method": method}
    ok, info = zmin.check_lower_bound(obj_node, qs_obj, rows, xs, L, tree)
    return {"values": values, "verdict": verdict, "cost": cost, "L": L if ok else None,
            "L_why": None if ok else info, "method": method,
            "zmin": dict(info, open=cnt.get("open", 0)) if ok else None}
