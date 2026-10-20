"""THE DUEL, ROUND B — the continuous blind bricks as the FULL problem: the solver chooses the amounts itself.

2026-10-18, the curator's "Делай 1. и 2.".

Round A gave the solvers only the stand's own answer to check. Here, per combination of the discrete slots (the
stand's designs, a continuous slot left as its range), one exists-forall problem:

    exists amounts x in their ranges:  forall data p in the box:  laws(p, x) => requirements(p, x)
    [and the nominal objective(x) <= C]

The objective is the stand's: box quantities at their middles (lp.run_continuous, nominal_fixed), the amounts free.
Translation as in round A (blind_duel.Tr, the stand's own compile_expr), plus:
  * explicit laws (name == expr) become SMT-LIB `let`s inside the quantifier; c06's three implicit linear laws are
    solved for z1 z2 z3 by sympy first (exact algebra, the same equations) — said here, done for every tool alike;
  * a helper of the z3/cvc5 encodings (sqrt as s*s = a, ln as exp(y) = a) under the quantifier is quantified with it,
    as a hypothesis.
A z3/cvc5 `sat` on exists-forall is exact: its model x holds. A dReal `delta-sat` is not a proof: its x (the middle of
the model box, rationalised) is accepted only when dReal itself then proves it with the round-A check (UNSAT of "some
box point breaks a requirement", x pinned). `unsat` is a proof for every tool.

Per brick and tool: (1) every combination without a cap: holds / refuted / undecided; (2) bisection on the cap C
between a proved lower bound and the best proved cost, every live combination per step, until the gap is <= 1e-4 of
the cost or the budget ends. The answer: the best cost with its x, the proved lower bound (only when EVERY live
combination was unsat at that cap) — the same shape as the stand's value / lower_bound.

    ~/venvs/competitors/bin/python bench/competitors/round_b.py [c01 ...] [--tools ...] [--limit S] [--budget S]
"""
import ast
import copy
import json
import math
import pathlib
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import blind_duel as BD  # noqa: E402
from blind_duel import B, S  # noqa: E402

OUT = HERE / "round_b_results.jsonl"
BRICKS = ["c01", "c06", "c07", "c10", "c11", "c12"]
TOL = F(1, 10000)
DREAL_PREC = "1e-6"    # MEASURED 18.10 c12: 1e-3..1e-8 all prove a mix at once, 1e-10 times out; its x is re-proved exactly anyway


class Tq(BD.Tr):
    """Tr whose helper variables are collected per context: (name, constraint) pairs — quantified with the forall
    when they sit under it, existential (declared at the top) when outside."""

    def __init__(self, tool):
        super().__init__(tool)
        self.helpers = []

    def fresh(self):
        self.k += 1
        return f"_h{self.k}"

    def _collect(self):
        # the base class appends "(assert (...))" strings to self.extra; move them into self.helpers' constraints
        cons = [re.match(r"\(assert (.*)\)$", e).group(1) for e in self.extra if e.startswith("(assert")]
        self.extra = []
        return cons


def numf(f):
    return BD.num(f)


def topo_defs(b):
    """The laws as ordered explicit definitions [(name, ast)]; implicit linear ones solved by sympy."""
    laws = [B.compile_expr(l["zfl"], b.get("define")) for l in b["laws"]]
    defs, impl = {}, []
    for L in laws:
        t = ast.parse(L, mode="eval").body
        if isinstance(t.left, ast.Name) and t.left.id not in BD.var_names(t.comparators[0]):
            defs[t.left.id] = t.comparators[0]
        else:
            impl.append(L)
    if impl:
        import sympy as sp
        eqs, unk = [], set()
        for L in impl:
            lhs, rhs = L.split("==")
            eqs.append(sp.sympify(lhs) - sp.sympify(rhs))
        names = set().union(*[e.free_symbols for e in eqs])
        unk = [s for s in names if s.name not in defs and not any(s.name in BD.var_names(v) for v in [])]
        unk = [s for s in unk if s.name.startswith("z")]           # c06: the stage concentrations
        sol = sp.solve(eqs, unk, dict=True)
        if len(sol) != 1:
            raise BD.NotExpressible(f"implicit laws: {len(sol)} solutions")
        for s, e in sol[0].items():
            defs[s.name] = ast.parse(str(sp.simplify(e)).replace("**", "**"), mode="eval").body
    order, seen = [], set()

    def visit(n):
        if n in seen or n not in defs:
            return
        seen.add(n)
        for m in sorted(BD.var_names(defs[n])):
            visit(m)
        order.append(n)
    for n in sorted(defs):
        visit(n)
    return [(n, defs[n]) for n in order]


