# s05 report: worst-case trip temperatures of an NTC + parallel-resistor network on a charger TS pin (TI SPVA059, example 1)

## SOURCE
- https://www.ti.com/lit/pdf/SPVA059 : Texas Instruments application note SPVA059 (June 2026, A. Lehman), section 3.1 and 4.2.
  Manufacturer app note, freely readable. Trust: moderate-good. The RNTC values (5,260 / 4,477 / 21,127 / 16,146 ohm) I reproduced
  by hand to the ohm. The final temperatures are given only in whole degrees with no stated rounding rule. The NTC is
  implicitly at nominal R25/beta although the method lists their tolerances. The TS pin tolerances come from the charger
  datasheet as quoted by the note, which I did not open.

## WHERE THE UNCERTAINTY COMES FROM
| quantity | range | place in the source |
|---|---|---|
| IBIAS (Ib) | 76.8 .. 83.2 uA | sec 4.2 step 1, bullet "IBIAS: 76.8 (min), 80 (typ), 83.2 (max)" |
| VHOT | 0.272 .. 0.280 V | sec 4.2 step 1 |
| VCOLD | 0.576 .. 0.584 V | sec 4.2 step 1 |
| RP | 12 kohm +-1 % | sec 3.1 step 4 (E96, 1 % series) and sec 4.2 step 1 ("RS and RP resistor tolerances: 1%") |
| NTC temperature T | a range, searched by `find` | the quantity the answer is about |
| fixed, no tolerance in the example | R25 = 10 kohm, beta = 3435 K, RS = 0 | sec 3.1 steps 3-4 |
Added by me: nothing. (Because I added no tolerance, there is no "without" run to make.)

## PUBLISHED ANSWER vs STAND
Source (whole degrees C): HOT entry 42 .. 48, COLD entry 6 .. 14.
Stand (4 `find` bricks, K converted to C; grid step 0.01 K; my hand calculation in hand.py gives the same, last column):

| claim | stand proved limit (K / C) | stand: one grid step beyond | hand (exact limit) | published |
|---|---|---|---|---|
| HOT surely trips for every T >= a (highest HOT entry) | a = 320.51 K = 47.36 C | 320.50 REFUTED (witness Ib 83.2, RP 12120, VHOT 0.272) | 47.358 C | 48 |
| HOT surely does not trip for T <= a (lowest HOT entry) | a = 315.75 K = 42.60 C | 315.76 REFUTED | 42.607 C | 42 |
| COLD surely trips for T <= a (lowest COLD entry) | a = 279.97 K = 6.82 C | 279.98 REFUTED | 6.823 C | 6 |
| COLD surely does not trip for T >= a (highest COLD entry) | a = 286.25 K = 13.10 C | 286.24 REFUTED | 13.097 C | 14 |

