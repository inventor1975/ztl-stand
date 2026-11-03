"""Red team, 3D: frame3d's second-order displacements and member stresses (both sides) and its stability bracket
against redteam/ref3d.py on random space frames with AXIAL member loads (columns' self-weight), transverse member
loads on beams, braces, both THETAs, random element orientation, tolerance 0 or 0.5 %.
    PYTHONPATH=. python3 redteam/hunt3d.py SEED0 COUNT [--mutant NAME]
--mutant: one of frame3d._MUTANT's test-only switches (axial_const_moment, no_geo_moment) — the check must see it."""
import json, os, random, sys, time
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import ref3d  # noqa: E402
from ustand import frame3d as F3  # noqa: E402


def fnum(s):
    return float(F(str(s).split()[0]))


def gen(seed):
    rng = random.Random(seed)
    nodes, elems, sups, loads, qloads = {}, [], [], [], []
    nid = [0]

    def node(x, y, z):
        nid[0] += 1
        nodes[nid[0]] = (x, y, z)
        return nid[0]

    def member(a, b):
        elems.append((a, b) if rng.random() < 0.5 else (b, a))
        return len(elems)
    bx, by = rng.choice([(1, 1), (2, 1), (1, 2)])
    st = rng.choice([1, 1, 2])
    H = rng.choice([3, 4])
    Wx, Wy = rng.choice([4, 5, 6]), rng.choice([3, 4, 5])
    g = {(i, j, s): node(i * Wx, j * Wy, s * H) for i in range(bx + 1) for j in range(by + 1) for s in range(st + 1)}
    fixed = rng.random() < 0.6
    for i in range(bx + 1):
        for j in range(by + 1):
            for d in (("ALL",) if fixed else ("UX", "UY", "UZ", "ROTZ")):
                sups.append((g[(i, j, 0)], d))
    cols, beams = [], []
    nec = rng.choice([1, 2, 2])                                       # elements per column
    for s in range(st):
        for i in range(bx + 1):
            for j in range(by + 1):
                a, b = g[(i, j, s)], g[(i, j, s + 1)]
                if nec == 2:
                    mid = node(i * Wx, j * Wy, F(2 * s + 1, 2) * H)
                    cols += [member(a, mid), member(mid, b)]
                else:
                    cols.append(member(a, b))
    for s in range(1, st + 1):
        for i in range(bx + 1):
            for j in range(by + 1):
                if i < bx:
                    beams.append(member(g[(i, j, s)], g[(i + 1, j, s)]))
                if j < by:
                    beams.append(member(g[(i, j, s)], g[(i, j + 1, s)]))
    if rng.random() < 0.5 and Wx == 4 and H == 3:                     # a brace in the XZ plane: (4, 0, 3), L = 5
        beams.append(member(g[(0, 0, 0)], g[(1, 0, 1)]))
    for k in cols:
        qloads.append((k, "FZ", -rng.randint(1, 120) * 1000))
    for k in beams:
        if rng.random() < 0.7:
            qloads.append((k, "FZ", -rng.randint(1, 40) * 1000))
        if rng.random() < 0.2:
            qloads.append((k, rng.choice(["FX", "FY"]), rng.choice([-1, 1]) * rng.randint(1, 30) * 1000))
    tops = [g[(i, j, st)] for i in range(bx + 1) for j in range(by + 1)]
    loads.append((tops[0], "FX", rng.randint(1, 60) * 1000))
    loads.append((tops[-1], "FY", rng.randint(1, 60) * 1000))
    for t in tops:
        if rng.random() < 0.6:
            loads.append((t, "FZ", -rng.randint(0, 600) * 1000))
    theta = rng.choice([0, 90])
    Iz, Iy = rng.choice([(8e-5, 3e-5), (2e-4, 1e-5), (5e-5, 5e-5)])
    lines = ["ET, 1, BEAM4", "MP, EX, 1, 210e9", "MP, PRXY, 1, 0.3",
             f"R, 1, 0.01, {Iz}, {Iy}, 0.2, 0.3, {theta}, 0, 5e-5"]
    lines += [f"N, {n}, {x}, {y}, {z}" for n, (x, y, z) in sorted(nodes.items())]
    lines += [f"E, {a}, {b}" for a, b in elems]
    lines += [f"D, {n}, {d}, 0" for n, d in sups]
    lines += [f"F, {n}, {d}, {v}" for n, d, v in loads]
    lines += [f"QLOAD, {k}, {d}, {q}" for k, d, q in qloads]
    free_nodes = [n for n in nodes if not any(s[0] == n for s in sups)]
    return "\n".join(lines) + "\n", len(elems), free_nodes