def problem(b, design):
    fixed, boxes, derived, _ = S.frame(b, design)
    cont = BD.S  # noqa: F841
    xs = {}
    for s, (cname, it) in design.items():
        cat = b["catalog"][cname]
        if isinstance(cat, dict) and "continuous" in cat:
            n = f"{s}__{cat['continuous']['field']}"
            xs[n] = boxes.pop(n)
    obj = ast.parse(B.compile_expr(b["objective"]["minimize"], b.get("define")), mode="eval").body
    return dict(fixed=fixed, boxes=boxes, xs=xs, defs=topo_defs(b), reqs=BD.reqs_si(b), obj=obj)


def lets(tr, defs, body, used):
    """(let ((n e)) ...) nested in order, only the definitions the body needs (transitively)."""
    need, frontier = set(), set(used)
    dd = dict(defs)
    while frontier:
        n = frontier.pop()
        if n in dd and n not in need:
            need.add(n)
            frontier |= BD.var_names(dd[n])
    out = body
    for n, e in reversed(defs):
        if n in need:
            out = f"(let (({n} {tr.t(e)})) {out})"
    return out, need


def inline(tree, defs):
    """The tree with every defined name replaced by its definition (dReal: no `let` under a quantifier)."""
    dd = dict(defs)

    class Sub(ast.NodeTransformer):
        def visit_Call(self, node):
            node.args = [self.visit(a) for a in node.args]
            return node

        def visit_Name(self, node):
            return self.visit(copy.deepcopy(dd[node.id])) if node.id in dd else node
    return Sub().visit(copy.deepcopy(tree))


def term(tr, tree, names, defs=None):
    if defs is not None:
        tree = inline(tree, defs)
    names |= BD.var_names(tree)
    return tr.t(tree)


