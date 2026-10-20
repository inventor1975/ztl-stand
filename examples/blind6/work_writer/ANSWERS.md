# ANSWERS (writer's intended outcomes; NOT for the solver). Every number below was produced by the scripts in this folder (p1.py ... p12.py, final_checks*.py).

Method: each script enumerates the catalog (and fine grids of continuous amounts) and evaluates the worst case over all uncertain quantities at the corners of their ranges (all laws are monotone in each uncertain quantity, or both ends / a fine scan were tried; P6 scanned temperature at 61 points, P10 and P12 used corners of every range). Margins are (limit/value - 1) in the sense that positive = satisfied.

## Summary
Impossible by design: 4 (heat trace), 7 (detention pond), 11 (fleet insurance).
Tight (<1 % at the worst case): 2 (min margin 0.12 %), 5 (min margin 0.77 %).
Chains: 2, 3, 5, 6, 8, 10 (shared upstream source in 2, 5, 8).
Limit questions: 2, 3, 4, 8, 9 (and 12 asks the admissible interval limits).

## 1. Hoist rope (mechanical)
Cheapest: W-10 (10 mm), D = 0.2115 m (exact minimum 0.21148 m, set by the life requirement R1), price 84 m * 3.2 EUR + 0.50 + 16 D^2 = 1.4844 kEUR.
W-8 fails R2 (class C safety factor 3.47 < 5). W-12 needs D >= 0.216 (D/d >= 18 binds, life not binding), price 1.633. W-14: D >= 0.252, 2.062. W-16 violates fairlead (R3). Class C safety factor of W-10 = 5.41.

## 2. Feeders (electrical chain, tight)
Cheapest: feeder 1 cable C50 + breaker B63; feeder 2 cable C16 + breaker B40. Price 2.8255 kEUR (cables 14*160 + 5.5*85 EUR = 2240 + 467.5; breakers 70 + 48... total 2.8255 kEUR).
Worst-case margins of that design: R2 start of M1 (terminal voltage vs 340 V) = +0.124 % (tightest), R1 M1 running +0.27 %, R1 M2 running +0.40 %, R3 +3.2 %, breaker no-nuisance (R4) +2.3 % / +3.9 %, magnetic (R5) +18.9 % / +25 %, cable protection (R6) large.
Next cheaper cable for feeder 1 (C35) fails R2/R1 at L1 = 160 m. Limit: largest L1 for which any design exists (C95 on feeder 1) = 251.99 m (other data unchanged); at L1 = 200 m cheapest is C70, at 230 m C95.

## 3. Cordless saw pack (electrical chain, limit question)
Cheapest at -10 degC: cell H25, Np = 4 (20 cells), BMS M60, heater fitted. Price 20*2.9 + 7.5 + 4.5 = 70.0 EUR. Margins: R1 +3.9 %, R2 +15.4 %, R3 +38 %, R4 +26.9 %, R5 +4.2 %.
Only other feasible design at -10: H25, Np=4, M80, heater (73.5 EUR). Without heater nothing is feasible at -10 degC (cheapest no-heater design needs T >= about -5 degC: H25, Np=4, M60, 65.5 EUR at -5).
Limits: lowest ambient with ANY design: -16.12 degC (H25/4/M80/heater; R1 binds); for the chosen design (M60 + heater): -15.54 degC.

## 4. Heat trace (thermal, IMPOSSIBLE at Ta = -40, limit question)
No admissible design at -40 degC. Conflict: R1 (freeze) needs cable output at 3 degC and 207 V >= heat loss. Best allowed insulation under R3 (outer diameter <= 180 mm) is PIR-40 (170 mm), loss 14.43 W/m at -40; T15 gives only 13.74 W/m (short by 5 %); T20 gives 18.32 W/m but 25.25 W/m at 253 V violates R2 (cap 24 W/m). PIR-50 (loss 12.34 W/m, T15 would pass) and MW-50 (190 mm) violate R3 clearance. So R1 vs R2 vs R3 conflict; relaxing any ONE of them (e.g. cap 26 W/m, clearance 190 mm, or Ta) is enough.
Limit: lowest ambient with an admissible design = -37.86 degC: PIR-40 + T15 (price 3108 EUR for 140 m); at -35 also PIR-40+T15 only (MW-50 excluded by clearance).

