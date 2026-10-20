"""INDEPENDENT REFERENCE for the SPICE duel: exhaustive enumeration of the tolerance box's vertices — its own tiny
nodal-analysis builder (R, V, I, E, and Q in the active region), floats over every vertex, then the extreme vertices
re-solved EXACTLY in fractions. Shares no code with the stand (ustand/*). Valid where the extremes sit at vertices
(a linear circuit whose every element enters by one layer — the classical result for resistive networks with
controlled sources; the vertex enumeration then IS the answer). Feasible up to ~2^22 vertices.

    python3 reference.py T01 "V(2)"
"""
import itertools, re, sys, csv, time
from fractions import Fraction as F
import numpy as np

SUF = {"f": F(1, 10**15), "p": F(1, 10**12), "n": F(1, 10**9), "u": F(1, 10**6), "m": F(1, 1000), "k": F(1000),
       "meg": F(10**6), "g": F(10**9)}


def num(t):
    m = re.match(r"^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)(meg|[fpnumkg])?", t, re.I)
    v = F(m.group(1))
    return v * SUF[m.group(2).lower()] if m.group(2) else v


def read(task):
    lines = [l.split(";")[0].strip() for l in open(f"tasks/{task}/circuit.cir")][1:]
    els, models = [], {}
    for l in lines:
        if not l or l.startswith("*") or l.lower().startswith(".end"):
            continue
        t = l.split()
        if t[0].lower() == ".model":
            mp = dict((k.lower(), num(v)) for k, v in re.findall(r"(\w+)\s*=\s*([^\s)]+)", l))
            models[t[1].lower()] = (t[2].split("(")[0].upper(), mp)
            continue
        els.append(t)
    tol = {}
    try:
        for row in csv.DictReader(open(f"tasks/{task}/bom.csv")):
            ref = row.get("Reference") or row.get("Designator") or row.get("Ref")
            tol[ref.lower()] = F(row["Tolerance"].strip().rstrip("%")) / 100
    except FileNotFoundError:
        pass
    return els, models, tol


def build(els, models, vals):
    """-> (A, b, index) floats/fractions by the values given; unknowns: node voltages + branch currents."""
    nodes = sorted({n for e in els for n in (e[1:3] if e[0][0].lower() not in "eq" else (e[1:5] if e[0][0].lower() == "e" else e[1:4])) if n != "0"})
    idx = {n: i for i, n in enumerate(nodes)}
    extra = [e[0].lower() for e in els if e[0][0].lower() in "ve"] + [e[0].lower() + "_ib" for e in els if e[0][0].lower() == "q"]
    for k in extra:
        idx["I:" + k] = len(idx)
    n = len(idx)
    A = [[0] * n for _ in range(n)]
    b = [0] * n
    def stamp_g(a, c, g):
        for x, y, s in ((a, a, 1), (c, c, 1), (a, c, -1), (c, a, -1)):
            if x != "0" and y != "0":
                A[idx[x]][idx[y]] += s * g
    for e in els:
        k, nm = e[0][0].lower(), e[0].lower()
        if k == "r":
            stamp_g(e[1], e[2], 1 / vals[nm])
        elif k == "v":
            j = idx["I:" + nm]
            for nd, s in ((e[1], 1), (e[2], -1)):
                if nd != "0":
                    A[idx[nd]][j] += s
                    A[j][idx[nd]] += s
            b[j] += vals[nm]
        elif k == "i":                          # from n+ through the source to n-: it leaves n+, enters n-
            for nd, s in ((e[1], -1), (e[2], 1)):
                if nd != "0":
                    b[idx[nd]] += s * vals[nm]
        elif k == "e":
            j = idx["I:" + nm]
            g = vals[nm]
            for nd, s in ((e[1], 1), (e[2], -1)):
                if nd != "0":
                    A[idx[nd]][j] += s
                    A[j][idx[nd]] += s
            for nd, s in ((e[3], -g), (e[4], g)):
                if nd != "0":
                    A[j][idx[nd]] += s
        elif k == "q":                          # NPN, active: V(b) - V(e) = Vbe; Ic = BF Ib
            c, bn, em = e[1:4]
            j = idx["I:" + nm + "_ib"]
            bf, vbe = vals[nm + ".bf"], vals[nm + ".vbe"]
            for nd, s in ((bn, 1), (em, -1)):
                if nd != "0":
                    A[j][idx[nd]] += s
            b[j] += vbe
            for nd, s in ((bn, 1), (c, bf), (em, -(1 + bf))):
                if nd != "0":
                    A[idx[nd]][j] += s
    return A, b, idx


