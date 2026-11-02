"""Red team: ustand.ltb against the EXACT critical factor of a doubly symmetric member between forks under UNIFORM
moment M and constant axial force N (tension +), both scaled by lambda:
    (lambda M)^2 = i0^2 (N_cr,z + lambda N)(N_cr,T + lambda N),  N_cr,z = pi^2 E I_z / L^2,
    N_cr,T = (G J + pi^2 E I_w / L^2) / i0^2       (the sinusoidal mode is exact for forks; i0^2 = (I_y + I_z)/A)
the smallest positive root. Compression AND tension (the night battery's sweep I has N <= 0 only), I_w = 0 too,
boxes of N and M (the lower bound must stay below the exact factor at every vertex of its box) and point values
(the upper witness must stay above). --mutant: the lower bound x 1.05 and the upper x 0.95.
    PYTHONPATH=. python3 redteam/check_ltb.py [COUNT] [--mutant]"""
import json, math, random, sys
from fractions import Fraction as F
from ustand import ltb as LTB

MUT = "--mutant" in sys.argv


def exact_alpha(L, EIz, GJ, EIw, i02, M, N):
    """smallest lambda > 0 with lambda^2 M^2 = i0^2 (Pz + lambda N)(PT + lambda N)"""
    Pz = math.pi ** 2 * EIz / L ** 2
    PT = (GJ + math.pi ** 2 * EIw / L ** 2) / i02
    a = M * M - i02 * N * N
    b = -i02 * N * (Pz + PT)
    c = -i02 * Pz * PT
    roots = []
    if abs(a) < 1e-300:
        roots = [-c / b] if b else []
    else:
        d = b * b - 4 * a * c
        if d >= 0:
            roots = [(-b + s * math.sqrt(d)) / (2 * a) for s in (1, -1)]
    pos = [r for r in roots if r > 0]
    # in compression the column (flexural or torsional) may come first: lambda |N| = min(Pz, PT) bounds it from above
    if N < 0:
        pos.append(min(Pz, PT) / -N)
    return min(pos) if pos else math.inf


def main(count):
    rng = random.Random(3)
    out = {"cases": 0, "low_viol": [], "up_viol": [], "tension": 0}
    for t in range(count):
        L = F(rng.randint(3, 10))
        E = F(210 * 10 ** 9); G = E / F(26, 10)
        Iz = F(rng.randint(2, 40), 10 ** 6); Iy = Iz * rng.randint(3, 15); A = F(rng.randint(3, 15), 1000)
        J = F(rng.randint(5, 50), 10 ** 8); Iw = F(0) if rng.random() < 0.3 else F(rng.randint(1, 30), 10 ** 8)
        sec = (E * Iz, G * J, E * Iw, (Iy + Iz) / A)
        Pz = float(E * Iz) * math.pi ** 2 / float(L) ** 2
        M = F(rng.choice([-1, 1]) * rng.randint(10 ** 4, 10 ** 6))
        kind = rng.choice(["comp", "tens", "zero"])
        N = F(0) if kind == "zero" else F(int((-1 if kind == "comp" else 1) * rng.uniform(0.05, 0.9) * Pz))
        out["tension"] += kind == "tens"
        box = rng.random() < 0.5
        rM = abs(M) / rng.choice([20, 50]) if box else F(0)
        rN = abs(N) / 20 if box else F(0)
        Nr = (N - rN, N + rN)
        if kind == "comp":
            Nr = (Nr[0], min(Nr[1], F(0)))
        if kind == "tens":
            Nr = (max(Nr[0], F(0)), Nr[1])
        m = rng.choice([2, 4, 8])
        try:
            lo = LTB.alpha_lower(L, sec, Nr, (M - rM, M + rM), (M - rM, M + rM), F(0), m=m, rel=F(1, 10 ** 5))
            up = LTB.alpha_upper(L, sec, M, M, F(0), N, m=m)
        except Exception as e:                                  # noqa: BLE001
            out.setdefault("errors", []).append(repr(e)[:120]); continue
        lo = lo.get("alpha_low") if isinstance(lo, dict) else lo
        up = up.get("alpha_high") if isinstance(up, dict) else up
        ex_nom = exact_alpha(float(L), float(sec[0]), float(sec[1]), float(sec[2]), float(sec[3]), float(M), float(N))
        verts = [(float(a), float(n)) for a in (M - rM, M + rM) for n in Nr]
        ex_min = min(exact_alpha(float(L), float(sec[0]), float(sec[1]), float(sec[2]), float(sec[3]), a, n)
                     for a, n in verts)
        out["cases"] += 1
        if lo is not None:
            L_ = float(lo) * (1.05 if MUT else 1)
            if L_ > ex_min * (1 + 1e-9):
                out["low_viol"].append({"t": t, "kind": kind, "Iw0": Iw == 0, "m": m, "box": box, "lower": L_,
                                        "exact_min": ex_min})
        if up is not None and not box:
            U_ = float(up) * (0.95 if MUT else 1)
            if U_ < ex_nom * (1 - 1e-9):
                out["up_viol"].append({"t": t, "kind": kind, "upper": U_, "exact": ex_nom})
        out.setdefault("ratios", []).append((float(lo) / ex_min) if lo else None)
    r = [x for x in out.get("ratios", []) if x]
    print(json.dumps({"mutant": MUT, "cases": out["cases"], "tension_cases": out["tension"],
                      "lower_violations": len(out["low_viol"]), "upper_violations": len(out["up_viol"]),
                      "first": (out["low_viol"] + out["up_viol"])[:3], "max_lower_over_exact": max(r) if r else None,
                      "errors": out.get("errors", [])[:3]}))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 40)
