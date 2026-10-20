"""A Pratt truss bridge girder as a stand brick (2026-10-20, the curator's "Да" to "a bridge: measure first").

12 panels x 3 m = 36 m span, height 4 m (diagonals 5 m: 3-4-5, every length rational). 24 nodes, 45 bars, pinned at
the left end, on a roller at the right. Statically determinate, so the bar forces follow from node equilibrium
alone, without the moduli; the deflection at mid-span follows by virtual work, delta = sum N_i n_i L_i / (E_i A_i),
where n_i are the bar forces under a unit load at mid-span (the stand solves both systems).

Data, said:
- Loads: design (factored) loads at the 11 deck nodes, 150 kN each, every one independently within +-10 %.
- Steel: E 210 GPa, every bar's own modulus within +-0.5 %; fy 355 MPa.
- Sections: square hollow sections in five groups (bottom chord, top chord, verticals, end posts, diagonals), from
  one catalogue. IDEALISED sharp-corner sections: A = b^2 - (b - 2t)^2, I = (b^4 - (b - 2t)^4)/12 — not EN 10219
  table values (the corner radii make the real A and I slightly smaller).
- Requirements: every bar's stress within +-fy; every bar's force above -chi*A*fy, chi by EN 1993-1-1 6.3.1.2,
  buckling curve c (alpha 0.49), buckling length = bar length, gamma_M1 = 1; mid-span deflection <= L/500 = 72 mm under characteristic
  loads, taken as the factored loads / 1.35 (one partial factor on every load: a simplification).
- Objective: the least steel (volume).

NOT a bridge design: no load model (EN 1991-2), no combinations, no joints, fatigue, dynamics, lateral bracing.

    python3 examples/bridge/gen_pratt.py          -> examples/bridge/pratt36.json
"""
import json
import os
from fractions import Fraction as F

P, W, H = 12, 3, 4                       # panels, panel width (m), height (m)
nodes = {}
B, T = {}, {}
for i in range(P + 1):
    B[i] = f"B{i}"
    nodes[B[i]] = (W * i, 0)
for i in range(1, P):
    T[i] = f"T{i}"
    nodes[T[i]] = (W * i, H)
bars = []
for i in range(P):
    bars.append((B[i], B[i + 1], "BOT"))
for i in range(1, P - 1):
    bars.append((T[i], T[i + 1], "TOP"))
for i in range(1, P):
    bars.append((B[i], T[i], "VER"))
