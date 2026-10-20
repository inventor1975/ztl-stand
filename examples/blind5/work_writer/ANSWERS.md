# ANSWERS (writer's check results; not for authors)

Scripts: p01.py ... p12.py in this folder, `check_all.py` (output saved in `check_all_output.txt`), `check_p06_p07_p09.py`. All checks are brute force / fine scans / LP, written by the same author (no independent second implementation).

Summary of outcomes:
- IMPOSSIBLE by design: 6 (footing), 7 (shielding), 9 (warehouse).
- TIGHT (< 1 % at the worst case): 1 (bearing life, +0.72 %), 12 (weighted service level 0.8756 vs 0.87, +0.64 %).
- Others feasible with a normal margin.
- Singular parameter values: 4 (slope 0 = no flow), 5 (B + D = 0 unbounded cycles; D > 0 here so only a remark), 10 (no oxygen balance if C_ss <= 0), 12 (n <= A: no steady state, SL = 0).
- "Or none" parts: 1 (kit), 2 (capacitor bank), 3 (insulation upgrade), 5 (inhibitor, acid), 7 (lead/barite/concrete layers), 8 (roof solar), 10 (LOX, units not running), 11 (options), 12 (IVR).
- Summed/averaged requirements: 1 (Miner damage over cycles), 2 (annual loss energy over seasons), 3 (annual back-up energy), 5 (annual make-up), 7 (weekly dose over examination types), 8 (route-mix average consumption), 9 (annual cost), 10 (annual energy), 11 (annual profit), 12 (call-weighted SL).

## 1. Bearing
Cheapest feasible: R-60F + VG150 + no kit, price 1.70 kEUR, worst-case life 56 403 h vs 56 000 required (+0.72 %, TIGHT). Binding: R1 life. Static check C0/P0 >= 2.5 removes R-60A (2.1) only; R-60G violates OD. Cheaper designs have lives 1.4e3 to 2.8e4 h. Next feasible: R-60F VG320 (1.80, life 78 267 h). Worst case is every Fr at its top and every T at its top (damage monotone: higher T lowers viscosity). Monte Carlo (2000 samples) never went below the corner value.

## 2. Transformer
Exactly ONE admissible design: 1000 kVA, class A (amorphous), capacitor bank C150. Worst-case lifetime cost 131.76 kEUR (capex 16.3 + PV 115.5), y1 losses 31 548 kWh (limit 32 000), S30 = 0.977 Sn, dU peak 3.708 % (limit 3.8), night rise -0.618 % (limit -0.8), mass 2820 kg. Why others fail: 1250 S (cheapest overall 125.6) has losses 33.3 MWh and 1250 L/A exceed 3000 kg; 1000 L C150 has losses 33.3 MWh; 1000 A C200 violates the night voltage rise (-0.91 %); 1000 A C100 violates peak drop (4.0 %); 1000 A none violates S30 (1.06) and drop (4.6 %). 72 combinations in total.

## 3. Solar thermal
Cheapest feasible: F2 flat selective, n = 5 (11.5 m2), V = 750 L, no insulation upgrade, price 4.623 kEUR. Worst-case back-up energy 3643 kWh (limit 3700), Tmax 72.9 degC (limit 80), V/A = 65. 29 feasible designs of 960 (6 x 16 x 5 x 2). Runner-up: T2 n=3 V=500 (4.80). Worst case at the corners of (H, T_a, T_c), draw = 660 (confirmed by 3-point and 5-point grids).

## 4. Sewer
Cheapest feasible: PVC, reach A D=250 mm S=0.005, reach B D=300 mm S=0.0035; cost 191.57 kEUR; outfall depth 4.93 m (limit 5.0); worst v_dry 0.678 (A), 0.699 (B); worst y/D at storm 0.478 / 0.578. Nine feasible designs under the 5.0 m outfall limit (all PVC); with the limit at 4.9 m none is feasible (the self-cleansing velocity forces slopes that bring the outfall to 4.93 m). Concrete never gets cheaper because it needs steeper slopes to reach 0.6 m/s. Slope 0 is always inadmissible.

## 5. Cooling tower
Cheapest: Town water, programme P2, acid 70 %, blowdown 0.165 / 0.290 / 0.415 m3/h (winter / midseason / summer); annual cost 54.08 kEUR, annual make-up 24 502 m3 (limit 26 000). Binding limit in all seasons: sulphate (N_max = 10.47). Without the make-up cap, Well + P2 + 70 % would be cheapest (34.3 kEUR) but uses 30 414 m3. Designs meeting the cap: 6; next Town P1/70 % (55.38, 25 783 m3), Town P3/40 % (57.07). Well with no programme and no acid (or with 40 % acid) is infeasible at any blowdown (LSI).

