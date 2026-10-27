"""The stand: bricks in, a verdict in three out.

    EARNED    a design (an item from the catalog in every slot) whose required
              quantities stay inside their requirements for EVERY value the
              tolerances allow — shown by sound ranges (ZTL's for the linear
              system; the labelled forward step for nonlinear definitions) and
              confirmed by the independent checker.
    REFUTED   no design can: for each one a concrete point (its nominal, or a
              corner of its tolerance box) violates a requirement. The closest
              design and its violating point are returned.
    OPEN      neither could be shown for some design, and none was earned.
    STAND FAULT  the judge and the checker disagree; reported instead of a verdict.

EARNED rests on its grounds: a catalog tolerance is the datasheet's word
(credit in ZTL), so EARNED here means "earned on the datasheet".

Usage: python -m ustand.stand bricks.json            (prints JSON)
"""
from __future__ import annotations

import ast
import itertools
import json
import re
import sys
from fractions import Fraction as F

from . import bricks as B
from . import checker as C
from . import parallel as PL
from . import mode as MODE
from . import exact as X
from . import forward as W
from . import judge_ztl as J
from . import units as U
from . import certify as K


def _approx(x, digits=6):
    """~value for a fraction of any size (float overflows past 1e308: then the power of ten)."""
    try:
        return f"{float(x):.{digits}g}"
    except OverflowError:
        e = len(str(abs(x.numerator))) - len(str(x.denominator))
        return f"{'-' if x < 0 else ''}~1e{e}"


