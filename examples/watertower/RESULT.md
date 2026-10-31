# Water tower — the measurement (2026-10-31)

`tower.json` (from `gen_tower.py`): a 100 m3 steel tank (6 m x 3.6 m, 14 t +-5 %) on one tubular steel shaft 20 m
high, on a square concrete pad 1.2 m thick. Water anywhere from empty to full; wind 22..28 m/s; drag 0.7..0.9; steel
modulus +-0.5 %; allowable soil pressure 150..250 kPa (site range). Requirements: shaft stress (factored 1.35 / 1.5)
<= fy/1.1; Euler load >= 3x the factored weight (free-standing cantilever, effective length 2H); sway <= H/150; edge
soil pressure <= allowable; resultant inside the kern (no uplift). 22 idealised circular hollow sections (D/t <= 59)
x 20 pads (2.5..12 m) = 440 designs. Prices illustrative.

    python3 -m ustand.stand examples/watertower/tower.json --jobs 16 --dev

| | |
|---|---|
| verdict | **EARNED, optimal** — every cheaper design refuted |
| design | shaft CHS 914x16, pad 4.0 x 4.0 m |
| cost | 18 632.20 EUR (illustrative prices) |
| guaranteed, over every water level, wind and tolerance | stress 26.8..79.1 MPa (limit 322.7); Euler use 0.137..0.825 (limit 1); sway 16.7..35.2 mm (limit 133); soil 54.3..130.5 kPa (limit 150); kern margin 152..965 kN*m (>= 0) |
| what decides | the shaft: Euler buckling (87 cheaper designs refuted on it); the pad: soil pressure (the 2.5, 3.0 and 3.5 m pads refuted on it) |
| designs | 96 tried in cost order: 85 failed at the nominal point, 11 judged in full, 0 open |
| checked | ZTL + the independent checker (dev mode): every corner of the box recomputed exactly |
| time | 0.47 s on 16 workers (i9-14900F) |

Hand check of the optimum (full tank, wind 28 m/s, drag 0.9): N = 121.1 t x 9.81 = 1188 kN; Euler 5894 kN ->
3 x 1.35 x 1188 x 1.05/5894 = 0.82; M = 9.53 kN x 21.8 m + 8.06 kN x 10 m = 288 kN*m; soil (1188 + 461)/16 +
6 x 288/64 = 130 kPa. Agrees with the stand's upper ends.

Limits: closed-form checks only — no shell buckling of the tank, no wind dynamics or vortex shedding, no seismic
case, no second-order (P-delta) amplification beyond the Euler safety factor, no foundation settlement; sections
idealised, not EN 10210 values.
