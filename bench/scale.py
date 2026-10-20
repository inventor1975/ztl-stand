"""SCALE — what the stand handles in reasonable time, on which machine (2026-10-13, the curator's question).

Synthetic bricks along one axis of difficulty each, sizes growing until a run does not finish within the limit.
Every run: one performance core (taskset), ~/bin/heavy with a memory cap, `timeout`; wall time and peak memory
(GNU time) recorded with the verdict. Results: bench/results/<axis>.jsonl; `--table` prints them.

    python3 bench/scale.py AXIS [--cpu N] [--limit S]     # one axis, sizes in order, stops at the first timeout
    python3 bench/scale.py --table

The bricks are generated, not hand-written: each axis isolates one cost (corners, designs, amounts, unknowns,
network size, chain length, modes). The verdicts are part of the record — a fast wrong answer is not a speed.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
RES = HERE / "results"


def q(v, tol=None, unit="", rng=None):
    d = {"role": "given", "unit": unit}
    if rng is not None:
        d["range"] = [str(rng[0]), str(rng[1])]
    else:
        d["value"] = str(v)
        if tol:
            d["tolerance"] = str(tol)
    return d


def der(unit=""):
    return {"role": "derived", "unit": unit}


# ── the axes ────────────────────────────────────────────────────────────────────────────────────────────────────
def corners_lin(n):
    """n toleranced quantities in a linear law: decided at the corners (the easy class)."""
    qs = {f"x{i}": q(10 + i, "0.05") for i in range(n)}
    qs["y"] = der()
    nominal = sum(10 + i for i in range(n))
    return {"stand": "ztl-stand/1", "quantities": qs,
            "laws": [{"zfl": "y == " + " + ".join(f"{1 + i % 3}*x{i}" for i in range(n))}],
            "requirements": [{"quantity": "y", "op": "<=", "value": str(round(nominal * 2.2, 3))}]}


def corners_peak(n):
    """n toleranced quantities, each term with its peak INSIDE its box (x(20 - x), box 9..11): the extreme is
    interior, corners do not decide — a certificate has to. The bound 1 % above the true maximum 100 n."""
    qs = {f"x{i}": q(10, "0.1") for i in range(n)}
    qs["y"] = der()
    return {"stand": "ztl-stand/1", "quantities": qs,
            "laws": [{"zfl": "y == " + " + ".join(f"x{i}*(20 - x{i})" for i in range(n))}],
            "requirements": [{"quantity": "y", "op": "<=", "value": str(100 * n * 1.01)}]}


def corners_rational(n):
    """n toleranced quantities, each term x/(1 + x^2) with its peak (x = 1) INSIDE the box 0.5..2 — no polynomial,
    so no exact reading: a certificate has to decide. The bound 1 % above the true maximum n/2."""
    qs = {f"x{i}": q(0, rng=("0.5", "2")) for i in range(n)}
    qs["y"] = der()
    return {"stand": "ztl-stand/1", "quantities": qs,
            "laws": [{"zfl": "y == " + " + ".join(f"x{i}/(1 + x{i}*x{i})" for i in range(n))}],
            "requirements": [{"quantity": "y", "op": "<=", "value": str(round(n * 0.5 * 1.01, 6))}]}


def corners_mono(n):
    """n toleranced quantities in a MONOTONE nonlinear law sum exp(x_i/10)·x_(i+1) (each name twice): exact at the
    corners in truth, but no reading is; the bound 1 % above the all-high corner's value."""
    import math
    qs = {f"x{i}": q(10, "0.1") for i in range(n)}
    qs["y"] = der()
    terms = [f"exp(x{i}/10)*x{(i + 1) % n}" for i in range(n)]
    top = sum(math.exp(1.1) * 11 for _ in range(n))
    return {"stand": "ztl-stand/1", "quantities": qs, "laws": [{"zfl": "y == " + " + ".join(terms)}],
            "requirements": [{"quantity": "y", "op": "<=", "value": str(round(top * 1.01, 6))}]}


