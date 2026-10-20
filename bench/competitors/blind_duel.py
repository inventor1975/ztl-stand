"""THE DUEL, ROUND 2 — the blind-round bricks (examples/blind6, written by an independent writer) against Z3, cvc5, dReal.

2026-10-18, the curator's "Да, сначала A".

The translation reuses the STAND'S OWN reading of a brick (so a translation error cannot pose as a solver's loss):
  * bricks.load, the compiled laws (defines expanded, slot.field -> slot__field; an implicit law kept as the equation
    with its search range), the requirements moved into SI as the stand moves them;
  * stand.frame(b, design): exact values, tolerance boxes (catalog ranges included), derived names, computed values;
  * stand.designs(b) and stand._nominal_cost for the catalog and its cost order; stand._mode_brick for modes.
Per design one SMT problem: "some point of the box breaks some requirement" (every mode separately). UNSAT = the
design holds over its whole box; SAT = a counterexample; dReal's DELTA-SAT = undecided.

  * DISCRETE bricks (c02 c03 c04 c05 c08 c09): the full problem — designs in the stand's cost order, each checked,
    the first that holds is the solver's answer (optimal only if every cheaper design was REFUTED, not timed out);
  * bricks with CONTINUOUS choices (c01 c06 c07 c10 c11 c12): the check of the stand's own answer only (its design and
    amounts pinned) — the search over amounts is not given to the solvers (round B, dReal's exists-forall, later).
Functions: sqrt as s*s = a, s >= 0 (z3, cvc5) / sqrt (dReal); exp: cvc5, dReal (z3: not expressible); ln: cvc5 as
exp(y) = a, dReal log; pow with an integer exponent as a product, else exp(c ln a) / dReal pow; min, max, abs as ite.

    ~/venvs/competitors/bin/python bench/competitors/blind_duel.py [c02 ...] [--limit S] [--budget S] [--jobs J]
"""
import ast
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from ustand import bricks as B, stand as S  # noqa: E402

VENV = pathlib.Path.home() / "venvs" / "competitors" / "bin"
BLIND = ROOT / "examples" / "blind6"
OUT = HERE / "blind_results.jsonl"
DISCRETE = ["c02", "c03", "c04", "c05", "c08", "c09"]
CONTINUOUS = ["c01", "c06", "c07", "c10", "c11", "c12"]


class NotExpressible(Exception):
    pass


def var_names(tree):
    """Quantity names in an expression — not the names of the functions it calls."""
    funcs = {id(c.func) for c in ast.walk(tree) if isinstance(c, ast.Call)}
    return {x.id for x in ast.walk(tree) if isinstance(x, ast.Name) and id(x) not in funcs}


def num(f):
    f = F(f)
    a = f"(/ {abs(f.numerator)}.0 {f.denominator}.0)" if f.denominator != 1 else f"{abs(f.numerator)}.0"
    return a if f >= 0 else f"(- {a})"


def const(n):
    """An exact constant expression's value, or None when it names a quantity."""
    if isinstance(n, ast.Constant):
        return F(str(n.value))
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
        v = const(n.operand)
        return None if v is None else -v
    if isinstance(n, ast.BinOp) and not isinstance(n.op, ast.Pow):
        x, y = const(n.left), const(n.right)
        if x is None or y is None:
            return None
        return {ast.Add: x + y if True else 0, ast.Sub: x - y, ast.Mult: x * y,
                ast.Div: x / y if y else None}[type(n.op)] if not isinstance(n.op, ast.Add) else x + y
    return None


