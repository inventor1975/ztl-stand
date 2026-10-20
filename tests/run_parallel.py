"""Run tests/test_stand.py on many cores (the curator, 2026-10-15: "the tests run on one core, and we have many").

The suite is one long script (~930 top-level statements, ~280 checks): later sections read earlier ones' variables.
It is cut by SLICING, not by hand: every top-level statement that checks something (a `check(...)` call, directly or
through a helper that calls it) is a TARGET; the targets are dealt to N shards; each shard runs, in the file's own
order, its targets plus exactly the statements they depend on:
  - for every name a statement reads, the LAST earlier statement that binds or mutates it (an assignment, a def, an
    import, `x[...] = `, `x.attr = `, `x.method(...)`), recursively; a function's free names are read at the call;
  - the PRELUDE (every statement before the first target: imports, helpers, the dev-mode switch);
  - every statement that patches an imported module's state (`J.judge = lying`, `_MODE.DEV[0] = False`, their
    restores, `CM._CACHE.clear()`, `_sys.path.insert(...)`) before the shard's last statement — hidden state, read
    by the stand without naming it.
A shard re-runs the prerequisites another shard owns; their checks are silenced (each check is reported by exactly
one shard). The suite's verdict is the union.

The cut is CHECKED, not trusted: `--compare LOG` reads a sequential run's output and requires the same multiset of
check lines (name and OK/FAIL). Run: python3 -m tests.run_parallel [--jobs 16] [--compare seq.log] (repo root).
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import subprocess
import sys
import time
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "test_stand.py"


def _base(t):
    while isinstance(t, (ast.Attribute, ast.Subscript, ast.Starred)):
        t = t.value
    return t.id if isinstance(t, ast.Name) else None


class _Scan(ast.NodeVisitor):
    """Top-level binds (and mutations) of one statement, and every name it reads."""
    def __init__(self, modules=frozenset()):
        self.binds, self.reads, self.depth, self.modules = set(), set(), 0, modules

    def visit_Name(self, n):
        if isinstance(n.ctx, ast.Load):
            self.reads.add(n.id)
        elif self.depth == 0:
            self.binds.add(n.id)

    def _scope(self, n):
        self.depth += 1
        self.generic_visit(n)
        self.depth -= 1

    def visit_FunctionDef(self, n):
        if self.depth == 0:
            self.binds.add(n.name)
        for d in n.decorator_list:
            self.visit(d)
        self._scope(n)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, n):
        if self.depth == 0:
            self.binds.add(n.name)
        self._scope(n)

    def visit_Lambda(self, n):
        self._scope(n)

    def visit_ListComp(self, n):
        self._scope(n)

    visit_SetComp = visit_DictComp = visit_GeneratorExp = visit_ListComp

    def visit_Import(self, n):
        for a in n.names:
            if self.depth == 0:
                self.binds.add((a.asname or a.name).split(".")[0])

    visit_ImportFrom = visit_Import

    def _mut(self, t):
        b = _base(t)
        if b and self.depth == 0 and not isinstance(t, ast.Name):
            self.binds.add(b)               # x[...] = / x.a = : a mutation of x
            self.reads.add(b)

    def visit_Assign(self, n):
        for t in n.targets:
            for x in _targets(t):
                self._mut(x)
        self.generic_visit(n)

    def visit_AugAssign(self, n):
        self._mut(n.target)
        if isinstance(n.target, ast.Name) and self.depth == 0:
            self.reads.add(n.target.id)
        self.generic_visit(n)

    def visit_Delete(self, n):
        for t in n.targets:
            for x in _targets(t):
                self._mut(x)
        self.generic_visit(n)

    def visit_Call(self, n):
        if isinstance(n.func, ast.Attribute) and self.depth == 0:
            b = _base(n.func.value)
            if b and b != "check" and b not in self.modules:
                self.binds.add(b)           # x.pop(...), x["k"].update(...): may mutate x (S.run(...) does not
                #                             mutate the module S: counted, it chained every run to the one before)
        self.generic_visit(n)


def _targets(t):
    """Assignment targets, tuples unpacked: `a.x, b.y = ...` patches both (2026-10-15: a tuple restore of a patched
    kernel was missed, and a shard ran with ZTL's certificate check silenced)."""
    if isinstance(t, (ast.Tuple, ast.List)):
        return [x for e in t.elts for x in _targets(e)]
    return [t]


def _calls(stmt):
    return {n.func.id for n in ast.walk(stmt) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}


def plan(src_text):
    mod = ast.parse(src_text)
    body = mod.body
    imported = set()
    for s in body:
        if isinstance(s, (ast.Import, ast.ImportFrom)):
            imported |= {(a.asname or a.name).split(".")[0] for a in s.names}
        elif isinstance(s, ast.Assign) and isinstance(s.value, ast.Call) and getattr(s.value.func, "id", "") == "__import__":
            imported |= {t.id for t in s.targets if isinstance(t, ast.Name)}
    info = []
    for s in body:
        sc = _Scan(frozenset(imported))
        sc.visit(s)
        info.append(sc)
    # functions that check (directly or through another): calling them makes a statement a target
    checking = {"check"}
    funcs = {s.name: s for s in body if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))}
    while True:
        more = {nm for nm, f in funcs.items() if nm not in checking and _calls(f) & checking}
        if not more:
            break
        checking |= more
    targets = [i for i, s in enumerate(body)
               if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)) and _calls(s) & checking]
    first = targets[0]
    patches = []
    for i, s in enumerate(body):
        for node in ast.walk(s):
            # a METHOD of a module's attribute changes the module's state without naming a variable:
            # `_sys.path.insert(0, "bench")`, `CM._CACHE.clear()` (2026-10-15: both were missed — a shard could not
            # import `scale`, another reused a work-mode contract in --dev)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and isinstance(node.func.value, (ast.Attribute, ast.Subscript)) and _base(node.func.value) in imported:
                patches.append(i)
                break
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                ts = [x for t in (node.targets if isinstance(node, ast.Assign) else [node.target]) for x in _targets(t)]
                if any(isinstance(t, (ast.Attribute, ast.Subscript)) and _base(t) in imported for t in ts):
                    patches.append(i)
                    break
    binders = {}
    for i, sc in enumerate(info):
        for nm in sc.binds:
            binders.setdefault(nm, []).append(i)

    def last_before(nm, i):
        best = None
        for j in binders.get(nm, ()):
            if j < i:
                best = j
            else:
                break
        return best

    def closure(seed):
        need = set(range(first)) | set(seed)
        todo = [(i, i) for i in need]
        seen = set()
        while todo:
            i, at = todo.pop()
            if (i, at) in seen:
                continue
            seen.add((i, at))
            names = info[i].reads
            for nm in names:
                j = last_before(nm, at if isinstance(body[i], (ast.FunctionDef, ast.AsyncFunctionDef)) else i)
                if j is None:
                    continue
                if j not in need:
                    need.add(j)
                todo.append((j, j))
                if isinstance(body[j], (ast.FunctionDef, ast.AsyncFunctionDef)):
                    todo.append((j, at if isinstance(body[i], (ast.FunctionDef, ast.AsyncFunctionDef)) else i))
        return need

    return body, targets, patches, closure