def ef_text(P, tool, cap=None, pin=None):
    """The exists-forall SMT-LIB text; `pin` = {x: value} fixes the amounts (then it is round A's check, negated)."""
    tr = Tq(tool)
    names = set()
    viol, holds = [], []
    dfs = P["defs"] if tool == "dreal" else None
    for q, op, bd in P["reqs"]:
        qt = term(tr, ast.Name(id=q, ctx=ast.Load()), names, dfs)

        def bt(x):
            return numf(x[1]) if x[0] == "num" else term(tr, x[1], names, dfs)
        if op == "within":
            lo, hi = bt(bd[0]), bt(bd[1])
            holds.append(f"(and (>= {qt} {lo}) (<= {qt} {hi}))")
        else:
            rel = {"<=": "<=", "<": "<", ">=": ">=", ">": ">", "==": "="}[op]
            holds.append(f"({rel} {qt} {bt(bd)})")
    under = tr._collect()
    req = "(and " + " ".join(holds) + ")"
    # the defs are translated inside lets: their helpers too sit under the quantifier
    body, need = ("@BODY@", set()) if dfs else lets(tr, P["defs"], "@BODY@", names)
    under += tr._collect()
    for n in need:
        names |= BD.var_names(dict(P["defs"])[n])
    names.discard("pi")
    univ = sorted(n for n in names if n in P["boxes"])
    hyps = [f"(<= {numf(P['boxes'][n][0])} {n})" for n in univ] + [f"(<= {n} {numf(P['boxes'][n][1])})" for n in univ]
    hk = [h for h in re.findall(r"_h\d+", " ".join(under))]
    helpers = sorted(set(hk), key=lambda s: int(s[2:]))
    head = ["(set-logic ALL)"]
    xs = P["xs"]
    for n, (lo, hi) in xs.items():
        head.append(f"(declare-fun {n} () Real)")
        if pin is not None:
            head.append(f"(assert (= {n} {numf(pin[n])}))")
        else:
            head += [f"(assert (<= {numf(lo)} {n}))", f"(assert (<= {n} {numf(hi)}))"]
    for n in sorted(names):
        if n in P["fixed"] and n not in xs:
            head += [f"(declare-fun {n} () Real)", f"(assert (= {n} {numf(P['fixed'][n])}))"]
    for n in sorted(names - set(P["fixed"]) - set(xs) - set(P["boxes"]) - set(dict(P["defs"]))):
        raise BD.NotExpressible(f"name {n} neither given, box, amount nor defined")
    inner = body.replace("@BODY@", f"(=> (and {' '.join(hyps + under) or 'true'}) {req})")
    binders = " ".join(f"({n} Real)" for n in univ + helpers)
    if pin is None:
        main = f"(assert (forall ({binders}) {inner}))" if binders else f"(assert {inner})"
    else:                                       # round A: some point breaks it
        for n in univ + helpers:
            head.append(f"(declare-fun {n} () Real)")
        main = "(assert (not " + inner + "))"
    tail = []
    if cap is not None:
        to = Tq(tool)
        to.k = 1000                              # its helpers apart from the quantified ones
        consts = {n: (lo + hi) / 2 for n, (lo, hi) in P["boxes"].items()}   # the nominal objective: box middles
        consts.update({n: v for n, v in P["fixed"].items() if n not in xs})
        ob = term(to, inline(P["obj"], list(P["defs"]) + [(n, ast.Constant(value=v)) for n, v in consts.items()]),
                  set())
        ohelp = to._collect()
        for h in sorted(set(re.findall(r"_h\d+", " ".join(ohelp)))):
            tail.append(f"(declare-fun {h} () Real)")
        tail += [f"(assert {c})" for c in ohelp]
        tail.append(f"(assert (<= {ob} {numf(cap)}))")
    get = [f"(get-value ({' '.join(xs)}))"] if (pin is None and tool != "dreal" and xs) else []
    return "\n".join(head + tail + [main, "(check-sat)"] + get + ["(exit)"]) + "\n"


# ── the float reading of the objective (to report a found x's cost; the stand's value is the reference) ───────────
FN = dict(sqrt=math.sqrt, exp=math.exp, ln=math.log, log=math.log, log10=math.log10, pow=pow, min=min, max=max,
          abs=abs, sin=math.sin, cos=math.cos, tan=math.tan, atan=math.atan)


def fval(P, x):
    env = {n: float(v) for n, v in P["fixed"].items()}
    env.update({n: float((lo + hi) / 2) for n, (lo, hi) in P["boxes"].items()})
    env.update({n: float(v) for n, v in x.items()})
    env["pi"] = math.pi
    for n, e in P["defs"]:
        try:
            env[n] = eval(compile(ast.Expression(e), "<d>", "eval"), dict(FN), env)
        except (ValueError, ZeroDivisionError, OverflowError):
            env[n] = float("nan")
    return eval(compile(ast.Expression(P["obj"]), "<o>", "eval"), dict(FN), env)


def run(tool, text, limit):
    import os
    import subprocess
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".smt2", delete=False) as fh:
        fh.write(text)
        path = fh.name
    cmd = {"z3": [str(BD.VENV / "z3"), path],
           "cvc5": [str(BD.VENV / "python"), str(HERE / "cvc5_run.py"), path],
           "dreal": [str(BD.VENV / "dreal"), "--model", "--precision", DREAL_PREC, path]}[tool]
    t0 = time.time()
    p = subprocess.run(["timeout", str(limit)] + cmd, capture_output=True, text=True)
    os.unlink(path)
    out = (p.stdout + p.stderr).strip()
    res = ("TIMEOUT" if p.returncode == 124 else "UNSAT" if out.startswith("unsat") else
           "DELTA-SAT" if out.startswith("delta-sat") else "SAT" if out.startswith("sat") else
           "UNKNOWN" if out.startswith("unknown") else "ERROR: " + out[-200:].replace("\n", " "))
    return res, out, time.time() - t0