def main(task, what):
    els, models, tol = read(task)
    nominal = {}
    for e in els:
        k, nm = e[0][0].lower(), e[0].lower()
        if k == "r":
            nominal[nm] = num(e[3])
        elif k in "vi":
            nominal[nm] = num([x for x in e[3:] if x.lower() != "dc"][0])
        elif k == "e":
            nominal[nm] = num(e[5])
        elif k == "q":
            mt, mp = models[e[4].lower()]
            nominal[nm + ".bf"], nominal[nm + ".vbe"] = mp["bf"], mp["vbe"]
            tol.setdefault(nm + ".bf", tol.pop(nm, F(0)))
            if "vbetol" in mp:
                tol[nm + ".vbe"] = F(5, 100) if mp["vbetol"] else 0
    for e in els:                                       # VbeTol=5% in the model card
        if e[0][0].lower() == "q":
            ln = [l for l in open(f"tasks/{task}/circuit.cir") if l.lower().startswith(".model")][0]
            m_ = re.search(r"vbetol\s*=\s*([\d.]+)%", ln, re.I)
            if m_:
                tol[e[0].lower() + ".vbe"] = F(m_.group(1)) / 100
    names = [k for k in nominal if tol.get(k, 0)]
    A0, b0, idx = build(els, models, nominal)
    m = re.match(r"^V\((\w+)(?:,(\w+))?\)$", what)
    a_, c_ = m.group(1), m.group(2)
    def out(sol):
        va = sol[idx[a_]] if a_ != "0" else 0
        vc = (sol[idx[c_]] if c_ != "0" else 0) if c_ else 0
        return va - vc
    nv = len(names)
    print(f"{task}: {nv} toleranced quantities, {2**nv} vertices", flush=True)
    t0 = time.time()
    best = {"min": (None, None), "max": (None, None)}
    for chunk in itertools.islice(itertools.count(), 0, None):
        lo, hi = chunk * 4096, min((chunk + 1) * 4096, 2 ** nv)
        if lo >= 2 ** nv:
            break
        for code in range(lo, hi):
            v = dict(nominal)
            for i, nm in enumerate(names):
                v[nm] = nominal[nm] * (1 + tol[nm] if (code >> i) & 1 else 1 - tol[nm])
            A, b, _ = build(els, models, {k: float(x) for k, x in v.items()})
            o = out(np.linalg.solve(np.array(A, float), np.array(b, float)))
            if best["min"][0] is None or o < best["min"][0]:
                best["min"] = (o, code)
            if best["max"][0] is None or o > best["max"][0]:
                best["max"] = (o, code)
    res = {}
    for side in ("min", "max"):
        code = best[side][1]
        v = dict(nominal)
        for i, nm in enumerate(names):
            v[nm] = nominal[nm] * (1 + tol[nm] if (code >> i) & 1 else 1 - tol[nm])
        A, b, _ = build(els, models, v)
        M = [row[:] + [b[i]] for i, row in enumerate(A)]
        nn = len(M)
        for col in range(nn):
            p = next(r for r in range(col, nn) if M[r][col] != 0)
            M[col], M[p] = M[p], M[col]
            for r in range(nn):
                if r != col and M[r][col] != 0:
                    f = F(M[r][col]) / M[col][col]
                    M[r] = [x - f * y for x, y in zip(M[r], M[col])]
        sol = [F(M[i][nn]) / M[i][i] for i in range(nn)]
        res[side] = out(sol)
        res[side + "_vertex"] = {nm: ("+" if (code >> i) & 1 else "-") for i, nm in enumerate(names)}
    An, bn, _ = build(els, models, {k: float(x) for k, x in nominal.items()})
    nomv = out(np.linalg.solve(np.array(An, float), np.array(bn, float)))
    print(f"  nominal {nomv:.9g}  min {float(res['min']):.9g}  max {float(res['max']):.9g}  (exact at the vertices)  "
          f"{time.time() - t0:.1f} s")
    print(f"  min = {res['min']}\n  max = {res['max']}")
    return res


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
