"""Round 2: frame3d on WHOLE space frames WITH END RELEASES (after dc0367f) against redteam/round2/ref3d_rel.py:
second-order displacements (every free node X/Y/Z), member |sigma| from both sides, the stability bracket.
Frames: round 1's generator (redteam/hunt3d.gen) plus random RELEASEs — beams pinned at one or both ends (MZ, MY or
both), braces pinned, some column tops pinned about one axis. Tolerance 0 or 0.5 % with box vertices.
--mutant NAME: frame3d._MUTANT[NAME] (no_geo_moment) — the check must see it; --mutant drop_release: the RELEASE lines
are removed from the deck the STAND sees (the round-1 bug in effect) — the check must see that too.
    PYTHONPATH=. python3 redteam/round2/hunt3d_rel.py SEED0 COUNT [--mutant NAME]"""
import json, os, random, sys, time
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ref3d_rel as RR  # noqa: E402
from hunt3d import gen as gen1  # noqa: E402
from ustand import frame3d as F3  # noqa: E402


def fnum(s):
    return float(F(str(s).split()[0]))


def gen(seed):
    deck, m, free_nodes = gen1(seed)
    rng = random.Random(seed * 31 + 7)
    lines = deck.splitlines()
    elems = [tuple(int(x) for x in ln.split(",")[1:3]) for ln in lines if ln.startswith("E, ")]
    nodes = {int(ln.split(",")[1]): tuple(float(F(x)) for x in ln.split(",")[2:5]) for ln in lines if ln.startswith("N, ")}
    rel = []
    for k, (a, b) in enumerate(elems, 1):
        horizontal = abs(nodes[a][2] - nodes[b][2]) < 1e-12
        if horizontal and rng.random() < 0.6:                  # beams: pinned connections
            for end in rng.choice([["I"], ["J"], ["I", "J"]]):
                rel.append(f"RELEASE, {k}, {end}, {rng.choice(['MZ', 'MY', 'MZ, MY'])}")
        elif not horizontal and rng.random() < 0.15:            # a column end pinned about one axis
            rel.append(f"RELEASE, {k}, {rng.choice(['I', 'J'])}, {rng.choice(['MZ', 'MY'])}")
    return deck + "\n".join(rel) + "\n", m, free_nodes, len(rel)


def check(seed, mutant=None):
    deck, m, free_nodes, nrel = gen(seed)
    tol = "0" if seed % 2 == 0 else "0.5%"
    t = 0.0 if tol == "0" else 0.005
    F3._MUTANT.clear()
    seen = deck
    if mutant == "drop_release":
        seen = "\n".join(ln for ln in deck.splitlines() if not ln.startswith("RELEASE")) + "\n"
    elif mutant:
        F3._MUTANT[mutant] = True
    targets = [f"U({n},{d})" for n in free_nodes for d in ("X", "Y", "Z")]
    out = {"seed": seed, "tol": tol, "members": m, "releases": nrel}
    t0 = time.time()
    try:
        sd = F3.second_order_disp(seen, tol, targets)
        ss = F3.second_order_stress(seen, tol, 10 ** 12)
        sl = F3.stability_lower(seen, tol)
        su = F3.stability_upper(seen)
    except Exception as e:                                   # noqa: BLE001
        F3._MUTANT.clear()
        return dict(out, status="error", why=repr(e)[:160])
    F3._MUTANT.clear()
    out["t_stand"] = round(time.time() - t0, 1)
    if not isinstance(ss, dict) or "members" not in ss:
        return dict(out, status="open", why=str(ss.get("why") if isinstance(ss, dict) else ss)[:160])
    try:
        rng = random.Random(seed)
        verts = [[1.0] * m] + ([[1 - t] * m, [1 + t] * m] + [[1 + t * rng.choice([-1, 1]) for _ in range(m)]
                                                             for _ in range(2)] if t else [])
        refs = [RR.solve(deck, v, ns=12) for v in verts]
        ref24 = RR.solve(deck, verts[0], ns=24)
    except Exception as e:                                   # noqa: BLE001  (a mechanism: the reference is singular)
        return dict(out, status="ref_error", why=repr(e)[:160])
    viol, n = [], 0
    rows = {r["element"]: r for r in ss["members"]}
    for k in range(1, m + 1):
        lo, hi = (fnum(x) for x in rows[k]["sigma_abs"])
        err = abs(refs[0][0][k - 1] - ref24[0][k - 1]) * 20 + 1e-7 * ref24[0][k - 1]
        for vi, (sig, disp) in enumerate(refs):
            n += 1
            if sig[k - 1] > hi + err:
                viol.append({"member": k, "what": "sigma above the proved max", "vertex": vi, "hi": hi, "ref": sig[k - 1]})
        n += 1
        if ref24[0][k - 1] < lo - err:
            viol.append({"member": k, "what": "sigma below the proved lower bound of the max", "lo": lo,
                         "ref": ref24[0][k - 1]})
    dd = sd["BASE"] if "BASE" in sd else next(iter(sd.values()))
    for tg in targets:
        r = dd.get(tg)
        if not isinstance(r, list):
            continue
        lo, hi = fnum(r[0]), fnum(r[1])
        nd, d = int(tg[2:-1].split(",")[0]), "XYZ".index(tg[-2])
        e2 = abs(refs[0][1][nd][d] - ref24[1][nd][d]) * 20 + 1e-7 * (abs(ref24[1][nd][d]) + 1e-9)
        for vi, (sig, disp) in enumerate(refs):
            n += 1
            v = disp[nd][d]
            if not (lo - e2 <= v <= hi + e2):
                viol.append({"target": tg, "vertex": vi, "proved": [lo, hi], "ref": v})
    lam_c = RR.buckling(deck, None, ns=8)
    lam_f = RR.buckling(deck, None, ns=16)
    lam_lo_v = RR.buckling(deck, verts[1], ns=16) if t else lam_f
    le = abs(lam_c - lam_f) * 10 + 1e-9 if lam_f else 0
    if sl.get("lam_low") is not None and lam_f:
        n += 1
        if float(sl["lam_low"]) > min(lam_f, lam_lo_v) + le:
            viol.append({"what": "lam_low above the reference", "lam_low": float(sl["lam_low"]), "ref": min(lam_f, lam_lo_v)})
    if su.get("lam_high") is not None and lam_f:
        n += 1
        if float(su["lam_high"]) < lam_f - le:
            viol.append({"what": "lam_high below the reference", "lam_high": float(su["lam_high"]), "ref": lam_f})
    return dict(out, status="checked", checks=n, violations=len(viol), first=viol[:3],
                lam=[float(sl["lam_low"]) if sl.get("lam_low") else None, lam_f])


if __name__ == "__main__":
    s0, cnt = int(sys.argv[1]), int(sys.argv[2])
    mut = sys.argv[sys.argv.index("--mutant") + 1] if "--mutant" in sys.argv else None
    for s in range(s0, s0 + cnt):
        try:
            print(json.dumps(check(s, mut)), flush=True)
        except Exception as e:                               # noqa: BLE001
            print(json.dumps({"seed": s, "status": "harness_error", "why": repr(e)[:300]}), flush=True)