def build(jobs, times=None):
    text = SRC.read_text(encoding="utf-8")
    body, targets, patches, closure = plan(text)
    # deal the targets: contiguous runs balanced by an estimate (measured check times when given, else equal)
    cost = [1.0] * len(targets)
    if times:
        for t_i, i in enumerate(targets):
            seg = ast.get_source_segment(text, body[i]) or ""
            cost[t_i] = 1.0 + sum(v for nm, v in times.items() if nm and nm in seg)
    # CONTIGUOUS runs of targets (a shard then needs only what precedes its run), cut at equal cost
    total = sum(cost)
    shards, acc, k = [[] for _ in range(jobs)], 0.0, 0
    for t_i, i in enumerate(targets):
        if acc >= total * (k + 1) / jobs and k < jobs - 1:
            k += 1
        shards[k].append(i)
        acc += cost[t_i]
    files = []
    for k, mine in enumerate(shards):
        if not mine:
            continue
        need = closure(mine)
        top = max(need)
        need |= {p for p in patches if p < top}
        need = closure(need)
        mine_set = set(mine)
        out, emitting, wrapped = [], None, False
        prelude_end = min(targets)
        for i in sorted(need):
            if i >= prelude_end and not wrapped:
                wrapped = True
                out.append("_check_real = check\n_EMIT = [False]\n\n\ndef check(name, cond, why=''):\n"
                           "    if _EMIT[0]:\n        _check_real(name, cond, why)\n")
            want = i in mine_set
            if i >= prelude_end and want != emitting:
                out.append(f"_EMIT[0] = {want}")
                emitting = want
            out.append(ast.get_source_segment(text, body[i], padded=True).lstrip()
                       if body[i].col_offset == 0 else ast.unparse(body[i]))
        out.append("print(f'SHARD {ok} ok, {fail} failed')")
        f = HERE / f"_shard_{k:02d}.py"
        f.write_text("\n".join(out) + "\n", encoding="utf-8")
        files.append((f, len(mine), len(need)))
    return files, len(targets)