def designs(total):
    """Discrete combinations: 3 slots of k items each (k^3 ~ total), a toleranced law, a window that few pass,
    cost minimised — the catalog search with pruning."""
    k = max(2, round(total ** (1 / 3)))
    cat = lambda off: {"items": [{"v": str(off + j), "p": str(1 + (j * 7) % 13)} for j in range(k)],
                       "fields": {"v": {"unit": ""}, "p": {"unit": "EUR"}}}
    return {"stand": "ztl-stand/1",
            "quantities": {"g": q(1, "0.02"), "y": der()},
            "slots": {"A": {"from": ["ca"]}, "B": {"from": ["cb"]}, "C": {"from": ["cc"]}},
            "catalog": {"ca": cat(1), "cb": cat(2), "cc": cat(3)},
            "laws": [{"zfl": "y == g*(A.v + 2*B.v + 3*C.v)"}],
            # the window 6 % wide at every k (a fixed +-3 window became impossible past k ~ 70: g's 2 % alone is wider —
            # the stand's REFUTED at 10^6 was right, the generator wrong, 2026-10-13)
            "requirements": [{"quantity": "y", "op": "within", "value": [str(3 * k), str(round(3 * k * 1.06, 3))]}],
            "objective": {"minimize": "A.p + B.p + C.p", "unit": "EUR"}}


def lp_amounts(n):
    """n continuous amounts, a diet: n/2 + 2 nutrient rows with +-5 % coefficients, a batch total — the robust LP."""
    rows = n // 2 + 2
    qs, laws, reqs, slots, cats = {}, [], [], {}, {}
    for j in range(n):
        slots[f"I{j}"] = {"from": [f"i{j}"]}
        cats[f"i{j}"] = {"continuous": {"field": "x", "from": "0", "to": "1", "unit": ""}}
    for r in range(rows):
        terms = []
        for j in range(n):
            c = 1 + ((r * 7 + j * 3) % 9)
            qs[f"a{r}_{j}"] = q(c, "0.05")
            terms.append(f"a{r}_{j}*I{j}.x")
        qs[f"N{r}"] = der()
        laws.append({"zfl": f"N{r} == " + " + ".join(terms)})
        reqs.append({"quantity": f"N{r}", "op": ">=", "value": "2"})
    qs["T"] = der()
    laws.append({"zfl": "T == " + " + ".join(f"I{j}.x" for j in range(n))})
    reqs.append({"quantity": "T", "op": "within", "value": ["1", "1"]})
    return {"stand": "ztl-stand/1", "quantities": qs, "slots": slots, "catalog": cats, "laws": laws,
            "requirements": reqs,
            "objective": {"minimize": " + ".join(f"{1 + (j * 5) % 7}*I{j}.x" for j in range(n))}}


def nl_amounts(n):
    """n continuous amounts entering NONLINEARLY (sum a_i / x_i <= B): the local solver and zmin's split."""
    qs = {f"a{i}": q(1 + i, "0.05") for i in range(n)}
    qs["S"] = der()
    slots = {f"X{i}": {"from": [f"x{i}"]} for i in range(n)}
    cats = {f"x{i}": {"continuous": {"field": "v", "from": "0.5", "to": "10", "unit": ""}} for i in range(n)}
    return {"stand": "ztl-stand/1", "quantities": qs, "slots": slots, "catalog": cats,
            "laws": [{"zfl": "S == " + " + ".join(f"a{i}/X{i}.v" for i in range(n))}],
            "requirements": [{"quantity": "S", "op": "<=", "value": str(n)}],
            "objective": {"minimize": " + ".join(f"X{i}.v" for i in range(n))}}


def lin_system(n):
    """n linear unknowns: a resistor LADDER, node i: (left - u_i)/R_i == u_i/G_i + (u_i - u_{i+1})/R_{i+1},
    toleranced R and G — the stand solves it (the kernel itself up to 6 unknowns)."""
    qs = {"Vs": q(10, "0.02", "V")}
    laws = []
    for i in range(n):
        qs[f"R{i}"] = q(100 + 10 * i, "0.01", "ohm")
        qs[f"G{i}"] = q(200 + 10 * i, "0.01", "ohm")
        qs[f"u{i}"] = der("V")
    for i in range(n):
        left = "Vs" if i == 0 else f"u{i - 1}"
        right = f" + (u{i} - u{i + 1})/R{i + 1}" if i + 1 < n else ""
        laws.append({"zfl": f"(({left}) - u{i})/R{i} == u{i}/G{i}{right}"})
    return {"stand": "ztl-stand/1", "quantities": qs, "laws": laws,
            "requirements": [{"quantity": f"u{n - 1}", "op": ">=", "value": "0.001"}]}