class Tr:
    """Python-AST expression -> SMT-LIB term for one tool; fresh helper variables go to self.extra."""

    def __init__(self, tool):
        self.tool, self.extra, self.k = tool, [], 0

    def fresh(self):
        self.k += 1
        n = f"_h{self.k}"
        self.extra.append(f"(declare-fun {n} () Real)")
        return n

    def t(self, n):
        if isinstance(n, ast.BinOp):
            if isinstance(n.op, ast.Pow):
                return self.power(n.left, n.right)
            op = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}[type(n.op)]
            return f"({op} {self.t(n.left)} {self.t(n.right)})"
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return f"(- {self.t(n.operand)})"
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.UAdd):
            return self.t(n.operand)
        if isinstance(n, ast.Constant):
            return num(F(str(n.value)))
        if isinstance(n, ast.Name):
            if n.id == "pi":
                return num(F("3.14159265358979323846"))
            return n.id
        if isinstance(n, ast.Call):
            f, a = n.func.id, n.args
            if f == "sqrt":
                x = self.t(a[0])
                if self.tool == "dreal":
                    return f"(sqrt {x})"
                s = self.fresh()
                self.extra += [f"(assert (= (* {s} {s}) {x}))", f"(assert (>= {s} 0.0))"]
                return s
            if f == "exp":
                if self.tool == "z3":
                    raise NotExpressible("exp")
                return f"(exp {self.t(a[0])})"
            if f in ("ln", "log", "log10"):
                x = self.t(a[0])
                if self.tool == "z3":
                    raise NotExpressible(f)
                if self.tool == "dreal":
                    v = f"(log {x})"
                else:
                    y = self.fresh()
                    self.extra.append(f"(assert (= (exp {y}) {x}))")
                    v = y
                return v if f != "log10" else f"(/ {v} {self.ln10()})"
            if f == "pow":
                return self.power(a[0], a[1])
            if f in ("sin", "cos", "tan", "atan"):
                if self.tool == "z3":
                    raise NotExpressible(f)
                name = {"atan": "arctan" if self.tool == "cvc5" else "atan"}.get(f, f)
                return f"({name} {self.t(a[0])})"
            if f in ("min", "max"):
                x, y = self.t(a[0]), self.t(a[1])
                return f"(ite (<= {x} {y}) {x if f == 'min' else y} {y if f == 'min' else x})"
            if f == "abs":
                x = self.t(a[0])
                return f"(ite (>= {x} 0.0) {x} (- {x}))"
            raise NotExpressible(f)
        raise NotExpressible(ast.dump(n)[:60])

    def ln10(self):
        if self.tool == "dreal":
            return "(log 10.0)"
        y = self.fresh()
        self.extra.append(f"(assert (= (exp {y}) 10.0))")
        return y

    def power(self, base, ex):
        e = const(ex)
        if e is not None and e.denominator == 1 and 0 <= e.numerator <= 12:
            if e == 0:
                return "1.0"
            b = self.t(base)
            return b if e == 1 else "(* " + " ".join([b] * e.numerator) + ")"
        if e is not None and e.denominator == 1 and -12 <= e.numerator < 0:
            b = self.t(base)
            return f"(/ 1.0 (* {' '.join([b] * (-e.numerator))}))" if e.numerator < -1 else f"(/ 1.0 {b})"
        if self.tool == "dreal":
            return f"(pow {self.t(base)} {self.t(ex)})"
        if self.tool == "z3":
            raise NotExpressible("non-integer power")
        y = self.fresh()
        self.extra.append(f"(assert (= (exp {y}) {self.t(base)}))")
        return f"(exp (* {self.t(ex)} {y}))"


def reqs_si(b):
    """The requirements in SI, as stand._run moves them (a number scaled by the quantity's unit; a bound with names
    compiled, not scaled)."""
    qscale = {n: S._scale(q.get("unit")) for n, q in b["quantities"].items()}
    out = []
    for r in b["requirements"]:
        sc = qscale[r["quantity"]]

        def bound(v):
            try:
                return ("num", B.num(v) * sc)
            except (ValueError, ZeroDivisionError, TypeError):
                text = B.compile_expr(v, b.get("define"))
                tree = ast.parse(text, mode="eval").body
                if not any(isinstance(n, ast.Name) for n in ast.walk(tree)):
                    lo, _ = B._ival(tree, {})
                    return ("num", lo * sc)
                return ("expr", tree)
        if r["op"] == "within":
            out.append((r["quantity"], "within", [bound(v) for v in r["value"]]))
        else:
            out.append((r["quantity"], r["op"], bound(r["value"])))
    return out


