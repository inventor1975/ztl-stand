"""THE DUEL — ztl-stand against Z3, cvc5 and dReal on the stand's own synthetic axes (bench/scale.py).

Started 2026-10-18 on the curator's word ("начинай с Z3, cvc5 и dReal").

Each instance is one brick of an axis at one size, in two variants:
  * PROVE   — the axis' own bound (true over the whole tolerance box): the stand should say EARNED, a solver UNSAT for
              "some point of the box violates the requirement";
  * REFUTE  — the bound moved just inside the true extreme (or to the nominal value, where the extreme is not known in
              closed form): the stand should say REFUTED, a solver SAT (a counterexample).
The SMT-LIB is generated from the brick itself (quantities -> bounded reals, laws -> equalities, the requirement
negated); for `network` the nodal equations, for `chain` the composition. Solvers:
  * z3 (CLI from the z3-solver wheel; no exp — a transcendental law is "not expressible");
  * cvc5 (Python API, logic ALL: transcendental extension, incomplete);
  * dReal 4 (delta = 1e-3: UNSAT is a proof, DELTA-SAT is not a counterexample — it may be within delta).
Every run under `timeout`, one process per instance; several instances run in parallel (times are upper bounds).

    ~/venvs/competitors/bin/python bench/competitors/duel.py [axis ...] [--limit S] [--jobs J]
-> bench/competitors/results.jsonl (one row per instance x variant x tool)
"""
import ast
import json
import math
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F

HERE = pathlib.Path(__file__).resolve().parent
BENCH = HERE.parent
ROOT = BENCH.parent
sys.path.insert(0, str(BENCH))
import scale  # noqa: E402

VENV = pathlib.Path.home() / "venvs" / "competitors" / "bin"
STAND_PY = os.environ.get("USTAND_PY", sys.executable)   # a python with numpy and sympy
OUT = HERE / "results.jsonl"


# ── bricks -> SMT-LIB ────────────────────────────────────────────────────────────────────────────────────────────
def num(s):
    f = F(str(s))
    if f.denominator == 1:
        return str(f.numerator) + ".0" if f >= 0 else f"(- {-f.numerator}.0)"
    a = f"(/ {abs(f.numerator)}.0 {f.denominator}.0)"
    return a if f >= 0 else f"(- {a})"


def sx(node):
    """A Python expression node (the stand's zfl infix) as an SMT-LIB term."""
    if isinstance(node, ast.BinOp):
        op = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}[type(node.op)]
        return f"({op} {sx(node.left)} {sx(node.right)})"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return f"(- {sx(node.operand)})"
    if isinstance(node, ast.Constant):
        return num(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call) and node.func.id == "exp":
        return f"(exp {sx(node.args[0])})"
    raise ValueError(f"not encoded: {ast.dump(node)}")


def box(d):
    if "range" in d:
        return F(d["range"][0]), F(d["range"][1])
    v = F(d["value"])
    t = F(d.get("tolerance") or 0)
    lo, hi = v * (1 - t), v * (1 + t)
    return min(lo, hi), max(lo, hi)


def smt_laws(brick, req_bound):
    """SMT-LIB for 'some point of the box breaks the requirement' (single-requirement bricks with zfl laws)."""
    lines = ["(set-logic ALL)"]
    names = []
    for nm, d in brick["quantities"].items():
        names.append(nm)
        lines.append(f"(declare-fun {nm} () Real)")
        if d["role"] == "given":
            lo, hi = box(d)
            lines.append(f"(assert (<= {num(lo)} {nm}))")
            lines.append(f"(assert (<= {nm} {num(hi)}))")
    for law in brick["laws"]:
        tree = ast.parse(law["zfl"].replace("==", "=="), mode="eval").body
        lines.append(f"(assert (= {sx(tree.left)} {sx(tree.comparators[0])}))")
    r = brick["requirements"][0]
    viol = {"<=": ">", ">=": "<"}[r["op"]]
    lines.append(f"(assert ({viol} {r['quantity']} {num(req_bound)}))")
    lines += ["(check-sat)", "(exit)"]
    return "\n".join(lines) + "\n"


