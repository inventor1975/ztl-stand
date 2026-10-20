"""THE DUEL vs SCIP — the 12 blind bricks as a mixed-integer nonlinear program (MINLP), the way an engineer would pose
them to a classical global optimizer.

2026-10-18, the curator's "Делай 1. и 2.".

SCIP 10 (pyscipopt) is a global MINLP solver: catalog choices as binaries, amounts as continuous variables, exp / log /
pow / sqrt / abs as its own expressions; "optimal" is its own spatial branch-and-bound in floating point (no checked
certificate). It has no "for every point of a box": the tolerances must be posed some way. Two ways, both usual:
  * NOMINAL — every toleranced quantity at its middle (what the stand's objective uses too);
  * CORNERS — every requirement at every corner of the box (2^k scenarios; for k > CORNER_MAX a seeded sample of
    corners plus the middle) — robust only when the worst case lies at a corner.
Translation: the stand's own reading again (frame per catalog item, compile_expr, reqs_si, modes); one binary per
catalog item of a slot (designs are the full Cartesian product — checked: designs == product for all 12); a slot field
= sum y_i * v_i(corner); explicit laws substituted, implicit ones as variables with their equation per scenario;
min/max via abs; tan = sin/cos. Each answer is then JUDGED BY THE STAND: a discrete design by the stand's own listing
(every design cheaper than the stand's answer was REFUTED there, with its reason), a continuous one by the stand run
on the brick with SCIP's amounts pinned.

    ~/venvs/competitors/bin/python bench/competitors/scip_duel.py [c01 ...] [--time S] [--jobs J]
"""
import ast
import itertools
import json
import math
import pathlib
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import blind_duel as BD  # noqa: E402
from blind_duel import B, S  # noqa: E402

OUT = HERE / "scip_results.jsonl"
CORNER_MAX = 10                       # 2^10 = 1024 scenarios per mode at most; beyond: a seeded sample of 1024


def slots_of(b):
    """[(slot, [(catalog, item)...], continuous (lo, hi, field) or None)] in designs' order."""
    out = []
    for s, sp in b["slots"].items():
        items, cont = [], None
        for cn in sp["from"]:
            cat = b["catalog"][cn]
            if isinstance(cat, dict) and "continuous" in cat:
                cont = cn
            else:
                items += [(cn, it) for it in B.items(cat)]
        out.append((s, items, cont))
    return out


class Enc:
    def __init__(self, b, model, ys, xs):
        self.b, self.m, self.ys, self.xs = b, model, ys, xs

    def item_values(self, mb, base):
        """Per slot: per item, {field name: number or (lo, hi)} in SI, read by the stand's frame."""
        vals = {}
        for s, items, cont in slots_of(self.b):
            if cont:
                continue
            per = []
            for cn, it in items:
                d = dict(base)
                d[s] = (cn, it)
                fixed, boxes, _, _ = S.frame(mb, d, with_computed=False)
                per.append({n: (boxes[n] if n in boxes else fixed[n]) for n in set(fixed) | set(boxes)
                            if n.startswith(s + "__")})
            vals[s] = per
        return vals