def _s(x):
    if isinstance(x, F):
        if x.denominator == 1:
            return str(x.numerator)
        return f"{x.numerator}/{x.denominator} (~{_approx(x)})"
    if isinstance(x, dict):
        return {k: _s(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_s(v) for v in x]
    return x


def designs(b):
    """Every assignment of a catalog item to every slot: {slot: (catalog, item)} — those that pass "where".

    SCALE (blind test 5, c10: 10.7 M combinations, round 4 c06: 112 k at ~1 ms each — a full frame per
    combination): each `where` condition is tested at the DEPTH of the slot enumeration where every slot it reads
    is chosen, and a branch it rejects is not expanded; each item's exact values are read ONCE. The order is
    itertools.product's (the first slot outermost), so the designs come in the same order as before."""
    slots = list((b.get("slots") or {}).items())
    names = [s for s, _ in slots]
    options = [[(c, it) for c in spec["from"] for it in B.items(b["catalog"][c])] for _, spec in slots]
    conds = [(i, X.parse(B.compile_expr(w))) for i, w in enumerate(b.get("where") or [])]
    if (conds or b.get("computed")) and all(options):
        try:
            _exact_units(b, {s: opts[0] for s, opts in zip(names, options)})   # before the enumeration
        except U.UnitError as e:
            if "has no unit" not in str(e):  # a brick without units is "not checked", as unit_check says
                raise
    import time as _time
    t0 = last = _time.time()
    count = [0]

    def tick():
        count[0] += 1
        if count[0] % 4096 == 0:
            _stop_check()           # blind test 5, c10: a timeout unheard while `where` filtered
            nonlocal last
            if _time.time() - last > 30:
                last = _time.time()
                print(f"[stand] filtering by `where`: {count[0]} branches read, {int(last - t0)} s",
                      file=sys.stderr, flush=True)
    if not conds:
        for combo in itertools.product(*options):
            tick()
            yield {s: pick for s, pick in zip(names, combo)}
        return
    # the exact environment, piece by piece: the givens once, each item's own values once
    base_fx, base_bx, _, _ = frame(b, {}, with_computed=False)
    base_env = dict(base_fx)
    base_nom = {n: (lo + hi) / 2 for n, (lo, hi) in base_bx.items()}
    part = []
    for s, opts in zip(names, options):
        row = []
        for pick in opts:
            fx, bx, _, _ = frame(b, {s: pick}, with_computed=False)
            env = {k: v for k, v in fx.items() if k not in base_fx}
            for f, spec in pick[1].items():
                if spec[0] == "label":
                    env[B.ident(f"{s}.{f}")] = spec[1]
            nom = {k: (lo + hi) / 2 for k, (lo, hi) in bx.items() if k not in base_bx}
            row.append((env, nom))
        part.append(row)
    # which slots each computed value and each condition reads
    comp = b.get("computed") or {}
    comp_nodes = {cn: X.parse(B.compile_expr(cv if isinstance(cv, str) else cv["value"])) for cn, cv in comp.items()}
    prefix = {B.ident(f"{s}.x")[:-1]: k for k, s in enumerate(names)}       # "S__" -> slot index

    def slots_of(node, seen=()):
        out = set()
        for n in _outer_names(node) | {x.id for x in ast.walk(node) if isinstance(x, ast.Name)}:
            for p_, k in prefix.items():
                if n.startswith(p_):
                    out.add(k)
            if n in comp_nodes and n not in seen:
                out |= slots_of(comp_nodes[n], seen + (n,))
        return out
    comp_names = {cn: _outer_names(nd) for cn, nd in comp_nodes.items()}     # read once (31 s re-walked, c10)
    depth_of = lambda deps: max(deps) if deps else -1
    comp_at = {}
    for cn, nd in comp_nodes.items():
        comp_at.setdefault(depth_of(slots_of(nd)), []).append(cn)
    cond_at = {}
    for i, nd in conds:
        cond_at.setdefault(depth_of(slots_of(nd)), []).append((i, nd))

    def settle(depth, env):
        """The computed values complete at this depth, then its conditions: False when one fails."""
        todo = list(comp_at.get(depth, []))
        while todo:
            done = []
            for cn in todo:
                if comp_names[cn] - env.keys() - {"__nominal__"}:
                    continue
                try:
                    v = X.evaluate(comp_nodes[cn], env, f"computed.{cn}")
                except X.ExactError as e:
                    raise B.BrickError(str(e))
                if isinstance(v, X._Iv):
                    raise B.BrickError(f"computed.{cn}: exp/ln/log10/sqrt give an irrational value — a computed "
                                       "value must be exact (round it with ceil/floor, or make it a law); they are "
                                       "for `where` tests")
                env[cn] = v
                done.append(cn)
            if not done:
                missing = sorted({n for c in todo for n in _outer_names(comp_nodes[c])} - set(env))
                raise B.BrickError(f"computed {', '.join(sorted(todo))}: no exact value for "
                                   f"{', '.join(m.replace('__', '.') for m in missing)} (a tolerance, a range, a "
                                   "derived quantity, or computed values that lean on each other)")
            todo = [c for c in todo if c not in done]
        try:
            return all(X.evaluate(nd, env, f"where[{i}]") for i, nd in cond_at.get(depth, []))
        except X.ExactError as e:
            raise B.BrickError(str(e))

    env0 = dict(base_env)
    env0["__nominal__"] = dict(base_env, **base_nom)
    if not settle(-1, env0):
        return

    def go(k, env, chosen):
        if k == len(names):
            yield {s: pick for s, pick in zip(names, chosen)}
            return
        for pick, (penv, pnom) in zip(options[k], part[k]):
            tick()
            env2 = dict(env, **penv)
            env2["__nominal__"] = dict(env["__nominal__"], **penv, **pnom)
            if settle(k, env2):
                yield from go(k + 1, env2, chosen + [pick])
    yield from go(0, env0, [])


def combinations(b):
    """How many slot assignments there are before "where"."""
    n = 1
    for spec in (b.get("slots") or {}).values():
        n *= sum(len(B.items(b["catalog"][c])) for c in spec["from"])
    return n


_NOMCACHE = {}


def _excluded(b, all_designs, pr):
    """Combinations "where" removed — the pruned groups' designs are designs (refuted), not excluded."""
    if pr is None:
        return combinations(b) - len(all_designs)
    if any(p[3] < 0 for p in pr[1]):
        return "not counted (a pruned group too large to count against where)"
    return combinations(b) - len(all_designs) - sum(p[3] for p in pr[1])


def _run_continuous(b, parts, conflicts=False):
    """Continuous choices (ustand/lp.py): per discrete combination the solver's cheapest robust mix, judged by
    the ordinary stand; ZTL's dual check proves the lower bound over every mix in the box."""
    from . import lp as LP
    # a candidate mix is judged BRIEF: only its verdict and why reach the answer (below); the reasons and the
    # each-requirement listing of a refuted candidate were 870 s of c11's 987 s (MEASURED, profile 2026-10-18)
    res = LP.run_continuous(b, parts, lambda pb: _run(pb, conflicts=False, brief=True))
    if res is None:
        return {"verdict": "BRICK ERROR", "why": "continuous choices need every derived quantity defined explicitly "
                                                 "(X == expression) — version 1"}
    sc = _obj_scale(b)
    earned = [e for e in res if e.get("verdict", {}).get("verdict") == "EARNED"]
    covered = [e for e in res if e.get("L") is not None]
    nomix = [e for e in res if "none" in e]          # proved by Farkas: no mix at all in that combination
    notes = [f"{e['label'] or 'the mix'}: {e['lp']}" for e in res if "lp" in e]
    notes += [f"{e['label'] or 'the mix'}: ZTL did not accept the dual certificate: {e['L_why']}"
              for e in res if "lp" not in e and "none" not in e and e.get("L") is None]
    L = min((e["L"] for e in covered), default=None)
    zm = [e["zmin"] for e in covered if e.get("zmin")]
    how_none = "Farkas" if all("zmin" not in e["none"] for e in nomix) else (
        "a split of the amounts, zmin" if all("zmin" in e["none"] for e in nomix) else "Farkas, or a split of the amounts")
    out = {"stand": "ztl-stand/1", "judge": f"ZTL {J.ztl_commit()}", "continuous": True,
           "combinations": len(res), "notes": notes[:10]}
    if nomix:
        out["combinations_proved_without_mix"] = len(nomix)
    if not earned:
        # REFUTED only where "no mix exists" is PROVED (Farkas) in every combination: a mix the solver found and the
        # stand refuted shows that mix fails, not that every mix does (blind test 4, c12, 2026-10-11 — a binding
        # margin missed by rounding was reported REFUTED although a feasible mix existed)
        out.update(verdict="REFUTED" if len(nomix) == len(res) else "OPEN",
                   why=(f"ZTL proved ({how_none}) that no mix in the box meets the requirements"
                        if len(nomix) == len(res) else
                        "not decided: no mix the solver found was earned, and no proof that none exists"
                        + (f" ({len(nomix)} combination(s) proved to have no mix)" if nomix else ""))
                   + ("" if not notes else " (see notes)"),
                   mixes=[{"design": e["label"], "verdict": e.get("verdict", {}).get("verdict"),
                           "why": e.get("verdict", {}).get("why") or e.get("lp") or e.get("none")}
                          for e in res][:20])
        if out["verdict"] == "REFUTED" and len(parts) == 1 and all("none_reqs" in e for e in nomix):
            # THE CORE (2026-10-18): the requirements the proofs use — any set holding them is refuted by the same
            # proofs (minimal_conflicts drops the rest without a run)
            out["_core"] = sorted(set().union(*[e["none_reqs"] for e in nomix]))
        if conflicts and out["verdict"] == "REFUTED":
            # J10 (2026-10-12): WHICH requirements cannot hold together, as for a catalog — each subset judged
            # by the same continuous path (its objective kept: the path needs one)
            out["minimal_conflicts"] = minimal_conflicts(b, out.get("_core"))
        return out
    best = min(earned, key=lambda e: e["cost"])
    v = best["verdict"]
    mix = {s_: {"catalog": cat, fld: _s(val)} for s_, (cat, fld, val) in best["values"].items()}
    gap = best["cost"] - L if L is not None else None
    if gap is not None and gap < 0:
        # a proved lower bound ABOVE an earned mix's cost: the two contradict, so one of them is wrong — the stand's own
        # fault, said, never printed as a negative gap (blind test 6, c10: a false EARNED showed gap -0.34, unflagged)
        return {"verdict": "STAND FAULT",
                "why": (f"the proved lower bound {_s(L / sc)} lies above the earned mix's cost {_s(best['cost'] / sc)} "
                        f"({best['label'] or 'the mix'}): the bound and the verdict contradict — a stand bug, no answer "
                        f"given")}
    obj = {"minimize": b["objective"]["minimize"], "value": _s(best["cost"] / sc), **_obj_unit(b),
           "lower_bound": _s(L / sc) if L is not None else None,
           "gap": _s(gap / sc) if gap is not None else None,
           "lower_bound_is": ((("proved by ZTL (zlp) from the LP solver's dual multipliers: no mix in the continuous "
                                "box costs less") if not zm else
                              ("proved by ZTL: no mix in the continuous box costs less — zmin: the amounts' box of "
                               f"{len(zm)} combination(s) split in {sum(z['pieces'] for z in zm)} pieces, "
                               f"{sum(z['cost'] for z in zm)} with the objective >= L, {sum(z['fails'] for z in zm)} "
                               "failing a requirement at one point of its data"
                               + (f" ({sum(z.get('open', 0) for z in zm)} left open by the search's budget, each "
                                  "bounded by its own reading)" if any(z.get("open") for z in zm) else "")
                               + ("; zlp (the LP solver's dual multipliers) for the rest"
                                  if len(zm) < len(covered) else "")))
                              + (", over the discrete combinations whose LP found a mix — "
                                                  f"{len(res) - len(covered) - len(nomix)} not covered (see notes)"
                                                  if len(covered) + len(nomix) < len(res) else "")
                              + (f"; {len(nomix)} combination(s) proved to have no mix at all ({how_none})"
                                 if nomix else "")
                              + ("; the box LP had no mix (its coefficients' worst cases taken apart), so the robust "
                                 "LP was relaxed to data points — " + ", ".join(sorted(
                                     {e["method"] for e in covered if e.get("method", "").startswith("scenario")}))
                                 + " — a RELAXATION of the robust problem: its bound holds for every mix"
                                 if any(e.get("method", "").startswith("scenario") for e in covered) else "")),
           "optimal": gap is not None and gap <= 0 and len(covered) + len(nomix) == len(res),
           "optimal_means": ("true only at a zero gap; otherwise the mix is PROVED to cost at most `gap` above the "
                             "cheapest possible (blind test 4, c03: optimal false at a 0.00093 EUR gap)")}
    out.update(verdict="EARNED", design=dict(_design_out({k: x for k, x in best["design"].items()
                                                         if k not in best["values"]}), **mix),
               objective=obj, guaranteed=v.get("guaranteed"), how=v.get("how"),
               **({"per_mode": v["per_mode"], "modes": v.get("modes")} if v.get("per_mode") else {}),
               mix_verdict_checker=v.get("checker") or ({m: pm.get("checker") for m, pm in v["per_mode"].items()}
                                                         if v.get("per_mode") else None))
    return out


def _si_reqs(bm):
    """[(requirement in SI, its interval)] for the requirements with NUMERIC bounds (group pruning, v1)."""
    out = []
    for r in bm.get("requirements") or []:
        sc = _scale(bm["quantities"][r["quantity"]].get("unit"))
        vals = r["value"] if isinstance(r["value"], list) else [r["value"]]
        try:
            si = [str(B.num(v) * sc) for v in vals]
        except (ValueError, ZeroDivisionError, TypeError):
            continue
        r2 = dict(r, value=si if isinstance(r["value"], list) else si[0])
        out.append((r2, B.req_interval(r2)))
    return out


def _pruned_outcomes(pr, b, check_names=None):
    from . import prune as P
    survivors, pruned, read, options = pr
    outs = []
    for g, r, rg, n in pruned:
        o = {"design": P.label(options, g), "verdict": "REFUTED",
             "fails": r.get("why") or f"{r['quantity']} {r['op']} {r['value']}",
             "group": (f"{n} designs" if n > 0 else f"up to {-n} designs (not counted against \"where\")"),
             "how": "refuted as a GROUP: ZTL's reading and the checker's own both put the quantity past its bound "
                    "over the whole group"}
        if check_names:
            o["mode"] = check_names[r["_check"]]
        outs.append(o)
    return outs


def _obj_unit_str(b):
    """The objective's own unit: its "unit", or — when none is given — the ONE unit every dimensioned name in
    the objective is declared in (blind test 5: c01, c02, c08 priced in kEUR saw 1700 / 141514 / 14850 in SI)."""
    obj = b.get("objective") or {}
    if obj.get("unit"):
        return obj["unit"], False
    text = obj.get("minimize")
    if not isinstance(text, str):
        return None, False
    units = set()
    for slot, f in re.findall(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\b", text):
        for c in ((b.get("slots") or {}).get(slot) or {}).get("from") or []:
            u = B.field_units((b.get("catalog") or {}).get(c) or {}).get(f)
            if u:
                units.add(u)
    for n in re.findall(r"(?<![\w.])([A-Za-z_]\w*)\b(?!\.)", text):
        u = ((b.get("quantities") or {}).get(n) or {}).get("unit")
        if u:
            units.add(u)
    dimensioned = {u for u in units if any(U.parse(u)[1])}
    return (dimensioned.pop(), True) if len(dimensioned) == 1 else (None, False)


def _obj_scale(b):
    """The objective's own unit (optional "unit"): its value is shown in it, not in SI (blind test 3, c04:
    8.4e-09 for 30.35 EUR/MWh)."""
    u, _ = _obj_unit_str(b)
    return _scale(u) if u else F(1)


def _obj_unit(b):
    u, inferred = _obj_unit_str(b)
    return ({"unit": u, "unit_from": "the unit of the prices in the objective (no objective \"unit\" given)"}
            if inferred else {"unit": u}) if u else {}


def _closure(laws, wanted, derived):
    """The laws that determine `wanted` (derived names): each defining law X == ..., and those of every derived name
    it reads, transitively; a law that is not a definition (an implicit one, a system) comes in with every derived
    name it reads. -> (laws, derived names) for checker.solve_at; all of them if the closure cannot be told."""
    defs, others = {}, []
    for law in laws:
        m = re.match(r"\s*([A-Za-z_]\w*)\s*==", law)
        if m and m.group(1) in derived and m.group(1) not in defs:
            defs[m.group(1)] = law
        else:
            others.append(law)
    need, todo, out = set(), list(wanted), []
    names_in = lambda t: set(re.findall(r"[A-Za-z_]\w*", t)) & derived
    while todo:
        n = todo.pop()
        if n in need:
            continue
        need.add(n)
        if n in defs:
            todo += list(names_in(defs[n].split("==", 1)[1]))
        else:
            hit = [o for o in others if n in names_in(o)]
            if not hit:
                return laws, sorted(derived)        # not told by a law of its own: the whole system, as before
            for o in hit:
                if o not in out:
                    out.append(o)
                    todo += list(names_in(o))
    return [defs[n] for n in defs if n in need] + out, sorted(need)


def _nominal_cost(b, d, node, laws):
    """The objective at the NOMINAL point (every toleranced value at its nominal). Derived quantities in it
    (I3, blind test 3: the nominal energy of a house or a turbine) are read by the checker's exact solution
    of the laws there — an interval where a function is irrational: its middle orders the designs."""
    fx, bx, derived, _ = frame(b, d)
    point = dict(fx, **{n: (lo + hi) / 2 for n, (lo, hi) in bx.items()})
    known = {n: (v, v) for n, v in point.items()}
    names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    if names & set(derived):
        # ONLY THE LAWS THE OBJECTIVE NEEDS (its definitions, closed): a weak motor's rail speed sqrt(2*(F/m0 - g)*L)
        # has no value at its nominal point (thrust below weight) and stopped the whole catalog as a BRICK ERROR —
        # the price never reads it (the multi-node motor, 2026-10-16). A design whose price itself has no value
        # still is one.
        use_laws, use_derived = _closure(laws, names & set(derived), set(derived))
        try:
            vals = C.solve_at(use_laws, point, use_derived)
        except (C.CheckError, ZeroDivisionError) as e:
            raise B.BrickError(f"objective: the laws have no value at the nominal point of a design: {e}")
        known.update({k: (v if isinstance(v, tuple) else (v, v)) for k, v in vals.items()})
    try:
        lo, hi = C._ivl(node, known)
    except C.CheckError as e:
        raise B.BrickError(f"objective: {e}")
    return (lo + hi) / 2


def _outer_names(node):
    """Names read EXACTLY (outside nominal(...)): those must have exact values."""
    out = set()

    def walk(n):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "nominal":
            return
        if isinstance(n, ast.Name):
            out.add(n.id)
        for c in ast.iter_child_nodes(n):
            if not (isinstance(n, ast.Call) and c is n.func):
                walk(c)
    walk(node)
    return out


def exact_env(b, design):
    """Exact values in SI for "where" and "computed": exact givens and fields, labels, computed values."""
    fixed, boxes_e, _, _ = frame(b, design, with_computed=False)
    env = dict(fixed)
    for s, (cname, item) in design.items():
        for f, spec in item.items():
            if spec[0] == "label":
                env[B.ident(f"{s}.{f}")] = spec[1]
    comp = b.get("computed") or {}
    env["__nominal__"] = dict(env, **{n: (lo + hi) / 2 for n, (lo, hi) in boxes_e.items()})
    todo = dict(comp)
    while todo:
        done = []
        for cn, cv in todo.items():
            node = X.parse(B.compile_expr(cv if isinstance(cv, str) else cv["value"]))
            if _outer_names(node) - set(env):
                continue
            try:
                env[cn] = X.evaluate(node, env, f"computed.{cn}")
            except X.ExactError as e:
                raise B.BrickError(str(e))
            if isinstance(env[cn], X._Iv):
                raise B.BrickError(f"computed.{cn}: exp/ln/log10/sqrt give an irrational value — a computed value must "
                                   "be exact (round it with ceil/floor, or make it a law); they are for `where` tests")
            done.append(cn)
        if not done:
            missing = sorted({n for cv in todo.values()
                              for n in _outer_names(X.parse(B.compile_expr(cv if isinstance(cv, str) else cv["value"])))} - set(env))
            raise B.BrickError(f"computed {', '.join(sorted(todo))}: no exact value for "
                               f"{', '.join(m.replace('__', '.') for m in missing)} (a tolerance, a range, a derived "
                               "quantity, or computed values that lean on each other)")
        for cn in done:
            del todo[cn]
    return env


def _scale(unit):
    return U.parse(unit)[0] if unit else F(1)


def frame(b, design, with_computed=True):
    """fixed values, tolerance boxes, derived names, grounds — identifiers compiled, values in SI.
    "computed" values join the fixed ones (exact, per design)."""
    fixed, boxes, grounds = {}, {}, {}

    def put(name, spec, ground=None, scale=F(1)):
        if spec[0] == "label":
            return
        if spec[0] == "range":
            _, lo, hi = spec
            lo, hi = lo * scale, hi * scale
            if lo == hi:
                fixed[name] = lo
            else:
                boxes[name] = (lo, hi)
            return
        nom, tol = spec
        nom = nom * scale
        if tol:
            a, c = nom * (1 - tol), nom * (1 + tol)
            boxes[name] = (min(a, c), max(a, c))
        else:
            fixed[name] = nom
            if ground:
                grounds[name] = ground

    for n, q in b["quantities"].items():
        if q["role"] == "given":
            put(n, B.field(q if "range" in q else {"value": q["value"], "tolerance": q.get("tolerance", "0")}),
                q.get("ground"), _scale(q.get("unit")))
    for s, (cname, item) in design.items():
        fu = B.field_units(b["catalog"][cname])
        for f, spec in item.items():
            put(B.ident(f"{s}.{f}"), spec, scale=_scale(fu.get(f)))
    derived = [n for n, q in b["quantities"].items() if q["role"] == "derived"]
    if with_computed and b.get("computed"):
        env = exact_env(b, design)
        for cn in b["computed"]:
            if isinstance(env[cn], str):
                raise B.BrickError(f"computed.{cn}: a label is not a value for the laws")
            fixed[cn] = F(env[cn])
    return fixed, boxes, derived, grounds


def _exact_units(b, design, dims=None):
    """Units of "where" and "computed" (strict: a bare number beside a unit is refused). Called once at the
    FIRST combination, before the enumeration (blind test 3, c06: the error surfaced after 4 minutes)."""
    comp = b.get("computed") or {}
    if dims is None:
        dims = {}
        for n, q in b["quantities"].items():
            if q.get("unit") is not None:
                dims[n] = U.parse(q["unit"])[1]
        for s_, (cname, item) in design.items():
            fu = B.field_units(b["catalog"][cname])
            for f in item:
                if fu.get(f) is not None:
                    dims[B.ident(f"{s_}.{f}")] = U.parse(fu[f])[1]
        for cn, cv in comp.items():
            dims[cn] = U.parse(cv.get("unit", "") if isinstance(cv, dict) else "")[1]
    labels = {B.ident(f"{s_}.{f}") for s_, (c, item) in design.items() for f, v in item.items() if v[0] == "label"}

    def dimof(n):
        if n in labels:
            return "label"
        if n not in dims:
            raise U.UnitError(f"{n.replace('__', '.')} has no unit")
        return dims[n]
    try:
        for i, w in enumerate(b.get("where") or []):
            X.dims(X.parse(B.compile_expr(w)), dimof, f"where[{i}]", U.show)
        for cn, cv in comp.items():
            d = X.dims(X.parse(B.compile_expr(cv if isinstance(cv, str) else cv["value"])), dimof, f"computed.{cn}", U.show)
            want = dims[cn]
            if (d or tuple(0 for _ in want)) != want:
                raise U.UnitError(f"computed.{cn}: the expression is {U.show(d) if d else 'dimensionless'}, "
                                  f"the declared unit is {U.show(want)}")
    except X.ExactError as e:
        raise U.UnitError(str(e))


def unit_check(b, design, laws):
    """None when every law's dimensions agree; 'not checked: ...' when a unit is missing.
    Raises UnitError on a mismatch (a law with wrong units means nothing)."""
    dims, missing = {}, []
    for n, q in b["quantities"].items():
        if q.get("unit") is None:
            missing.append(n)
        else:
            dims[n] = U.parse(q["unit"])[1]
    for s, (cname, item) in design.items():
        fu = B.field_units(b["catalog"][cname])
        for f, spec in item.items():
            if spec[0] == "label":
                continue
            if fu.get(f) is None:
                missing.append(f"{s}.{f}")
            else:
                dims[B.ident(f"{s}.{f}")] = U.parse(fu[f])[1]
    comp = b.get("computed") or {}
    for cn, cv in comp.items():
        dims[cn] = U.parse(cv.get("unit", "") if isinstance(cv, dict) else "")[1]
    if missing:
        return "not checked: no unit for " + ", ".join(sorted(missing))
    dims.update({B.ROOT + n: dims[n] for n, q in b["quantities"].items() if "search" in q})
    _exact_units(b, design, dims)
    obj = b.get("objective") or {}
    if obj.get("unit") is not None and obj.get("minimize"):
        U.check_law(f"__objective == {B.compile_expr(obj['minimize'], b.get('define'))}",
                    dict(dims, __objective=U.parse(obj["unit"])[1]), "the objective against its unit")
    for raw, law in zip(b["laws"], laws):
        U.check_law(law, dims, raw["zfl"])
    # a bound WITH NAMES has a dimension of its own: it must be the quantity's (2026-10-10, G4)
    all_reqs = list(b.get("requirements") or []) + [r for m in (b.get("modes") or {}).values()
                                                    for r in (m.get("requirements") or [])]
    for r in all_reqs:
        for v in (r["value"] if isinstance(r["value"], list) else [r["value"]]):
            if not isinstance(v, str):
                continue
            text = B.compile_expr(v, b.get("define"))
            tree = ast.parse(text, mode="eval").body
            if any(isinstance(n, ast.Name) for n in ast.walk(tree)):
                U.check_law(f"{r['quantity']} == {text}", dims, f"the bound {v!r} of {r['quantity']}")
    return None


def reasons(laws, fixed, boxes, derived, point, r, req_iv):
    """Why the closest design fails (gap J7): how wide its spread of the violated quantity
    is against the window, and which toleranced quantities move it most. Recomputed exactly
    at the corners (the true range in the monotone class)."""
    q = r["quantity"]
    out = {}
    try:
        cs = C.corners(laws, fixed, boxes, derived) if len(boxes) <= REASONS_CORNER_PARAMS else []
    except (C.CheckError, ZeroDivisionError) as e:      # a corner the laws cannot be solved at
        out["not_computed"] = f"the spread over the corners: {e}"
        cs = []
    if len(boxes) > REASONS_CORNER_PARAMS:
        # an EXPLANATION, not the verdict (2026-10-20: 16 tolerances, all 65 536 corners solved exactly for this
        # text = 24 of 24 s of a refutation): said, not estimated — the contributors below are one at a time
        out["not_computed"] = (f"the spread over the corners: 2^{len(boxes)} corners (more than "
                               f"2^{REASONS_CORNER_PARAMS}); the largest contributors below, one quantity at a time")
    if cs:
        lo = min((v[q][0] if isinstance(v[q], tuple) else v[q]) for _, v in cs)
        hi = max((v[q][1] if isinstance(v[q], tuple) else v[q]) for _, v in cs)
        out["spread_over_tolerances"] = _s([lo, hi])
        a, c = req_iv
        if a is not None and c is not None:
            out["window"] = _s([a, c])
            if hi - lo > c - a:
                out["verdict_on_window"] = ("for this design the spread over its tolerances alone is wider than "
                                            "the window: centring cannot fix it, only tighter tolerances or "
                                            "another design")
    contrib = []
    import time as _time
    for n, (lo_n, hi_n) in boxes.items():
        e_lo, e_hi = dict(fixed, **point), dict(fixed, **point)
        e_lo[n], e_hi[n] = lo_n, hi_n
        t0 = _time.monotonic()
        try:
            vh, vl = C.solve_at(laws, e_hi, derived)[q], C.solve_at(laws, e_lo, derived)[q]
        except (C.CheckError, ZeroDivisionError):
            continue
        took = _time.monotonic() - t0
        if took > 2 * GREEDY_SOLVE_MAX and not contrib:
            # two exact solutions per quantity, each too dear (Muhanna's benchmark 1: 27 s each, 420 moduli -> ~6 h
            # for every refutation, MEASURED 2026-10-16) — said, not computed
            out["not_computed"] = (f"the largest contributors: two exact solutions took {took:.0f} s, "
                                   f"x {len(boxes)} quantities")
            break
        mid = lambda v: (v[0] + v[1]) / 2 if isinstance(v, tuple) else v     # a function's interval: its middle
        d = abs(mid(vh) - mid(vl))
        contrib.append((d, n))
    contrib.sort(reverse=True)
    out["largest_contributors"] = [{"quantity": n.replace("__", "."), "moves_it_by": _s(d)}
                                   for d, n in contrib[:5] if d]
    return out


MAX_OUTCOMES = 200
CORNERS_BEFORE_CERT = 8      # more tolerances than this: the certificate before the exact corners (2026-10-20)
REASONS_CORNER_PARAMS = 10   # an explanation's spread over the corners only up to 2^10 of them (2026-10-20)


def _point_scale(b, design, name, qscale):
    """SI -> the author's own unit for a point coordinate: a quantity, or a slot.field of this design."""
    if name in qscale:
        return qscale[name]
    if "__" in name:
        slot, fld = name.split("__", 1)
        if slot in design:
            u = B.field_units(b["catalog"][design[slot][0]]).get(fld)
            return _scale(u)
    return F(1)


def _point_unit(b, design, name):
    if name in b["quantities"]:
        return b["quantities"][name].get("unit", "")
    if "__" in name:
        slot, fld = name.split("__", 1)
        if slot in design:
            return B.field_units(b["catalog"][design[slot][0]]).get(fld) or ""
    return ""


def _ties(all_designs, design, cost, outcomes=None):
    """Other designs with exactly the same objective (blind test 2, c02: two bolts at $5.60, one reported as
    THE optimum), each with what the stand knows of it (blind test 4, c01/c09/c10, 2026-10-11: the list named
    designs that fail, with nothing to say so): its verdict if it was judged, "not judged" otherwise."""
    c = cost(design)
    same = [d for d in all_designs if d is not design and cost(d) == c]
    if not same:
        return None
    seen = {o["design"]: o["verdict"] for o in (outcomes or [])}
    return {"same_objective": len(same),
            "first": [{"design": _label(d), "verdict": seen.get(_label(d), "not judged")} for d in same[:3]],
            "note": "these cost the same; \"not judged\" ones come after the earned design in the search, which "
                    "stops at the first EARNED — \"report\": \"all\" judges them"}


def _listing(outcomes):
    """(listed, counts, not_listed). When the list is cut, EARNED come first, then OPEN, then REFUTED —
    blind test 2 (c02, c06, c09, c10): the first 200 by cost were all REFUTED and hid exactly the earned and
    undecided designs the authors needed; and there was no count. Within each verdict, the run's order."""
    counts = {}
    for o in outcomes:
        counts[o["verdict"]] = counts.get(o["verdict"], 0) + 1
    if len(outcomes) <= MAX_OUTCOMES:
        return outcomes, counts, 0
    rank = {"EARNED": 0, "OPEN": 1, "REFUTED": 2}
    listed = sorted(outcomes, key=lambda o: rank.get(o["verdict"], 3))[:MAX_OUTCOMES]
    return listed, counts, len(outcomes) - MAX_OUTCOMES


def _label(design):
    """A short name for a design: each slot's catalog and its item's nominal fields."""
    parts = []
    for slot, (cat, item) in design.items():
        fs = []
        for f, v in item.items():
            if v[0] == "label":
                fs.append(f"{f}={v[1]}")
            elif v[0] == "range":
                fs.append(f"{f}=[{_s_fr(v[1])},{_s_fr(v[2])}]")
            else:
                fs.append(f"{f}={_s_fr(v[0])}")
        # labels first, then up to 8 fields, "..." when cut (blind test 2, c10: the first four fields of two
        # different gear pairs were equal and the designs read the same)
        fs = [x for x, (f, v) in zip(fs, item.items()) if v[0] == "label"] + \
             [x for x, (f, v) in zip(fs, item.items()) if v[0] != "label"]
        parts.append(f"{slot}={cat}(" + ", ".join(fs[:8]) + (", ..." if len(fs) > 8 else "") + ")")
    return "; ".join(parts)


def _bound_shares_box(r, boxes):
    """True when a requirement's bound reads a toleranced quantity: its least favourable end is then
    taken apart from the quantity's own range, so a design can fail the conservative check while no
    corner violates it — undecided, never a STAND FAULT (2026-10-10: a ratiometric window Vin*0.49)."""
    for v in (r["value"] if isinstance(r["value"], list) else [r["value"]]):
        if isinstance(v, str):
            names = set(re.findall(r"[A-Za-z_]\w*", B.compile_expr(v) if B.DOTTED.search(v) else v))
            if names & set(boxes):
                return True
    return False


def _req_at(r, point_env):
    """The requirement's interval at one concrete point (named bounds take the point's value)."""
    return B.req_interval(r, {}, point_env)


# ── OPERATING MODES (gap J8, 2026-10-10) ─────────────────────────────────────
# A design must hold in every mode at once: cold start and full load, idle and peak.
# A mode overrides given quantities (value / tolerance / range) and adds requirements;
# the laws and the catalog are the same. Built ON the single-mode machinery, not beside
# it: each (design, mode) is run as an ordinary brick with every slot pinned to the
# design's item — so every check, label and fault of `run` applies per mode unchanged.

def _s_fr(x):
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def _raw_field(v):
    if v[0] == "range":
        return {"range": [_s_fr(v[1]), _s_fr(v[2])]}
    if v[0] == "label":
        return v[1]
    return {"value": _s_fr(v[0]), "tolerance": _s_fr(v[1])}


def _pinned(b, design):
    """The brick with every slot reduced to the one item the design gives it."""
    import copy
    # everything but the catalog copied; the catalog holds ONLY the pinned items (it was deep-copied whole,
    # hundreds of items, for every design and every mode — blind test 2, c10, 2026-10-10)
    out = copy.deepcopy({k: v for k, v in b.items() if k != "catalog"})
    out["catalog"] = {}
    for slot, (cat, item) in design.items():
        name = f"__pinned_{slot}"
        src = b["catalog"][cat]
        fields = {f: ({"unit": u} if u is not None else {}) for f, u in B.field_units(src).items()}
        out["catalog"][name] = {"items": [{f: _raw_field(v) for f, v in item.items()}], "fields": fields,
                                **({"ground": src["ground"]} if src.get("ground") else {})}
        out["slots"][slot] = {"from": [name]}
    return out


def _mode_brick(b, mode, spec):
    import copy
    out = copy.deepcopy(b)
    out.pop("modes", None)
    out.pop("objective", None)
    for q, over in (spec.get("quantities") or {}).items():
        base = out["quantities"].get(q)
        if not base or base.get("role") != "given":
            raise B.BrickError(f"mode {mode!r}: {q!r} is not a given quantity of the brick (a mode overrides givens only)")
        new = {k: v for k, v in base.items() if k not in ("value", "tolerance", "range")}
        new.update(over)
        out["quantities"][q] = new
    # a tolerance NAMING a given the mode overrides is read again in the mode (audit 2026-10-13, cx2: the base brick's
    # load had resolved it to the base number, and the mode's own tolerance was never used — a false EARNED)
    over = set(spec.get("quantities") or {})
    for q, qq in out["quantities"].items():
        if q not in over and isinstance(qq, dict) and qq.get("_tolerance_of") in over:
            qq["tolerance"] = qq.pop("_tolerance_of")
    out["requirements"] = list(out.get("requirements") or []) + list(spec.get("requirements") or [])
    # MODE-SPECIFIC DEFINES AND LAWS (blind test G9, 2026-10-10: "one instance down" is N_active = N - 1;
    # a standby circuit has its own law). A mode's define replaces the brick's of that name; its laws
    # are added to the brick's.
    if spec.get("define"):
        out["define"] = dict(out.get("define") or {}, **spec["define"])
    if spec.get("laws"):
        out["laws"] = list(out["laws"]) + list(spec["laws"])
    return out


def _mode_item(i):
    """One design's runs in every mode — exactly the loop's own calls (a worker of ustand/parallel.py, or here)."""
    per_mode, ds = PL.STATE["modes"]
    out = {}
    for m, bm in per_mode.items():
        out[m] = _run(_pinned(bm, ds[i]), conflicts=False, brief=True, loaded=True)   # exact inside; the door shortens
        if out[m]["verdict"] in ("BRICK ERROR", "STAND FAULT", "STAND ERROR"):
            break                               # the loop returns at this mode: the later ones are never read
    return out


def _plain_item(i):
    """One design judged alone (a worker of ustand/parallel.py): ("REFUTED", (point, values, requirement index,
    overshoot, at the nominal point)) or (verdict, None) — then the main loop judges it itself."""
    b, ds = PL.STATE["plain"]
    PL.STATE["raw"] = True
    try:
        r = _run(_pinned(b, ds[i]), conflicts=False, brief=True, loaded=True)
    except Exception:                       # noqa: BLE001 — the main loop meets the same error itself
        return ("ERROR", None)
    finally:
        PL.STATE["raw"] = False
    return ("REFUTED", r["_raw"]) if "_raw" in r else (r.get("verdict"), None)


def run_modes(b, conflicts=False) -> dict:
    modes = b["modes"]
    if not isinstance(modes, dict) or not modes:
        return {"verdict": "BRICK ERROR", "why": "modes: an object of named modes is required"}
    try:
        per_mode = {m: B.load(_mode_brick(b, m, spec)) for m, spec in modes.items()}   # checked ONCE
    except B.BrickError as e:
        return {"verdict": "BRICK ERROR", "why": str(e)}
    from . import lp as LP
    if LP.continuous_slots(b):
        # CONTINUOUS CHOICES WITH MODES (2026-10-10): every mode's requirements, each over its own box, in one LP
        return _run_continuous(b, [(bm, bm["requirements"],
                                    B.implicit_laws(bm, [B.compile_expr(l["zfl"], bm.get("define")) for l in bm["laws"]]))
                                   for bm in per_mode.values()], conflicts)
    from . import prune as P
    names_m = list(per_mode)
    checks = [(bm, B.implicit_laws(bm, [B.compile_expr(l["zfl"], bm.get("define")) for l in bm["laws"]]),
               _si_reqs(bm)) for bm in per_mode.values()]
    pr = P.prune(b, checks) if not (b.get("objective") or {}).get("case") == "worst" else None
    all_designs = pr[0] if pr is not None else list(designs(b))
    cost = None
    if b.get("objective"):
        expr = B.compile_expr(b["objective"]["minimize"], b.get("define"))
        import ast as _ast
        node = _ast.parse(expr, mode="eval").body

        base_laws = B.implicit_laws(b, [B.compile_expr(l["zfl"], b.get("define")) for l in b["laws"]])

        def cost(d):
            return _nominal_cost(b, d, node, base_laws)
        all_designs.sort(key=cost)
    tried = undecided = undecided_before = 0
    closest = None
    report_all, outcomes, first_earned = b.get("report") == "all", [], None
    # PARALLEL (ustand/parallel.py): each design's per-mode runs computed ahead by workers, in this order
    PL.STATE["modes"] = (per_mode, all_designs)
    pre = PL.iterate(_mode_item, len(all_designs))
    for design in all_designs:
        tried += 1
        _tick(tried, len(all_designs), outcomes)
        results = {}
        mres = next(pre)
        for m, bm in per_mode.items():
            r = mres[m]                         # = _run(_pinned(bm, design), conflicts=False, brief=True, loaded=True)
            if r["verdict"] in ("BRICK ERROR", "STAND FAULT", "STAND ERROR"):
                return dict(r, mode=m, design=_design_out(design))
            results[m] = r
        verdicts = {m: r["verdict"] for m, r in results.items()}
        if all(v == "EARNED" for v in verdicts.values()):
            outcomes.append({"design": _label(design), "verdict": "EARNED"})
            if first_earned is None:
                out = {"stand": "ztl-stand/1", "judge": f"ZTL {J.ztl_commit()}", "verdict": "EARNED",
                       "modes": list(modes), "designs_tried": tried, "undecided": undecided,
                       "design": _design_out(design),
                       "per_mode": {m: {"guaranteed": r["guaranteed"], "how": r["how"], "checker": r.get("checker")}
                                    for m, r in results.items()}}
                if cost:
                    out["objective"] = {"minimize": b["objective"]["minimize"], "value": _s(cost(design) / _obj_scale(b)), **_obj_unit(b),
                                        "optimal": undecided_before == 0,
                                        "note": ("every cheaper design was refuted in some mode" if undecided_before == 0
                                                 else f"{undecided_before} cheaper design(s) undecided")}
                    ties = _ties(all_designs, design, cost, outcomes)
                    if ties:
                        out["objective"]["ties"] = ties
                first_earned = out
            if not report_all:
                break
            continue
        refuted = {m: r for m, r in results.items() if r["verdict"] == "REFUTED"}
        if refuted:
            best = None
            for m, r in refuted.items():
                over = B.num(str(r["overshoot"]).split(" ")[0])
                if closest is None or over < closest[0]:
                    closest = (over, design, m, r)
                if best is None or over < best[0]:
                    best = (over, m, r)
            req = best[2]["requirement"]
            outcomes.append({"design": _label(design), "verdict": "REFUTED", "mode": best[1],
                             "fails": req.get("why") or f"{req['quantity']} {req['op']} {req['value']}",
                             "by_at_witness": best[2]["overshoot"], "unit": best[2].get("unit", ""),
                             # EVERY mode it fails in (real problems r01, r02: only the first was named)
                             "failing_modes": sorted(refuted)})
        else:
            undecided += 1
            if first_earned is None:
                undecided_before += 1
            outcomes.append({"design": _label(design), "verdict": "OPEN",
                             "why": "undecided in: " + "; ".join(
                                 f"{m} ({(results[m].get('designs') or [{}])[0].get('why') or results[m].get('why', '')})"
                                 for m, v in verdicts.items() if v != "EARNED")})
    if pr is not None:
        outcomes = _pruned_outcomes(pr, b, names_m) + outcomes
    pre.close()                     # the workers stop here (ahead of an EARNED design their work is not needed)
    group_info = {"refuted_by_groups": sum(abs(p[3]) for p in pr[1]), "groups_pruned": len(pr[1]),
                  "groups_read": pr[2]} if pr is not None else {}
    if first_earned is not None:
        listed, counts, cut = _listing(outcomes)
        first_earned.update(group_info)
        if b.get("where"):
            first_earned["excluded_by_where"] = _excluded(b, all_designs, pr)
        return dict(first_earned, designs=listed, designs_count=counts, designs_tried=tried,
                    **({"designs_not_listed": cut, "listing": "earned first, then open, then refuted"} if cut else {}))
    base = {"stand": "ztl-stand/1", "judge": f"ZTL {J.ztl_commit()}", "modes": list(modes),
            "designs_tried": tried, "undecided": undecided}
    base["designs"], base["designs_count"], cut = _listing(outcomes)
    base.update(group_info)
    if b.get("where"):
        base["excluded_by_where"] = _excluded(b, all_designs, pr)
    if cut:
        base["designs_not_listed"], base["listing"] = cut, "earned first, then open, then refuted"
    if undecided:
        return dict(base, verdict="OPEN", why=f"{undecided} design(s) could not be decided in every mode and none was earned")
    if closest is None and pr is not None and pr[1]:
        out = dict(base, verdict="REFUTED", why="every design is refuted — by whole groups, each read by ZTL and by "
                                                "the checker past a bound over the group, in some mode")
        if conflicts:
            out["minimal_conflicts"] = minimal_conflicts(b)
        return out
    over, design, m, r = closest
    fm = next((o.get("failing_modes") for o in outcomes if o.get("design") == _label(design) and o.get("failing_modes")), [m])
    out = dict(base, verdict="REFUTED",
               why="every design violates a requirement in at least one mode, at a concrete point",
               closest_design=_design_out(design), failing_mode=m, failing_modes=fm,
               its_violating_point=r["its_violating_point"], value_there=r["value_there"],
               requirement=r["requirement"], overshoot=r["overshoot"], checker=r["checker"])
    if conflicts:
        out["minimal_conflicts"] = minimal_conflicts(b)
    return out


_LONG = re.compile(r"^(-?\d+)/(\d+) \(~([^)]*)\)$")


_KEEP_EXACT = [False]


def _as_checked(got, laws, bound, fixed, boxes, unknowns, q, op):
    """The checker's arguments for a zlin certificate: the RESCALED system and bound when the prover changed the
    unknowns' units (certify._scaling) — the certificate is for that system, an exact equivalent of the original."""
    if got.get("checked_as"):
        laws, bound = got["checked_as"]
    return laws, fixed, boxes, unknowns, q, op, bound, got["cert"]


def _shorten(x):
    """ONLY AT THE DOOR: a bracket end of exp/ln/... is an exact fraction hundreds of digits long.
    Shown rounded, with its length said; everything inside compared the exact value (2026-10-10).
    A CALLER THAT READS THE NUMBERS BACK (spice.range_of: each refuted value is the next bound) asks for them whole
    via _KEEP_EXACT — the duel of 2026-10-15 (T09, 24 resistors at 0.1 %) parsed "~6.4579273651" and stopped."""
    if _KEEP_EXACT[0]:
        return x
    if isinstance(x, dict):
        return {k: _shorten(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_shorten(v) for v in x]
    if isinstance(x, str) and len(x) > 80:
        m = _LONG.match(x)
        if m:
            return f"~{_approx(F(int(m.group(1)), int(m.group(2))), 12)} (an exact fraction of {len(m.group(2))} digits)"
        if x.startswith("outside ZTL") or x.startswith("ZTL"):
            return re.sub(r"-?\d{30,}/\d{30,}", lambda mm: f"~{_approx(F(mm.group(0)), 12)}", x)
    return x


from . import fwitness as FW   # noqa: E402 — a float witness search before certificates (2026-10-16)
from .stopflag import Stopped, STOP as _STOP, check as _stop_check   # noqa: E402


# what the design loops have decided so far — read only when a run is stopped, or for the progress line (blind
# test 4, J4, 2026-10-11: four authors' runs were killed at 900 s and printed NOTHING)
_PROGRESS = {"tried": 0, "total": 0, "outcomes": None, "stderr": False, "t0": None, "last": 0.0}


def _tick(tried, total, outcomes):
    import time as _t
    _stop_check()
    _PROGRESS.update(tried=tried, total=total, outcomes=outcomes)
    now = _t.time()
    if _PROGRESS["t0"] is None:
        _PROGRESS["t0"] = now
    if _PROGRESS["stderr"] and now - _PROGRESS["last"] >= 30:
        _PROGRESS["last"] = now
        cnt = {}
        for o in outcomes or []:
            cnt[o["verdict"]] = cnt.get(o["verdict"], 0) + 1
        print(f"[stand] {tried}/{total} designs, {now - _PROGRESS['t0']:.0f} s: "
              + ", ".join(f"{v} {k}" for k, v in sorted(cnt.items())), file=sys.stderr, flush=True)


def _stopped_report():
    outs = list(_PROGRESS["outcomes"] or [])
    out = {"stand": "ztl-stand/1", "judge": f"ZTL {J.ztl_commit()}", "verdict": "OPEN",
           "why": (f"stopped by a signal (a time limit) after {_PROGRESS['tried']} of {_PROGRESS['total']} designs: "
                   "only the designs listed were decided; the verdict over the rest, and optimality, are not known"
                   if _PROGRESS["total"] else "stopped by a signal (a time limit) before any verdict"),
           "designs_tried": _PROGRESS["tried"], "designs_total": _PROGRESS["total"]}
    if outs:
        out["designs"], out["designs_count"], cut = _listing(outs)
        if cut:
            out["designs_not_listed"], out["listing"] = cut, "earned first, then open, then refuted"
    return out


def run(b, conflicts=True) -> dict:
    """Never a traceback (the blind test of 2026-10-10 met eight). A malformed brick is a BRICK
    ERROR with its reason; anything else that escapes is a STAND ERROR — the stand's own bug,
    named as such, never blamed on the brick and never a verdict about the design."""
    # NESTED runs (minimal_conflicts judges every subset by run()): only the OUTERMOST resets the progress and the
    # stop flag, and a nested run passes a stop up (blind test 5, c07, 2026-10-11: `timeout 900` ran 1041 s — each
    # subset's run() cleared the flag, and a stopped subset counted as OPEN while the enumeration went on)
    top = _DEPTH[0] == 0
    if top:
        _PROGRESS.update(tried=0, total=0, outcomes=None, t0=None)
        _STOP[0] = False
    _DEPTH[0] += 1
    try:
        raw = b if isinstance(b, dict) else json.load(open(b, encoding="utf-8"))
        if top and isinstance(raw, dict) and raw.get("components"):
            from . import components as CM  # component files only inside the brick's own folder (components.py)
            import os as _os
            CM.check_files(raw, _os.path.dirname(_os.path.abspath(b)) if isinstance(b, str) else None)
        if isinstance(b, str) and isinstance(raw, dict) and raw.get("components"):
            from . import components as CM  # its component files resolved from ITS directory, once
            import os as _os
            raw = CM.absolutize(raw, _os.path.dirname(_os.path.abspath(b)))
            b = raw
        if top and isinstance(raw, dict) and "find" in raw:
            out = _shorten(_find(raw))      # an inverse question: the nested runs judge each tried range
            if out.get("verdict") not in ("BRICK ERROR", "STAND ERROR") and not _STOP[0]:
                # THE DECISION TOO (blind test 6: c03, c04, c09, c12 each kept a second brick for it): the brick as
                # written, without its find — its verdict, design, conflicts — next to the limit
                dec = _shorten(run({k: v for k, v in raw.items() if k != "find"}, conflicts))
                out["decision"] = {k: dec.get(k) for k in ("verdict", "why", "design", "objective", "guaranteed",
                                                           "minimal_conflicts", "fails", "its_violating_point")
                                   if dec.get(k) is not None}
            out["checked_by"] = ("ZTL + the independent checker (dev mode)" if MODE.DEV[0] else
                                 "ZTL (work mode; a refutation's witness recomputed exactly; --dev adds the "
                                 "independent checker on every design)")
            return out
        if isinstance(raw, dict) and raw.get("components") and "find" not in raw:
            from . import components as CM  # a system of components: assume-guarantee contracts (ustand/components.py)
            import os as _os
            base = _os.path.dirname(_os.path.abspath(b)) if isinstance(b, str) else _os.getcwd()
            out = _shorten(CM.run_system(raw, base))
            if top:
                out["checked_by"] = ("ZTL + the independent checker (dev mode)" if MODE.DEV[0] else
                                     "ZTL (work mode; a refutation's witness recomputed exactly; --dev adds the "
                                     "independent checker on every design)")
            return out
        if isinstance(raw, dict) and "network" in raw and "find" not in raw:
            from . import network as NW     # a network brick: the network certificate's verdict (ustand/network.py)
            from .stopflag import interruptible
            # a stop from outside ends the network's search at once (capacity bench, 2026-10-13: a 50 x 50 grid ran on
            # past `timeout 600` — no safe point in netsearch/znet; their code is pure arithmetic, no bare `except:`)
            with interruptible():
                out = _shorten(NW.run_network(raw))
            return out
        out = _shorten(_run(b, conflicts))
        if top and isinstance(out, dict):
            out["checked_by"] = ("ZTL + the independent checker (dev mode)" if MODE.DEV[0] else
                                 "ZTL (work mode; a refutation's witness recomputed exactly; --dev adds the "
                                 "independent checker on every design)")
        return out
    except Stopped:
        if not top:
            raise
        return _shorten(_stopped_report())
    except (B.BrickError, U.UnitError) as e:
        return {"verdict": "BRICK ERROR", "why": f"{type(e).__name__}: {e}"}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        if top or not isinstance(b, str):
            return {"verdict": "BRICK ERROR", "why": f"the brick cannot be read: {e}"}
        raise
    except (W.ForwardError, C.CheckError) as e:
        return {"verdict": "BRICK ERROR", "why": f"laws: {e}"}
    except Exception as e:                                  # noqa: BLE001 — the last line of defence
        import traceback
        where = traceback.extract_tb(e.__traceback__)[-1]
        return {"verdict": "STAND ERROR",
                "why": f"the stand failed on this brick — a bug in the stand, not a verdict: "
                       f"{type(e).__name__}: {str(e)[:300]} (at {where.filename.split('/')[-1]}:{where.lineno})"}
    finally:
        _DEPTH[0] -= 1


_DEPTH = [0]


def _couples(reqs, b):
    """Name sets the checker's corners must move together (checker._groups): each requirement's quantity with the
    names in its bound, and a worst-case objective's names."""
    out = []
    for r in reqs:
        ns = {r["quantity"]}
        for v in (r["value"] if isinstance(r.get("value"), list) else [r.get("value")]):
            if isinstance(v, str):
                try:
                    ns |= _names(v)
                except SyntaxError:
                    pass
        out.append(ns)
    if (b.get("objective") or {}).get("minimize") and b["objective"].get("case") == "worst":
        # only a worst-case objective is read at the corners; coupling a nominal one would only enlarge groups
        try:
            out.append(_names(B.compile_expr(b["objective"]["minimize"], b.get("define"))))
        except SyntaxError:
            pass
    return out


# ── inverse questions: "the largest (smallest) value that still works" (since 2026-10-12; real round 1, r03) ─────
# The stand judges a RANGE, not points: the brick with the quantity over [from, a] (largest) or [a, to] (smallest)
# is EARNED only when every value in it works — so "works on the whole range" is monotone in a by construction and
# bisection on a is exact, with no assumption that the design gets worse monotonically. The answer is a bracket:
# proved up to `proved`; beyond it a failing point (REFUTED) or an undecided range (OPEN), never guessed.



def _find_halts(r):
    return r.get("verdict") not in ("EARNED", "REFUTED", "OPEN") or "stopped" in r


def _fstr(x):
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


_FIND_RANK = ("STAND ERROR", "STAND FAULT", "BRICK ERROR", "REFUTED", "OPEN", "EARNED")


def _find(raw) -> dict:
    spec = raw.get("find")
    if isinstance(spec, list):
        # SEVERAL limits in one brick (real round 2, s05: four trip temperatures were four bricks; the curator's "да",
        # 2026-10-12). Each item is searched on its own; its "requirements", when given, replace the brick's for it.
        if not spec:
            raise B.BrickError("find: an empty list")
        out = []
        for i, item in enumerate(spec):
            one = json.loads(json.dumps(raw))
            try:
                if not isinstance(item, dict):
                    raise B.BrickError("must be an object")
                item = dict(item)
                if "requirements" in item:
                    one["requirements"] = item.pop("requirements")
                one["find"] = item
                r = _find(one)
            except B.BrickError as e:
                r = {"verdict": "BRICK ERROR", "why": f"find[{i}]: {e}"}
            r["find_index"] = i
            out.append(r)
        verdict = min((r.get("verdict") for r in out),
                      key=lambda v: _FIND_RANK.index(v) if v in _FIND_RANK else 0)
        return {"stand": "ztl-stand/1", "verdict": verdict,
                "why": "several limits, each searched on its own; the verdict is the weakest of theirs",
                "finds": out}
    if isinstance(spec, dict) and "requirements" in spec:
        raw = json.loads(json.dumps(raw))
        spec = dict(spec)
        raw["requirements"] = spec.pop("requirements")
        raw["find"] = spec
    if not isinstance(spec, dict):
        raise B.BrickError('find: must be an object like {"largest": "Rsa", "from": "0", "to": "20", '
                           '"precision": "0.01"}')
    sides = [k for k in ("largest", "smallest") if k in spec]
    if len(sides) != 1:
        raise B.BrickError("find: name exactly one of 'largest' or 'smallest'")
    side, name = sides[0], spec[sides[0]]
    q = (raw.get("quantities") or {}).get(name)
    if not isinstance(q, dict) or q.get("role") != "given":
        raise B.BrickError(f"find: {name!r} must be a given quantity (its value or range is what is searched)")
    # WITH MODES (real round 4, k02, 2026-10-12): every tried range is judged in every mode; refused only when a
    # mode overrides the searched given itself (whose range would the search then be moving?)
    for m, spec_m in (raw.get("modes") or {}).items():
        if isinstance(spec_m, dict) and name in (spec_m.get("quantities") or {}):
            raise B.BrickError(f"find: mode {m} overrides {name}, the quantity searched — search it without that "
                               f"override, or per mode")
    try:
        lo, hi = B.num(spec["from"]), B.num(spec["to"])
        eps = B.num(spec["precision"]) if "precision" in spec else (hi - lo) / 1000
    except KeyError as e:
        raise B.BrickError(f"find: needs {e.args[0]!r}")
    except (ValueError, ZeroDivisionError, TypeError, AttributeError):
        raise B.BrickError("find: from, to and precision are numbers written as strings")
    if not lo < hi or eps <= 0:
        raise B.BrickError("find: needs from < to and a positive precision")
    unit = q.get("unit", "")
    largest = side == "largest"
    anchor, far = (lo, hi) if largest else (hi, lo)       # every tried range shares the anchor end
    tries = []

    def judge(a):
        b = json.loads(json.dumps(raw))
        del b["find"]
        qq = b["quantities"][name]
        for k in ("value", "tolerance", "range"):
            qq.pop(k, None)
        if a == anchor:
            qq["value"] = _fstr(a)
        else:
            qq["range"] = [_fstr(min(a, anchor)), _fstr(max(a, anchor))]
        try:
            r = run(b, conflicts=False)
        except Stopped:
            r = {"verdict": "OPEN", "stopped": "a stop asked from outside, mid-search: the bracket so far"}
        tries.append({name: _s(a), "verdict": r.get("verdict")})
        return r

    def span(a):
        return f"[{_s(min(a, anchor))}, {_s(max(a, anchor))}] {unit}".strip()

    head = {"find": side, "quantity": name, "unit": unit}
    r = judge(anchor)
    if _find_halts(r):
        return {**r, **head, "stopped_at": _s(anchor), "tries": tries}
    if r.get("verdict") != "EARNED":
        return {"verdict": r.get("verdict"), **head,
                "why": (f"even {name} = {_s(anchor)} alone fails — no value in the search range works"
                        if r.get("verdict") == "REFUTED" else
                        f"the stand could not decide even {name} = {_s(anchor)} alone"),
                "at_the_end": r, "tries": tries}
    good, good_r = anchor, r
    r = judge(far)
    if _find_halts(r):
        return {**r, **head, "stopped_at": _s(far), "proved": _s(good), "tries": tries}
    if r.get("verdict") == "EARNED":
        return {"verdict": "EARNED", **head, "proved": _s(far),
                "proved_means": f"every {name} in {span(far)} works — the WHOLE search range; widen it to find the limit",
                "at_proved": r, "tries": tries}
    bad, bad_r = far, r                       # the nearest end not proved
    refuted = far if r.get("verdict") == "REFUTED" else None    # the nearest end with a failing point
    while abs(bad - good) > eps:
        # the midpoint on the precision's grid (from + k * precision), so the answer reads 7.149, not 58563/8192
        base = lo if largest else hi
        mid = base + round(((good + bad) / 2 - base) / eps) * eps
        if not min(good, bad) < mid < max(good, bad):
            break
        r = judge(mid)
        v = r.get("verdict")
        if v == "EARNED":
            good, good_r = mid, r
        elif v in ("REFUTED", "OPEN") and not _find_halts(r):
            bad, bad_r = mid, r
            if v == "REFUTED":
                refuted = mid
        if _find_halts(r):
            return {**r, **head, "stopped_at": _s(mid), "proved": _s(good), "tries": tries}
    out = {"verdict": "EARNED", **head, "proved": _s(good),
           "proved_means": f"every {name} in {span(good)} works (EARNED on the whole range)",
           "beyond": _s(bad),
           "beyond_is": (f"REFUTED: the range {span(bad)} holds a concrete failing point (at_beyond)"
                         if refuted == bad else
                         f"OPEN: the stand could not decide the range {span(bad)} — the limit lies between "
                         f"{_s(good)} and {_s(bad)}, unproved"
                         + (f"; a failing point is proved within {span(refuted)}" if refuted is not None else "")),
           "precision": _s(abs(bad - good)),
           "at_proved": good_r, "at_beyond": bad_r, "tries": tries}
    return out


def _names(text):
    """The names an expression reads."""
    return {n.id for n in ast.walk(ast.parse(text.strip(), mode="eval").body) if isinstance(n, ast.Name)}


def _run(b, conflicts=True, brief=False, loaded=False) -> dict:
    """brief: a mode's sub-run — no reasons for a refutation (the modes keep only verdict and overshoot);
    loaded: the brick was loaded and checked already (a mode brick, pinned to one design)."""
    if not loaded:
        raw = b if isinstance(b, dict) else json.load(open(b, encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("totals") is not None:
            raw = B.joint_totals(raw)       # J8: the modes judged as one brick, the totals summed across them
            r = _run(B.load(raw), conflicts, brief, loaded=True)
            r["modes_joined"] = (f"the modes {', '.join(raw['_joined_modes'])} judged as ONE brick (totals): a quantity "
                                 "Q of mode m is Q_in_m; a given no mode overrides is the same value in every mode")
            return r
        b = B.load(raw)
    if b.get("conflicts") is False:
        conflicts = False           # the brick switches minimal_conflicts off (blind test 5, c06; the curator's "да")
    if b.get("modes"):
        return run_modes(b, conflicts=conflicts and not brief)
    laws = B.implicit_laws(b, [B.compile_expr(l["zfl"], b.get("define")) for l in b["laws"]])
    reqs_given = b["requirements"]
    qscale = {n: _scale(q.get("unit")) for n, q in b["quantities"].items()}
    reqs = []                       # requirement numbers moved into SI (names stay names)

    def si_bound(v, sc):
        """A number (or an arithmetic of numbers) is in the quantity's own unit: scaled. A bound with
        NAMES is an expression like a law's — the names are in SI already — compiled, not scaled."""
        try:
            return str(B.num(v) * sc)
        except (ValueError, ZeroDivisionError, TypeError):
            pass
        text = B.compile_expr(v, b.get("define"))
        tree = ast.parse(text, mode="eval").body
        if not any(isinstance(n, ast.Name) for n in ast.walk(tree)):
            lo, _ = B._ival(tree, {})
            return str(lo * sc)
        return text

    for r in reqs_given:
        r2 = dict(r)
        sc = qscale[r["quantity"]]
        if r["op"] == "within":
            r2["value"] = [si_bound(v, sc) for v in r["value"]]
        else:
            r2["value"] = si_bound(r["value"], sc)
        reqs.append(r2)
    couple = _couples(reqs, b)      # the checker's corners: a requirement's bound names move with its quantity
    tried = pruned = judged = undecided = 0
    undecided_before_earned = 0
    unconfirmed = []            # certificates ZTL accepted and the checker could not re-check
    checker_notes = []          # designs the checker could not evaluate (left undecided)
    units_note, checked_maps = None, set()
    earned = None
    closest = None              # (overshoot, design, point, values, requirement)

    def violation(values, env):
        for r in reqs:
            v = values[r["quantity"]]
            iv = _req_at(r, env)
            if B.violates(v, iv):
                a, c = iv
                lo, hi = v if isinstance(v, tuple) else (v, v)
                low_side = a is not None and (hi <= a if getattr(iv, "strict_lo", False) else hi < a)
                return r, ((a - hi) if low_side else (lo - c))   # the nearer end: certain (0 = on a strict bound)
        return None

    def note(design, point, values, r, over):
        nonlocal closest
        if closest is None or over < closest[0]:
            closest = (over, design, point, values, r)
        prev = refuted_by.get(id(design))
        if prev is None or over < prev[1]:
            refuted_by[id(design)] = (r, over)

    # EVERY DESIGN'S OUTCOME (blind test G5, 2026-10-10: "which springs pass, and why does each fail").
    # Recorded when the loop moves on, so no branch of the judgement is touched.
    report_all = b.get("report") == "all"
    outcomes, refuted_by = [], {}
    open_why = {}               # id(design) -> what was not decided, and why (G12)
    earned_ids = set()          # every EARNED design (2026-10-10: a second one, P3 of the pump, was dropped
                                # from the list — only the first was remembered)

    earned_ranges = {}

    def finalize(design, und_before):
        if id(design) in earned_ids:
            o = {"design": _label(design), "verdict": "EARNED"}
            if earned_ranges.get(id(design)):
                o["guaranteed"] = earned_ranges[id(design)]
            if id(design) in earned_all:
                _, Ub, L = earned_all[id(design)]
                o["objective_worst"] = {"proved_at_most": _s(Ub) if Ub is not None else "not bounded",
                                        "reached_at_least": _s(L) if L is not None else "not evaluated"}
            outcomes.append(o)
        elif id(design) in refuted_by:
            r, over = refuted_by[id(design)]
            outcomes.append({"design": _label(design), "verdict": "REFUTED",
                             "fails": r.get("why") or f"{r['quantity']} {r['op']} {r['value']}",
                             "by_at_witness": _s(over / qscale[r["quantity"]]), "unit": b["quantities"][r["quantity"]].get("unit", "")})
        elif undecided > und_before:
            outcomes.append({"design": _label(design), "verdict": "OPEN",
                             "why": open_why.get(id(design), "not decided either way")})

    from . import lp as LP
    if LP.continuous_slots(b):
        return _run_continuous(b, [(b, reqs_given, laws)], conflicts)
    from . import prune as P
    si_list = _si_reqs(dict(b, requirements=reqs_given))
    pr = P.prune(b, [(b, laws, si_list)]) \
        if not (b.get("objective") or {}).get("case") == "worst" else None
    if pr is not None:
        all_designs = pr[0]                # the survivors; the rest refuted in groups (blind test 3, c11)
    else:
        all_designs = list(designs(b))
    objective = None
    worst_case = bool(b.get("objective")) and b["objective"].get("case") == "worst"
    earned_all = {}             # id(design) -> (earned tuple, Ub, L): the worst-case objective (G11)
    if worst_case:
        # G11 (blind b09, 2026-10-10: "minimize the worst-case total paid" had to be written by hand):
        # the objective's WORST over the box is known only after judging — every design is judged
        report_all = True
        obj_node = ast.parse(B.compile_expr(b["objective"]["minimize"], b.get("define")), mode="eval").body
    elif b.get("objective"):
        expr = B.compile_expr(b["objective"]["minimize"], b.get("define"))
        import ast as _ast
        node = _ast.parse(expr, mode="eval").body

        def cost(d):
            return _nominal_cost(b, d, node, laws)
        all_designs.sort(key=cost)          # stable: catalog order breaks ties
        objective = (b["objective"]["minimize"], cost)

    prev_design, und_mark = None, 0
    i_design, tight_now = 0, set()          # designs judged a second time with implicit edges pulled in
    # PARALLEL (ustand/parallel.py, JOBS > 1 only): each design judged ALONE by a worker, ahead, in this order; a
    # design a worker REFUTED is taken with the worker's witness (point, values, requirement, overshoot — checked
    # exactly there); every other design is judged here as before
    pre, pre_res = None, None
    if PL.JOBS[0] > 1 and not brief and len(all_designs) > 1:
        PL.STATE["plain"] = (b, all_designs)
        pre = PL.iterate(_plain_item, len(all_designs))
    while i_design < len(all_designs):
        design = all_designs[i_design]
        i_design += 1
        if prev_design is not design:
            if prev_design is not None:
                finalize(prev_design, und_mark)
            prev_design, und_mark = design, undecided
            tried += 1
            if not brief:                   # a mode's sub-run is one design of the outer loop, not a loop of its own
                _tick(tried, len(all_designs), outcomes)
            pre_res = next(pre) if pre is not None else None
        und_unconf = len(unconfirmed)
        fixed, boxes, derived, grounds = frame(b, design)
        try:
            lin0, defs0 = W.split(laws, derived)
            C.classify(laws, set(fixed) | set(boxes), derived)
        except (W.ForwardError, C.CheckError) as e:
            return {"verdict": "BRICK ERROR", "why": f"laws: {e}"}
        used_in_linear = sorted({n for l in lin0 for n in re.findall(r"[A-Za-z_]\w*", l)} & set(defs0))
        if used_in_linear:
            # (fuzz, 2026-10-10) neither ZTL's linear solve nor the checker reads a NONLINEARLY defined
            # quantity inside a linear law (Ptot == P1 + P2 with P1 == I*I*R1): said, not crashed
            return {"verdict": "BRICK ERROR",
                    "why": f"laws: {', '.join(used_in_linear)} defined by a nonlinear law AND used in a linear law — "
                           "not supported yet: write that linear law with the definition expanded "
                           "(e.g. Ptot == I*I*R1 + I*I*R2), or bound the sum by its own definition"}
        sig = tuple(c for c, _ in design.values())
        if sig not in checked_maps:
            checked_maps.add(sig)
            try:
                note_u = unit_check(b, design, laws)
            except U.UnitError as e:
                return {"verdict": "BRICK ERROR", "why": f"units: {e}"}
            units_note = units_note or note_u
        if pre_res is not None and pre_res[0] == "REFUTED":
            pt, vals, ri, over, at_nominal = pre_res[1]
            if at_nominal:
                pruned += 1
            else:
                judged += 1
            note(design, pt, vals, reqs[ri], over)
            continue
        linear, defs = W.split(laws, derived)
        nominal = dict(fixed, **{n: (lo + hi) / 2 for n, (lo, hi) in boxes.items()})
        try:
            nv = C.solve_at(laws, nominal, derived)
            hit = violation(nv, nominal)
        except (C.CheckError, ZeroDivisionError):
            hit = None              # the laws have no solution at the box's middle: no shortcut, judge as usual
            # but the part of the laws that does NOT lean on an implicit quantity may still refute the design
            # there (blind test 2, c11: a duct too narrow for the velocity limit stayed OPEN because its fan's
            # operating point had no root — the velocity never depended on it)
            nv, hit = _independent_hit(laws, nominal, derived, reqs)
        if hit:
            pruned += 1             # the nominal point itself already fails: it is the witness
            note(design, {n: nominal[n] for n in boxes}, nv, *hit)
            continue
        judged += 1
        lin_derived = [d for d in derived if d not in defs]
        ranges, log, disposition = J.judge(linear, fixed, boxes, lin_derived, grounds)
        unbounded = [d for d in lin_derived if d not in ranges]
        fallback = W.explicit(linear, set(unbounded))
        # ZTL left these unbounded (e.g. TWO shared parameters, each in several stiffnesses: its
        # rank-many rule refuses) and no law defines them explicitly. Until 2026-10-10 the design
        # was OPEN here; now they stay without a range and only a CERTIFICATE (the kernel solves
        # the system itself) can decide a requirement on them
        refused = set(unbounded) - set(fallback)
        # and everything that leans on them, through explicit laws and definitions, goes with them
        leans = dict(fallback, **defs)
        grew = True
        while grew:
            grew = False
            for n, e in leans.items():
                if n not in refused and set(re.findall(r"[A-Za-z_]\w*", ast.unparse(e))) & refused:
                    refused.add(n); grew = True
        fallback = {n: e for n, e in fallback.items() if n not in refused}
        known = {n: (v, v) for n, v in fixed.items()}
        known.update(boxes)
        known.update({d: (lo, hi) for d, (lo, hi, _) in ranges.items()})
        # the DEFINITIONS go to ZTL too (ZTL 3a296b5 reads them: interval reading, sound),
        # with the linear unknowns as the boxes the system gave them
        def_ranges = {}
        # IMPLICIT quantities first (G6): ZTL checks a root-exclusion certificate the stand searched;
        # the definitions leaning on them then read them as boxes
        impl = {n: ast.unparse(e) for n, e in defs.items()
                if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id == "implicit"}
        impl_how, impl_fail = {}, None
        for n, text in impl.items():
            got_i, how_i, _ = J.implicit(text, fixed, boxes, grounds)
            if got_i is not None and "corner" not in how_i and id(design) in tight_now:
                # SECOND PASS: the plain enclosure left the design undecided — ask ZTL to pull the edges in (a
                # partition of the parameter box per edge, each checked by the kernel; 2026-10-10, blind test 2
                # c01: Tho 28.3..72.7 -> 40.7..59.1, the truth <= 58.9)
                goal = _implicit_goal(n, reqs, boxes, fixed)
                tight = J.implicit(text, fixed, boxes, grounds, goal=goal, tighten=8)
                if tight[0] is not None:
                    got_i, how_i = tight[0], tight[1] + "; edges pulled in by partitions of the parameter box"
            if got_i is None:
                impl_fail = f"{n}: {how_i}"
                break
            def_ranges[n] = (got_i[0], got_i[1], "implicit")
            impl_how[n] = how_i
        if impl_fail:
            undecided += 1
            undecided_before_earned += 1
            checker_notes.append(f"{_design_out(design)}: {impl_fail}")
            open_why[id(design)] = f"the implicit law of {impl_fail}"
            continue
        if set(defs) - set(impl):
            def_laws = [l for l in laws if l not in linear and l.split("==")[0].strip() not in impl]
            dboxes = dict(boxes, **{d: (lo, hi) for d, (lo, hi, _) in ranges.items() if lo != hi})
            dboxes.update({n: (lo, hi) for n, (lo, hi, _) in def_ranges.items()})
            dfixed = dict(fixed, **{d: lo for d, (lo, hi, _) in ranges.items() if lo == hi})
            # a linear unknown ZTL left without a range is still a NAME in the definitions: declared
            # unknown here (fuzz, 2026-10-10: a repeated law left I rangeless and ZTL's reader raised)
            rangeless = [d for d in lin_derived if d not in ranges]
            # ONE DEFINITION AT A TIME, in the order they lean on each other (blind test 4, J2, 2026-10-11: sent
            # together, ZTL read the explicit definitions as a SYSTEM — "1 independent equalities for 3 unknowns:
            # not uniquely solvable" — and bounded none; in c09 every temperature and force was bounded by the
            # stand instead. Each alone, over the ranges of those before it, ZTL bounds them in milliseconds.)
            law_of = {l.split("==")[0].strip(): l for l in def_laws}
            todo = [d for d in defs if d not in impl and d in law_of]
            if not rangeless:
                deps = {d: _names(law_of[d].split("==", 1)[1]) & set(todo) for d in todo}
                progress = True
                while todo and progress:
                    progress = False
                    for d in list(todo):
                        if deps[d] - set(def_ranges):
                            continue
                        lo_hi = {e: (lo, hi) for e, (lo, hi, _) in def_ranges.items() if lo != hi}
                        fx1 = dict(dfixed, **{e: lo for e, (lo, hi, _) in def_ranges.items() if lo == hi})
                        g1, l1, _ = J.judge([law_of[d]], fx1, dict(dboxes, **lo_hi), [d], grounds)
                        # WITH THE SYSTEM (2026-10-20, the bridge girder): a definition reading two or more of the
                        # system's unknowns is ALSO sent together with the linear laws, those unknowns left unknown —
                        # ZTL then reads it through their dependence on the data (znumsolve._affine_def_eq) instead of
                        # their separate ranges. Both answers are sound; their intersection is kept.
                        reads = _names(law_of[d].split("==", 1)[1]) & {u for u in lin_derived if u in ranges
                                                                       and ranges[u][0] != ranges[u][1]}
                        if len(reads) >= 2:
                            fx2 = dict(fixed, **{e: lo for e, (lo, hi, _) in def_ranges.items() if lo == hi})
                            g2, l2, _ = J.judge(linear + [law_of[d]], fx2, dict(boxes, **lo_hi),
                                                lin_derived + [d], grounds)
                            if d in g2 and d in g1:
                                lo_, hi_ = max(g1[d][0], g2[d][0]), min(g1[d][1], g2[d][1])
                                if lo_ <= hi_:
                                    tight = g2[d] if (g2[d][0], g2[d][1]) == (lo_, hi_) else g1[d]
                                    g1 = dict(g1, **{d: (lo_, hi_, tight[2] if (tight[0], tight[1]) == (lo_, hi_)
                                                         else False)})
                                    l1 = l1 + [l for l in l2 if l.startswith(f"{d} -> ")]
                            elif d in g2:
                                g1 = dict(g1, **{d: g2[d]})
                                l1 = l1 + [l for l in l2 if l.startswith(f"{d} -> ")]
                        todo.remove(d)
                        progress = True
                        if d in g1:
                            def_ranges[d] = g1[d]
                        log = log + l1
            rest_laws = [law_of[d] for d in todo] + [l for l in def_laws if l.split("==")[0].strip() not in law_of]
            if todo or rangeless:
                got, dlog, _ = J.judge(rest_laws, dfixed, dict(dboxes, **{e: (lo, hi) for e, (lo, hi, _) in
                                                                         def_ranges.items() if lo != hi}),
                                       todo + rangeless, grounds)
                got = {d: v for d, v in got.items() if d in defs and d not in impl and d not in def_ranges}
                def_ranges.update(got)
                log = log + dlog
        rest = {n: e for n, e in dict(fallback, **defs).items() if n not in def_ranges and n not in refused}
        try:
            fwd = W.bound(rest, dict(known, **{d: (lo, hi) for d, (lo, hi, _) in def_ranges.items()}))
        except W.ForwardError as e:
            # A WITNESS BEFORE GIVING UP (2026-10-20, the interior showcase i03: a mount resonating at the band's
            # edge, T = 11 at a CORNER, was left OPEN — the reading of (1 - r*r)*(1 - r*r) touched zero, and the
            # design was dropped before any point was tried). A failing point needs no range: found and recomputed
            # exactly, it refutes; none found, the design stays OPEN as before.
            try:
                hit_ = _witness_first(laws, fixed, boxes, derived, reqs, violation)
            except (C.CheckError, ZeroDivisionError):
                hit_ = None
            if hit_:
                note(design, hit_[0], hit_[1], *hit_[2])
                continue
            undecided += 1
            undecided_before_earned += 1
            open_why[id(design)] = f"a definition could not be bounded: {e}"
            continue
        ztl_gap = set(rest)                         # bounded by the stand because ZTL could not
        ztl_defs = set(def_ranges)                  # definitions ZTL itself bounded
        rng = {d: (lo, hi) for d, (lo, hi, _) in ranges.items()}
        rng.update({d: (lo, hi) for d, (lo, hi, _) in def_ranges.items()})
        rng.update(fwd)             # whatever ZTL left unbounded, bounded by the stand
        cons = B.windows(reqs, boxes, fixed)     # least favourable bounds, MERGED per quantity (a dict by quantity
                                                 # kept only the last requirement: a false EARNED, 2026-10-11)
        ok = all(r["quantity"] in rng and B.inside(*rng[r["quantity"]], cons[r["quantity"]]) for r in reqs)
        # the checker CONFIRMS each implicit range by its own exclusion first; a confirmed range is then its
        # own to use for the definitions that lean on it (2026-10-10: its own enclosure was looser than ZTL's
        # pulled-in one, and the disagreement read as a STAND FAULT)
        impl_confirmed = {}
        if impl and MODE.DEV[0]:
            cbox = {k: (v, v) for k, v in fixed.items()}
            cbox.update(boxes)
            for n in impl:
                lo_n, hi_n, _ = def_ranges[n]
                if C.implicit_excludes(defs[n], cbox, lo_n, hi_n):
                    impl_confirmed[n] = (lo_n, hi_n)
        no_corners = False
        deferred_corners = False
        try:
            if not MODE.DEV[0]:
                # WORK MODE (ustand/mode.py): ZTL's readings decide; corners only for a witness (exact points)
                dbound, cs, corner_hit = {}, None, None
                if ok and not worst_case:
                    cs = []
                elif ok:
                    cs = C.corners(laws, fixed, boxes, derived, couple)  # the worst case of the objective
                else:
                    try:
                        corner_hit = _witness_first(laws, fixed, boxes, derived, reqs, violation)
                        if corner_hit or len(boxes) <= CORNERS_BEFORE_CERT:
                            cs = [] if corner_hit else C.corners(laws, fixed, boxes, derived, couple)
                        else:
                            # CERTIFICATE FIRST (2026-10-20, the duel's interior peak: 16 tolerances, 65 536 exact
                            # corners = 94 % of 25 s, then a certificate EARNED it in 0.4 s): the corners are read
                            # only if the certificate leaves a requirement unshown (below) — the same witnesses,
                            # later, so nothing is lost
                            cs, deferred_corners = [], True
                    except (C.CheckError, ZeroDivisionError):
                        cs = []             # no witness by corners here; the certificate search comes next
            else:
                try:
                    dbound, cs = C.bound_definitions(laws, fixed, boxes, derived, implicit_ranges=impl_confirmed,
                                                       lazy=True, couple=couple)
                except C.CheckError as e:
                    if "corners too many" not in str(e) or worst_case:
                        raise
                    dbound, cs, no_corners = {}, [], True     # past the corner wall: certificates only (below)
                corner_hit = None
            if cs is None:
                # SPEED (blind test 5, c03: 4016 corners x 4 implicit roots, ~110 s per design). The corners are
                # needed only (a) for a witness when the readings do not show the design, (b) for a worst-case
                # objective. When ZTL showed it and the checker's own bounds of every requirement quantity are
                # inside, every corner is inside too (the bounds enclose them): no corner is read. For a witness,
                # a GREEDY walk first (each quantity flipped to its other end when that makes the requirement
                # worse: n readings, not 2^n); all corners only if it finds none.
                if ok and not worst_case and all(r["quantity"] in defs and r["quantity"] in dbound
                                                 and B.inside(*dbound[r["quantity"]], cons[r["quantity"]])
                                                 for r in reqs):
                    cs = []
                else:
                    corner_hit = _witness_first(laws, fixed, boxes, derived, reqs, violation)
                    try:
                        cs = [] if corner_hit else C.corners(laws, fixed, boxes, derived, couple)
                    except C.CheckError as e:
                        # PAST THE CORNER WALL (2026-10-15): more than 16 tolerances in one coupled group. Not
                        # given up: every requirement must then be CERTIFIED and the certificate re-checked by the
                        # checker's own means (below); a requirement without one stays OPEN, said
                        if "corners too many" not in str(e) or worst_case:
                            raise
                        cs, no_corners = [], True
        except (C.CheckError, ZeroDivisionError) as e:
            # e.g. a denominator that spans zero over the tolerances (blind test b10, 2026-10-10):
            # the checker has no value at some corner, so nothing is shown either way
            undecided += 1
            undecided_before_earned += 1
            checker_notes.append(f"{_design_out(design)}: the checker could not evaluate it: {e}")
            open_why[id(design)] = f"the checker could not evaluate it: {e}"
            continue
        for p, v in cs if corner_hit is None else []:
            hit = violation(v, dict(fixed, **p))
            if hit:
                corner_hit = (p, v, hit)
                break
        certified, no_range_why = {}, {}
        if (not ok or no_corners) and corner_hit is None:
            # FIRST the judge's honesty: an exact corner range leaving a requirement that no corner
            # violates is a STAND FAULT — a certificate must never paper over it (2026-10-09: the
            # Z6 path earned the design under a lying judge, the mutation test caught it)
            exact_fail = [r for r in reqs if r["quantity"] not in defs and r["quantity"] in ranges
                          and ranges[r["quantity"]][2] == "corners" and r["quantity"] in rng
                          and not B.inside(*rng[r["quantity"]], cons[r["quantity"]])
                          and not _bound_shares_box(r, boxes)]
            if exact_fail:
                return {"verdict": "STAND FAULT",
                        "why": "an exact range leaves a requirement, but no corner violates it",
                        "design": _design_out(design)}
            # the extreme may sit INSIDE the box: the stand SEARCHES a certificate, ZTL checks it
            got = _certify(reqs, rng, cons, linear, defs, derived, fixed, boxes, laws, ranges, dbound, force=no_corners)
            if "witness" in got:
                p, v = got["witness"]
                note(design, p, v, *violation(v, dict(fixed, **p)))
                continue
            if "fault" in got:
                return {"verdict": "STAND FAULT", "why": got["fault"], "design": _design_out(design)}
            if "why" in got:
                no_range_why.update(got["why"])
            if "unconfirmed" in got:
                unconfirmed.append(got["unconfirmed"])   # ZTL accepted, the checker could not: not earned
            if "certified" in got:
                certified = got["certified"]
                for q, (lo, hi) in got["ranges"].items():
                    rng[q] = (lo, hi)
                ok = all(r["quantity"] in rng and B.inside(*rng[r["quantity"]], cons[r["quantity"]]) for r in reqs)
        if deferred_corners and not ok:
            # the certificate left a requirement unshown: the deferred corners, for a witness
            try:
                for p_, v_ in C.corners(laws, fixed, boxes, derived, couple):
                    hit = violation(v_, dict(fixed, **p_))
                    if hit:
                        corner_hit = (p_, v_, hit)
                        break
            except (C.CheckError, ZeroDivisionError):
                pass
            if corner_hit:
                note(design, corner_hit[0], corner_hit[1], *corner_hit[2])
                continue
        if ok and MODE.DEV[0] and no_corners:
            # past the corner wall: only a re-checked certificate confirms a requirement
            missing = sorted({r["quantity"] for r in reqs if r["quantity"] not in certified})
            if missing:
                unconfirmed.append(f"{_design_out(design)}: {len(boxes)} tolerances — past the checker's corners "
                                   f"({C.MAX_CORNER_PARAMS} per coupled group), and no certificate it re-checked for "
                                   f"{', '.join(missing)}")
                ok = False
        elif ok and MODE.DEV[0]:
            # the checker, independently: every corner inside (point-wise), exact linear ranges
            # equal to its corner ranges, its own bound of each definition inside the requirement
            agree = all(violation(v, dict(fixed, **p)) is None for p, v in cs)
            wider = []      # the checker's OWN bound of a definition is wider than the requirement: not confirmed,
            #                 which is not a disagreement (audit 2026-10-13, fz-3020: tight through min/max, every
            #                 corner inside, the checker's interval bound [0.0025, 15.7] against y <= 1.77 — a STAND FAULT
            #                 on a correct EARNED)
            for r in reqs:
                q = r["quantity"]
                if q in certified:
                    pass        # the certificate: checked by ZTL AND re-checked by the checker (_certify)
                elif q in defs:
                    if not B.inside(*dbound[q], cons[q]):
                        wider.append(q)
                elif q in ztl_gap:
                    pass        # a linear quantity: every corner inside (checked above) is its true range
                elif ranges[q][2] == "corners":
                    agree = agree and (min(v[q] for _, v in cs), max(v[q] for _, v in cs)) == ranges[q][:2]
                elif ranges[q][2] == "critical":
                    # the extreme may be inside: the corners can only be checked to lie within it
                    agree = agree and all(ranges[q][0] <= v[q] <= ranges[q][1] for _, v in cs)
            suspect = not agree or bool(wider)     # a wider own bound still sends the checker after a hidden root
            if suspect and set(impl) - set(impl_confirmed):
                # first: is ZTL's range WRONG? a root the checker proves outside it at a corner is a fault
                for n in sorted(set(impl) - set(impl_confirmed)):
                    lo_n, hi_n, _ = def_ranges[n]
                    for p, _v in cs:
                        root = C.implicit_root_outside(defs[n], dict(fixed, **p), lo_n, hi_n)
                        if root:
                            return {"verdict": "STAND FAULT",
                                    "why": f"ZTL's range of the implicit {n} misses a root the checker proves at a "
                                           f"corner (a sign change in [{_approx(root[0])}, {_approx(root[1])}])",
                                    "design": _design_out(design)}
            if suspect and set(impl) - set(impl_confirmed):
                # not a fault: the checker could not confirm an implicit range with its own means
                unconfirmed.append(f"{_design_out(design)}: the checker could not confirm the implicit range of "
                                   f"{', '.join(sorted(set(impl) - set(impl_confirmed)))} by its own exclusion")
                ok = False
            elif not agree:
                return {"verdict": "STAND FAULT",
                        "why": "the stand showed the design inside its requirements, the checker disagrees",
                        "design": _design_out(design)}
            elif wider:
                # every corner inside and every exact range equal: only the checker's own bound is too wide to confirm
                # ZTL's — not earned in dev mode (undecided), never a fault
                unconfirmed.append(f"{_design_out(design)}: the checker's own bound of {', '.join(sorted(wider))} is "
                                   f"wider than the requirement (every corner inside) — ZTL's range not confirmed")
                ok = False
        if ok:
            earned_ids.add(id(design))
            # each EARNED design's requirement ranges, for the listing (real r06: only the first one showed them)
            earned_ranges[id(design)] = {r["quantity"]: _s([x / qscale[r["quantity"]] for x in rng[r["quantity"]][:2]])
                                         for r in reqs if r["quantity"] in rng and not isinstance(rng[r["quantity"]], str)
                                         and None not in rng[r["quantity"]][:2]}
            this = (design, rng, ranges, defs, dbound, disposition, log, ztl_gap, fixed, boxes, ztl_defs, certified,
                    impl_how)
            if earned is None:
                earned = this
            if worst_case:
                # Ub: a proved upper bound of the objective over the box (the readings' ranges);
                # L: its largest value at the checker's corners — the worst case reaches at least L
                known_o = {n: (v, v) for n, v in fixed.items()}
                known_o.update(boxes)
                known_o.update(rng)
                try:
                    Ub = W._iv(obj_node, known_o)[1]
                except (W.ForwardError, ZeroDivisionError):
                    Ub = None
                L = None
                for p, v in cs:
                    env = {n: (x, x) for n, x in fixed.items()}
                    env.update({n: (x, x) for n, x in p.items()})
                    env.update({n: (x if isinstance(x, tuple) else (x, x)) for n, x in v.items()})
                    try:
                        lo_c = C._ivl(obj_node, env)[0]
                    except (C.CheckError, ZeroDivisionError):
                        continue
                    L = lo_c if L is None else max(L, lo_c)
                earned_all[id(design)] = (this, Ub, L)
            if not report_all:
                break
            continue
        if corner_hit:
            note(design, corner_hit[0], corner_hit[1], *corner_hit[2])
        else:
            if impl and id(design) not in tight_now and any("corner" not in impl_how.get(n, "") for n in impl):
                tight_now.add(id(design))       # the second pass: the same design, implicit edges pulled in
                del unconfirmed[und_unconf:]
                i_design -= 1
                judged -= 1
                continue
            undecided += 1      # a nonlinear definition may peak inside the box: not shown either way
            undecided_before_earned += 1
            # SAY WHICH (blind b06, 2026-10-10: "OPEN with no reason" — the author could not tell what was undecided)
            parts = []
            for r in reqs:
                q = r["quantity"]
                label = r.get("why") or f"{q} {r['op']} {r['value']}"
                if q not in rng:
                    parts.append(f"{label}: {q} has no proved range" + (f" ({no_range_why[q]})" if q in no_range_why else ""))
                elif not B.inside(*rng[q], cons[q]):
                    lo_q, hi_q = rng[q]
                    sc = qscale[q]
                    parts.append(f"{label}: {q} proved within [{_approx(lo_q / sc)}, {_approx(hi_q / sc)}] "
                                 f"{b['quantities'][q].get('unit', '')}, which reaches past the bound, yet no corner "
                                 "violates it — the extreme may lie inside the box and no certificate decided it"
                                 + (" (certificates prove only <= and >=: a non-strict bound lets one decide)"
                                    if r["op"] in ("<", ">") else ""))
            if unconfirmed and unconfirmed[-1] and len(unconfirmed) > und_unconf:
                parts.append(f"a certificate ZTL accepted was not confirmed by the checker: {unconfirmed[-1]}")
            open_why[id(design)] = "; ".join(parts) or "not decided either way"

    if prev_design is not None:
        finalize(prev_design, und_mark)
    if pre is not None:
        pre.close()                 # the workers stop here
    worst_note = None
    if worst_case and earned_all:
        bounded = [(Ub, i, t, L) for i, (t, Ub, L) in earned_all.items() if Ub is not None]
        if bounded:
            Ub_best, i_best, earned, L_best = min(bounded, key=lambda x: x[0])
            rivals = [t[0] for Ub, i, t, L in bounded if i != i_best and (L is None or L < Ub_best)]
            unbounded = [t[0] for i, (t, Ub, L) in earned_all.items() if Ub is None]
            opens = sum(1 for o in outcomes if o["verdict"] == "OPEN")
            optimal = not rivals and not unbounded and opens == 0
            worst_note = {"minimize": b["objective"]["minimize"], "case": "worst",
                          "value": _s(Ub_best / _obj_scale(b)), **_obj_unit(b), "value_is": "a proved upper bound of the worst case over the box",
                          "reached_at_least": _s(L_best / _obj_scale(b)) if L_best is not None else None,
                          "optimal": optimal,
                          "note": ("its proved worst case is at or below the worst case every other earned design "
                                   "reaches at a corner of its box; the rest refuted, none open" if optimal else
                                   "best by the proved bound; NOT proved optimal: " + "; ".join(
                                       ([f"{len(rivals)} earned design(s) whose worst case may be lower "
                                         f"({', '.join(_label(d) for d in rivals[:3])})"] if rivals else [])
                                       + ([f"{len(unbounded)} earned with the objective unbounded"] if unbounded else [])
                                       + ([f"{opens} design(s) OPEN"] if opens else [])))}
        else:
            earned = None
    if report_all and not worst_case:       # OPEN only BEFORE the first EARNED counts against "optimal"
        first = next((i for i, o in enumerate(outcomes) if o["verdict"] == "EARNED"), len(outcomes))
        undecided_before_earned = sum(1 for o in outcomes[:first] if o["verdict"] == "OPEN")
    out = {"stand": "ztl-stand/1", "judge": f"ZTL {J.ztl_commit()}",
           **({"excluded_by_where": _excluded(b, all_designs, pr)} if b.get("where") else {}),
           "designs_tried": tried, "failed_at_nominal": pruned, "judged": judged,
           "undecided": undecided, "units": units_note or "checked: every law's dimensions agree"}
    if pr is not None:
        outcomes = _pruned_outcomes(pr, b) + outcomes
        out["refuted_by_groups"] = sum(abs(p[3]) for p in pr[1])
        out["groups_pruned"], out["groups_read"] = len(pr[1]), pr[2]
    out["designs"], out["designs_count"], cut = _listing(outcomes)
    if any(o["verdict"] == "REFUTED" for o in outcomes):
        # blind test 2 (c05, c07): "by" read as the worst shortfall — it is the one at the witness found
        # blind test 5 (c02, c07, c09): still read as the worst case — renamed `by_at_witness`
        out["designs_by"] = ("'by_at_witness' is the overshoot at the witness point the stand found (the nominal point or a "
                             "corner), in the quantity's own unit — the worst case may be larger")
    if cut:
        out["designs_not_listed"], out["listing"] = cut, "earned first, then open, then refuted"
    if unconfirmed:
        out["certificates_unconfirmed"] = unconfirmed[:5]
    if checker_notes:
        out["checker_could_not_evaluate"] = checker_notes[:5]
    back = lambda q, v: tuple(x / qscale[q] for x in v) if isinstance(v, tuple) else v / qscale[q]   # SI -> own unit
    if earned:
        design, rng, ranges, defs, dbound, disposition, log, ztl_gap, fx_e, bx_e, ztl_defs, certified, impl_how = earned
        if worst_note:
            out["objective"] = worst_note
        elif objective:
            out["objective"] = {"minimize": objective[0], "value": _s(objective[1](design) / _obj_scale(b)), **_obj_unit(b),
                                "optimal": (undecided_before_earned == 0),
                                "note": ("every cheaper design was refuted" if undecided_before_earned == 0 else
                                         f"{undecided_before_earned} cheaper design(s) undecided: optimal only among "
                                         "the decided ones")}
            ties = _ties(all_designs, design, objective[1], outcomes)
            if ties:
                out["objective"]["ties"] = ties
        how = {}
        for r in reqs:
            q = r["quantity"]
            if q in certified:
                how[q] = (f"ZTL, certificate checked exactly ({certified[q]['pieces']} pieces; found by the stand's "
                          "search, the extreme may lie inside the box"
                          + ("; ZTL solved the linear system itself" if certified[q]["system"] else "")
                          + (f"; a SUM proved term by term ({certified[q]['split']} terms, each over its own data, the "
                             "bounds added — sound; a datum shared by terms may make it wider)"
                             if certified[q].get("split") else "")
                          + ("; the implicit quantities read as roots that move with the box, their brackets and "
                             "the implicit-function derivative checked (Lean: ZImplicit.implicit_monotone_leaf)"
                             if certified[q].get("implicit") else "")
                          + ("); the checker re-checked the same certificate from the laws with its own "
                             "derivative and interval arithmetic" if MODE.DEV[0] else ")"))
            elif q in impl_how:
                how[q] = (f"ZTL, implicit law: a root-exclusion certificate (searched by the stand) checked by the "
                          f"kernel — {impl_how[q]}" + _ck(q, dbound, back, "enclosure"))
            elif q in defs and q in ztl_defs and any(l.startswith(f"{q} -> ") and "affine in the system" in l
                                                     for l in log):
                how[q] = ("ZTL, the definition read through the system's dependence on the data — each datum at the "
                          "end its coefficient's sign picks, the rest by interval reading (sound)" + _ck(q, dbound, back))
            elif q in defs and q in ztl_defs:
                how[q] = ("ZTL, interval reading of the definition (" + _wide(rng, q) + ")" + _ck(q, dbound, back))
            elif q in defs:
                how[q] = ("outside ZTL: interval bound over ZTL's ranges (" + _wide(rng, q) + ")" + _ck(q, dbound, back))
            elif q in ztl_gap:
                how[q] = ("outside ZTL: ZTL left it unbounded (a product of toleranced quantities); "
                          "interval bound by the stand, every corner checked inside")
            else:
                how[q] = {"corners": "ZTL, exact at the corners",
                          "critical": "ZTL, exact at the corners and the critical points of a shared parameter"
                          }.get(ranges[q][2], "ZTL, outer range")
        out.update(verdict="EARNED", design=_design_out(design),
                   guaranteed={r["quantity"]: [_s(back(r["quantity"], x)) if x is not None else ("-inf", "inf")[i]
                                               for i, x in enumerate(rng[r["quantity"]])] for r in reqs},
                   guaranteed_unit={r["quantity"]: b["quantities"][r["quantity"]].get("unit", "") for r in reqs},
                   # an end a CERTIFICATE proved is the requirement's bound, not the computed extreme (blind test 3,
                   # c03/c05: 6.8 L read as the minimum, the true one 7.97 L)
                   **({"guaranteed_ends": {q: "an end equal to the requirement's bound is what a certificate PROVED "
                                              "(the quantity stays on its side of it); the true extreme may lie "
                                              "further inside" for q in certified}} if certified else {}),
                   how=how, requirements=reqs_given,
                   rests_on=f"ZTL disposition {disposition}: the tolerances and ranges are the brick's data (the given "
                            "quantities and the catalog's datasheet values) — taken as stated, not verified",
                   checker=("every corner of the tolerance box recomputed exactly and inside; exact ranges equal; "
                            "definitions bounded by the checker's own interval arithmetic" if MODE.DEV[0] else
                            "not run (work mode: ZTL's verdict; --dev runs the independent checker)"),
                   judge_log=log[:6])
    elif worst_case and earned_all:
        out.update(verdict="OPEN", why="designs were earned, but the worst case of the objective could not be bounded "
                                       "for any of them")
    elif undecided:
        out.update(verdict="OPEN", why=f"{undecided} design(s) could not be decided and none was earned")
    elif closest is None and pr is not None and pr[1]:
        out.update(verdict="REFUTED", why="every design is refuted — by whole groups, each read by ZTL and by the "
                                          "checker past a bound over the group (no single witness point)")
    else:
        over, design, point, values, r = closest
        if PL.STATE.get("raw"):             # a worker's single-design run: the witness, exactly, for the main loop
            return {"verdict": "REFUTED", "_raw": (point, values, reqs.index(r), over, pruned > 0)}
        fx, bx, dv, _ = frame(b, design)
        q = r["quantity"]
        rs = {} if brief else reasons(laws, fx, bx, dv, point, r, B.req_interval(r, bx, fx))
        for k in ("spread_over_tolerances", "window"):
            if k in rs:
                rs[k] = _s([back(q, B.num(x.split(" ")[0])) for x in rs[k]])
        for c in rs.get("largest_contributors", []):
            c["moves_it_by"] = _s(back(q, B.num(c["moves_it_by"].split(" ")[0])))
        out.update(verdict="REFUTED",
                   why="every design in the catalog violates a requirement at a concrete point",
                   closest_design=_design_out(design),
                   closest_by=("the smallest overshoot found, each in its own requirement's unit — overshoots of "
                               "different requirements are not comparable (blind test 4, c11)"),
                   # built-in constants (pi's bracket) are not part of the witness a reader acts on (real r05)
                   its_violating_point={k.replace("__", "."): v for k, v in
                                        _s({n: x / _point_scale(b, design, n, qscale) for n, x in point.items()
                                            if n not in B.CONSTANTS}).items()},
                   point_units={k.replace("__", "."): _point_unit(b, design, k) for k in point if k not in B.CONSTANTS},
                   value_there=_s({q: back(q, values[q])}),
                   unit=b["quantities"][q].get("unit", ""),
                   requirement=reqs_given[reqs.index(r)],
                   overshoot=_s(back(q, over)),
                   reasons=rs,
                   checker="the violating point recomputed exactly (rational arithmetic, no judge code)")
        if not brief and len(reqs_given) > 1:
            out["each_requirement"] = _each_requirement(b, design, reqs_given)
    if out.get("verdict") == "REFUTED":
        # THE CORE (2026-10-18): the requirement each design (each pruned group) fails — every design fails one of
        # them, so any set holding them all is refuted the same way. Only when every design is accounted for.
        def _core():
            if not all(id(d_) in refuted_by for d_ in all_designs):
                return None
            core = {reqs.index(refuted_by[id(d_)][0]) for d_ in all_designs}
            for _g, r_, _rg, _n in (pr[1] if pr else []):
                rr = {k: v for k, v in r_.items() if k not in ("_check", "value")}
                j_ = next((j for j, x in enumerate(reqs_given)
                           if {k: v for k, v in x.items() if k != "value"} == rr), None)
                if j_ is None:
                    return None
                core.add(j_)
            return sorted(core)
        core = _core()
        if core is not None:
            out["_core"] = core
        if conflicts and out.get("its_violating_point") is not None:
            out["minimal_conflicts"] = minimal_conflicts(b, out.get("_core"))
    return out


def _each_requirement(b, design, reqs_given):
    """Every requirement's OWN verdict on the refuted (closest) design — a REFUTED names one failing requirement and
    says nothing of the others (real round 2, s03 split its brick by hand to see them; the curator's "да",
    2026-10-12). Each is the design pinned, with that requirement alone."""
    # A LISTING ON A SMALL BUDGET (2026-10-16, the 28-datum motor): the refutation was found in a second, then the
    # listing tried to PROVE every other requirement with the full certificate budget. Each row gets EACH_REQ_PIECES
    # (a COUNT, not a clock: the listing must not depend on the machine — the curator's rule for minimal_conflicts)
    from . import linsearch as _LS
    keep = (K.MAX_PIECES, _LS.MAX_PIECES)
    K.MAX_PIECES, _LS.MAX_PIECES = EACH_REQ_PIECES, EACH_REQ_PIECES
    # IN PARALLEL with --jobs (2026-10-20, the bridge girder: 91 requirements, 836 of 842 s were this listing, row by
    # row on one core while the verdict took 6 s). The rows are independent; the workers fork after the budget is
    # set, compute them in order, and the list is the same as the serial one.
    PL.STATE["each_req"] = (b, design, list(reqs_given))
    try:
        with PL.prefetch(_each_req_row, len(reqs_given)) as rows:
            return list(rows)
    finally:
        K.MAX_PIECES, _LS.MAX_PIECES = keep
        PL.STATE.pop("each_req", None)


def _each_req_row(i):
    """Row i of each_requirement (a worker's unit: module level, so the pool can call it)."""
    b, design, reqs = PL.STATE["each_req"]
    return _each_one(b, design, reqs[i])


EACH_REQ_PIECES = 200       # each row of the listing after a REFUTED: a certificate search budget (pieces)


def _each_one(b, design, r):
    """One requirement's own verdict on the pinned design (a row of each_requirement)."""
    one = _pinned(b, design)
    one["requirements"] = [r]
    try:
        res = _run(one, conflicts=False, brief=True, loaded=True)
    except Stopped:
        raise
    except Exception as e:                      # noqa: BLE001 — a listing, never the verdict
        res = {"verdict": "OPEN", "why": f"not judged alone: {type(e).__name__}"}
    row = {"requirement": r, "verdict": res.get("verdict")}
    if res.get("verdict") == "EARNED" and res.get("guaranteed"):
        row["guaranteed"] = res["guaranteed"]
    elif res.get("verdict") == "REFUTED":
        row["overshoot"] = res.get("overshoot")
    elif res.get("why"):
        row["why"] = f"{res['why']} (the listing's budget: {EACH_REQ_PIECES} pieces per requirement)"
    return row


def _implicit_goal(n, reqs, boxes, fixed):
    """The range the requirements on n itself ask for (least favourable bounds), or None."""
    lo = hi = None
    for r in reqs:
        if r["quantity"] == n:
            a, c = B.req_interval(r, boxes, fixed)
            lo = a if lo is None or (a is not None and a > lo) else lo
            hi = c if hi is None or (c is not None and c < hi) else hi
    return (lo, hi) if (lo is not None or hi is not None) else None


def _implicit_matters(n, rng_n, reqs, defs, laws, fixed, boxes, ranges):
    """Would a tighter range of the implicit n decide something? Its own requirement is not met by the plain
    range, or a requirement on a quantity defined through n is not met by the forward reading with it."""
    for r in reqs:
        if r["quantity"] == n and not B.inside(*rng_n, B.req_interval(r, boxes, fixed)):
            return True
    lean = {n}
    grew = True
    while grew:
        grew = False
        for d, e in defs.items():
            if d not in lean and set(re.findall(r"[A-Za-z_]\w*", ast.unparse(e))) & lean:
                lean.add(d); grew = True
    dep = [r for r in reqs if r["quantity"] in lean and r["quantity"] != n]
    if not dep:
        return False
    known = {k: (v, v) for k, v in fixed.items()}
    known.update(boxes)
    known.update({d: (lo, hi) for d, (lo, hi, _) in ranges.items()})
    known[n] = rng_n
    try:
        got = W.bound({d: e for d, e in defs.items() if d in lean and d != n}, known)
    except W.ForwardError:
        return True
    return any(r["quantity"] not in got or not B.inside(*got[r["quantity"]], B.req_interval(r, boxes, fixed))
               for r in dep)


def _independent_hit(laws, point, derived, reqs):
    """(values, hit) from the laws that lean on no implicit quantity, at one point — or (None, None)."""
    lean = {l.split("==")[0].strip() for l in laws if "implicit(" in l}
    if not lean:
        return None, None
    grew = True
    while grew:                                     # everything defined through an implicit quantity
        grew = False
        for l in laws:
            lhs = l.split("==")[0].strip()
            if lhs not in lean and set(re.findall(r"[A-Za-z_]\w*", l)) & lean:
                lean.add(lhs); grew = True
    keep = [l for l in laws if not set(re.findall(r"[A-Za-z_]\w*", l)) & lean]
    sub = [d for d in derived if d not in lean]
    mine = [r for r in reqs if r["quantity"] in sub]
    if not keep or not mine:
        return None, None
    try:
        values = C.solve_at(keep, point, sub)
    except (C.CheckError, ZeroDivisionError):
        return None, None
    for r in mine:                                  # the same rule as violation(): the nearer end, certain
        iv = _req_at(r, point)
        v = values[r["quantity"]]
        if B.violates(v, iv):
            a, c = iv
            lo, hi = v if isinstance(v, tuple) else (v, v)
            low_side = a is not None and (hi <= a if getattr(iv, "strict_lo", False) else hi < a)
            return values, (r, (a - hi) if low_side else (lo - c))
    return None, None


def _is_implicit(e):
    return isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id == "implicit"


def _witness_first(laws, fixed, boxes, derived, reqs, violation):
    """A failing point: the FLOAT search first (fwitness — every candidate re-solved exactly); the exact greedy walk
    only when the floats could not read the laws. MEASURED 2026-10-16 (the 28-datum motor, a design that holds):
    the exact walk was 54 % of the run — 540 exact solutions, each with an implicit root — and found nothing."""
    hit = FW.find(laws, fixed, boxes, derived, reqs, violation, _req_at, C.solve_at)
    if hit is None and not FW.RAN[0]:
        hit = _greedy_corner(laws, fixed, boxes, derived, reqs, violation)
    return hit


GREEDY_SOLVE_MAX = 1.0      # seconds for one exact solution, above which the exact greedy walk is skipped


def _greedy_corner(laws, fixed, boxes, derived, reqs, violation):
    """A violating CORNER found by a greedy walk, or None: per requirement, from the all-low and the all-high corner,
    each toleranced quantity flipped to its other end when that makes the requirement worse — n + 1 exact
    solutions instead of 2^n. A corner it returns is checked like any other (violation at that exact point);
    finding none proves nothing, and the caller then reads every corner."""
    names = sorted(boxes)
    wide = [n for n in names if boxes[n][0] < boxes[n][1]]

    def badness(r, vals, pt):
        v = vals.get(r["quantity"])
        if v is None:
            return None
        lo, hi = v if isinstance(v, tuple) else (v, v)
        a, c = _req_at(r, dict(fixed, **pt))
        parts = ([hi - c] if c is not None else []) + ([a - lo] if a is not None else [])
        return max(parts) if parts else None

    # ONE SOLUTION PER POINT, shared by every requirement's walk (2026-10-20, the bridge girder: 91 requirements x 2
    # starts x 57 solutions = ~10 000 exact solutions of a 141-unknown system per design, 97 % of the time — and the
    # walks share their start corners and their first steps). A point's solution does not depend on which
    # requirement asked for it; the walk and its result are unchanged.
    seen = {}

    def solve(pt):
        k = tuple(pt[n] for n in names)
        if k in seen:
            return seen[k]
        try:
            v = C.solve_at(laws, dict(fixed, **pt), derived)
        except (C.CheckError, ZeroDivisionError):
            v = None
        seen[k] = v
        return v
    import time as _time
    for r in reqs:
        for start in (0, 1):
            pt = {n: boxes[n][start] for n in names}
            t0 = _time.monotonic()
            vals = solve(pt)
            if _time.monotonic() - t0 > GREEDY_SOLVE_MAX:
                # one exact solution too dear for n + 1 of them (Muhanna's benchmark 1: 230 unknowns, 26.9 s each,
                # 420 parameters -> 377 min per requirement, MEASURED 2026-10-16); a large LINEAR system's own walk
                # (linsearch.greedy_vertex, floats, its find re-solved exactly) comes with the certificate search
                return None
            if vals is None:
                continue
            cur = badness(r, vals, pt)
            for n in wide:
                trial = dict(pt, **{n: boxes[n][1] if pt[n] == boxes[n][0] else boxes[n][0]})
                tv = solve(trial)
                if tv is None:
                    continue
                tb = badness(r, tv, trial)
                if tb is not None and (cur is None or tb > cur):
                    pt, vals, cur = trial, tv, tb
            hit = violation(vals, dict(fixed, **pt))
            if hit:
                return pt, vals, hit
    return None


def _certify_row(i):
    """Requirement i of _certify (a worker's unit: module level, so the pool can call it)."""
    one, reqs = PL.STATE["certify"]
    return one(reqs[i])

def _range_row(i):
    """The proved range of unknown i (a worker's unit: module level, so the pool can call it)."""
    core_laws, core_u, used, fixed, boxes = PL.STATE["ranges"]
    return K.prove_linear_range(core_laws, core_u, used[i], fixed, boxes)

def _wide(rng, q):
    """'sound, may be wide' — or, for a single value, that it is exact (real r05: said of a point)."""
    r = (rng or {}).get(q)
    if r is not None and not isinstance(r, str) and len(r) >= 2 and r[0] == r[1]:
        return "a single value, exact"
    return "sound, may be wide"


def _ck(q, dbound, back, word="bound"):
    """"; checker's own bound [..]" — when the checker ran (dev mode) and bounded q."""
    if q not in (dbound or {}):
        return ""
    return f"; checker's own {word} {_s(list(back(q, dbound[q])))}"


def _certify(reqs, rng, cons, linear, defs, derived, fixed, boxes, laws, ranges, dbound=None, force=False):
    """For each requirement the readings did not show: search a certificate (ustand/certify.py),
    ZTL checks it. {"certified": {q: pieces}, "ranges": {q: range}} when all are proved;
    {"witness": (point, values)} when a point inside the box fails (recomputed by the checker);
    {} otherwise."""
    impl = {n for n, e in defs.items() if _is_implicit(e)}
    all_laws, all_derived = laws, derived
    impl_g = {}                     # J6: each implicit quantity's law g (== 0), its placeholder renamed back
    for n in impl:
        call = defs[n]
        ph = call.args[0].id
        g = ast.parse(re.sub(rf"\b{re.escape(ph)}\b", n, ast.unparse(call.args[1])), mode="eval").body
        impl_g[n] = g
    if impl:
        # G6: an IMPLICIT quantity enters the certificate as a BOX of its proved range — sound, as its
        # true value at every point of the box lies in that range (ZTL's certificate); kept as ONE
        # variable, so P = rho*g*Q*(H0 - a*Q^2)/eta keeps Q correlated with itself (2026-10-10, the
        # pump: the interval reading of Q*H lost it and left the design OPEN). The checker confirms
        # the range with its OWN enclosure first.
        cbox = {k: (v, v) for k, v in fixed.items()}
        cbox.update(boxes)
        for n in impl if MODE.DEV[0] else []:
            if not C.implicit_excludes(defs[n], cbox, *rng[n]):
                return {"unconfirmed": f"{n}: the checker could not exclude a root outside ZTL's range "
                                       f"{_s(list(rng[n]))} with its own readings"}
        boxes = dict(boxes, **{n: rng[n] for n in impl})
        defs = {k: v for k, v in defs.items() if k not in impl}
        derived = [d for d in derived if d not in impl]
        laws = [l for l in laws if l.split("==")[0].strip() not in impl]
        reqs = [r for r in reqs if r["quantity"] not in impl]   # its own range decides it: nothing to certify
    explicit = dict(W.explicit(linear, set(derived)), **defs)
    certified, shown = {}, {}       # (not `ranges`: that is ZTL's, the parameter — 2026-10-10 the
    def _one(r):                    #  shadowing switched the exact-range guard below off unnoticed)
        certified, shown = {}, {}   # this requirement's rows only; merged below in order
        q = r["quantity"]
        a, c = cons[q]
        lo, hi = rng.get(q, (None, None))          # no range: ZTL refused it — both ends need a certificate
        # force (--dev past its corner wall, 2026-10-15): every finite bound is certified, so that the checker has
        # a certificate to re-check where it has no corners
        claims = ([(">=", a)] if a is not None and (force or lo is None or lo < a) else []) + \
                 ([("<=", c)] if c is not None and (force or hi is None or hi > c) else [])
        if not claims:
            return ("ok", certified, shown)        # already shown by the readings (a STRICT bound too: B.inside honours strictness)
        if r["op"] in ("<", ">"):
            return ("ret", {})       # a STRICT bound still to show: certificates prove <= and >= only. (It returned {}
                            # BEFORE looking whether anything was left to show — a law's domain "valid: > 0",
                            # already met, switched every certificate of the design off: blind test 2, c06)
        witness_only = False
        if q in ranges and ranges[q][2] == "critical":
            # ZTL's range is exact WITH interior critical points and leaves the requirement while
            # no corner does: a failing point lies INSIDE. Search it (2026-10-10; it was OPEN).
            # A PROOF here would contradict ZTL's own exact range — that is a STAND FAULT.
            witness_only = True
        elif q in ranges and ranges[q][2] and not force:
            return ("ret", {})   # exact at the corners: nothing to certify — ZTL decides
        lin_unknowns = [d for d in derived if d not in defs]
        if q in explicit:
            text, left = K.expression(q, explicit, set(derived))
        elif q in lin_unknowns:
            text, left = q, {q}         # a linear unknown with no law of its own: the system decides it
        else:
            return ("ret", {})
        system = None
        if left:
            # Z6: linear unknowns inside — solved symbolically from the linear laws, so their
            # correlation with the tolerances is kept (a range as a free box would lose it)
            # only the CORE of the system: the unknowns no explicit law gives, from the laws that
            # are not such definitions, with the explicit ones substituted in (t7c: 10 linear
            # unknowns, but N1..N4, s1..s4 are explicit — the core is 2x2 in ux, uy)
            core_u = sorted(u for u in lin_unknowns if u not in explicit)
            core_laws = []
            for law in linear:
                l, rr = law.split("==")
                if l.strip() in explicit and l.strip() not in rr:
                    continue                    # it IS an explicit definition
                lt, _ = K.expression("_lhs", dict(explicit, _lhs=ast.parse(l.strip(), mode="eval").body), set(derived))
                rt, _ = K.expression("_rhs", dict(explicit, _rhs=ast.parse(rr.strip(), mode="eval").body), set(derived))
                core_laws.append(f"{lt} == {rt}")
            # in --dev the checker re-derives a symbolic solution by Cramer's rule only up to C.MAX_CRAMER unknowns;
            # above it the system goes by zlin, whose certificate the checker re-checks in full (2026-10-15: an
            # LM317-like regulator, 6 unknowns, stayed OPEN in --dev — "Cramer's n! terms too many for the checker")
            by_zlin = len(core_u) > K.MAX_SYSTEM or (MODE.DEV[0] and len(core_u) > C.MAX_CRAMER)
            sol = None if by_zlin else K.solve_linear(core_laws, core_u)
            if sol is None and by_zlin:
                lin_laws, lin_u = core_laws, core_u
                if text.strip() != q or q not in core_u:
                    # AN EXPRESSION of the unknowns (2026-10-15): when it is LINEAR in them (Vout = u3 - u5, a current
                    # (u2 - u3)/R), it becomes one more unknown of the same system — q == expression — and zlin
                    # certifies it as it does any unknown; the kernel is unchanged
                    import zlin as _ZL
                    from znumjudge import parse_quantities
                    aug_laws, aug_u = core_laws + [f"{q} == {text}"], core_u + [q]
                    try:
                        _ZL.system(aug_laws, aug_u, parse_quantities(J.sheet(fixed, boxes, aug_u, {}))[0])
                        lin_laws, lin_u = aug_laws, aug_u
                    except (_ZL.LinError, ValueError):
                        lin_laws = None
                if lin_laws is None:
                    # A NONLINEAR expression of the unknowns (P = u*u/G): each unknown it reads gets a PROVED range
                    # from zlin, and enters ZTL's certificate for the expression as a BOX (sound, wider than the
                    # truth: the unknowns' tie to the tolerances is not kept — the implicit quantities' rule, G6)
                    used = [u for u in core_u if re.search(rf"\b{re.escape(u)}\b", text)]
                    boxes2, why_u, nl_pieces = dict(boxes), None, 0
                    # EACH UNKNOWN'S RANGE IS ITS OWN PROOF — in parallel with --jobs (2026-10-20, the bridge girder: the
                    # deflection reads 90 unknowns of a 141-unknown system, 92 % of a design's time, one by one). The
                    # proofs are independent; they are read in order, the first refusal stops the reading as before.
                    PL.STATE["ranges"] = (core_laws, core_u, list(used), fixed, boxes)
                    try:
                        with PL.prefetch(_range_row, len(used)) as grs:
                            got_ranges = list(grs) if PL.JOBS[0] > 1 else None
                    finally:
                        PL.STATE.pop("ranges", None)
                    for iu, u in enumerate(used):
                        gr = got_ranges[iu] if got_ranges is not None else K.prove_linear_range(core_laws, core_u, u,
                                                                                                fixed, boxes)
                        if "range" not in gr:
                            why_u = gr["open"]
                            break
                        if MODE.DEV[0]:
                            for op_u, bd_u, cert_u in gr["certs"]:
                                okc, whyc = C.check_linear_certificate(core_laws, fixed, boxes, core_u, u, op_u, bd_u,
                                                                       cert_u)
                                if not okc:
                                    return ("ret", {"unconfirmed": f"{u} {op_u} {bd_u}: the checker could not re-check "
                                                           f"zlin's certificate: {whyc}"})
                        boxes2[u] = gr["range"]
                        nl_pieces += gr["pieces"]
                    if why_u is not None:
                        return ("ret", {"why": {q: f"it reads {len(core_u)} coupled linear unknowns nonlinearly, and a range "
                                           f"of one could not be proved: {why_u}"}})
                    for op, bound in claims:
                        got = K.prove(text, fixed, boxes2, op, bound)
                        if "proved" not in got:
                            # a failing point of the enlarged box is not a true point (the unknowns are not free)
                            return ("ret", {"why": {q: f"it reads {len(core_u)} coupled linear unknowns NONLINEARLY; their "
                                               f"proved ranges as boxes did not settle {q} {op} {bound} (the ranges lose "
                                               "the unknowns' tie to the tolerances) — a LINEAR expression of them is "
                                               "certified exactly (zlin)"}})
                        if MODE.DEV[0]:
                            okc, whyc = C.check_certificate([f"{q} == {text}"], fixed, boxes2, [q], q, op, bound,
                                                            got["cert"])
                            if not okc:
                                return ("ret", {"unconfirmed": f"{q} {op} {bound}: {whyc}"})
                        nl_pieces += got["proved"]
                    certified[q] = {"pieces": nl_pieces, "system": True, "implicit": False, "split": 0,
                                    "linear": f"zlin: proved ranges of {', '.join(used)} ({len(core_u)} unknowns), "
                                              "then ZTL's certificate over them as boxes"}
                    shown[q] = ((max(lo, a) if lo is not None else a) if a is not None else lo,
                                (min(hi, c) if hi is not None else c) if c is not None else hi)
                    return ("ok", certified, shown)
                # LARGE LINEAR SYSTEMS (2026-10-15, the curator's "да"): no symbolic solution — a certificate over the
                # box, searched outside (linsearch) and checked exactly by the kernel module zlin
                lin_pieces = 0
                for op, bound in claims:
                    got = K.prove_linear(lin_laws, lin_u, q, fixed, boxes, op, bound)
                    if "witness" in got:
                        point = dict({n: (b0 + b1) / 2 for n, (b0, b1) in boxes.items()}, **got["witness"])
                        values = C.solve_at(all_laws, dict(fixed, **point), all_derived)     # the checker, exactly
                        if [rr for rr in reqs if B.violates(values[rr["quantity"]], _req_at(rr, dict(fixed, **point)))]:
                            return ("ret", {"witness": (point, values)})
                        return ("ret", {})
                    if "proved" not in got:
                        return ("ret", {"why": {q: f"one of {len(core_u)} coupled linear unknowns: {got['open']}"}})
                    if MODE.DEV[0]:
                        # the checker, independently: the SAME certificate re-checked with its own means (no code
                        # shared with zlin) — and, up to 2^10 corners, every corner solved exactly as well
                        okc, whyc = C.check_linear_certificate(*_as_checked(got, lin_laws, bound, fixed, boxes, lin_u, q, op))
                        if not okc:
                            return ("ret", {"unconfirmed": f"{q} {op} {bound}: the checker could not re-check zlin's "
                                                   f"certificate: {whyc}"})
                        free = [n for n, (b0, b1) in boxes.items() if b0 != b1]
                        if (1 << len(free)) <= DEV_LIN_CORNERS:
                            for corner in itertools.product(*[boxes[n] for n in free]):
                                env = dict(fixed, **dict(zip(free, corner)))
                                v = C.solve_at(all_laws, env, all_derived)[q]
                                if op == "<=" and v > bound or op == ">=" and v < bound:
                                    return ("ret", {"fault": f"the kernel certified {q} {op} {bound} over the box, yet the "
                                                     f"checker solves {q} = {v} at a corner"})
                    lin_pieces += got["proved"]
                certified[q] = {"pieces": lin_pieces, "system": True, "implicit": False, "split": 0,
                                "linear": f"zlin: {len(core_u)} unknowns" + (", the requirement's expression as one more"
                                          if len(lin_u) > len(core_u) else "") + ", certificate checked exactly"}
                shown[q] = ((max(lo, a) if lo is not None else a) if a is not None else lo,
                            (min(hi, c) if hi is not None else c) if c is not None else hi)
                return ("ok", certified, shown)
            if sol is None or left - set(sol):
                return ("ret", {})
            # ZTL gets the TARGET with the unknowns still in it, and the laws: it solves them itself
            system = (text, core_laws, core_u)
            for u, t in sol.items():
                text = re.sub(rf"\b{re.escape(u)}\b", t, text)
            text = K.simplify(text)
        # A FIXED ZERO folded away (2026-10-12, blind test 5 c11 by scenario cuts): with an option amount O1.x = 0
        # the term SK.on*O1.x*(1/min(S1, K) - 1/S1) is 0, but its min still blocked every monotone leaf in S1 (min
        # has no derivative where its arguments cross) and the design stayed OPEN. The value is unchanged: each name
        # replaced is EXACTLY 0 in this design (a fixed value, not a box); ZTL checks the certificate on this text.
        zeros = [n for n, v in fixed.items() if v == 0 and re.search(rf"\b{re.escape(n)}\b", text)]
        if zeros and system is None:
            text = K.fold_zeros(text, set(zeros))     # only the zeros: simplify's expanded form ruined the readings
        pieces = 0
        # J6 (2026-10-11): the implicit quantities in the text, if the free-box reading (G6) brings no proof,
        # are read once more as ROOTS that move with the box (zcertify's implicit tranche)
        in_text = {n for n in impl if re.search(rf"\b{re.escape(n)}\b", text)}
        as_roots = False
        n_split = 0
        # A SUM, term by term (2026-10-12, the curator's "да"): a quantity defined as a sum — each term proved over its
        # own data, the bounds added (certify.prove_sum: sound, maybe wider). Tried FIRST when every term reads fewer
        # data than the whole (c11: the annual sum over five data, no certificate in 25 min; each quarter over two,
        # 4 pieces), else after the whole has no certificate.
        sum_terms, split_first = [], False
        if system is None and not in_text and explicit.get(q) is not None:
            terms_n = []

            def _flat(nd):
                if isinstance(nd, ast.BinOp) and isinstance(nd.op, ast.Add):
                    _flat(nd.left)
                    _flat(nd.right)
                else:
                    terms_n.append(nd)
            _flat(explicit[q])
            if len(terms_n) >= 2:
                for t_n in terms_n:
                    tt, lft = K.expression("_term_", dict(explicit, _term_=t_n), set(derived))
                    if lft:
                        sum_terms = []
                        break
                    if system is None and zeros:
                        tt = K.fold_zeros(tt, set(zeros))                 # the same exact zeros as the whole
                    sum_terms.append(K.simplify(tt))
            if sum_terms:
                data = lambda t: {n for n in re.findall(r"[A-Za-z_]\w*", t) if n in boxes and boxes[n][0] != boxes[n][1]}
                whole = data(text)
                split_first = all(len(data(t)) < len(whole) for t in sum_terms)
        for op, bound in claims:
            tries = [None] + ([{n: ast.unparse(impl_g[n]) for n in in_text}] if in_text and system is None else [])
            if len(tries) == 2 and all(boxes[n][1] - boxes[n][0] <= F(1, 10 ** 9) * max(abs(boxes[n][0]),
                                                                                     abs(boxes[n][1]), 1)
                                       for n in in_text if n in boxes):
                # A HAIR-WIDE ROOT (a design's constant, the nozzle's exit Mach: 1e-12 wide) read as a free box
                # needs a sign of the target in it, which its width cannot show — no monotone leaf, ever: the
                # free-box search cut the OTHER quantities to its budget (200 pieces 157 s, hours in all; the
                # multi-node motor, 2026-10-16). As a root that moves with the box: one monotone leaf, 0.7 s.
                tries.reverse()
            pre_split, budget = None, None
            if split_first:
                pre_split = K.prove_sum(sum_terms, fixed, boxes, op, bound)
                if pre_split is not None and "miss" in pre_split:
                    # the terms' extremes miss the bound: their point, decided EXACTLY by the checker
                    point = {n: v for n, v in pre_split["miss"].items() if n not in impl}
                    point = dict({n: (b0 + b1) / 2 for n, (b0, b1) in boxes.items() if n not in impl}, **point)
                    values = C.solve_at(all_laws, dict(fixed, **point), all_derived)
                    pt_env = dict(fixed, **point)
                    if [rr for rr in reqs if B.violates(values[rr["quantity"]], _req_at(rr, pt_env))]:
                        return ("ret", {"witness": (point, values)})
                    pre_split = None
                if pre_split is not None:
                    tries = []
                else:
                    # the whole reads MORE data than every term (that is why the split went first): its search gets
                    # a small budget, enough for a witness near the top, not the hours a 5-datum certificate took
                    # (c11 by scenario cuts, round 3: a mix tight to 0.13 in 300000, > 10 min in the whole's search)
                    budget = K.WHOLE_AFTER_SPLIT
            for implicit in tries:
                got = K.prove(text, fixed, boxes, op, bound, system, implicit, budget)
                if "witness" in got:
                    point = dict({n: (b0 + b1) / 2 for n, (b0, b1) in boxes.items()}, **got["witness"])
                    # an implicit quantity's box value is NOT its value at that point: dropped, and the
                    # checker recomputes it from its law — a witness only if the true point fails
                    point = {n: v for n, v in point.items() if n not in impl}
                    values = C.solve_at(all_laws, dict(fixed, **point), all_derived)     # the checker, exactly
                    pt_env = dict(fixed, **point)
                    bad = [rr for rr in reqs if B.violates(values[rr["quantity"]], _req_at(rr, pt_env))]
                    if bad:
                        return ("ret", {"witness": (point, values)})
                    continue                # the free box's corner, not a true point: try the roots
                if "proved" in got:
                    break
            else:
                split = pre_split if pre_split is not None else (
                    K.prove_sum(sum_terms, fixed, boxes, op, bound) if sum_terms and not split_first else None)
                if split is not None and "miss" in split:
                    split = None
                if split is None and system is not None:
                    # the SYMBOLIC path found no certificate (2026-10-15: a CE stage's V(c) <= max, 4 unknowns): the
                    # same linear system by zlin — the target an unknown, or its expression joined as one more
                    tgt_text, s_laws, s_u = system
                    fb_laws, fb_u = (s_laws, s_u) if tgt_text.strip() in s_u else \
                        (s_laws + [f"_zq_ == {tgt_text}"], s_u + ["_zq_"])
                    fb_t = tgt_text.strip() if tgt_text.strip() in s_u else "_zq_"
                    try:
                        fb = K.prove_linear(fb_laws, fb_u, fb_t, fixed, boxes, op, bound)
                    except Exception:                   # noqa: BLE001 — not linear after all: no fallback
                        fb = {"open": "zlin could not read the system"}
                    if "witness" in fb:
                        point = dict({n: (b0 + b1) / 2 for n, (b0, b1) in boxes.items()}, **fb["witness"])
                        values = C.solve_at(all_laws, dict(fixed, **point), all_derived)
                        if [rr for rr in reqs if B.violates(values[rr["quantity"]], _req_at(rr, dict(fixed, **point)))]:
                            return ("ret", {"witness": (point, values)})
                    if "proved" in fb:
                        if MODE.DEV[0]:
                            okc, whyc = C.check_linear_certificate(*_as_checked(fb, fb_laws, bound, fixed, boxes, fb_u, fb_t, op))
                            if not okc:
                                return ("ret", {"unconfirmed": f"{q} {op} {bound}: the checker could not re-check zlin's "
                                                       f"certificate: {whyc}"})
                        pieces += fb["proved"]
                        continue                        # this claim proved; the next one
                if split is None:
                    return ("ret", {})
                got = {"proved": split["proved"], "split": split}
                implicit = None
            if witness_only:
                return ("ret", {"fault": f"ZTL's exact range for {q} leaves {op} {bound}, yet its certificate check "
                                 f"accepts {q} {op} {bound} over the whole box"})
            # J9: the checker re-checks the same certificate from the laws, with its own means
            if "split" in got:
                # the checker re-checks each term's certificate on the term itself, from its own reading
                agree, why = True, None
                if MODE.DEV[0]:
                    for t_text, b_i, _p, cert_i in got["split"]["terms"]:
                        tq = "_split_term_"
                        ok_t, why_t = C.check_certificate(laws + [f"{tq} == {t_text}"], fixed, boxes, derived + [tq],
                                                          tq, op, b_i, cert_i)
                        if not ok_t:
                            agree, why = False, f"a term of {q}: {why_t}"
                            break
            else:
                agree, why = (True, None) if not MODE.DEV[0] else C.check_certificate(laws, fixed, boxes, derived, q, op, bound, got["cert"],
                                                 implicit={n: impl_g[n] for n in implicit} if implicit else None)
            if not agree:
                return ("ret", {"unconfirmed": f"{q} {op} {bound}: {why}"})
            pieces += got["proved"]
            as_roots = as_roots or bool(implicit)
            n_split = max(n_split, len(got["split"]["terms"]) if "split" in got else 0)
        certified[q] = {"pieces": pieces, "system": system is not None, "implicit": as_roots, "split": n_split}
        shown[q] = ((max(lo, a) if lo is not None else a) if a is not None else lo,
                    (min(hi, c) if hi is not None else c) if c is not None else hi)
        return ("ok", certified, shown)
    # The rows run IN ORDER, one by one: MEASURED on the bridge girder (2026-10-20), 90 of 91 rows took seconds and one
    # (the deflection, reading 90 unknowns) took the rest — rows in parallel left 15 of 16 workers idle. The parallel
    # work is inside a row instead: the unknowns' range proofs (below). The first early return wins, as before.
    for r in reqs:
        kind, *rest = _one(r)
        if kind == "ret":
            return rest[0]
        certified.update(rest[0])
        shown.update(rest[1])
    return {"certified": certified, "ranges": shown} if certified else {}


DEV_LIN_CORNERS = 1 << 10     # --dev re-solves every corner of a zlin-certified box exactly up to 2^10 corners


CONFLICT_RUNS_PER_REQ = 4      # the default budget of subset runs: max(4 per requirement, CONFLICT_RUNS_MIN) —
CONFLICT_RUNS_MIN = 24         # a COUNT, not a clock, so the listing does not depend on the machine. RAISED 2026-10-18
                               # (the curator's "да"): with existence-only subsets, monotone inference and complement
                               # probes, blind 6 c07's COMPLETE list (6 conflicts) takes 22 runs + 515 inferred, 68 s
                               # (was 529 runs, 530 s); c11 complete in 6 runs. MEASURED before that
                               # 2026-10-13: blind 6 c07, 10 requirements, 40 runs = 37 min after a 25 s verdict (a
                               # subset that turns out satisfiable costs a full mix search); with 4 requirements every
                               # subset (15) still fits, as before


def _conflict_item(i):
    """One subset's verdict and its proof's core (a worker of ustand/parallel.py, or here): the enumeration's own run."""
    make, cands = PL.STATE["conflicts"]
    r = run(make(cands[i]), conflicts=False)
    return r["verdict"], r.get("_core")


def minimal_conflicts(b, core=None):
    """WHY no design exists, as the minimal SETS of requirements that cannot hold together on
    this catalog (gap J7). ZTL's backward pass (zbackward.py) gives the family of minimal sets
    for its own atoms; this is the same idea — an antichain, no member containing another —
    over the requirements: a set is a conflict when the stand REFUTES it (every design fails
    at a concrete point), and minimal when no proper subset is refuted. Each conflict must be
    dropped or relaxed as a whole: removing a requirement outside every conflict changes
    nothing. A subset judged OPEN is neither, and is reported as such.

    HOW (2026-10-13, speed-up lever 3, the curator's "да"; capacity bench: c11's subsets ran past 50 min after a 5 min
    verdict, and more than 8 requirements were refused outright — blind 6 c07 found its conflict by hand):
      1. DELETION — n runs, any n: from the whole (refuted) set, each requirement in turn is dropped if the rest is
         still refuted. What remains is ONE minimal conflict (refutation is monotone: a superset of a refuted set is
         refuted — every design that fails the smaller set fails the larger). A drop judged OPEN keeps the
         requirement, and the set is then said to be minimal among the decided drops only.
      2. ENUMERATION — subsets by size, smallest first, skipping supersets of known conflicts, within a budget of
         subset runs (deterministic: a count, not a clock). Default 4 per requirement; the brick's `"conflicts"` may
         be a number (the budget) or "all" (every subset, as before). `complete` says whether every subset was judged.
         A set found at size k is minimal: every smaller subset was judged before it."""
    # ACROSS MODES (2026-10-10): the requirements are the brick's (every mode) and each mode's own, one flat list;
    # a subset keeps its brick-wide members and, per mode, that mode's members; a mode left with nothing to ask
    # (no brick-wide member, none of its own) is dropped from the subset
    modes = b.get("modes") or {}
    reqs = [(None, r) for r in b.get("requirements") or []]
    reqs += [(m, r) for m, spec in modes.items() for r in (spec.get("requirements") or [])]
    n = len(reqs)
    want = b.get("conflicts")
    budget = None if want == "all" else (want if isinstance(want, int) and not isinstance(want, bool)
                                         else max(CONFLICT_RUNS_PER_REQ * n, CONFLICT_RUNS_MIN))

    def subset(idx):
        top = [reqs[i][1] for i in idx if reqs[i][0] is None]
        sub = dict(b, requirements=top)
        sub.pop("conflicts", None)
        from . import lp as _LP
        if not _LP.continuous_slots(b):
            sub.pop("objective", None)          # a continuous brick keeps it: its path needs one (J10, 2026-10-12)
        else:
            sub["_existence_only"] = True       # only "is there a mix?" — no bound (lp.run_continuous, 2026-10-18)
        if modes:
            kept = {}
            for m, spec in modes.items():
                own = [reqs[i][1] for i in idx if reqs[i][0] == m]
                if own or top:
                    kept[m] = dict(spec, requirements=own)
            if kept:
                sub["modes"] = kept
            else:
                sub.pop("modes", None)
        return sub

    def label(i):
        m, r = reqs[i]
        t = r.get("why") or f"{r['quantity']} {r['op']} {r['value']}"
        return t if m is None else f"[{m}] {t}"

    seen = {tuple(range(n)): "REFUTED"}         # the whole set: the verdict this is called for
    runs, inferred = [0], [0]
    # MONOTONICITY (2026-10-18, the duel: c07's 20 subset runs were 1192 s of a 1216 s profile). A subset EARNED is
    # held by one design (one mix) — that design holds every smaller subset too: all EARNED, no run. A subset REFUTED
    # makes every larger one REFUTED (each design already fails a member). OPEN says neither. So a deletion drop that
    # leaves the rest EARNED proves that EVERY conflict contains the dropped requirement.
    earned_sets, refuted_sets = [], [frozenset(range(n))]
    # THE CORE of a refutation (2026-10-18): the requirements its proof used (indices into the subset's own list) —
    # any set holding them is refuted by the same proof. Without modes only (a mode's requirement is not indexed so).
    use_core = not modes
    if use_core and core is not None:
        refuted_sets.append(frozenset(core))

    def known(idx):
        s_ = frozenset(idx)
        if any(s_ <= e for e in earned_sets):
            return "EARNED"
        if any(r_ <= s_ for r_ in refuted_sets):
            return "REFUTED"
        return None

    def learn(idx, v, core_=None):
        if v == "EARNED":
            earned_sets.append(frozenset(idx))
        elif v == "REFUTED":
            refuted_sets.append(frozenset(idx))
            if use_core and core_ is not None:
                idx_ = sorted(idx)
                refuted_sets.append(frozenset(idx_[j] for j in core_))

    def judge(idx):
        idx = tuple(sorted(idx))
        if idx not in seen:
            k_ = known(idx)
            if k_ is not None:
                inferred[0] += 1
                seen[idx] = k_
            else:
                runs[0] += 1
                r_ = run(subset(idx), conflicts=False)
                seen[idx] = r_["verdict"]
                learn(idx, seen[idx], r_.get("_core"))
        return seen[idx]

    found, opened, kept_open = [], [], []
    complete = True

    def report(stopped=None):
        out = {"sets": [[label(i) for i in c] for c in found],
               "undecided_sets": [[label(i) for i in c] for c in opened],
               "complete": complete and stopped is None, "subset_runs": runs[0],
               "subsets_inferred": inferred[0],
               "how": ("first one minimal set by deletion (each requirement dropped in turn while the rest stays "
                       "refuted), then every subset by size, smallest first; a subset of an EARNED set is EARNED and a "
                       "superset of a REFUTED one REFUTED without a run (monotone: one design holds the smaller set)"
                       + ("" if budget is None else f", within a budget of {budget} subset runs")
                       + (" — a mode's own requirement is marked [mode]; the brick's apply in every mode"
                          if modes else ""))}
        if kept_open:
            out["deletion_note"] = ("the first set is minimal among the decided drops only: dropping "
                                    + ", ".join(label(i) for i in kept_open) + " was judged OPEN")
        if not out["complete"] and stopped is None:
            out["incomplete"] = ("the budget of subset runs ran out: the sets listed are minimal conflicts, but there "
                                 "may be others — ask for more with \"conflicts\": N (runs) or \"all\"")
        if stopped:
            out["stopped"] = stopped
        return out

    try:
        # 1. deletion: one minimal conflict in n runs
        cur = list(range(n))
        for i in range(n):
            if len(cur) == 1:
                break
            rest = [j for j in cur if j != i]
            if i not in cur:
                continue
            v = judge(rest)
            if v == "REFUTED":
                cur = rest
            elif v == "OPEN":
                kept_open.append(i)
        if n:
            found.append(tuple(cur))
        # 1b. COMPLEMENT PROBES (2026-10-18, c07: 529 subset runs for 6 conflicts, 3 inferred): for each member e of a
        # conflict found, the whole set without e. EARNED there — every subset without e is EARNED (monotone), so
        # EVERY conflict contains e; the enumeration below then skips hundreds of subsets without a run.
        probed = set()

        def probe(conf):
            for e in conf:
                if e not in probed and n > 1 and (budget is None or runs[0] < budget):
                    probed.add(e)
                    judge([j for j in range(n) if j != e])
        if n:
            probe(cur)
        # 2. enumeration by size, within the budget. The candidates of one size are known before any of them is
        # judged (a superset of a conflict is skipped, and conflicts of the SAME size are never supersets of each
        # other), so they are judged ahead by the workers with --jobs (ustand/parallel.py), in this order; the
        # result is the same as one process
        for k in range(1, n + 1):
            cands = [idx for idx in itertools.combinations(range(n), k)
                     if not any(set(c) <= set(idx) for c in found)]
            for idx in cands:                   # what monotonicity already decides: no run
                if idx not in seen and known(idx) is not None:
                    seen[idx] = known(idx)
                    inferred[0] += 1
            new = [idx for idx in cands if idx not in seen]
            if budget is not None and runs[0] + len(new) > budget:
                complete = False
                keep = set(new[:max(0, budget - runs[0])])
                cands = [idx for idx in cands if idx in seen or idx in keep]
                new = [idx for idx in new if idx in keep]
            PL.STATE["conflicts"] = (subset, new)
            for idx, (v, core_) in zip(new, PL.iterate(_conflict_item, len(new))):
                runs[0] += 1
                seen[idx] = v
                learn(idx, v, core_)
                _stop_check()           # with workers the main process waits here: a stop ends the pool at once
            for idx in cands:
                v = seen[idx]
                if v == "REFUTED":
                    # minimal: every smaller subset was judged before it; the deletion set, if it contains this one,
                    # was minimal only among decided drops — replace it
                    found[:] = [c for c in found if not set(idx) < set(c)] + [idx]
                    probe(idx)
                elif v == "OPEN":
                    opened.append(idx)
            if not complete:
                break
    except Stopped:
        complete = False
        return report("by a signal (a time limit) while judging the subsets — the sets below are those found so "
                      "far; the list is not complete")
    found.sort(key=lambda c: (len(c), c))
    return report()


def _design_out(design):
    def fo(spec):
        if spec[0] == "label":
            return spec[1]
        return {"range": _s([spec[1], spec[2]])} if spec[0] == "range" else \
               {"nominal": _s(spec[0]), "tolerance": _s(spec[1])}
    return {s: {"catalog": c, **{f: fo(spec) for f, spec in item.items()}} for s, (c, item) in design.items()}


def main():
    import signal

    from .stopflag import on_signal
    # the flag, seen at the next safe point (stopflag.py says why not raised here) — or at once inside a ZTL search
    signal.signal(signal.SIGTERM, on_signal)
    _PROGRESS["stderr"] = True
    args = sys.argv[1:]
    if "--dev" in args:             # the independent checker on every design (ustand/mode.py)
        MODE.DEV[0] = True
        args.remove("--dev")
    if "--jobs" in args:            # judge designs in N worker processes (ustand/parallel.py); the verdict is the same
        k = args.index("--jobs")
        PL.JOBS[0] = max(1, int(args[k + 1]))
        del args[k:k + 2]
    print(json.dumps(run(args[0]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