def main(argv):
    jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 16
    compare = argv[argv.index("--compare") + 1] if "--compare" in argv else None
    times = None
    tf = HERE / ".check_times.tsv"
    if tf.exists():
        times = {}
        for line in tf.read_text(encoding="utf-8").splitlines():
            sec, _, nm = line.partition("\t")
            times[nm[:60]] = times.get(nm[:60], 0) + float(sec)
    t0 = time.time()
    files, n_targets = build(jobs, times)
    root = HERE.parent
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1")
    procs = [(f, subprocess.Popen([sys.executable, "-m", f"tests.{f.stem}"], cwd=root, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)) for f, _, _ in files]
    lines, bad, took = [], [], []
    limit = int(argv[argv.index("--shard-timeout") + 1]) if "--shard-timeout" in argv else 1800
    for f, p in procs:
        try:
            out, _ = p.communicate(timeout=max(1, limit - (time.time() - t0)))
        except subprocess.TimeoutExpired:
            p.kill()
            out, _ = p.communicate()
            out += f"\nKILLED after {limit} s"
        took.append((f.stem, time.time() - t0))
        got = [l for l in out.splitlines() if l.startswith("  OK   ") or l.startswith("  FAIL ")]
        lines += got
        if p.returncode != 0 or not any(l.startswith("SHARD ") for l in out.splitlines()):
            bad.append((f.name, p.returncode, out[-1500:]))
    for f, _, _ in files:
        f.unlink()
    ok = sum(1 for l in lines if l.startswith("  OK"))
    fail = len(lines) - ok
    for l in lines:
        if l.startswith("  FAIL"):
            print(l)
    for name, rc, tail in bad:
        print(f"SHARD {name} exited {rc}:\n{tail}")
    print("shards done at (s): " + ", ".join(f"{n[-2:]}:{t:.0f}" for n, t in took))
    print(f"ztl-stand (parallel, {len(files)} shards over {n_targets} checking statements, "
          f"{time.time() - t0:.0f} s): {ok} ok, {fail} failed")
    green = fail == 0 and not bad
    if compare:
        seq = [l for l in pathlib.Path(compare).read_text(encoding="utf-8").splitlines()
               if l.startswith("  OK   ") or l.startswith("  FAIL ")]
        norm = lambda ls: Counter(re.sub(r"\s+", " ", l)[:160] for l in ls)
        a, b = norm(lines), norm(seq)
        if a != b:
            green = False
            print("COMPARE: the parallel cut DIFFERS from the sequential run:")
            for l in (b - a):
                print("  only sequential:", l)
            for l in (a - b):
                print("  only parallel:  ", l)
        else:
            print(f"COMPARE: the same {sum(a.values())} check lines as the sequential run")
    print("USTAND GREEN" if green else "USTAND RED")
    return 0 if green else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
