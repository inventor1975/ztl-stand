"""Red team, 2D: the stand's second-order member bounds (frame.second_order_case) against redteam/ref2d.py.

    PYTHONPATH=. python3 redteam/hunt2d.py SEED0 COUNT [--mutant NAME] [--family F]

For every deck: every element is checked (limit 1e12, so only the proved bounds matter): |sigma| from above
(sigma_abs_max >= the reference's max over the element) and both end moments (the proved interval holds the reference),
at the nominal moduli and at random VERTICES of the box (each member's modulus at E(1 +- t) independently).
A violation is counted when the reference lies outside by more than REL of the member's moment / stress scale, REL
well above the reference's own error (measured by ns = 64 vs 128 on the same deck: the larger of 1e-7 and 20 x that
difference). --mutant sets one of ustand.frame._MUTANT's test-only switches: the test must then SEE violations.
"""
import json
import os
import random
import sys
import time
from fractions import Fraction as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import ref2d  # noqa: E402
from ustand import frame as FRM  # noqa: E402

E0, A0, I0, H0 = 210e9, 0.01, 8e-5, 0.2


def fnum(s):
    return float(F(str(s).split()[0]))


def deck_of(nodes, elems, sups, loads, qloads, sec=(A0, I0, H0)):
    lines = ["ET, 1, BEAM3", f"MP, EX, 1, {E0:.0f}", f"R, 1, {sec[0]}, {sec[1]}, {sec[2]}"]
    lines += [f"N, {n}, {x}, {y}" for n, (x, y) in sorted(nodes.items())]
    lines += [f"E, {i}, {j}" for i, j in elems]
    lines += [f"D, {n}, {d}, 0" for n, d in sups]
    lines += [f"F, {n}, {d}, {v}" for n, d, v in loads]
    lines += [f"QLOAD, {k}, {d}, {q}" for k, d, q in qloads]
    return "\n".join(lines)