def model_x(tool, out, xs):
    x = {}
    if tool == "dreal":
        for n in xs:
            m = re.search(rf"^{n} : \[([^,]+), ([^\]]+)\]", out, re.M)
            if not m:
                return None
            x[n] = F((F(m.group(1)) + F(m.group(2))) / 2).limit_denominator(10 ** 9)
        return x
    for n in xs:
        m = re.search(rf"\({n} ([^()]+|\([^()]*\)|\(- \([^()]*\)\)|\(- [^()]+\))\)", out)
        if not m:
            return None
        x[n] = sexp_num(m.group(1))
    return x


def sexp_num(s):
    s = s.strip()
    if s.startswith("(- "):
        return -sexp_num(s[3:-1])
    if s.startswith("(/ "):
        a, b_ = s[3:-1].split()
        return F(a) / F(b_)
    return F(s)


def attempt(P, tool, limit, cap):
    """('HOLDS', x, cost) | ('REFUTED',) | ('UNDECIDED', why)."""
    res, out, _ = run(tool, ef_text(P, tool, cap), limit)
    if res == "UNSAT":
        return ("REFUTED",)
    if res in ("SAT", "DELTA-SAT") and P["xs"]:
        x = model_x(tool, out, P["xs"])
        if x is None:
            return ("UNDECIDED", f"{res}, no model read")
        for n, (lo, hi) in P["xs"].items():
            x[n] = min(max(x[n], lo), hi)
        if tool == "dreal":                     # delta-sat is no proof: dReal must prove its x (round A's check)
            r2, _, _ = run(tool, ef_text(P, tool, None, pin=x), limit)
            if r2 != "UNSAT":
                return ("UNDECIDED", f"delta-sat, its x not proved ({r2})")
        return ("HOLDS", x, fval(P, x))
    return ("UNDECIDED", res)


def brick(cid, tool, limit, budget):
    b = BD.load(cid)
    t0 = time.time()
    combos = []
    for d in S.designs(b):
        try:
            combos.append((S._label({k: v for k, v in d.items()}), problem(b, d)))
        except BD.NotExpressible as e:
            return dict(result=f"NOT EXPRESSIBLE: {e}")
    try:
        for _, P in combos:
            ef_text(P, tool)
    except BD.NotExpressible as e:
        return dict(result=f"NOT EXPRESSIBLE: {e}")
    live, best, log = [], None, []
    refuted = undecided = 0
    for lab, P in combos:
        if time.time() - t0 > budget:
            return dict(result="BUDGET (feasibility pass)", combos=len(combos), refuted=refuted,
                        undecided=undecided, best=best and best[:2])
        r = attempt(P, tool, limit, None)
        if r[0] == "REFUTED":
            refuted += 1
            continue
        live.append((lab, P))
        if r[0] == "UNDECIDED":
            undecided += 1
        elif best is None or r[2] < best[1]:
            best = (lab, r[2], {k: str(v) for k, v in r[1].items()})
    if not live:
        return dict(result="REFUTED (every combination unsat)", combos=len(combos), wall=round(time.time() - t0, 1))
    if best is None:
        return dict(result="NONE PROVED", combos=len(combos), refuted=refuted, undecided=undecided)
    # lo: the highest cap proved infeasible for every live combination; probe: where the bisection stands (an
    # undecided cap moves only the probe — the cost can still improve above it, the bound is not proved there)
    lo = probe = F(0)
    hi = F(best[1]).limit_denominator(10 ** 12)
    steps = 0
    while hi - probe > TOL * hi and time.time() - t0 < budget:
        cap = (probe + hi) / 2
        steps += 1
        found, und = None, False
        for lab, P in live:
            if time.time() - t0 > budget:
                und = True
                break
            r = attempt(P, tool, limit, cap)
            if r[0] == "HOLDS":
                found = (lab, r[2], {k: str(v) for k, v in r[1].items()})
                break
            if r[0] == "UNDECIDED":
                und = True
        if found:
            best = found if found[1] < best[1] else best
            hi = min(cap, F(found[1]).limit_denominator(10 ** 12))
        else:
            probe = cap
            if und:
                log.append(f"cap {float(cap):.8g}: undecided")
            else:                               # every live combination unsat under this cap: a proved bound
                lo = max(lo, cap)
    lo_proved = lo > 0
    return dict(result="FOUND", design=best[0], cost=best[1], x=best[2], lower_bound=float(lo),
                lower_bound_proved=lo_proved, gap_rel=float((F(best[1]).limit_denominator(10 ** 12) - lo) / F(best[1]).limit_denominator(10 ** 12)), probe=float(probe),
                combos=len(combos), refuted=refuted, undecided_first_pass=undecided, steps=steps, log=log)


