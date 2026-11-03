"""Red team, 2D stability brackets: frame.stability_lower (for every modulus in the box) <= the reference's
lambda_cr at random box vertices; frame.stability_upper (a witness at the nominal moduli) >= the reference at the
nominal moduli. Reference: redteam/ref2d.buckling (ns sub-elements, its error measured by ns vs 2 ns).
--mutant: the lower bound multiplied by 1.05 and the upper by 0.95 (a broken bracket the check must see).
    PYTHONPATH=. python3 redteam/hunt2d_stab.py SEED0 COUNT [--mutant]"""
import json, os, random, sys
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref2d  # noqa: E402
from hunt2d import gen  # noqa: E402
from ustand import frame as FRM  # noqa: E402

MUT = "--mutant" in sys.argv


def one(seed):
    fam, deck = gen(seed)
    tol = "0" if seed % 2 == 0 else "0.5%"
    t = 0.0 if tol == "0" else 0.005
    m = deck.count("\nE, ")
    try:
        lo = FRM.stability_lower(deck, tol)
        up = FRM.stability_upper(deck)
    except Exception as e:                                   # noqa: BLE001
        return {"seed": seed, "fam": fam, "status": "error", "why": repr(e)[:150]}
    llo, lhi = lo.get("lam_low"), up.get("lam_high")
    if llo is None and lhi is None:
        return {"seed": seed, "fam": fam, "status": "none", "why": str(lo.get("why"))[:100]}
    ref_nom = ref2d.buckling(deck, None, 32)
    ref_nom2 = ref2d.buckling(deck, None, 64)
    if ref_nom is None:
        return {"seed": seed, "fam": fam, "status": "no_ref_mode"}
    err = abs(ref_nom - ref_nom2) + 1e-9 * ref_nom
    rng = random.Random(seed)
    verts = [[1 - t] * m] + ([[1 + t * rng.choice([-1, 1]) for _ in range(m)] for _ in range(3)] if t else [])
    refs = [ref2d.buckling(deck, v, 32) for v in verts] + [ref_nom]
    out = {"seed": seed, "fam": fam, "tol": tol, "status": "checked", "ref_nominal": ref_nom, "ref_err": err,
           "lam_low": float(llo) if llo else None, "lam_high": float(lhi) if lhi else None, "violations": []}
    if llo is not None:
        L = float(llo) * (1.05 if MUT else 1)
        rmin = min(r for r in refs if r is not None)
        out["low_over_ref"] = L / rmin
        if L > rmin + 20 * err:
            out["violations"].append({"what": "lam_low above the reference", "lam_low": L, "ref_min": rmin})
    if lhi is not None:
        H = float(lhi) * (0.95 if MUT else 1)
        out["ref_over_high"] = ref_nom / H
        if H < ref_nom - 20 * err:
            out["violations"].append({"what": "lam_high below the reference", "lam_high": H, "ref": ref_nom})
    return out


if __name__ == "__main__":
    s0, n = int(sys.argv[1]), int(sys.argv[2])
    for s in range(s0, s0 + n):
        try:
            print(json.dumps(one(s)), flush=True)
        except Exception as e:                               # noqa: BLE001
            print(json.dumps({"seed": s, "status": "harness_error", "why": repr(e)[:200]}), flush=True)
