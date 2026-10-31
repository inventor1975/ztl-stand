"""An elevated steel water tower: a cylindrical tank on one tubular steel shaft, on a square concrete footing.

Written 2026-10-31 as the stand's first water-tower brick (the curator's question to Arkadiy's Foresight request:
"a water tower and the like" as an existing class). Closed-form checks only:
  - shaft stress, axial + bending, factored (1.35 on weight, 1.5 on wind), against fy/1.1;
  - Euler buckling of the shaft as a free-standing cantilever (effective length 2H), safety 3 on the factored weight;
  - sway at the shaft top under the characteristic wind, H/150;
  - the footing: the resultant inside the kern (no uplift anywhere), and the edge soil pressure against the soil's
    allowable pressure, characteristic loads.
The water in the tank is anywhere from EMPTY to FULL: full is the worst case for stress and soil pressure, empty for
the kern (overturning). The stand has to prove both at once, over every wind speed and every tolerance.

Sections are IDEALISED circular hollow sections computed from D and t (exact annulus formulas), not EN 10210 table
values; only sections with D/t <= 59 are listed (cross-section class 3 limit for S355, 90*235/355 = 59.6), so local
buckling is excluded by the catalogue, not checked. Prices are illustrative.

    python3 examples/watertower/gen_tower.py > examples/watertower/tower.json
    python3 -m ustand.stand examples/watertower/tower.json --jobs 16
"""
import json
from fractions import Fraction as Fr

PI = Fr(355, 113)          # only for the catalogue's section properties (the laws use the stand's own pi)


def chs(D_mm, t_mm):
    D, d = Fr(D_mm), Fr(D_mm) - 2 * Fr(t_mm)
    A = PI / 4 * (D * D - d * d)                      # mm^2
    I = PI / 64 * (D ** 4 - d ** 4)                   # mm^4
    W = 2 * I / D                                     # mm^3
    m = A * Fr(7850) / 10 ** 6                        # kg/m
    pm = m * Fr(18, 10) + Fr(D_mm, 10)                # EUR/m: 1.80 EUR/kg + a fabrication term
    f = lambda x, n=6: f"{float(x):.{n}g}"
    return {"name": f"CHS{D_mm}x{t_mm}", "D": str(D_mm), "A": f(A / 100), "I": f(I / 10 ** 4),
            "W": f(W / 10 ** 3), "m": f(m), "pm": f(pm, 5)}


shafts = [chs(D, t) for D in (508, 610, 711, 813, 914, 1016, 1220) for t in (8, 10, 12.5, 16, 20, 25)
          if Fr(D) / Fr(t) <= 59]

footings = []
for B10 in range(25, 125, 5):                         # 2.5 .. 12.0 m
    B = Fr(B10, 10)
    price = B * B * Fr(12, 10) * 190 + B * B * 25    # concrete 190 EUR/m^3 at 1.2 m, earthworks 25 EUR/m^2
    footings.append({"name": f"F{B10/10:.1f}", "B": f"{float(B):g}", "price": f"{float(price):.2f}"})

Q = lambda **k: k
brick = {
    "stand": "ztl-stand/1",
    "title": "Elevated steel water tower: 100 m3 tank on one tubular shaft, square footing; water empty..full, wind 22..28 m/s",
    "quantities": {
        "H": Q(role="given", value="20", unit="m", why="shaft height, ground to tank floor"),
        "Dt": Q(role="given", value="6", unit="m", why="tank diameter"),
        "Ht": Q(role="given", value="3.6", unit="m", why="tank height (about 100 m3)"),
        "mw": Q(role="given", range=["0", "100"], unit="t", why="water in the tank: empty to full"),
        "mtank": Q(role="given", value="14", tolerance="0.05", unit="t", why="tank steel, roof and fittings, +-5 %"),
        "vb": Q(role="given", range=["22", "28"], unit="m/s", why="design wind speed at tank height (site range)"),
        "rho_a": Q(role="given", value="1.25", unit="kg/m^3", why="air density"),
        "Cd": Q(role="given", value="0.8", tolerance="0.125", unit="1", why="drag coefficient of a cylinder, 0.7..0.9"),
        "E": Q(role="given", value="210", tolerance="0.005", unit="GPa", why="steel modulus"),
        "fy": Q(role="given", value="355", unit="MPa", why="S355 yield strength"),
        "gc": Q(role="given", value="24", unit="kN/m^3", why="reinforced concrete unit weight"),
        "hf": Q(role="given", value="1.2", unit="m", why="footing thickness"),
        "qa": Q(role="given", range=["150", "250"], unit="kPa", why="allowable soil pressure: site survey range"),
        "sigma": Q(role="derived", unit="MPa"),
        "ub": Q(role="derived", unit="1"),
        "delta": Q(role="derived", unit="mm"),
        "pmax": Q(role="derived", unit="kPa"),
        "kern": Q(role="derived", unit="kN*m"),
    },
    "slots": {"S": {"from": ["chs"]}, "F": {"from": ["footing"]}},
    "catalog": {
        "chs": {"ground": "circular hollow sections, properties computed from D and t (idealised), D/t <= 59; prices illustrative",
                "fields": {"D": {"unit": "mm"}, "A": {"unit": "cm^2"}, "I": {"unit": "cm^4"}, "W": {"unit": "cm^3"},
                           "m": {"unit": "kg/m"}, "pm": {"unit": "EUR/m"}},
                "items": shafts},
        "footing": {"ground": "square pad footings, 1.2 m thick; prices illustrative",
                    "fields": {"B": {"unit": "m"}, "price": {"unit": "EUR"}},
                    "items": footings},
    },
    "define": {
        "q": "rho_a*vb*vb/2",
        "Ft": "q*Cd*Dt*Ht",
        "Fs": "q*Cd*S.D*H",
        "Mb": "Ft*(H + Ht/2) + Fs*H/2",
        "Nk": "(mw + mtank + S.m*H)*g0",
        "Wf": "gc*F.B*F.B*hf",
    },
    "laws": [
        {"zfl": "sigma == 1.35*Nk/S.A + 1.5*Mb/S.W", "source": "axial + bending stress at the shaft base, factored"},
        {"zfl": "ub == 3*1.35*Nk*4*H*H/(pi*pi*E*S.I)", "source": "Euler, free-standing cantilever (effective length 2H), safety 3"},
        {"zfl": "delta == Ft*H*H*H/(3*E*S.I) + Fs*H*H*H/(8*E*S.I)", "source": "cantilever sway: tank force at the top, shaft wind uniform"},
        {"zfl": "pmax == (Nk + Wf)/(F.B*F.B) + 6*Mb/(F.B*F.B*F.B)", "source": "edge soil pressure, resultant within the kern"},
        {"zfl": "kern == (Nk + Wf)*F.B/6 - Mb", "source": "resultant inside the middle third: no uplift"},
    ],
    "requirements": [
        {"quantity": "sigma", "op": "<=", "value": "fy/1.1", "why": "steel resistance, gamma_M = 1.1"},
        {"quantity": "ub", "op": "<=", "value": "1", "why": "Euler load at least 3x the factored weight"},
        {"quantity": "delta", "op": "<=", "value": "H/150", "why": "sway limit at the tank floor"},
        {"quantity": "pmax", "op": "<=", "value": "qa", "why": "soil pressure within the allowable"},
        {"quantity": "kern", "op": ">=", "value": "0", "why": "no uplift under any wind, tank empty or full"},
    ],
    "objective": {"minimize": "S.pm*H + F.price", "unit": "EUR"},
}
print(json.dumps(brick, indent=1, ensure_ascii=False))
