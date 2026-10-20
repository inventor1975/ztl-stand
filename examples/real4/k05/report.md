# k05 report: gearhead ratio for a 115 V induction-motor belt conveyor (belt speed 7 in/s +-10 %)

Files (all in examples/real4/k05/): PROBLEM.md; brick.json (main, flat); system.json + comp_belt/comp_gear/comp_motor.json (same chain as
components); vA..vE (variants, below); out_*.txt (raw outputs, `_work` and `_dev`); gen.py, run.sh, summ.py (scratch).

## SOURCE
Oriental Motor, Technical Reference "Motor Sizing Calculations", belt-conveyor example with a standard AC motor (page F-8):
https://www.orientalmotor.com/products/pdfs/F_TecRef/TecMtrSiz.pdf ; plus the same maker's General Catalog 2000-2001, p. A-53
(https://www.orientalmotor.com/products/pdfs/2000-2001/5IK40GN-AUL.pdf) for the motor's starting torque, the gear-ratio list, the
gearhead torque table and the "speed is 2-20 % below synchronous" footnote. Manufacturer documents, so the arithmetic is reliable
and the numbers are catalog values; but the example is a sales-engineering illustration, the two documents are different editions,
and the example's gear-ratio range uses a loose reading (see below). The final answer is checkable by hand: it is.

## WHERE THE UNCERTAINTY COMES FROM
| quantity | range | place in the source |
|---|---|---|
| belt speed requirement | 7 in/s +-10 % -> [6.3, 7.7] | tech ref, spec list (a requirement window, not data) |
| motor speed at rated torque, Nr | 1450 ... 1550 r/min | tech ref, "Determine the Gear Ratio" (4-pole, 60 Hz) |
| motor no-load speed N0 | 1740 r/min, "approximately" | tech ref, final speed check (taken exact, no tolerance added) |
| gearhead efficiency | 0.66 ... 0.81 | 0.66 in this example (50:1), 0.81 in the ball-screw example of the same document (9:1); the HULL for every ratio is MINE |
| actual-speed shortfall (variant D only) | 2 ... 20 % below 1800 r/min | catalog p. A-53 footnote |
| gear ratio | list of 20 values | catalog p. A-53 |
Added by me (not in either source): the linear speed-torque line between N0 and Nr (main brick only); the efficiency hull for ratios
other than 50 and 9. The runs WITHOUT my line are vB, vC, vD.

## PUBLISHED ANSWER vs STAND
Published: ratio 50 (5GN50KA); belt speed 7.3 in/s at the no-load speed 1740 r/min; start-up torque 19.4 oz-in is enough.

| run | what motor speed it allows | stand verdict | ratio window the stand proves (find) | hand check (python) |
|---|---|---|---|---|
| vE_point1740 (the source's own final check) | 1740 exactly | EARNED, only 5GN50KA; V = 7.2885 in/s | - | 7.2885: AGREE with the source's 7.3 |
| brick.json (main: linear line N0 -> Nr, eta 0.66-0.81) | speed from load | EARNED 5GN50KA; V in [6.9622, 7.1143]; Tstart [15.8, 19.4] oz-in; the other 19 ratios REFUTED | vA: 46.11 ... 55.51 | same numbers (window 46.11 ... 55.51, V range identical to 4 digits) |
| system.json (components, same chain) | same | EARNED 5GN50KA; V in [6.952, 7.121]; 12 cheaper ratios OPEN | - | consistent, wider by 0.01 (ranges only between components) |
| vC_rated (the source's range 1450-1550, all values) | any speed in 1450-1550 | REFUTED, all 20 ratios (50 gives 6.07 ... 6.49 in/s) | 42.16 ... 48.20 | 42.16 ... 48.20: the stand is right |
| vB_envelope (1450 ... 1740, no line) | any speed in the envelope | REFUTED, all 20 ratios (50 gives 6.07 ... 7.29) | 47.33 ... 48.20 | 47.33 ... 48.20 |
| vD_catalog_slip (catalog 2-20 % below 1800) | 1440 ... 1764 | REFUTED, all 20 ratios; find: "even ig = 48 alone fails" | empty (needs i >= 47.98 and i <= 47.87) | confirmed |

Verdict on agreement:
- Published final claim (ratio 50 works, 7.3 in/s, torque OK): AGREE, in the main brick and in the point run.
- Published ratio RANGE 39.5 ... 51.5: DISAGREE with the stand when read as "works for every motor speed in 1450-1550": the proved window is
  42.16 ... 48.20, and 50 is outside it (at the slow end of the range 50 gives 6.07 in/s < 6.3). By hand: i <= 1450*pi*4/(60*6.3) = 48.2 and
  i >= 1550*pi*4/(60*7.7) = 42.16. The stand is right; the source's range is the union over pairings ("some speed"), which is not the same.
  The source rescues ratio 50 by a different argument (the motor is nearly unloaded, so it runs near 1740), which is physically reasonable but is NOT a
  statement the source puts a number on for loads in between. My linear line supplies the number: V in [6.96, 7.11], inside the window.
- So "ratio 50 is right" survives only through the load-dependence of the slip; with the full catalog band (2-20 % whatever the load) NO ratio of the list
  (and no ratio at all) can hold +-10 %: the window needed is 1.2222 wide and the speed spread is 1.2250.
- Torque side: the stand's Tstart range for 50:1 is 15.8 ... 19.4 oz-in against 27.8 oz-in; ratio 30 fails (26.3 ... 32.3 oz-in > 27.8 at low efficiency),
  ratio 36 passes torque but fails speed (V about 9.5 in/s). Matches my hand calculation.
Which one is right where they differ: the stand (hand-checked above in three cases).

## EXPRESSED FAITHFULLY
- Load torque chain: friction force, torque at the drum shaft (/ 2 / belt efficiency), torque at the motor shaft (/ ratio / gear efficiency), factor 2.
- Belt speed from drum diameter, motor speed and ratio; the +-10 % window; units (lbf*in, in/s, rpm; oz-in converted by /16).
- The ratio list and the gearhead's permissible-torque table (catalog), the motor's rated and starting torque (catalog), the rating checks
  "TL <= permissible torque" and "2*TM <= starting torque".
- The source's ranges Nr and the catalog's 2-20 % band as real ranges (variants C, D), and the source's own final point (variant E).

## APPROXIMATED
1. Linear speed-torque line N = N0 - (N0 - Nr)*TM/Tr (main brick, system). MINE. Nobody checks it: the stand takes it as data. Its effect is
   decisive for ratio 50 (variants B/C show 50 fails without it). Safety margin: ratio 50 would fail only if the motor ran below about 1505 r/min at 22-27 % of
   rated torque, which an induction motor does not do, but this is my physical judgement, not a sourced number.
2. Efficiency 0.66 ... 0.81 for every ratio (two published points, hull mine). Checked by the stand as a range; ratio 50 alone (0.66) is a subset, so EARNED stands.
3. N0 = 1740 exact ("approximately" in the source); 60 Hz and 115 V exact; the factor 2 stands for voltage fluctuation, no voltage range modelled.
4. Drum "radius 4 in" read as diameter 4 in (the source's own arithmetic does); weight 30 lb read as force 30 lbf.
5. System version: the chosen ratio travels to the system in the field `cost` (objective = ratio, a workaround); the speed conversion is a system law;
   drum diameter is entered twice (comp_belt.json and system.json); bands on the gear input TL (0, 19.9, 20) and motor input TM (13 bands) are mine,
   finer bands tighten the system range. The system is sound but looser than the flat brick (6.952 ... 7.121 against 6.962 ... 7.114).
6. The ratio is DISCRETE (a catalog list), so no continuous catalog was used for the pick; the continuous ratio appears only in the `find` variants
   (vA-vD *_find.json, `ig` as a given), where the ratio sits in two laws (torque path and speed path) and the stand handled it as one shared quantity.
   Hand check of the window matches to the grid (0.01).

## COULD NOT EXPRESS
- The source's ratio range 39.5 ... 51.5 as such: the stand has only "for every value", not "for some pairing of motor and drum".
- A measured speed-torque curve (the sources give none), so the in-between speed is my line.
- The load-inertia check (source compares 2061 with 10000 oz-in^2): left out (needs the motor's rotor inertia; not needed for the speed question).
- A cheaper-candidate refutation in the system: the system can only say OPEN for the 12 smaller ratios, not REFUTED (`optimal: false`); the flat brick refutes them.
- Supply voltage / frequency tolerance: the sources give none, nothing invented.

## TOOL OUTPUT
All runs: `OPENBLAS_NUM_THREADS=1 timeout 900 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand ...`; each took 0-2 s (my wall timer), no run killed,
no error. Work mode and `--dev` gave the SAME verdicts, the same guaranteed ranges and the same find limits in all 10 bricks; `checked_by` in the
dev files says "ZTL + the independent checker".
- brick.json: `"verdict": "EARNED"`, design 5GN50KA, `"objective": ... "optimal": true, "note": "every cheaper design was refuted"`;
  V ["3110274116426156353583/446737500000000000000 (~6.9622)", "22810231593089497069/3206250000000000000 (~7.1143)"]. `how`: V and Tstart "outside ZTL: ZTL left it
  unbounded (a product of toleranced quantities); interval bound by the stand, every corner checked inside" -- so in the main brick the speed bound is the stand's,
  not ZTL's (the system version says "ZTL, exact at the corners"). 19 other ratios refuted at the nominal point (`failed_at_nominal: 19`).
- system.json: EARNED 5GN50KA, `"optimal": false` (the cheaper combinations are OPEN: ratios 3-9 "a band its input touches has no guarantee" (gear rating),
  12.5 "the range arriving from GR.TM ... leaves the component's assume", 15-30 motor starting-torque band, 36 "the system fails at a point of the components'
  guaranteed ranges, but those ranges enclose ... not a refutation").
- vA/vB/vC finds: EARNED with limits 46.11/55.51, 47.33/48.20, 42.16/48.20; each `beyond` REFUTED with a concrete failing point. vD find: REFUTED, "even ig = 48 alone fails",
  witness etag 0.66, s 0.2, V = 6.28319 in/s.
- A first run printed one "[stand] 1/20 designs" progress line to stderr (merged into out_brick_work.txt by my redirect before I re-ran it).

## DOC GAPS
- BRICKS.md 7d does not say that a component may have NO inputs (`"inputs": {}`); it works.
- A tuned component's slot can be exported only as the objective's `cost`; there is no way to export the chosen item's fields (the ratio), so I made cost = ratio.
  7d says "its field cost" but not that this is the only channel.
- Unit `rpm`: not defined in section 5. By the passing unit check and by hand, 1 rpm = (1/60) s^-1 (a revolution is dimensionless: V = pi*D*N works with no 2*pi); `oz`/`ozf` is
  not a unit, so oz-in had to be converted to lbf*in by hand (/16).
- Bands: not stated whether an arriving point that sits exactly on a band edge touches the neighbouring band. My gear input arrived at 20 with a band [0, 20] (very wide result, [0, 0.606]);
  with edges 0, 19.9, 20 it was tight. Untested for an interior edge.
- `find` result keys: `proved/beyond` are documented, but the per-item entries print `find: largest|smallest` not as keys named `largest`/`smallest` (cosmetic; my summariser first missed them).
- Not clear from 7a how `find` behaves for a quantity that appears in two laws (torque path and speed path); it worked here and matched my own calculation, but the doc does not promise it.