def smt(b, design, tool):
    fixed, boxes, derived, _ = S.frame(b, design)
    tr = Tr(tool)
    head = ["(set-logic ALL)"]
    names = set()
    laws = [B.compile_expr(l["zfl"], b.get("define")) for l in b["laws"]]
    body = []
    for law in laws:
        tree = ast.parse(law, mode="eval").body
        names |= var_names(tree)
        body.append(f"(assert (= {tr.t(tree.left)} {tr.t(tree.comparators[0])}))")
    viol = []
    for q, op, bd in reqs_si(b):
        names.add(q)

        def bt(x):
            if x[0] == "num":
                return num(x[1])
            names.update(var_names(x[1]))
            return tr.t(x[1])
        if op == "within":
            viol.append(f"(or (< {q} {bt(bd[0])}) (> {q} {bt(bd[1])}))")
        elif op == "<=":
            viol.append(f"(> {q} {bt(bd)})")
        elif op == "<":
            viol.append(f"(>= {q} {bt(bd)})")
        elif op == ">=":
            viol.append(f"(< {q} {bt(bd)})")
        elif op == ">":
            viol.append(f"(<= {q} {bt(bd)})")
        elif op == "==":
            viol.append(f"(not (= {q} {bt(bd)}))")
        else:
            raise NotExpressible(f"requirement op {op}")
    search = {n: q["search"] for n, q in b["quantities"].items() if q.get("role") == "derived" and "search" in q}
    names.discard("pi")
    for n in sorted(names):
        head.append(f"(declare-fun {n} () Real)")
        if n in fixed:
            head.append(f"(assert (= {n} {num(fixed[n])}))")
        elif n in boxes:
            lo, hi = boxes[n]
            head += [f"(assert (<= {num(lo)} {n}))", f"(assert (<= {n} {num(hi)}))"]
        elif n in search:
            sc = S._scale(b["quantities"][n].get("unit"))
            lo, hi = B.num(search[n][0]) * sc, B.num(search[n][1]) * sc
            head += [f"(assert (<= {num(lo)} {n}))", f"(assert (<= {n} {num(hi)}))"]
        elif n not in derived:
            raise NotExpressible(f"name {n} neither given, catalog nor derived")
    return "\n".join(head + tr.extra + body + [f"(assert (or {' '.join(viol)}))", "(check-sat)", "(exit)"]) + "\n"


def run_tool(tool, text, limit):
    with tempfile.NamedTemporaryFile("w", suffix=".smt2", delete=False) as fh:
        fh.write(text)
        path = fh.name
    cmd = {"z3": [str(VENV / "z3"), path], "cvc5": [str(VENV / "python"), str(HERE / "cvc5_run.py"), path],
           "dreal": [str(VENV / "dreal"), path]}[tool]
    t0 = time.time()
    p = subprocess.run(["timeout", str(limit)] + cmd, capture_output=True, text=True)
    os.unlink(path)
    out = (p.stdout + p.stderr).strip()
    res = ("TIMEOUT" if p.returncode == 124 else "UNSAT" if out.startswith("unsat") else
           "DELTA-SAT" if out.startswith("delta-sat") else "SAT" if out.startswith("sat") else
           "UNKNOWN" if out.startswith("unknown") else "ERROR: " + out[-160:].replace("\n", " "))
    return res, time.time() - t0


# ── bricks, designs, modes ───────────────────────────────────────────────────────────────────────────────────────
def load(cid):
    raw = json.load(open(BLIND / f"{cid}.json"))
    raw = {k: v for k, v in raw.items() if k != "find"}     # the decision, as the stand reports it next to the limit
    return B.load(raw)


def mode_bricks(b):
    if not b.get("modes"):
        return [("", b)]
    out = []
    for m, spec in b["modes"].items():
        mb = S._mode_brick(b, m, spec)
        try:
            mb = B.load(mb)
        except Exception:  # noqa: BLE001 — already loaded parts
            pass
        out.append((m, mb))
    return out


def check_design(b, design, tool, limit):
    """('HOLDS' | 'BROKEN' | 'UNDECIDED' | 'NOT EXPRESSIBLE: ...', seconds) over every mode."""
    total = 0.0
    undecided = None
    for m, mb in mode_bricks(b):
        try:
            text = smt(mb, design, tool)
        except NotExpressible as e:
            return f"NOT EXPRESSIBLE: {e}", total
        res, t = run_tool(tool, text, limit)
        total += t
        if res == "SAT":
            return "BROKEN", total
        if res != "UNSAT":
            undecided = res
    return ("HOLDS" if undecided is None else f"UNDECIDED ({undecided})"), total


