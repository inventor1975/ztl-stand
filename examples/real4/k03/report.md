# k03 report: LT1083-5CP on a heat sink, two junction limits (datasheet thermal example)

## SOURCE
Linear Technology / Analog Devices datasheet "LT1083/LT1084/LT1085 Fixed" (code 1083ffd), Applications Information
(thermal example), Absolute Maximum Ratings, Electrical Characteristics. Read at
https://www.logosfoundation.org/instrum_gwr/zi/1083ffd.pdf (a copy; the analog.com URL timed out). A manufacturer
datasheet: trustworthy for its table values. The printed ARITHMETIC of the example is NOT fully trustworthy: the control
section figure is wrong for the numbers printed next to it (see below). Details: PROBLEM.md.

## WHERE THE UNCERTAINTY COMES FROM
- VOUT in [4.9, 5.1] V: Electrical Characteristics, row Output Voltage, LT1083/4/5-5, "0 <= IOUT <= IFULLLOAD,
  6.5 V <= VIN <= 20 V": MIN 4.900, MAX 5.100.
- VIN in [6.5, 9] V: 9 V is "VIN(max continuous)" in the thermal example; 6.5 V is the lower VIN of the same VOUT row
  (and "VIN >= 6.5 V" on the typical application). The lower end is a bound of validity, not a stated tolerance.
- Everything else (IOUT 6 A, TA 75 C, sink 1 C/W, case-to-sink 0.2 C/W, junction-to-case 0.5 and 1.6 C/W, limits 125
  and 150 C) is a single number, taken exact. Two uncertain quantities in all. Added by me: none (so no run
  "without them" is needed).

## PUBLISHED ANSWER vs STAND
| | published (nominal VIN 9, VOUT 5, PD 24 W) | stand, same nominal point (brick_nominal) | stand, with the datasheet windows (brick) |
|---|---|---|---|
| control TJ | 118 C (< 125) | 115.8 C | [89.28, 116.82] C |
| power transistor TJ | 142 C (< 150) | 142.2 C | [98.52, 143.88] C |
| verdict | both pass | EARNED | EARNED (max PD = 24.6 W at VIN 9, VOUT 4.9) |

- Verdict (PASS for both sections): AGREE.
- The printed number 118 C: DISAGREE with the stand. Hand check (python): 75 + 24*(1 + 0.2 + 0.5) = 115.8; 118.2 needs
  0.6 C/W, which is the K package's control figure (other copies of the datasheet print the example for the K package
  with 0.6). The stand is right; the printed 118 is a stale number in this revision (it passes either way). The power
  figure 142 matches 142.2.
- Extra questions the source does not ask, hand-checked: largest sink resistance for both limits with the windows:
  min(75/24.6 - 1.8, 50/24.6 - 0.7) = 1.24878 (power transistor binds); largest ambient at 1 C/W: 150 - 24.6*2.8 =
  81.12 C. Stand: find Rhs proved 1.2487, beyond 1.2488 REFUTED; find Ta proved 81.12, beyond 81.13 REFUTED; continuous
  sink 1.24878 with the lower bound proved within 5e-7. All AGREE with the hand values. The published answer does not
  cover these (NOT COMPARABLE with it), but they cross-check each other.
- System form (components, bands in P every 5 W): EARNED, Tj_c <= 117.5, Tj_p <= 145 C (flat: 116.82 / 143.88). Largest
  ambient 80 C (flat 81.12 C), with the stand saying OPEN beyond 80.01 (a system cannot refute). The hull of the 20..25 W
  band (25 W instead of 24.6 W) accounts for the difference exactly: 150 - 25*2.8 = 80. Consistent, sound, looser.