## 5. Compressed air (fluid chain, tight)
Cheapest: compressor K40, dryer D50, main pipe 50 mm. Price 8200 + 1900 + 21*180 = 13 880 EUR. Tightest requirement: tool B inlet pressure in S3 (+0.77 %); tool A in S3 +2.55 %, S1 +5.0 %, S2 tool B +4.3 %; R2 capacity +21 %; R3 +4.3 % / +10.4 %; R4 +61 %.
Traps: K40M (higher pressure) has comfortable pressure margins but fails R3 for tool A (8.4 + 0.15 = 8.55 > 8.5). K32 fails R2. Next feasible: K40/D60/50 (14 480), K40/D50/63 (16 040).

## 6. Extraction cascade (chemical, coupled linear balances)
Cheapest: extractor E3H, solvent SC, bed G1200, S = 1.3747 m3/h (R5 loaded-solvent limit binds exactly: y1 = 8.5 g/L at the worst case). 5-year cost = 20 + 3.2 + 5*8000*1.3747*4.5/1000 = 270.65 kEUR. At that S: x_N max = 0.0508 g/L, final 0.0051 g/L (R2 +18 %), bed life 2.25 months (R3 +12 %), R1 large margin.
Alternatives: E4/SC/G1200 S=1.3742 cost 272.6; E3/SC/G2000 S=1.414 cost 276.5; E3/SC/G1200 S=1.46 cost 283.0. SA and SB: no feasible S for any extractor (their best-case y1/x_N cannot satisfy R2 within S <= 1.8). E2 never feasible.
Note: the temperature scan was 7 points in the search and 61 points in the final check; the worst-case xN is at T = 30, rho = 0.04, cF = 7.5 (stated from the scan, not proved).

## 7. Detention pond (civil, IMPOSSIBLE)
No admissible design. Worst-case margins at A = 610 m2, H = 2.0 m: d=80 mm: R1 +60 %, R2 +134 %, R3 -6.8 %; d=100: R1 +4.3 %, R2 +52 %, R3 -4.6 %; d=120: R1 -26 %, R2 +7.3 %, R3 -1.7 %; d=150: R1 -51 %, R2 -29 %, R3 +3.8 %. (d=60 violates R4.)
The R3 (100-year depth within H - 0.3 and the site limits R5) conflicts with the discharge caps: the orifice that satisfies R3 (O150) violates both R1 and R2; dropping R1 alone is not enough (R2 limits to O120, which still fails R3 by 1.7 %); dropping R2 alone is not enough (R1 limits to O100); dropping both R1 and R2 gives a feasible design (O150, A ~ 590 m2, H = 2.0). Dropping R3 alone is feasible (e.g. O80, A 230 m2). Needed A for R3 at H=2.0: 641 m2 (O100), 622 (O120), 587 (O150).
Relaxing the 100-year cap R2 alone to about 65 L/s with R1 dropped makes O150 feasible, but R1 and R2 jointly with R3 cannot hold.

## 8. Twin-patient oxygen (biomedical chain, shared source, limit)
Cheapest at Tt = 35 min: 1 x CY10, regulator RB for patient 1, RC for patient 2, no conserver. Price 165 + 140 + 320 = 625 EUR; R1 margin +1.65 %, mass 14 kg <= 16.
Limits: for that design largest Tt = 36.37 min. Largest Tt for which ANY design exists = 153.4 min (2 x CY7H + manifold, RC, RC, conserver; 2410 EUR; mass 11.2 kg).
(Mass limit 16 kg removes CY7 pairs and CY10 pairs; at Tt = 32 min cheapest is CY10/RA/RB 365 EUR with margin 0.07 %; at 38 min CY10/RC/RC 805 EUR margin 0.14 %.)