bars += [(B[0], T[1], "END"), (B[P], T[P - 1], "END")]
for i in range(1, P // 2):
    bars.append((T[i], B[i + 1], "DIA"))
for i in range(P // 2 + 1, P):
    bars.append((T[i], B[i - 1], "DIA"))
LEN = {3: "La", 4: "Lb", 5: "Lc"}


def length(a, b):
    (x1, y1), (x2, y2) = nodes[a], nodes[b]
    d2 = (x2 - x1) ** 2 + (y2 - y1) ** 2
    d = round(d2 ** 0.5)
    assert d * d == d2
    return d


def frac(x):
    x = F(x)
    return str(x.numerator) if x.denominator == 1 else f"({x.numerator}/{x.denominator})"


q = {"La": {"role": "given", "value": "3", "unit": "m"},
     "Lb": {"role": "given", "value": "4", "unit": "m"},
     "Lc": {"role": "given", "value": "5", "unit": "m"},
     "fy": {"role": "given", "value": "355", "unit": "MPa", "ground": "EN 10219 S355"}}
for k in range(1, P):
    q[f"P{k}"] = {"role": "given", "value": "150", "tolerance": "0.1", "unit": "kN",
                  "why": f"design load at deck node B{k}"}
for i in range(1, len(bars) + 1):
    q[f"E{i}"] = {"role": "given", "value": "210", "tolerance": "0.005", "unit": "GPa", "why": f"bar {i} modulus"}
    q[f"N{i}"] = {"role": "derived", "unit": "kN"}
    q[f"n{i}"] = {"role": "derived", "unit": ""}
    q[f"s{i}"] = {"role": "derived", "unit": "MPa"}
for r in ("Rx0", "Ry0", "RyP"):
    q[r] = {"role": "derived", "unit": "kN"}
    q[r.lower()] = {"role": "derived", "unit": ""}
q["delta"] = {"role": "derived", "unit": "mm"}

laws = []
for nd, (x, y) in nodes.items():
    for ax in (0, 1):
        terms, unit_terms = [], []
        for i, (a, b, g) in enumerate(bars, 1):
            if nd not in (a, b):
                continue
            other = b if nd == a else a
            L = length(a, b)
            c = F(nodes[other][ax] - nodes[nd][ax], L)   # tension pulls the node toward the other end
            if c:
                terms.append(f"{frac(c)}*N{i}")
                unit_terms.append(f"{frac(c)}*n{i}")
        ext, uext = [], []
        if nd == B[0]:
            ext.append("Rx0" if ax == 0 else "Ry0")
            uext.append("rx0" if ax == 0 else "ry0")
        if nd == B[P] and ax == 1:
            ext.append("RyP")
            uext.append("ryp")
        k = int(nd[1:]) if nd.startswith("B") else None
        if ax == 1 and k is not None and 1 <= k <= P - 1:
            ext.append(f"(-1)*P{k}")
        if ax == 1 and nd == B[P // 2]:
            uext.append("(-1)")
        laws.append({"zfl": " + ".join(terms + ext) + " == 0", "source": f"equilibrium at {nd}, {'xy'[ax]}"})
        laws.append({"zfl": " + ".join(unit_terms + uext) + " == 0",
                     "source": f"equilibrium at {nd}, {'xy'[ax]}, unit load at mid-span"})
for i, (a, b, g) in enumerate(bars, 1):
    laws.append({"zfl": f"s{i} == N{i}/{g}.A", "source": f"stress, bar {i} ({g})"})
vw = " + ".join(f"N{i}*n{i}*{LEN[length(a, b)]}/(E{i}*{g}.A)" for i, (a, b, g) in enumerate(bars, 1))
laws.append({"zfl": f"delta == -({vw})", "source": "virtual work: mid-span deflection (positive up)"})

reqs = []
for i, (a, b, g) in enumerate(bars, 1):
    L = LEN[length(a, b)]
    lam = f"sqrt({g}.A*fy*{L}*{L}/(pi*pi*E{i}*{g}.I))"
    phi = f"(0.5*(1 + 0.49*({lam} - 0.2) + {lam}*{lam}))"
    chi = f"min(1, 1/({phi} + sqrt({phi}*{phi} - {lam}*{lam})))"
    reqs.append({"quantity": f"s{i}", "op": "within", "value": ["-355", "355"],
                 "why": f"bar {i} ({g}, {a}-{b}): stress within fy"})
    reqs.append({"quantity": f"N{i}", "op": ">=", "value": f"-({chi})*{g}.A*fy",
                 "why": f"bar {i} ({g}): flexural buckling, EN 1993-1-1 curve c"})
# DEFLECTION IS A SERVICEABILITY CHECK (2026-10-20, corrected the same evening): L/500 under the CHARACTERISTIC loads,
# not the factored ones. With ONE partial factor 1.35 on every load (a simplification, said) and a linear structure,
# the characteristic deflection is the factored one / 1.35 exactly: |delta_factored| <= 72 * 1.35 = 97.2 mm.
# The first run held the factored deflection to 72 mm and refuted the whole catalogue by 0.127 mm — 35 % too strict.
reqs.append({"quantity": "delta", "op": ">=", "value": "-97.2",
             "why": "mid-span deflection <= L/500 = 72 mm under characteristic loads (factored / 1.35)"})

# idealised SHS (sharp corners), b x t in mm
SHS = [(100, 6), (120, 8), (150, 8), (160, 10), (180, 10), (200, 10), (220, 12), (250, 12)]
items = []
for b, t in SHS:
    A = F(b * b - (b - 2 * t) ** 2)
    I = F(b ** 4 - (b - 2 * t) ** 4, 12)
    items.append({"name": f"SHS {b}x{t} (sharp corners)", "A": str(A), "I": f"{I.numerator}/{I.denominator}"
                  if I.denominator != 1 else str(I)})
groups = {"BOT": "bottom chord", "TOP": "top chord", "VER": "verticals", "END": "end posts", "DIA": "diagonals"}
total = {g: sum(length(a, b) for a, b, gg in bars if gg == g) for g in groups}
brick = {
    "stand": "ztl-stand/1",
    "why": "Pratt truss bridge girder, 36 m, 45 bars — a measurement of what the stand carries, not a bridge design",
    "quantities": q,
    "slots": {g: {"from": ["shs"], "why": groups[g]} for g in groups},
    "laws": laws,
    "requirements": reqs,
    "objective": {"minimize": " + ".join(f"{g}.A*{total[g]}" for g in groups), "why": "least steel (A x total length)"},
    "conflicts": False,
    "catalog": {"shs": {"ground": "idealised sharp-corner SHS, computed from b and t",
                        "items": items, "fields": {"A": {"unit": "mm^2"}, "I": {"unit": "mm^4"}}}},
}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pratt36.json")
json.dump(brick, open(out, "w"), indent=1)
print(f"{len(nodes)} nodes, {len(bars)} bars, {len(laws)} laws, {len(reqs)} requirements, "
      f"{len(SHS) ** len(groups)} designs -> {out}")
