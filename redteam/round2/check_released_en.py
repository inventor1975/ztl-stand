"""Round 2: EN 6.3.3 (frame3d.judge_interaction) and 6.3.2 (judge_ltb) on frames WITH RELEASES — their member inputs
against redteam/round2/ref3d_rel.py's first-order solve (phi = 0, tolerance 0): judge_interaction's M_a_max (about z',
plane a) and M_b_max (about y') and N_Ed_max must be >= the reference's max |M| / compression along the member;
judge_ltb's M_Ed_max >= the reference's strong-axis max |M|. --mutant: the stand's moments x 0.95.
    PYTHONPATH=. python3 redteam/round2/check_released_en.py SEED0 COUNT [--mutant]"""
import json, os, sys
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref3d_rel as RR  # noqa: E402
from hunt3d_rel import gen  # noqa: E402
from ustand import frame3d as F3  # noqa: E402

MUT = "--mutant" in sys.argv
fnum = lambda s: float(F(str(s).split()[0]))


def one(seed):
    deck, m, free_nodes, nrel = gen(seed)
    if "--keep-beam-qload" in sys.argv:
        # keep the BEAMS' transverse member loads (FZ on horizontal members); drop the columns' axial ones (refused)
        lines = deck.splitlines()
        el = [tuple(int(x) for x in ln.split(",")[1:3]) for ln in lines if ln.startswith("E, ")]
        nz = {int(ln.split(",")[1]): float(F(ln.split(",")[4])) for ln in lines if ln.startswith("N, ")}
        def keep(ln):
            if not ln.startswith("QLOAD"):
                return True
            k, d = int(ln.split(",")[1]), ln.split(",")[2].strip()
            a, b = el[k - 1]
            return d == "FZ" and abs(nz[a] - nz[b]) < 1e-12
        deck = "\n".join(ln for ln in lines if keep(ln)) + "\n"
    else:
        deck = "\n".join(ln for ln in deck.splitlines() if not ln.startswith("QLOAD")) + "\n"   # 6.3.3 v1: no axial QLOAD
    try:
        ji = F3.judge_interaction(deck, "0", 355e6, "b", "c", phi=0)
        jl = F3.judge_ltb(deck, "0", 355e6, "b", phi=0)
        ref = RR.first_order_members(deck, None, 16)
    except Exception as e:                                   # noqa: BLE001
        return {"seed": seed, "status": "error", "why": repr(e)[:150]}
    sc = 0.95 if MUT else 1.0
    viol, n = [], 0
    floor = 1e-9 * max(max(v[0], v[1]) for v in ref.values())      # float noise of a zero moment (released ends)
    for r in ji["members"]:
        if "M_a_max" not in r:
            continue
        k = r["member"] - 1
        Ma, Mb, N = fnum(r["M_a_max"]) * sc, fnum(r["M_b_max"]) * sc, fnum(r["N_Ed_max"]) * sc
        Mz, My, Nc = ref[k]
        for what, st, rf in (("M_a (about z')", Ma, Mz), ("M_b (about y')", Mb, My), ("N_Ed", N, Nc)):
            n += 1
            if st < rf * (1 - 1e-6) - floor:
                viol.append({"member": k + 1, "what": "6.3.3 " + what, "stand": st, "ref": rf})
    R_ = F3.read_deck(deck)[4]
    for r in jl["members"]:
        if "M_Ed_max" not in r:
            continue
        k = r["member"] - 1
        p = R_[k + 1]
        strong = ref[k][0] if p.izz >= p.iyy else ref[k][1]
        n += 1
        if fnum(r["M_Ed_max"]) * sc < strong * (1 - 1e-6) - floor:
            viol.append({"member": k + 1, "what": "LTB M_Ed", "stand": fnum(r["M_Ed_max"]) * sc, "ref": strong})
    return {"seed": seed, "status": "checked", "releases": nrel, "checks": n, "violations": len(viol), "first": viol[:3],
            "verdicts": [ji["verdict"], jl["verdict"]]}


if __name__ == "__main__":
    s0, cnt = int(sys.argv[1]), int(sys.argv[2])
    for s in range(s0, s0 + cnt):
        try:
            print(json.dumps(one(s)), flush=True)
        except Exception as e:                               # noqa: BLE001
            print(json.dumps({"seed": s, "status": "harness_error", "why": repr(e)[:200]}), flush=True)