def build(b, mode_bricks, form, rng):
    from pyscipopt import Model, exp, log, sqrt, sin, cos
    m = Model()
    m.hideOutput()
    ys, xs = {}, {}
    base = next(iter(S.designs(b)))
    for s, items, cont in slots_of(b):
        if cont:
            c = b["catalog"][cont]["continuous"]
            _, boxes, _, _ = S.frame(b, base)
            n = f"{s}__{c['field']}"
            lo, hi = boxes[n]
            xs[n] = m.addVar(name=n, lb=float(lo), ub=float(hi))
        else:
            ys[s] = [m.addVar(name=f"y_{s}_{i}", vtype="B") for i in range(len(items))]
            m.addCons(sum(ys[s]) == 1)
    enc = Enc(b, m, ys, xs)
    t_false = m.addVar(name="false", lb=0, ub=0)          # a requirement false whatever is chosen
    FN = dict(exp=exp, ln=log, log=log, sqrt=sqrt, sin=sin, cos=cos)
    nsc = 0

    def expr(tree, env, defs, memo):
        if isinstance(tree, ast.BinOp):
            a = expr(tree.left, env, defs, memo)
            if isinstance(tree.op, ast.Pow):
                c = BD.const(tree.right)
                return a ** float(c) if c is not None else exp(expr(tree.right, env, defs, memo) * log(a))
            c = expr(tree.right, env, defs, memo)
            return {ast.Add: lambda: a + c, ast.Sub: lambda: a - c, ast.Mult: lambda: a * c,
                    ast.Div: lambda: a / c}[type(tree.op)]()
        if isinstance(tree, ast.UnaryOp):
            v = expr(tree.operand, env, defs, memo)
            return -v if isinstance(tree.op, ast.USub) else v
        if isinstance(tree, ast.Constant):
            return float(F(str(tree.value)))
        if isinstance(tree, ast.Name):
            n = tree.id
            if n == "pi":
                return math.pi
            if n in env:
                return env[n]
            if n in memo:
                return memo[n]
            if n in defs:
                memo[n] = expr(defs[n], env, defs, memo)
                return memo[n]
            raise BD.NotExpressible(f"name {n}")
        if isinstance(tree, ast.Call):
            f, a = tree.func.id, [expr(x, env, defs, memo) for x in tree.args]
            if f in FN:
                return FN[f](a[0])
            if f == "log10":
                return log(a[0]) / math.log(10)
            if f == "tan":
                return sin(a[0]) / cos(a[0])
            if f == "pow":
                c = BD.const(tree.args[1])
                return a[0] ** float(c) if c is not None else exp(a[1] * log(a[0]))   # c10: pow(., 1/nP)
            if f == "abs":
                return abs(a[0])
            if f in ("min", "max"):
                return (a[0] + a[1] + (-1 if f == "min" else 1) * abs(a[0] - a[1])) / 2
            raise BD.NotExpressible(f)
        raise BD.NotExpressible(ast.dump(tree)[:60])

    def laws_of(mb):
        # "computed" values are exact per design (stand.frame folds them into the fixed ones): here expressions
        # of the choice (c05, c08 — MEASURED 18.10: folding the first design's Pman made SCIP reject the answer)
        defs = {cn: ast.parse(B.compile_expr(cv if isinstance(cv, str) else cv["value"]), mode="eval").body
                for cn, cv in (mb.get("computed") or {}).items()}
        impl = []
        for L in [B.compile_expr(l["zfl"], mb.get("define")) for l in mb["laws"]]:
            t = ast.parse(L, mode="eval").body
            if isinstance(t.left, ast.Name) and t.left.id not in BD.var_names(t.comparators[0]):
                defs[t.left.id] = t.comparators[0]
            else:
                impl.append(t)
        return defs, impl

    def scenario_env(mb, vals, boxes, fixed, pick, defs_impl_unknowns):
        env = {n: float(v) for n, v in fixed.items() if "__" not in n or n.split("__")[0] not in vals}
        for n, (lo, hi) in boxes.items():
            if n in xs or ("__" in n and n.split("__")[0] in vals):
                continue
            env[n] = float(pick(n, lo, hi))
        env.update(xs)
        for s, per in vals.items():
            for fld in per[0]:
                terms = []
                for i, it in enumerate(per):
                    v = it[fld]
                    v = pick(fld, v[0], v[1]) if isinstance(v, tuple) else v
                    terms.append(float(v) * ys[s][i])
                env[fld] = sum(terms)
        for n, (lo, hi) in defs_impl_unknowns.items():
            env[n] = m.addVar(lb=lo, ub=hi)
        return env

    for mb in mode_bricks:
        fixed, boxes, derived, _ = S.frame(mb, base, with_computed=False)
        vals = enc.item_values(mb, base)
        defs, impl = laws_of(mb)
        unknown = {}
        for n in derived:
            if n not in defs:
                q = mb["quantities"].get(n, {})
                if "search" in q:
                    sc = S._scale(q.get("unit"))
                    unknown[n] = (float(B.num(q["search"][0]) * sc), float(B.num(q["search"][1]) * sc))
                else:
                    unknown[n] = (None, None)
        # the dims of the box: given ranges and slot fields that are ranges for some item
        dims = {n: bx for n, bx in boxes.items() if n not in xs and not ("__" in n and n.split("__")[0] in vals)}
        for s, per in vals.items():
            for fld in per[0]:
                if any(isinstance(it[fld], tuple) for it in per):
                    dims[fld] = None
        names = sorted(dims)
        if form == "nominal":
            corners = [None]
        elif len(names) <= CORNER_MAX:
            corners = list(itertools.product((0, 1), repeat=len(names)))
        else:
            corners = [None] + [tuple(rng.randint(0, 1) for _ in names) for _ in range(2 ** CORNER_MAX)]
        reqs = BD.reqs_si(mb)
        for cor in corners:
            def pick(n, lo, hi, cor=cor):
                if cor is None:
                    return (lo + hi) / 2
                return hi if cor[names.index(n)] else lo
            env = scenario_env(mb, vals, boxes, fixed, pick, unknown)
            memo = {}
            for t in impl:
                m.addCons(expr(t.left, env, defs, memo) == expr(t.comparators[0], env, defs, memo))
            for q, op, bd in reqs:
                v = expr(ast.Name(id=q, ctx=ast.Load()), env, defs, memo)

                def rel(x, sense):
                    """v sense bound, NORMALISED by a numeric bound: the stand's SI makes "Dm <= 0.1/year"
                    3.2e-9 per second, below SCIP's feasibility tolerance (c01, MEASURED 18.10: SCIP ignored it)."""
                    if x[0] == "num" and x[1] != 0:
                        c = float(x[1])
                        lhs, rhs = v * (1 / abs(c)), c / abs(c)
                    else:
                        lhs, rhs = v, (float(x[1]) if x[0] == "num" else expr(x[1], env, defs, memo))
                    c = lhs <= rhs if sense == "<=" else lhs >= rhs if sense == ">=" else lhs == rhs
                    if isinstance(c, bool):              # no choice in it: a plain truth (c02)
                        if not c:
                            m.addCons(t_false >= 1)
                        return
                    m.addCons(c)
                if op == "within":
                    rel(bd[0], ">=")
                    rel(bd[1], "<=")
                elif op in ("<=", "<"):
                    rel(bd, "<=")
                elif op in (">=", ">"):
                    rel(bd, ">=")
                elif op == "==":
                    rel(bd, "==")
            nsc += 1
    # the objective: nominal, the main brick's laws
    fixed, boxes, derived, _ = S.frame(b, base, with_computed=False)
    vals = enc.item_values(b, base)
    defs, impl = laws_of(b)
    env = scenario_env(b, vals, boxes, fixed, lambda n, lo, hi: (lo + hi) / 2, {})
    obj = expr(ast.parse(B.compile_expr(b["objective"]["minimize"], b.get("define")), mode="eval").body, env, defs, {})
    t = m.addVar(name="cost", lb=None)
    m.addCons(t >= obj)
    m.setObjective(t, "minimize")
    return m, ys, xs, nsc