def network(n):
    """An n x n resistor grid, +-2 % each, a 10 V source across opposite corners, one branch current bounded."""
    qs = {"V": q(10, unit="V")}
    br = {}
    for i in range(n):
        for j in range(n):
            for (di, dj, tag) in ((0, 1, "h"), (1, 0, "v")):
                if i + di < n and j + dj < n:
                    nm = f"R{tag}{i}_{j}"
                    qs[nm] = q(100, "0.02", "ohm")
                    to = f"n{i + di}_{j + dj}" if (i + di, j + dj) != (n - 1, n - 1) else "gnd"
                    frm = f"n{i}_{j}" if (i, j) != (0, 0) else "a"
                    br[f"b{tag}{i}_{j}"] = {"from": frm, "to": to, "R": nm}
    return {"stand": "ztl-stand/1", "quantities": qs,
            "network": {"branches": br, "source": {"from": "a", "to": "gnd", "V": "V"}},
            "requirements": [{"quantity": "I(bh0_0)", "op": "<=", "value": "100", "unit": "mA"}]}


def chain(n):
    """A chain of n components, each out = g*in + off (g +-1 %, off +-1 mV), arriving bands: the system's cost."""
    comps, connect = {}, {}
    for i in range(n):
        comps[f"C{i}"] = {"brick": {
            "stand": "ztl-stand/1",
            "interface": {"inputs": {"vin": {"assume": ["0", "100"], "bands": "arriving"}}, "outputs": ["vout"]},
            "quantities": {"vin": q(1, unit="V"), "g": q("1.01", "0.01"), "off": q(0, rng=("-0.001", "0.001"), unit="V"),
                           "vout": der("V")},
            "laws": [{"zfl": "vout == g*vin + off"}], "requirements": []}}
        connect[f"C{i}.vin"] = "Vs" if i == 0 else f"C{i - 1}.vout"
    return {"stand": "ztl-stand/1", "components": comps, "connect": connect,
            "quantities": {"Vs": q(5, "0.01", "V"), "Vend": der("V")},
            "laws": [{"zfl": f"Vend == C{n - 1}.vout"}],
            "requirements": [{"quantity": "Vend", "op": "<=", "value": str(round(5 * 1.05 * 1.03 ** n, 3))}]}


def modes(n):
    """n operating modes of one design choice (ambient per mode), 27 designs — the per-mode cost."""
    # ambients spread over -20..60 C at every n (-20 + 5 i passed 150 C - P*3 K/W at n = 32: impossible, the stand right)
    md = {f"m{i}": {"quantities": {"Ta": {"value": str(round(-20 + 80 * i / max(1, n - 1), 3))}},
                    "requirements": [{"quantity": "Tj", "op": "<=", "value": "150"}]} for i in range(n)}
    k = 3
    cat = lambda off: {"items": [{"v": str(off + j), "p": str(1 + j)} for j in range(k)],
                       "fields": {"v": {"unit": "K/W"}, "p": {"unit": "EUR"}}}
    return {"stand": "ztl-stand/1",
            "quantities": {"P": q(10, "0.1", "W"), "Ta": q(25, unit="K"), "Tj": der("K")},
            "slots": {"A": {"from": ["ca"]}, "B": {"from": ["cb"]}, "C": {"from": ["cc"]}},
            "catalog": {"ca": cat(1), "cb": cat(1), "cc": cat(1)},
            "laws": [{"zfl": "Tj == Ta + P*(A.v + B.v + C.v)"}], "requirements": [], "modes": md,
            "objective": {"minimize": "A.p + B.p + C.p", "unit": "EUR"}}