## 6. Strip footing (IMPOSSIBLE)
Worst-case FS over the catalog with B <= 2.0 m: maximum 2.62 (B = 2.0, Df = 1.5), below 3.0. Settlement (<= 18 mm) and eccentricity (<= B/6) are not the problem. Conflict: R1 (FS >= 3) against R4 (B <= 2.0 m); removing R4 gives B = 2.4 m with Df = 1.2 (FS 3.04) or Df = 1.5 (FS 3.15). Cost would be 72*2.4 + 28*3.0*1.2 + 32 = 305.6 EUR/m for Df = 1.2.

## 7. Radiography shielding (IMPOSSIBLE)
Best dose with added mass <= 55 kg/m2 and thickness <= 60 mm: 0.0104 mSv/week (lead 3.0 mm only), twice the 0.005 limit. The 7 dose-feasible designs that also satisfy the thickness limit all weigh at least 61.0 kg/m2; the lightest is lead 3.0 mm + barite 10 mm (mass 61.02, thickness 13 mm, dose 0.0034). Conflict: R1 (dose) against R2 (mass); R3 thickness is not binding (it only excludes the concrete linings). Relaxing mass to 61.02 gives a feasible design.

## 8. Electric van
Cheapest feasible: pack B77, ultra tyres, full aero kit, heat pump, no roof solar; price 14.85 kEUR. Cold-day range ratios: urban 1.264, suburban 1.143, motorway 1.027 (binding, +2.7 %); average consumption 24.27 vs 24.8; gross mass 3430 vs 3500. B90 and B110 violate the gross-mass limit (3510, 3645); with the deflector instead of the full kit the motorway range ratio is 0.985 (fail). Roof solar adds 1.1 kEUR for 0.5 % range, never worthwhile.

## 9. Warehouse (IMPOSSIBLE)
LP optimum of the worst-case annual cost: T3 with B = 1795.5 gives 367.2 kEUR (T2 399.8 with B = 2495.5; T1 427.0 with B = 3195.5; T0 infeasible: the largest need 4295.5 positions exceeds 3200 + spot 300). Budget 355 kEUR is 3.3 % below the minimum. Binding chain: coverage in Q4 (B + 2200 + 300 >= 4295.5) forces B >= 1795.5 for T3, which fixes the cost. Conflict: R1 (coverage incl. spot availability) against R2 (budget). Raising the budget to 367.2 kEUR makes T3, B = 1795.5 feasible.

## 10. Aquaculture
Cheapest feasible: PW2 paddlewheels, n = 10 installed, running counts (winter, spring, summer, autumn) = (1, 3, 10, 3), LOX unit installed; 10-year cost 87.95 kEUR (capex 36.0 + 6.5 = 42.5, energy 28 406 kWh/yr). Worst C_ss 4.06 (fine T grid 81 points x 9 biomass points) vs 4.0, worst DO after the power cut 3.12 vs 3.0. Only 5 designs meet all requirements under the 31 000 kWh cap; without LOX the cheapest needs 12 units in summer (93.4 kEUR, energy above the cap, hence infeasible at 31 000). Zero running units in winter gives C_ss = 1.46 (fails).

## 11. FX hedge
No options: infeasible. K = 1.14: infeasible. K = 1.10: minimum cost 52.91 kEUR (e.g. h = 0.85, 0.85, 0.55, 0; o = 0, 0, 0.046, 0.85; the forward line of 9.0 million USD is binding). K = 1.06: 66.62 kEUR. Answer: strike 1.10, about 52.9 kEUR (several optimal vertices may exist; the cost is what matters). C = 3.00 million EUR per quarter, premium cap 0.10 not binding (about 0.043 million EUR at the K110 solution).

## 12. Call centre
Cheapest: advanced IVR with (n1..n4) = (25, 29, 22, 13); annual cost 2992.0 kEUR (agents 2961.0 + IVR 31). Worst SL_day 0.8756 (limit 0.87, +0.64 %, TIGHT); worst SL per part 0.943 / 0.884 / 0.847 / 0.781 (limit 0.70); max occupancy 0.793. Next best (25, 28, 23, 13) 2993.8 kEUR has SL_day 0.8704 (margin 0.05 %). Without IVR or with basic IVR the cost is higher (n per part at least 24/30/23/14 for none). The worst case of the weighted SL occurs at corners of lambda (verified by 20 000 random samples never below the corner minimum for three designs).

## Things not checked / caveats
- No formal monotonicity proof for the worst cases: corner/grid evaluation was used (P3 3/5-point grids, P4 five n values, P6 corner and 4-level grids, P10 9- and 81-point T grids, P12 corners plus random samples). The P12 and P10 searches use windows around the per-period minima (P12: minimum + 8 agents; P10 exhaustive over m_s in 0..16).
- P5 and P9 closed forms were taken from direct evaluation (B at the lower bound, F/S filling cheapest-first), cross-checked for P9 by LP; P5 not LP-checked, optimum B follows from monotonic cost in B.
- P2 uses corner maxima of the seasonal loss (the loss is convex in P and pf); not checked against a dense sample.
- P11 LP evaluates the kink S = K; not cross-checked by a nonlinear solver.
- Decimal rounding of printed limits could flip designs within about 1e-3 of a limit (P1, P12 in particular: P12 second best is 0.05 % above its limit).