def stand_reference(cid):
    """The stand's own answer at our objective reading (to compare like with like)."""
    out = json.load(open(HERE / "blind" / f"{cid}.out.json"))
    if out.get("verdict") != "EARNED":
        return dict(verdict=out.get("verdict"))
    b = BD.load(cid)
    d = BD.pinned_design(b, out)
    dd = {}
    x = {}
    for s, (cname, it) in d.items():
        cat = b["catalog"][cname]
        if isinstance(cat, dict) and "continuous" in cat:
            fld = cat["continuous"]["field"]
            x[f"{s}__{fld}"] = it[fld][0]
            lo, hi = F(B.num(cat["continuous"]["from"])), F(B.num(cat["continuous"]["to"]))
            dd[s] = (cname, {fld: ("range", lo, hi)})
        else:
            dd[s] = (cname, it)
    P = problem(b, dd)
    xs = {n: v * 1 for n, v in x.items()}
    # the amounts in SI as frame scales them: the range was scaled, the stand's printed value is in the slot's unit
    for s, (cname, it) in d.items():
        cat = b["catalog"][cname]
        if isinstance(cat, dict) and "continuous" in cat:
            n = f"{s}__{cat['continuous']['field']}"
            xs[n] = x[n] * S._scale(cat["continuous"].get("unit"))
    return dict(verdict="EARNED", design=S._label(d), our_reading=fval(P, xs), stand_value=out["objective"]["value"],
                stand_lower=out["objective"].get("lower_bound"))


def job(a):
    cid, tool, limit, budget = a
    t0 = time.time()
    try:
        r = brick(cid, tool, limit, budget)
    except Exception as e:  # noqa: BLE001
        r = dict(result=f"HARNESS ERROR: {type(e).__name__}: {str(e)[:300]}")
    r.update(brick=cid, tool=tool, wall_s=round(time.time() - t0, 1), at=time.strftime("%Y-%m-%d %H:%M:%S"))
    return r


def main():
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 60
    budget = int(args[args.index("--budget") + 1]) if "--budget" in args else 1800
    jobs = int(args[args.index("--jobs") + 1]) if "--jobs" in args else 18
    tools = args[args.index("--tools") + 1].split(",") if "--tools" in args else ["z3", "cvc5", "dreal"]
    cids = [a for a in args if re.fullmatch(r"c\d\d", a)] or BRICKS
    if "--ref" in args:
        for c in cids:
            print(c, json.dumps(stand_reference(c), ensure_ascii=False, default=str))
        return
    work = [(c, t, limit, budget) for c in cids for t in tools]
    with ProcessPoolExecutor(jobs) as ex, open(OUT, "a") as fh:
        for row in ex.map(job, work):
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            fh.flush()
            print(json.dumps(row, ensure_ascii=False, default=str)[:400], flush=True)


if __name__ == "__main__":
    main()