def smt_network(brick, req_bound_mA):
    """The grid's nodal equations: node potentials, each branch I = (from - to)/R, KCL at every free node."""
    qs, net = brick["quantities"], brick["network"]
    src = net["source"]
    lines = ["(set-logic ALL)"]
    nodes = set()
    for b in net["branches"].values():
        nodes |= {b["from"], b["to"]}
    for nm, d in qs.items():
        lines.append(f"(declare-fun {nm} () Real)")
        lo, hi = box(d)
        lines.append(f"(assert (<= {num(lo)} {nm}))")
        lines.append(f"(assert (<= {nm} {num(hi)}))")
    for n in sorted(nodes):
        lines.append(f"(declare-fun v_{n} () Real)")
    lines.append(f"(assert (= v_{src['to']} 0.0))")
    lines.append(f"(assert (= v_{src['from']} {src['V']}))")
    for bn, b in net["branches"].items():
        lines.append(f"(declare-fun {bn} () Real)")
        lines.append(f"(assert (= (* {bn} {b['R']}) (- v_{b['from']} v_{b['to']})))")
    for n in sorted(nodes - {src["from"], src["to"]}):
        out = [bn for bn, b in net["branches"].items() if b["from"] == n]
        inn = [bn for bn, b in net["branches"].items() if b["to"] == n]
        lines.append(f"(assert (= (+ 0.0 {' '.join(inn)}) (+ 0.0 {' '.join(out)})))")
    q = brick["requirements"][0]["quantity"][2:-1]
    lines.append(f"(assert (> (* 1000.0 {q}) {num(req_bound_mA)}))")
    lines += ["(check-sat)", "(exit)"]
    return "\n".join(lines) + "\n"


def smt_chain(brick, req_bound):
    """The chain composed: v_0 = Vs, v_{i+1} = g_i * v_i + off_i."""
    comps = brick["components"]
    n = len(comps)
    lines = ["(set-logic ALL)", "(declare-fun Vs () Real)"]
    lo, hi = box(brick["quantities"]["Vs"])
    lines += [f"(assert (<= {num(lo)} Vs))", f"(assert (<= Vs {num(hi)}))"]
    prev = "Vs"
    for i in range(n):
        qd = comps[f"C{i}"]["brick"]["quantities"]
        for nm in ("g", "off"):
            lo, hi = box(qd[nm])
            lines += [f"(declare-fun {nm}{i} () Real)", f"(assert (<= {num(lo)} {nm}{i}))",
                      f"(assert (<= {nm}{i} {num(hi)}))"]
        lines += [f"(declare-fun v{i} () Real)", f"(assert (= v{i} (+ (* g{i} {prev}) off{i})))"]
        prev = f"v{i}"
    lines.append(f"(assert (> {prev} {num(req_bound)}))")
    lines += ["(check-sat)", "(exit)"]
    return "\n".join(lines) + "\n"


# ── the axes: brick, its true extreme, the refuting bound ───────────────────────────────────────────────────────
def nominal_numeric(brick):
    """lin_system / network nominal values by numpy (for the REFUTE bound only)."""
    import numpy as np
    if "network" in brick:
        net = brick["network"]
        nodes = sorted({x for b in net["branches"].values() for x in (b["from"], b["to"])} - {"a", "gnd"})
        idx = {n: i for i, n in enumerate(nodes)}
        Gm = np.zeros((len(nodes), len(nodes)))
        rhs = np.zeros(len(nodes))
        V = float(brick["quantities"]["V"]["value"])
        for b in net["branches"].values():
            g = 1 / 100.0
            for a_, c_ in ((b["from"], b["to"]), (b["to"], b["from"])):
                if a_ in idx:
                    Gm[idx[a_], idx[a_]] += g
                    if c_ in idx:
                        Gm[idx[a_], idx[c_]] -= g
                    elif c_ == "a":
                        rhs[idx[a_]] += g * V
        v = np.linalg.solve(Gm, rhs)
        return float((V - v[idx["n0_1"]]) / 100.0 * 1000)
    return None


def instances(axis, size):
    gen = getattr(scale, axis)
    b = gen(size)
    if axis == "corners_lin":
        top = sum((1 + i % 3) * (10 + i) * F("1.05") for i in range(size))
        return b, "laws", float(top) * 0.99
    if axis == "corners_peak":
        return b, "laws", 100 * size * 0.999
    if axis == "corners_rational":
        return b, "laws", size * 0.5 * 0.999
    if axis == "corners_mono":
        return b, "laws", math.exp(1.1) * 11 * size * 0.999
    if axis == "lin_system":
        import numpy as np
        n = size
        A = np.zeros((n, n))
        rhs = np.zeros(n)
        for i in range(n):
            Ri, Gi = 100 + 10 * i, 200 + 10 * i
            A[i, i] += 1 / Ri + 1 / Gi
            if i > 0:
                A[i, i - 1] -= 1 / Ri
            else:
                rhs[i] += 10 / Ri
            if i + 1 < n:
                Rn = 100 + 10 * (i + 1)
                A[i, i] += 1 / Rn
                A[i, i + 1] -= 1 / Rn
        u = np.linalg.solve(A, rhs)
        return b, "laws", float(u[-1])            # u_{n-1} >= nominal: the low corner breaks it
    if axis == "network":
        return b, "network", nominal_numeric(b)
    if axis == "chain":
        nom = 5.0 * 1.01 ** size
        return b, "chain", nom
    raise ValueError(axis)


