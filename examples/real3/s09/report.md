# s09 report: maximum attenuation of a 20.5 km 1310 nm link vs. the worst optical card (Cisco 27042)

## SOURCE
- https://www.cisco.com/c/en/us/support/docs/optical-networking/ons-15454-sonet-multiservice-provisioning-platform-mspp/27042-max-att-27042.pdf
  Cisco support document "Calculate the Maximum Attenuation for Optical Fiber Links" (ID 27042).
- Kind: vendor support/how-to note with a worked example. Trust: the arithmetic is right (I recomputed all four TA values and the 17 dB budget).
  But it is a rule-of-thumb note: its table rows are generic planning values (not from a named fibre/connector datasheet), the 3 dB margin is "around 3 dB",
  the card figures are "assume certain values", and it ends by saying the link must be measured. The link figure was not readable in text.

## WHERE THE UNCERTAINTY COMES FROM
All ranges come from the source; I added none.
| quantity | range | place in the source |
|---|---|---|
| a, fibre loss at 1310 nm | 0.3 .. 0.5 dB/km | Table 1, column "Attenuation/Km", Min and Max rows |
| C, per connector | 0.4 .. 1 dB | Table 1, column "Attenuation/optical connector" |
| J, per splice | 0.02 .. 0.2 dB | Table 1, column "Attenuation/joint" |
| Tx, card transmit power | -3 .. 0 dBm | text after the formulas, "Tx = -3 dBm to 0dBm at 1310nm" |
| Sens, card receiver | -27 .. -20 dBm | same place, "Rx = -20 dBm to -27 dBm at 1310nm" |
Fixed (no tolerance given): L = 20.5 km, n = 2, c = 4 (from the worked formulas), M = 3 dB.
Added by me: none, so there is no "without them" run.

## PUBLISHED ANSWER vs STAND
| | published | stand |
|---|---|---|
| worst link loss TA | 16.05 dB | TA range [10.03, 16.05] (judge_log) |
| worst power budget | 17 dB (best 27) | Tx - Sens, folded into Mg |
| verdict | worst card 17 > worst link 16.05: works | EARNED for all values of the box |
| implied margin | 17 - 16.05 = 0.95 dB | guaranteed Mg = [0.95, 16.97] dB |
Status: AGREE (the same claim, the same worst-case number 0.95; the stand adds the best case 16.97 = 27 - 10.03, which the source does not print).
My python check: worst TA 16.05, best 10.03, margin 0.95, best margin 16.97 - all identical.
Extra (not in the source): `brick_find.json` asks the largest length L that still works: stand proved 22.4 km (22.41 km refuted, witness margin -0.005 dB);
hand: (17 - 2 - 0.8 - 3)/0.5 = 22.4 km. AGREE (NOT a published number, only my own hand check).
Honest note: with independent interval ranges the worst case is just the corner of every range, so this is an easy test of the tool; the published answer is also a corner calculation.

## EXPRESSED FAITHFULLY
- The formula TA = n*C + c*J + L*a + M as one law; the budget Tx - Sens as the second law; all five ranges as given ranges; requirement margin >= 0.
- Units checked ("every law's dimensions agree").

## APPROXIMATED
- dBm written as dB (no dBm unit): safe here, since Tx - Sens is a difference of two levels and the result is a dB margin; the stand cannot check dBm vs dB.
- "Works" = received power >= worst-case sensitivity number (margin >= 0). The source states it as budget > loss; same thing.
- Independence of the five ranges is my reading; the source is silent. In the real world a worst card with worst fibre is the pessimistic case, which is what was asked.
- Link layout n=2, c=4, L=20.5 inferred from the printed arithmetic (the figure was unreadable). The checker of this: me, by reproducing 12.39 / 16.05 / 8.41 / 13.
- M = 3 dB treated as exact, though the source says "around".

## COULD NOT EXPRESS
- The 1550 nm case was not run (the source gives card data only at 1310 nm); the average/normal rows are not in the box (they are inside it, so no loss for a proof).
- A receiver overload limit (too much power on the best card with the shortest, best link) - the source gives no Rx max, only sensitivity; the stand's range of Mg tops out at 16.97 dB with no way to ask whether that is above overload. Not a stand limit; a gap in the source.
- The distinction between dBm and dB; the field measurement the source asks for.

## TOOL OUTPUT
- brick.json, work mode: verdict EARNED, `Mg` guaranteed [19/20, 1697/100], how "ZTL, exact at the corners"; no errors; 0 s (the stand's own timer); judge ZTL 2a24683.
- brick.json, --dev: EARNED, checker: "every corner of the tolerance box recomputed exactly and inside; exact ranges equal; definitions bounded by the checker's own interval arithmetic". Work and dev agree. (Shell `time` showed 0.08 s; it measured the heavy wrapper, not necessarily the Python, so I do not rely on it.)
- brick_find.json (work): EARNED, proved L = 112/5 (22.4 km), beyond 22.41 km REFUTED. Not run in --dev.
- Nothing was killed by the limit (heavy -m 3G --cores 1, timeout 900).
- Output files: out_dev.txt, out_find.txt.

## DOC GAPS
- BRICKS.md has no dBm/dB-level convention (dB is in the unit list; dBm is not mentioned) - I guessed `dB` for levels.
- It does not say if a "requirement with a bound" `Tx - Sens - TA >= 0` is better written as a derived margin or as `Prx >= Sens`; I used the margin (it prints the guaranteed margin, useful), but the doc should say that the guaranteed range of the derived quantity is what you compare with a published margin.
- Not stated whether ranges of different givens are independent - from 7a/section 1 I infer yes ("every value inside the box"), but one sentence would help.
- A bare number like `2*C` for a count of connectors is fine as dimensionless; the doc says this only for `2`, `1`, `25` in passing.