Verdict: AGREE, with a caveat. Every published limit is the stand's limit rounded OUTWARD to whole degrees
(47.36 -> 48, 42.60 -> 42, 6.82 -> 6, 13.10 -> 14); the stand's limits are inside the published ones and lie within 0.9 C of
them. The stand's numbers are sharper (0.01 K) and each carries a proof on one side and a concrete failing point 0.01 K beyond.
It is not an exact match of numbers because the source rounds and the stand does not; the source's rounding rule is not stated,
and "outward" is my inference. Both agree with my hand calculation (the extremes sit at the corners
IBIAS/RP/threshold all adverse, as in the source's eq. 10-11). Nothing disagrees, so no tie-break was needed.

## EXPRESSED FAITHFULLY
- Beta equation `Rn = R25*exp(beta*(1/T - 1/T25))`, `Vts = Ib*RP*Rn/(RP+Rn)` (RS = 0 so RS + RNTC = RNTC), with Ib, RP and the threshold
  taking every value in the source's min/max ranges. T in kelvin (C offset is not handled).
- Thresholds as ranges: min/max exactly as in the source.
- RP as a one-item catalog (12 kohm, 1 %), as the source selects.

## APPROXIMATED
1. Inverse -> forward. The source computes the NTC resistance at the threshold; the brick asks the equivalent forward guarantee
   over a temperature range and bisects on its end (4 bricks, one per limit, because a `find` brick has one search). Safe if
   monotone and I reasoned so (Vts falls with T). The stand does not assume monotonicity on the range; the 0.01 K witness one
   step beyond each limit confirms the bisection stopped at the real edge. Checked by: ZTL, and by me by hand.
2. The threshold range Vth is used as a bound in the requirement (`Vts <= Vth`, `Vts >= Vth`), per BRICKS.md the least favourable end.
   Safe (the three quantities are independent), so no correlation is lost.
3. NTC at nominal R25/beta (as in the example): this is the source's own assumption, not an approximation of mine.
4. "Trip" is the non-strict comparison (Vts <= VHOT, Vts >= VCOLD at equality counts). Limits move by <0.01 K.
5. Search grid 0.01 K; limits are therefore bracketed to 0.01 K, not exact. `Rn` in the judge log is a wide hull
   ("interval reading"); the certificate (64 pieces on the first brick) does the proving.
6. Units: the stand needs absolute temperature in the exp, so T is in K, and I convert to C by hand when comparing.

## COULD NOT EXPRESS
- Several limits in one run (hot and cold, both ends): the `find` takes one quantity and one direction per brick.
- The source's literal output, the RNTC bounds (5,260 ... 16,146 ohm): possible only as additional derived values at the
  corner, not as limits; I verified them with hand.py rather than the stand.
- NTC R25/beta tolerances are not in the example, so not tested (the method in sec 4.1 lists them; not in the numbers).

## TOOL OUTPUT
Command as required (`~/bin/heavy -m 3G --cores 1`, `OPENBLAS_NUM_THREADS=1`, `timeout 900`). No run was killed.
| brick | work mode | --dev |
|---|---|---|
| brick.json (HOT, highest) | EARNED, proved 320.51 K, 3.8 s | EARNED, same, 4.1 s |
| brick_hot_low.json | EARNED, proved 315.75 K, 2.7 s | same, 2.9 s |
| brick_cold_high.json | EARNED, proved 279.97 K, 0.6 s | same, 0.6 s |
| brick_cold_low.json | EARNED, proved 286.25 K, 0.3 s | same, 0.3 s |
Work and --dev agree on every brick; --dev reports the checker recomputed every corner exactly and the failing witnesses in
rational arithmetic; no STAND FAULT, no `certificates_unconfirmed`. The top-level "EARNED" is the find's verdict for the range up to
the proved edge, the "beyond" range is REFUTED, which is what I expected. Outputs: out_*.txt, out_dev_*.txt.
One BRICK ERROR on my first try: `quantities.Ib.range[0]: '76.8/1000000' is not a number (write e.g. "0.01" or "1/3")`
(fixed by using unit uA and "76.8").
Generation script: gen.py; hand check: hand.py.

Naming caution: in the file names, "cold_high" is the brick for the LOWEST cold entry temperature (6.82 C): it asks "trip guaranteed up to a"
and finds the highest a, which is the source's lowest cold entry; the reverse for "cold_low".

## DOC GAPS
- Numbers like "76.8/1000000" are refused (a fraction needs integers); BRICKS.md says only "strings read as exact fractions"; decimal
  fractions must go through a prefix unit or an integer ratio. Worth one line.
- Section 7a does not say what `from`/`to` mean for `smallest` (which end is the shared end) beyond the example for `largest`; I inferred
  [a, to] from the text. It also does not say that the value in the quantity's own `value` field is a placeholder (I put 300).
- It is not stated whether a toleranced given may be a requirement bound AND a tolerance range at once (`Vth` range as bound);
  it worked, as the least favourable end, consistent with section 6.
- Nothing says that division of a derived quantity by a sum containing another derived quantity (`Rn/(RP+Rn)`) is within the
  accepted class; it worked ("interval reading").
