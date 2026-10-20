# n01 report: worst-case offset of a 4-resistor Wheatstone bridge (Analog Dialogue)

## SOURCE
- Analog Devices, Analog Dialogue vol. 48 no. 1 (2014), "How to Stay Out of Deep Water when Designing with Bridge
  Sensors"; read via the eeNews Europe republication
  https://www.eenewseurope.com/en/how-to-stay-out-of-trouble-when-designing-with-bridge-sensors/ (the Analog page
  itself timed out for me). Manufacturer technical article, freely readable.
- Trust: the claim is one sentence plus an equation (an image I could not see; a search summary gave
  VOS = TOL x VEX / 100). The number (5 mV) is simple and I verified it by hand (see below): it is exact for the
  worst corner. Author not confirmed. Very small example: one number, no part choice.

## WHERE THE UNCERTAINTY COMES FROM
| quantity | range | place in source |
|---|---|---|
| R1..R4 (four bridge elements) | each nominal x (1 +- 0.001) | sentence right after Eq. 1: each of the four elements has 0.1 % |
| VEX | 5 V, exact | same sentence: excitation 5 V (no tolerance given) |
| nominal R | 10 kohm | ADDED by me (source gives none); also ran 1 kohm |
| Rm (detector between mid-points) | 1 Gohm exact (also 10 Mohm) | ADDED by me, needed to get a current |
| tol 1 % variant | +-0.01 | ADDED by me (extends the formula; not in the source) |
Nothing else is invented. Without Rm there is no branch current, so the brick cannot be run "without my additions";
the effect of the addition is measured by changing Rm (1 Gohm vs 10 Mohm) and R (10 k vs 1 k).

## PUBLISHED ANSWER vs STAND
Published: offset <= 5 mV for 0.1 %, 5 V; stated as a reached maximum.
Stand (work mode), requirement |I(b5)| <= (offset bound)/Rm, in uA:

| brick | bound | stand verdict | stand's proved range of I5 | exact worst (my python) |
|---|---|---|---|---|
| brick.json (R 10k, Rm 1G, 0.1 %) | 5 mV/Rm = 5e-6 uA | EARNED | +-4.99995000073e-6 uA | 4.99995000055e-6 uA (= 4.99995 mV across Rm) |
| brick_tight.json | 4.999 mV/Rm | REFUTED at R1=9990,R2=10010,R3=10010,R4=9990 | same | same |
| brick_R1k.json (R 1k) | 5 mV/Rm | EARNED | +-4.99999500033e-6 uA | 4.99999500001e-6 uA |
| brick_Rm10M.json | 5 mV/Rm | EARNED | +-4.9950050e-4 uA | 4.99500499999e-4 uA |
| brick_Rm10M_tight.json | 4.99 mV/Rm | REFUTED (same corner) | same | same |
| brick_tol1pct.json (1 %) | 50 mV/Rm | EARNED | +-4.99995000551e-5 uA | 4.99995005e-5 uA |

Verdict: AGREE. The published bound holds (EARNED) and is tight: a bound just below it (4.999 mV, 4.99 mV) is
REFUTED at the corner where R1,R4 are low and R2,R3 are high (the opposite-arm pairing the formula implies).
The small gap below 5 mV (4.99995 mV) is the detector loading by Rm, which the source's "unloaded" offset does not
have: exact value is 5 mV x Rm/(Rm+R) = 5 mV x 1e9/(1e9+1e4). So strictly the comparison is "published unloaded bound
vs loaded current": APPROXIMATELY COMPARABLE (to 1e-5 relative at Rm=1 Gohm), not an exact reproduction of the
unloaded voltage. My hand check (exact fractions over all 16 corners, handcheck.py): the stand's proved ranges
contain it and are 3e-11 relative wider. Unloaded worst case by hand = t x VEX = 5.000 mV exactly (also for 1 %: 50 mV).
Random interior sampling gives lower values (4.91 mV), as it should: extremes are at corners.

## EXPRESSED FAITHFULLY
- Four elements with independent +-0.1 % boxes; 5 V source; the 4-resistor bridge topology; the worst-case search
  over all of the box (the verdict is for every value, proved by the network certificate).

## APPROXIMATED
- Unloaded output voltage -> current in a 1 Gohm detector (assumption, mine). Error 1e-5 relative, known exactly and
  confirmed by hand; checked by me, not by the stand. If a reader wants Rm = infinity, it cannot be written.
- The bound in the requirement is the published voltage divided by Rm (my arithmetic, exact in the brick).
- Nominal R = 10 kohm (source silent; result nearly independent, 1 kohm gives the same within 1e-6).
- Tolerance read as independent per element (source wording); no correlation between elements.

## COULD NOT EXPRESS
- The OUTPUT VOLTAGE of an unloaded bridge: "network" accepts requirements on branch currents only, so no direct
  "VOS <= 5 mV" requirement.
- Detector at infinite impedance (see above).
- "find" of the limiting tolerance (largest TOL for which the offset stays below a bound): the network branches take
  given quantities by name, and find replaces a given's range with a search range; a tolerance cannot be
  searched in a network brick (I did not try a trick via laws: network bricks take no laws). So the converse
  question "what tolerance keeps the offset at 5 mV" was answered only by two or three points, not by a find.
- The article's gain-400 arithmetic (+-2 V, 80 % of the swing): not a network quantity.

## TOOL OUTPUT
- All six bricks in work mode: verdicts as in the table, each run 0.16-0.18 s, within heavy -m 3G --cores 1, no kill,
  no errors. Output files: out_*.txt.
- --dev on brick.json: EARNED, "agrees: every one of 16 corners solved exactly lies in the proved range; the corners'
  exact extremes [-500000/100000999999, 500000/100000999999]" (= 4.99995e-6 uA). --dev was run only on the main brick.
- Work and --dev agree.
- Network metadata: nodes 4, branches 5, free branches 4; the certificate needed 2 rounds.

## DOC GAPS
- BRICKS.md 7c says requirements are on branch currents only but does not say how to bring a voltage requirement in
  (e.g. via a large detector resistor); I had to invent it.
- Not stated whether a very large resistance (1e9 vs 1e4 ohm, 5 orders) is within the numerical range of the
  certificate search; it worked here, but the doc gives no hint.
- Not stated whether find can search a tolerance (it cannot, apparently), nor how to ask "largest tolerance" in a
  network.
- "proved_range" is printed with approximate decimals ("~... an exact fraction of 41 digits"); the exact fraction
  is not shown, so I compared at 12 digits only.