def with_bound(brick, kind, bound):
    import copy
    b = copy.deepcopy(brick)
    r = b["requirements"][0]
    if kind == "network":
        r["value"] = repr(round(bound, 9))
    else:
        r["value"] = repr(round(bound, 9))
    return b


def smt_for(brick, kind):
    r = brick["requirements"][0]
    bound = F(r["value"])
    if kind == "network":
        return smt_network(brick, bound)
    if kind == "chain":
        return smt_chain(brick, bound)
    return smt_laws(brick, bound)


# ── the runs ─────────────────────────────────────────────────────────────────────────────────────────────────────
def run_tool(tool, smt, limit):
    with tempfile.NamedTemporaryFile("w", suffix=".smt2", delete=False) as fh:
        fh.write(smt)
        path = fh.name
    cmd = {"z3": [str(VENV / "z3"), path],
           "cvc5": [str(VENV / "python"), str(HERE / "cvc5_run.py"), path],
           "dreal": [str(VENV / "dreal"), path]}[tool]
    t0 = time.time()
    try:
        p = subprocess.run(["timeout", str(limit)] + cmd, capture_output=True, text=True)
        out = (p.stdout + p.stderr).strip()
        if p.returncode == 124:
            res = "TIMEOUT"
        elif out.startswith("unsat"):
            res = "UNSAT"
        elif out.startswith("delta-sat"):
            res = "DELTA-SAT"
        elif out.startswith("sat"):
            res = "SAT"
        elif out.startswith("unknown"):
            res = "UNKNOWN"
        else:
            res = "ERROR: " + out[-200:].replace("\n", " ")
    finally:
        os.unlink(path)
    return res, round(time.time() - t0, 2)


def run_stand(brick, limit):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=str(BENCH)) as fh:
        json.dump(brick, fh)
        path = fh.name
    t0 = time.time()
    try:
        p = subprocess.run(["timeout", str(limit), STAND_PY, "-m", "ustand.stand", path], capture_output=True,
                           text=True, cwd=str(ROOT), env=dict(os.environ, OPENBLAS_NUM_THREADS="1"))
        if p.returncode == 124:
            res = "TIMEOUT"
        else:
            try:
                res = json.loads(p.stdout).get("verdict", "?")
            except ValueError:
                res = "ERROR: " + p.stderr[-200:].replace("\n", " ")
    finally:
        os.unlink(path)
    return res, round(time.time() - t0, 2)


def job(args):
    axis, size, variant, tool, limit = args
    b, kind, refute_bound = instances(axis, size)
    if variant == "refute":
        b = with_bound(b, kind, refute_bound)
    if tool == "stand":
        res, t = run_stand(b, limit)
    else:
        try:
            smt = smt_for(b, kind)
        except ValueError as e:
            return dict(axis=axis, size=size, variant=variant, tool=tool, result=f"NOT ENCODED: {e}", wall_s=0)
        if tool == "z3" and "(exp " in smt:
            return dict(axis=axis, size=size, variant=variant, tool=tool, result="NOT EXPRESSIBLE (exp)", wall_s=0)
        res, t = run_tool(tool, smt, limit)
    return dict(axis=axis, size=size, variant=variant, tool=tool, result=res, wall_s=t,
                at=time.strftime("%Y-%m-%d %H:%M:%S"))


AXES = {
    "corners_lin": [4, 16, 64, 128],
    "corners_peak": [1, 2, 4, 8, 12, 16, 24],
    "corners_rational": [1, 2, 4, 8, 12, 16, 24],
    "corners_mono": [2, 4, 8, 16, 32],
    "lin_system": [2, 3, 4, 6, 8, 12],
    "network": [3, 5, 10, 20],
    "chain": [2, 8, 32, 128],
}


def main():
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 120
    jobs = int(args[args.index("--jobs") + 1]) if "--jobs" in args else 12
    axes = [a for a in args if a in AXES] or list(AXES)
    tools = args[args.index("--tools") + 1].split(",") if "--tools" in args else ["stand", "z3", "cvc5", "dreal"]
    variants = args[args.index("--variants") + 1].split(",") if "--variants" in args else ["prove", "refute"]
    work = [(a, s, v, t, limit) for a in axes for s in AXES[a] for v in variants for t in tools]
    with ProcessPoolExecutor(jobs) as ex, open(OUT, "a") as fh:
        for row in ex.map(job, work):
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            print(f"{row['axis']:17s} {row['size']:4d} {row['variant']:6s} {row['tool']:5s} {row['result']:22s} "
                  f"{row['wall_s']:7.2f}s", flush=True)


if __name__ == "__main__":
    main()