def answer(b, m, ys, xs):
    design, x = {}, {}
    for s, items, cont in slots_of(b):
        if cont:
            continue
        i = max(range(len(items)), key=lambda i: m.getVal(ys[s][i]))
        design[s] = items[i]
    for n, v in xs.items():
        x[n] = m.getVal(v)
    return design, x


def judge(cid, b, design, x):
    """The stand's verdict on SCIP's answer: a discrete design from the stand's own listing; with amounts, the stand
    run on the brick with SCIP's items and amounts pinned."""
    out = json.load(open(HERE / "blind" / f"{cid}.out.json"))
    out = out.get("decision", out)              # c04: the brick as given (Ta = -40), not the found limit
    if out.get("verdict") == "REFUTED" and not out.get("designs"):
        return dict(stand_on_it="REFUTED (every design: " + str(out.get("why", ""))[:80] + ")")
    lab = S._label(design)
    if not x:
        for row in out.get("designs", []):
            if row["design"] == lab:
                return dict(stand_on_it=row["verdict"], broken=row.get("fails"),
                            overshoot=(str(row.get("by_at_witness", "")).split("(~")[-1].rstrip(")") + " "
                                       + str(row.get("unit", ""))) if row.get("by_at_witness") else None)
        return dict(stand_on_it="not judged by the stand (dearer than its answer)")
    from ustand import lp as LP
    raw = {k: v for k, v in json.load(open(BD.BLIND / f"{cid}.json")).items() if k != "find"}
    for sl, (cn, it) in design.items():
        labels = {k: v[1] for k, v in it.items() if isinstance(v, tuple) and v[0] == "label"}
        cat = raw["catalog"][cn]
        items = cat["items"] if isinstance(cat, dict) else cat
        keep = [i for i in items if all(str(i.get(k)) == str(v) for k, v in labels.items())]
        if isinstance(cat, dict):
            cat["items"] = keep
        else:
            raw["catalog"][cn] = keep
        raw["slots"][sl] = {"from": [cn]}
    vals = {}
    for sl, items, cont in slots_of(b):
        if cont:
            c = b["catalog"][cont]["continuous"]
            v = F(x[f"{sl}__{c['field']}"]).limit_denominator(10 ** 9) / S._scale(c.get("unit"))
            vals[sl] = (cont, c["field"], v)
    res = S._run(LP._pinned(raw, vals), conflicts=False)
    r = dict(stand_on_it=res.get("verdict"), amounts={k: str(v[2]) for k, v in vals.items()})
    if res.get("verdict") == "REFUTED":         # how far over: a float tolerance or a real violation
        req = res.get("requirement") or {}
        ov = res.get("overshoot")
        r.update(broken=f"{req.get('quantity')} {req.get('op')} {req.get('value')}",
                 overshoot=str(ov).split("(~")[-1].rstrip(")") if ov is not None else None)
    return r