def gen(seed, family=None):
    """Random frames with AXIAL member loads (the newest code path), several families."""
    rng = random.Random(seed)
    fam = family or rng.choice(["portal", "portal", "pitched", "hanger", "column", "braced"])
    nodes, elems, sups, loads, qloads = {}, [], [], [], []
    flip = lambda i, j: (j, i) if rng.random() < 0.5 else (i, j)          # element orientation at random
    nid = [0]

    def node(x, y):
        nid[0] += 1
        nodes[nid[0]] = (x, y)
        return nid[0]

    def member(i, j, ne):
        """ne elements between nodes i and j; returns the element ids"""
        xi, yi = nodes[i]; xj, yj = nodes[j]
        ids = [i] + [node(xi + (xj - xi) * F(s, ne), yi + (yj - yi) * F(s, ne)) for s in range(1, ne)] + [j]
        out = []
        for a, b in zip(ids[:-1], ids[1:]):
            elems.append(flip(a, b))
            out.append(len(elems))
        return out
    ne = rng.choice([1, 1, 2])
    if fam == "portal" or fam == "pitched":
        bays, st = rng.choice([1, 1, 2]), rng.choice([1, 1, 2])
        H, Wd = rng.choice([3, 4, 5]), (rng.choice([6, 8]) if fam == "pitched" else rng.choice([4, 5, 6, 8]))
        grid = {(b, s): node(F(b * Wd), F(s * H)) for b in range(bays + 1) for s in range(st + 1)}
        base_fix = rng.random() < 0.6
        for b in range(bays + 1):
            sups += [(grid[(b, 0)], "UX"), (grid[(b, 0)], "UY")] + ([(grid[(b, 0)], "ROTZ")] if base_fix else [])
        cols, beams = [], []
        for s in range(st):
            for b in range(bays + 1):
                cols += member(grid[(b, s)], grid[(b, s + 1)], ne)
        for s in range(1, st + 1):
            for b in range(bays):
                if fam == "pitched" and s == st:
                    apex = node(F(b * Wd) + F(Wd, 2), F(s * H) + F({6: 4, 8: 3}[Wd]))      # rafters 5 m: rational
                    beams += member(grid[(b, s)], apex, ne) + member(apex, grid[(b + 1, s)], ne)
                else:
                    beams += member(grid[(b, s)], grid[(b + 1, s)], ne)
        for k in cols:
            qloads.append((k, "FY", -rng.randint(1, 300) * 1000))                 # self-weight-like, large
        for k in beams:
            if rng.random() < 0.8:
                qloads.append((k, "FY", -rng.randint(1, 60) * 1000))             # oblique on rafters
            if rng.random() < 0.3:
                qloads.append((k, "FX", rng.choice([-1, 1]) * rng.randint(1, 80) * 1000))   # axial on beams
        top = [grid[(b, st)] for b in range(bays + 1)]
        loads.append((top[0], "FX", rng.randint(1, 80) * 1000))
        for t in top:
            if rng.random() < 0.7:
                loads.append((t, "FY", -rng.randint(0, 900) * 1000))
    elif fam == "hanger":
        # a member hanging from a support (tension from its own weight) carrying a load, with a lateral pull
        Lh = rng.choice([3, 4, 6])
        a, b = node(F(0), F(Lh)), node(F(0), F(0))
        sups += [(a, "UX"), (a, "UY")] + ([(a, "ROTZ")] if rng.random() < 0.5 else [])
        ks = member(a, b, rng.choice([1, 2, 3]))
        sups += [(b, "UX")] if rng.random() < 0.5 else []
        for k in ks:
            qloads.append((k, "FY", -rng.randint(1, 400) * 1000))
            if rng.random() < 0.5:
                qloads.append((k, "FX", rng.choice([-1, 1]) * rng.randint(1, 30) * 1000))
        loads.append((b, "FY", rng.choice([-1, 1]) * rng.randint(0, 900) * 1000))   # down: tension; up: mixed sign
        if not any(s[0] == b for s in sups):
            loads.append((b, "FX", rng.randint(1, 30) * 1000))
        loads.append((b, "MZ", rng.choice([-1, 1]) * rng.randint(0, 40) * 1000))
    elif fam == "column":
        th, Lc = rng.choice([(0, 2), (0, 3), (0, 4), (0, 6), (3, 4), (4, 3), (6, 8), (5, 12)])   # inclined too
        a, b = node(F(0), F(0)), node(F(th), F(Lc))
        cant = rng.random() < 0.5
        sups += [(a, "UX"), (a, "UY")] + ([(a, "ROTZ")] if cant else [(b, "UX")])
        ks = member(a, b, rng.choice([1, 2, 3]))
        for k in ks:
            qloads.append((k, "FY", rng.choice([-1, -1, 1]) * rng.randint(5, 400) * 1000))
            if rng.random() < 0.5:
                qloads.append((k, "FX", rng.choice([-1, 1]) * rng.randint(1, 40) * 1000))
        loads.append((b, "FY", rng.choice([-1, 1]) * rng.randint(0, 900) * 1000))
        if cant:
            loads.append((b, "FX", rng.randint(1, 40) * 1000))
        loads.append((a, "MZ", rng.choice([-1, 1]) * rng.randint(0, 60) * 1000))
        loads.append((b, "MZ", rng.choice([-1, 1]) * rng.randint(0, 60) * 1000))
    else:   # braced: a portal with a diagonal brace carrying its own weight (oblique QLOAD FY)
        H, Wd = rng.choice([(3, 4), (4, 3), (6, 8)])
        p0, p1, p2, p3 = node(F(0), F(0)), node(F(Wd), F(0)), node(F(Wd), F(H)), node(F(0), F(H))
        for p in (p0, p1):
            sups += [(p, "UX"), (p, "UY")]
        ks = member(p0, p3, ne) + member(p1, p2, ne) + member(p3, p2, ne)
        br = member(p0, p2, ne)
        for k in ks + br:
            qloads.append((k, "FY", -rng.randint(1, 200) * 1000))
        loads.append((p3, "FX", rng.randint(1, 200) * 1000))
        loads.append((p2, "FY", -rng.randint(0, 900) * 1000))
    return fam, deck_of(nodes, elems, sups, loads, qloads)