AXES = {
    "corners_lin": (corners_lin, [4, 8, 12, 16, 20, 24, 32, 48, 64, 96, 128]),
    "corners_peak": (corners_peak, [1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32]),
    "corners_rational": (corners_rational, [1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 20, 24]),
    "corners_mono": (corners_mono, [2, 4, 8, 16, 32, 64, 128]),
    "designs": (designs, [10 ** 2, 10 ** 3, 10 ** 4, 10 ** 5, 10 ** 6, 10 ** 7]),
    "lp_amounts": (lp_amounts, [2, 5, 10, 20, 40, 80, 120, 160]),
    "nl_amounts": (nl_amounts, [1, 2, 3, 4, 5, 6, 8, 10]),
    "lin_system": (lin_system, [2, 3, 4, 5, 6, 7, 8, 10, 12]),
    "network": (network, [5, 10, 20, 30, 50]),
    "chain": (chain, [2, 4, 8, 16, 32, 64, 128, 256]),
    "modes": (modes, [1, 2, 4, 8, 16, 32, 64, 128]),
}


def run(brick, cpu, limit, extra=(), cores=1):
    """One stand run on the CPUs `cpu` (a taskset list), its wall time and peak RSS (GNU time's %M: the largest
    single process — with --jobs the main process or one worker, not their sum)."""
    if isinstance(brick, str):          # a brick file as it is (a real round's brick: its relative `file`s resolve)
        path, tmp = os.path.abspath(brick), False
    else:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=str(HERE)) as fh:
            json.dump(brick, fh)
            path, tmp = fh.name, True
    cmd = ["taskset", "-c", str(cpu), "/usr/bin/time", "-f", "TIME %e %M",
           os.path.expanduser("~/bin/heavy"), "-m", "8G", "--cores", str(cores),
           "timeout", str(limit), sys.executable, "-m", "ustand.stand", *extra, path]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT),
                       env=dict(os.environ, OPENBLAS_NUM_THREADS="1"))
    wall = time.time() - t0
    if tmp:
        os.unlink(path)
    rss = None
    for line in p.stderr.splitlines():
        if line.startswith("TIME "):
            rss = int(line.split()[2]) // 1024
    try:
        out = json.loads(p.stdout)
    except ValueError:
        out = {"verdict": "NO OUTPUT", "why": p.stderr[-300:]}
    return wall, rss, out


def main():
    args = sys.argv[1:]
    if "--table" in args:
        table()
        return
    axis = args[0]
    cpu = args[args.index("--cpu") + 1] if "--cpu" in args else "0"
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 600
    extra = ["--dev"] if "--dev" in args else []
    jobs = int(args[args.index("--jobs") + 1]) if "--jobs" in args else 1
    if jobs > 1:
        extra += ["--jobs", str(jobs)]
    if axis == "files":                 # `files a.json b.json ...`: real bricks, each its own row, none stops the rest
        gen, sizes = (lambda f: f), [a for a in args[1:] if a.endswith(".json")]
    else:
        gen, sizes = AXES[axis]
    if "--sizes" in args:
        sizes = [int(x) for x in args[args.index("--sizes") + 1].split(",")]
    RES.mkdir(exist_ok=True)
    for size in sizes:
        wall, rss, out = run(gen(size), cpu, limit, extra, cores=jobs)
        stopped = "stopped" in str(out.get("why", "")) or wall >= limit - 1
        rec = {"axis": axis, "size": size, "wall_s": round(wall, 2), "peak_mb": rss, "verdict": out.get("verdict"),
               "stopped": stopped, "why": str(out.get("why") or "")[:160], "mode": "dev" if "--dev" in extra else "work",
               "jobs": jobs, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "cpu": cpu}
        with open(RES / f"{axis}.jsonl", "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(json.dumps(rec), flush=True)
        if stopped and axis != "files":
            break


def table():
    rows = []
    for f in sorted(RES.glob("*.jsonl")):
        for line in open(f):
            rows.append(json.loads(line))
    for r in rows:
        print(f"{r['axis']:16s} {str(r['size'])[-22:]:>22} j{r.get('jobs', 1):<2} {r['wall_s']:>8.1f} s "
              f"{str(r['peak_mb']):>6} MB  {r['verdict']}"
              f"{'  (stopped)' if r['stopped'] else ''}")


if __name__ == "__main__":
    main()