def discrete(cid, tool, limit, budget):
    b = load(cid)
    obj = ast.parse(B.compile_expr(b["objective"]["minimize"], b.get("define")), mode="eval").body
    laws = B.implicit_laws(b, [B.compile_expr(l["zfl"], b.get("define")) for l in b["laws"]])
    ds = []
    for d in S.designs(b):
        try:
            ds.append((S._nominal_cost(b, d, obj, laws), d))
        except Exception:  # noqa: BLE001 — a design without a price is skipped, as the stand skips it
            pass
    ds.sort(key=lambda x: x[0])
    t0, undecided_cheaper, checked = time.time(), 0, 0
    for cost, d in ds:
        if time.time() - t0 > budget:
            return dict(result="BUDGET", checked=checked, undecided_cheaper=undecided_cheaper)
        res, _ = check_design(b, d, tool, limit)
        checked += 1
        if res.startswith("NOT EXPRESSIBLE"):
            return dict(result=res, checked=checked)
        if res == "HOLDS":
            return dict(result="FOUND", cost=str(cost), design=S._label(d), checked=checked,
                        optimal=undecided_cheaper == 0, undecided_cheaper=undecided_cheaper)
        if res.startswith("UNDECIDED"):
            undecided_cheaper += 1
    return dict(result="NONE HOLDS" if undecided_cheaper == 0 else "NONE PROVED", checked=checked,
                undecided_cheaper=undecided_cheaper)


def pinned_design(b, out):
    """The stand's answer back into frame's design form: catalog items by their labels, amounts by value."""
    d = {}
    for s, entry in out["design"].items():
        cname = entry["catalog"]
        cat = b["catalog"][cname]
        if isinstance(cat, dict) and "continuous" in cat:
            fld = cat["continuous"]["field"]
            v = entry[fld]
            d[s] = (cname, {fld: (F(v.split(" ")[0]), F(0))})
            continue
        labels = {k: v for k, v in entry.items() if isinstance(v, str) and k != "catalog"}
        for it in B.items(cat):
            if all(it.get(k) == ("label", v) for k, v in labels.items()):
                d[s] = (cname, it)
                break
        else:
            raise ValueError(f"{s}: item {labels} not found in {cname}")
    return d


def continuous(cid, tool, limit):
    out = json.load(open(HERE / "blind" / f"{cid}.out.json"))
    if out.get("verdict") != "EARNED":
        return dict(result=f"stand {out.get('verdict')}: no design to check (round B)")
    b = load(cid)
    res, t = check_design(b, pinned_design(b, out), tool, limit)
    return dict(result=res, wall=round(t, 2))


def job(a):
    cid, tool, limit, budget = a
    t0 = time.time()
    try:
        r = discrete(cid, tool, limit, budget) if cid in DISCRETE else continuous(cid, tool, limit)
    except Exception as e:  # noqa: BLE001
        r = dict(result=f"HARNESS ERROR: {type(e).__name__}: {str(e)[:200]}")
    r.update(brick=cid, tool=tool, wall_s=round(time.time() - t0, 2), at=time.strftime("%Y-%m-%d %H:%M:%S"))
    return r


def main():
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 60
    budget = int(args[args.index("--budget") + 1]) if "--budget" in args else 900
    jobs = int(args[args.index("--jobs") + 1]) if "--jobs" in args else 12
    tools = args[args.index("--tools") + 1].split(",") if "--tools" in args else ["z3", "cvc5", "dreal"]
    cids = [a for a in args if a.startswith("c") and len(a) == 3] or DISCRETE + CONTINUOUS
    work = [(c, t, limit, budget) for c in cids for t in tools]
    with ProcessPoolExecutor(jobs) as ex, open(OUT, "a") as fh:
        for row in ex.map(job, work):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            print(json.dumps(row, ensure_ascii=False)[:300], flush=True)


if __name__ == "__main__":
    main()