def check(seed, tol="0", mutant=None, family=None, nvert=4):
    fam, deck = gen(seed, family)
    t = float(F(tol.rstrip("%")) / 100) if tol.endswith("%") else float(F(tol))
    m = deck.count("\nE, ")
    FRM._MUTANT.clear()
    if mutant:
        FRM._MUTANT[mutant] = True
    t0 = time.time()
    try:
        r = FRM.second_order_case(deck, tol, [(k, F(10) ** 12) for k in range(1, m + 1)])
    except Exception as e:                                   # noqa: BLE001 — a refusal is not a finding
        return {"seed": seed, "fam": fam, "status": "error", "why": repr(e)[:200]}
    finally:
        FRM._MUTANT.clear()
    if not r.get("checks"):
        return {"seed": seed, "fam": fam, "status": "open", "why": (r.get("why") or "")[:160]}
    dt = time.time() - t0
    rng = random.Random(seed * 7 + 1)
    verts = [[1.0] * m]
    if t:
        verts += [[1 - t] * m, [1 + t] * m] + [[1 + t * rng.choice([-1, 1]) for _ in range(m)] for _ in range(nvert)]
    ref64 = [ref2d.solve(deck, v, ns=64)[0] for v in verts]
    ref128 = ref2d.solve(deck, verts[0], ns=128)[0]
    viol, n, worst = [], 0, None
    for k, c in enumerate(r["checks"]):
        sig_hi = fnum(c["sigma_abs_max"])
        mends = {e: (fnum(c["M_ends"][e][0]), fnum(c["M_ends"][e][1])) for e in ("I", "J")}
        # the reference's own error on this element (ns 64 vs 128 at the nominal point)
        err_s = abs(ref64[0][k]["sig"].max() - ref128[k]["sig"].max())
        err_m = max(abs(ref64[0][k]["M_I"] - ref128[k]["M_I"]), abs(ref64[0][k]["M_J"] - ref128[k]["M_J"]))
        scale_m = max(abs(ref128[k]["M"]).max(), 1.0)
        for vi, rr in enumerate(ref64):
            e = rr[k]
            n += 3
            smax = e["sig"].max()
            slack_s = max(1e-7 * smax, 20 * err_s)
            if smax > sig_hi + slack_s:
                viol.append({"elem": k + 1, "what": "sigma", "vertex": vi, "proved_hi": sig_hi, "ref": smax,
                             "excess_rel": smax / sig_hi - 1, "ref_err": err_s})
            for end, val in (("I", e["M_I"]), ("J", e["M_J"])):
                lo, hi = mends[end]
                slack = max(1e-7 * scale_m, 20 * err_m)
                if not (lo - slack <= val <= hi + slack):
                    viol.append({"elem": k + 1, "what": f"M_{end}", "vertex": vi, "proved": [lo, hi], "ref": val,
                                 "outside_by": min(abs(val - lo), abs(val - hi)), "ref_err": err_m})
            ratio = smax / sig_hi if sig_hi else 0
            worst = max(worst or 0, ratio)
    return {"seed": seed, "fam": fam, "tol": tol, "status": "checked", "elements": m, "vertices": len(verts),
            "checks": n, "violations": len(viol), "first": viol[:3], "max_ref_over_bound": worst,
            "verdict": r.get("verdict"), "t_stand": round(dt, 2)}


if __name__ == "__main__":
    s0, cnt = int(sys.argv[1]), int(sys.argv[2])
    mut = sys.argv[sys.argv.index("--mutant") + 1] if "--mutant" in sys.argv else None
    fam = sys.argv[sys.argv.index("--family") + 1] if "--family" in sys.argv else None
    tol = sys.argv[sys.argv.index("--tol") + 1] if "--tol" in sys.argv else None
    for s in range(s0, s0 + cnt):
        tl = tol or ("0" if s % 2 == 0 else "0.5%")
        try:
            o = check(s, tl, mut, fam)
        except Exception as e:                               # noqa: BLE001
            o = {"seed": s, "status": "harness_error", "why": repr(e)[:300]}
        print(json.dumps(o), flush=True)
