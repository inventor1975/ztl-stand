"""Red team: frame.judge_buckling_case (EN 1993-1-1 6.3.1) on a pin-ended 2D column (4 elements, so alpha_cr is close
to Euler's) against my own EN computation with the EXACT Euler force: the stand's utilisation upper bound must not
be below the exact utilisation (its alpha_cr is a lower bound). Loads chosen so that the exact utilisation is near 1
(0.9 .. 1.1), all five curves. --mutant: the stand's utilisation x 0.97.
    PYTHONPATH=. python3 redteam/check_en631.py [COUNT] [--mutant]"""
import json, math, random, sys
from fractions import Fraction as F
from ustand import frame as FRM

MUT = "--mutant" in sys.argv
ALPHA = {"a0": 0.13, "a": 0.21, "b": 0.34, "c": 0.49, "d": 0.76}


def chi(lb, a):
    if lb <= 0.2:
        return 1.0
    ph = 0.5 * (1 + a * (lb - 0.2) + lb * lb)
    return min(1.0, 1 / (ph + math.sqrt(ph * ph - lb * lb)))


def main(count):
    rng = random.Random(9)
    E, A, I, fy = 210e9, 0.01, 8e-5, 355e6
    out = {"cases": 0, "viol": [], "verdicts": {}}
    for t in range(count):
        L = rng.choice([2, 3, 4, 6, 8, 10])
        curve = rng.choice(list(ALPHA))
        Ncr = math.pi ** 2 * E * I / L ** 2
        target = rng.uniform(0.9, 1.1)
        # find N with exact utilisation ~ target: N = target * chi(lb(N)) A fy, by fixed point
        N = 0.5 * A * fy
        for _ in range(200):
            lb = math.sqrt(A * fy / Ncr) if True else 0
            N = target * chi(lb, ALPHA[curve]) * A * fy
        P = int(N)
        deck = (f"ET, 1, BEAM3\nMP, EX, 1, 210e9\nR, 1, {A}, {I}, 0.2\nN, 1, 0, 0\nN, 2, 0, {L}\nE, 1, 2\n"
                f"D, 1, UX, 0\nD, 1, UY, 0\nD, 2, UX, 0\nF, 2, FY, -{P}\nF, 2, MZ, 1\n")
        deck = FRM.subdivide(deck, 4)
        r = FRM.judge_buckling_case(deck, "0", F(fy), curve)
        out["verdicts"][r["verdict"]] = out["verdicts"].get(r["verdict"], 0) + 1
        lb = math.sqrt(A * fy / Ncr)
        u_exact = P / (chi(lb, ALPHA[curve]) * A * fy)
        u_st = float(F(r["utilisation_max"].split()[0])) * (0.97 if MUT else 1)
        out["cases"] += 1
        if u_st < u_exact * (1 - 1e-9) or (r["verdict"] == "EARNED" and u_exact > 1 + 1e-9) or \
                (MUT and u_st <= 1 < u_exact) or (r["verdict"] == "REFUTED" and u_exact <= 1):
            out["viol"].append({"t": t, "L": L, "curve": curve, "P": P, "u_exact": u_exact, "u_stand": u_st,
                                "verdict": r["verdict"]})
    print(json.dumps({"mutant": MUT, "cases": out["cases"], "violations": len(out["viol"]), "first": out["viol"][:3],
                      "verdicts": out["verdicts"]}))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 40)