## EXPRESSED FAITHFULLY
Flat brick (brick.json): the dissipation law, both series thermal paths, both junction limits, VIN and VOUT windows,
units checked. brick_nominal.json is the example's point. A find list for the largest sink resistance and the largest
ambient (brick_find.json, each with the other at the example's value). brick_cont.json: the sink as a continuous
choice 0..5 C/W. brick_choice.json: part from the datasheet's table (LT1083CP, LT1083CK, LT1084CP, LT1085CK) with a
continuous sink. system_s5.json / system_s1.json: REG, HS, TIM, DIE components and a connect list.

## APPROXIMATED
- Junction-to-case figures read as exact (the source gives one number; column label unverified). A real tolerance is
  not stated anywhere I read; nobody checks this.
- VIN lower bound 6.5 V is a validity bound rather than a stated range; irrelevant for the maximum (PD grows with VIN).
- brick_cont: "cheapest sink = largest R" is my assumption. The ZTL proof covers the optimum of -R, i.e. exactly the
  max R; it does not cover any cost.
- brick_choice: only commercial grades (a continuous slot needs numeric bounds, so the device's own limit could not be
  a bound); the K package's case-to-sink 0.2 C/W is my assumption. LT1084/LT1085 never appear as designs: the `where`
  on rated current removed them (design-space filtering, not a judged result). The stand reported only one design (CP);
  the K package ties at the same bound and is not shown.
- System form: the chain is split into per-device temperature rises driven by one power P (the interface needs
  one input per component for bands to mean anything); only ranges of P travel, bands every 5 W or 1 W. The upper
  bounds are looser than the flat (145 vs 143.88 C) by the band hull. Checked by the stand's own sound-but-wider
  rule; I compared against the flat brick.
- Heat sink was NOT a catalog of real parts (the source gives none); it is the example's 1 C/W, or searched.

## COULD NOT EXPRESS
- A component with a CONTINUOUS parameter inside it (BRICKS.md says not yet): so the sink resistance as a
  tuned parameter of a heat-sink component was not possible; the system `find` can only search a system given
  (ambient), not the sink.
- The continuous catalog together with a device-dependent bound (`DEV.Tc` as the limit): BRICK ERROR "continuous
  choices need numeric bounds (version 1)". Grades M (150/200 C limits) therefore left out.
- The 3-input structure "Tj = Ta + P*sum" as an affine contract between components: the rises are P-driven
  (different dimension), so no affine contract applied; ranges only.
- Dropout, current-limit and thermal-shutdown behaviour (the source has them; the example does not use them).

## TOOL OUTPUT
Work mode: all EARNED, run times 0.06-1.0 s each; none killed. Commands exactly as given (heavy -m 3G --cores 1).
- brick.json: EARNED, Tj_c [89.28, 116.82], Tj_p [98.52, 143.88], "ZTL, exact at the corners". --dev: EARNED, "every
  corner of the tolerance box recomputed exactly and inside; exact ranges equal".
- brick_nominal.json: EARNED, 579/5 = 115.8 and 711/5 = 142.2; --dev agrees.
- brick_find.json: EARNED; Rhs proved 12487/10000, beyond 1561/1250 "REFUTED: ... holds a concrete failing point";
  Ta proved 2028/25 = 81.12, beyond 81.13 REFUTED. 1 s. --dev: same proved values (1.4 s).
- brick_cont.json: EARNED, R = 1.24878, lower_bound -1.24878, gap 5e-7, "optimal": false (nonzero gap). --dev agrees.
- brick_choice.json: EARNED, same R, design LT1083CP; combinations 2. --dev agrees.
- system_s5 / system_s1: EARNED, Tj_p <= 145, Tj_c <= 117.5; --dev agrees. system_find_s5 and _s1: proved 80,
  "beyond_is": OPEN (80.01). Tuned bands (system_t.json, edges at 8.4 and 24.6 W, the flat brick's own PD range): OPEN
  ("fails at a point of the components' guaranteed ranges... not a refutation") and find 66 C - worse, not better: band
  edges that touch the arriving range pull in the neighbouring bands (REG's range [8.4, 24.6] touches three P bands).
  Shown only as a trap; the s5/s1 results are the honest ones.
- Work vs --dev: no disagreement in any run; no STAND FAULT, no errors apart from the one BRICK ERROR above.

## DOC GAPS
- "The bands the arriving range touches are used": not said that a band merely sharing an edge with the arriving range
  counts as touched (closed bands). That decided system_t (OPEN instead of EARNED).
- How bands work with several inputs of one component is not described; I used one input per component.
- The continuous section does not say that a requirement bound may not be a `slot.field` (section 6 says it may);
  found only by the BRICK ERROR.
- `find` list: each item needs its own quantities and laws if the two searched quantities must not move together; my
  workaround doubled the laws. Section 7a says this only for different scenarios.
- The `where` condition `DEV.Imax >= Iout` worked on a given without tolerance; not stated for plain givens
  outside computed, though "given quantities without tolerance" implies it.