## 9. Cargo lashing (transport/logistics, limit question)
Cheapest: strap S2, n = 9, mat M1: 9*19 + 140 = 311 EUR (required n = 8.63 -> 9). Next: S1 + M2 n = 6: 332; S2 + M2 n = 5: 355; S3 + M1 n=6: 368; S3 + M2 n = 4: 412. Forward direction (c = 0.80) is the binding one. M0 (bare deck) never fits within 10 straps.
Limit: largest cargo mass with any admissible design = 26 832 kg (n = 10 on S3 with M2 at the limit; forward case).

## 10. Maize drying and storage (agriculture chain)
Cheapest: dryer DR8, no fan, Td = 65.78 degC, Mf = 0.1768 (Mwb = 15.02 %), worst-case season cost 51.67 kEUR. R1 throughput and R3 storage both bind (equalities); R2 damage margin +4.9 %; worst-case drying time 9.0 h.
Runner-up: DR6 + F25, Td = 70.04, Mf = 0.1873, 52.03 kEUR (0.7 % more). Then DR8 + F8 (Td 64.96, Mf 0.1810): 53.70; DR8+F15: 55.08; DR10 + none: 57.07. DR4 infeasible (damage), DR6 with none/F8/F15 infeasible (damage index at the Td needed for throughput).

## 11. Fleet insurance (finance, IMPOSSIBLE)
No admissible design. Conflict R1 (normal-year cost <= 210) vs R4 (stability <= 62): D = 5 with SL60 (R = 20): totals 215.2 in every scenario, R1 fails by 2.4 % (needs premium 138.2 + SL 16 + r' 60 + 1 carry); D = 10 with SL60 (R = 30): normal 189.8, bad 247.8, catastrophe 199.8 but R4 gives |r'(bad)-r'(normal)| up to 78 kEUR > 62 (-20.5 %). D = 20 and above: R4 fails (-44 %). SL100/SL160/none worse on R1 or R4 (D=5/SL100 fails R1 by 16 %).
Dropping R1 alone: feasible (D=5, SL60, R=20, 3-scenario sum 645.6). Dropping R4 alone: feasible (D=10/SL60/R=30, D=20/SL60 R=60, D=20/SL100 R=60; the cheapest sum would be D=20/SL60: 167.6+255.6+207.6 = 630.8; D=10/SL60 gives 637.4). R2, R3, R5 are not part of the conflict. Dropping any single other requirement does not help.

## 12. Standby generator (operations)
Cheapest: TL (load-bank test) with condition monitoring. Admissible interval: 788.0 h <= tau <= 1376.8 h (32.8 to 57.4 days); cost decreases with tau, so choose the upper limit 1376.7 h (rounded down): annual cost = 8760/1376.78*1.6 + 2.2 = 12.38 kEUR/year. Minimum worst-case U of TL+monitoring = 2.182e-3 (R1 limit 2.25e-3, margin 3 %); TL without monitoring min U = 2.295e-3 (infeasible by 2 %); TS (+monitoring) min 2.316e-3, TF 2.94e-3 (infeasible).

## What was NOT checked / caveats
- All checks are by enumeration of corners/fine scans, not symbolic proof. For P6 the T-dependence of x_N and y1 was scanned (7 and 61 points), not proved monotone; P10 and P12 worst cases use range ends under the stated monotonic dependence; P3 assumes the worst-case cell temperature is the cold end including the heater rise of 9 K (smallest rise).
- P7 depth uses brentq roots on the stated balance; storms are evaluated at range corners (C, Cd, i), monotone.
- P2 conductor temperature uses the highest running current of the motor on that feeder and T_amb = 38 in every situation (stated in the text).