def job(a):
    cid, form, limit = a
    t0 = time.time()
    try:
        b = BD.load(cid)
        mbs = [mb for _, mb in BD.mode_bricks(b)]
        m, ys, xs, nsc = build(b, mbs, form, random.Random(18))
        m.setParam("limits/time", limit)
        m.setParam("parallel/maxnthreads", 1)
        m.setParam("numerics/feastol", 1e-9)    # SCIP's default 1e-6; tighter, in SCIP's favour
        tb = time.time()
        m.optimize()
        st = m.getStatus()
        r = dict(status=st, scenarios=nsc, build_s=round(tb - t0, 1), solve_s=round(time.time() - tb, 1))
        if m.getNSols() > 0:
            design, x = answer(b, m, ys, xs)
            r.update(cost=m.getObjVal(), dual_bound=m.getDualbound(), design=S._label(design),
                     x={k: v for k, v in x.items()})
            try:
                r.update(judge(cid, b, design, x))
            except Exception as e:  # noqa: BLE001
                r.update(judge_error=f"{type(e).__name__}: {str(e)[:200]}")
    except Exception as e:  # noqa: BLE001
        r = dict(status=f"HARNESS ERROR: {type(e).__name__}: {str(e)[:300]}")
    r.update(brick=cid, form=form, wall_s=round(time.time() - t0, 1), at=time.strftime("%Y-%m-%d %H:%M:%S"))
    return r


def main():
    args = sys.argv[1:]
    limit = int(args[args.index("--time") + 1]) if "--time" in args else 900
    jobs = int(args[args.index("--jobs") + 1]) if "--jobs" in args else 12
    forms = args[args.index("--forms") + 1].split(",") if "--forms" in args else ["nominal", "corners"]
    cids = [a for a in args if len(a) == 3 and a.startswith("c")] or BD.DISCRETE + BD.CONTINUOUS
    with ProcessPoolExecutor(jobs) as ex, open(OUT, "a") as fh:
        for row in ex.map(job, [(c, f, limit) for c in cids for f in forms]):
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            fh.flush()
            print(json.dumps(row, ensure_ascii=False, default=str)[:500], flush=True)


if __name__ == "__main__":
    main()