def check(seed, mutant=None, nvert=3):
    deck, m, free_nodes = gen(seed)
    tol = "0" if seed % 2 == 0 else "0.5%"
    t = 0.0 if tol == "0" else 0.005
    F3._MUTANT.clear()
    if mutant:
        F3._MUTANT[mutant] = True
    targets = [f"U({n},{d})" for n in free_nodes for d in ("X", "Y", "Z")]
    out = {"seed": seed, "tol": tol, "members": m}
    t0 = time.time()
    try:
        sd = F3.second_order_disp(deck, tol, targets)
        ss = F3.second_order_stress(deck, tol, 10 ** 12)
        sl = F3.stability_lower(deck, tol)
        su = F3.stability_upper(deck)
    except Exception as e:                                   # noqa: BLE001
        F3._MUTANT.clear()
        return dict(out, status="error", why=repr(e)[:160])
    F3._MUTANT.clear()
    out["t_stand"] = round(time.time() - t0, 1)
    if not isinstance(ss, dict) or "members" not in ss:
        return dict(out, status="open", why=str(ss.get("why") if isinstance(ss, dict) else ss)[:160])
    rng = random.Random(seed)
    verts = [[1.0] * m] + ([[1 - t] * m, [1 + t] * m] + [[1 + t * rng.choice([-1, 1]) for _ in range(m)]
                                                         for _ in range(nvert)] if t else [])
    refs = [ref3d.solve(deck, v, ns=16) for v in verts]
    ref32 = ref3d.solve(deck, verts[0], ns=32)
    viol, n = [], 0
    rows = {r["element"]: r for r in ss["members"]}
    for k in range(1, m + 1):
        lo, hi = (fnum(x) for x in rows[k]["sigma_abs"])
        err = abs(refs[0][0][k - 1] - ref32[0][k - 1]) * 20 + 1e-7 * ref32[0][k - 1]
        for vi, (sig, disp) in enumerate(refs):
            n += 1
            if sig[k - 1] > hi + err:
                viol.append({"member": k, "what": "sigma above the proved max", "vertex": vi, "hi": hi,
                             "ref": sig[k - 1], "excess": sig[k - 1] / hi - 1})
        if ref32[0][k - 1] < lo - err:
            viol.append({"member": k, "what": "sigma below the proved lower bound of the max", "lo": lo,
                         "ref": ref32[0][k - 1]})
    dd = sd["BASE"] if "BASE" in sd else next(iter(sd.values()))
    for tg in targets:
        r = dd.get(tg)
        if not isinstance(r, list):
            continue
        lo, hi = fnum(r[0]), fnum(r[1])
        nd, d = int(tg[2:-1].split(",")[0]), "XYZ".index(tg[-2])
        e32 = abs(refs[0][1][nd][d] - ref32[1][nd][d]) * 20 + 1e-7 * (abs(ref32[1][nd][d]) + 1e-9)
        for vi, (sig, disp) in enumerate(refs):
            n += 1
            v = disp[nd][d]
            if not (lo - e32 <= v <= hi + e32):
                viol.append({"target": tg, "vertex": vi, "proved": [lo, hi], "ref": v})
    lam_ref = [ref3d.buckling(deck, v, ns=12) for v in verts[:3]]
    lam_ref_fine = ref3d.buckling(deck, None, ns=24)
    le = abs(lam_ref[0] - lam_ref_fine) * 10 + 1e-9 if lam_ref[0] else 0
    if sl.get("lam_low") is not None and lam_ref[0]:
        n += 1
        if float(sl["lam_low"]) > min(x for x in lam_ref if x) + le:
            viol.append({"what": "lam_low above the reference", "lam_low": float(sl["lam_low"]), "ref": min(lam_ref)})
    if su.get("lam_high") is not None and lam_ref_fine:
        n += 1
        if float(su["lam_high"]) < lam_ref_fine - le:
            viol.append({"what": "lam_high below the reference", "lam_high": float(su["lam_high"]), "ref": lam_ref_fine})
    return dict(out, status="checked", checks=n, violations=len(viol), first=viol[:3],
                lam=[float(sl["lam_low"]) if sl.get("lam_low") else None, lam_ref_fine])


if __name__ == "__main__":
    s0, cnt = int(sys.argv[1]), int(sys.argv[2])
    mut = sys.argv[sys.argv.index("--mutant") + 1] if "--mutant" in sys.argv else None
    for s in range(s0, s0 + cnt):
        try:
            print(json.dumps(check(s, mut)), flush=True)
        except Exception as e:                               # noqa: BLE001
            print(json.dumps({"seed": s, "status": "harness_error", "why": repr(e)[:300]}), flush=True)
