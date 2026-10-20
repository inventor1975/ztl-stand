# k02 problem: worst-case error budget of an amplifier + 12-bit ADC chain

## Source
- Page: "Error Budget Analysis - Basic Amplifier and ADC" (Op Amp, 12-Bit ADC, +5V Ref), eCircuit Center.
  URL: https://ecircuitcenter.com/EBA/ADC/amp-ADC-1.html (figures on the same page: offset_err.JPG, gain_err.JPG,
  amp-adc-1-sch1.JPG; a companion spreadsheet amp-ref-ADC-1-EBA.xlsx is linked there, NOT downloaded).
- Kind: a tutorial page of an independent engineering-education site (copyright 2002 per the footer), not a manufacturer
  application note. It is a "tolerance stack-up" worked example.

## The problem, in my words
A source (500 ohm) drives a non-inverting op-amp stage with R1 = 10 kohm to ground and R2 = 40 kohm in feedback
(gain 1 + R2/R1 = 5). The op-amp output feeds a 12-bit ADC (4095 = 2^12 - 1 levels) whose reference is 5.0 V. The
full-scale input is 1 V, so 1 V -> 5 V -> code 4095. The designer wants the error referred to the input (RTI) to stay
within two budgets: offset error at most 5 mV, gain error at most 1 % of the reading. Everything may go to its limit
in either direction, and the temperature may move 30 C from the 25 C ambient. Totals are the plain sum of absolute values
(worst-case analysis, WCA). The page asks: does the design meet the budgets?

### Numbers the source gives
- Rs = 500 ohm, R1 = 10 k, R2 = 40 k, Vin = 1 V, Vo = 5 V, Vref = 5.0 V, N = 12 bits, Ta = 25 C, dT = 30 C.
- Resistors R1, R2: 0.1 % tolerance, 100 ppm/C each.
- Vref: 0.5 % tolerance, 50 ppm/C.
- ADC gain: 2 LSB initial, 0.08 LSB/C drift (page converts: 0.05 % and 20 ppm/C -> 0.06 % over 30 C).
- ADC offset: 3 LSB initial; drift 0.05 LSB/C in the page's table (0.04 LSB/C in its worked offset paragraph and in
  its sheet picture, 48.8 uV/C); resolution error 0.5 LSB; INL 1 LSB.
- Op-amp: the page's prose table says voff 1 mV (+10 uV/C), Ib 5 nA, Ios 5 nA (+1 nA/C each); the page's SPREADSHEET
  PICTURE (offset_err.JPG, the calculation actually behind the total) uses voff 0.1 mV (+10 uV/C), Ibn = Ibp = 10 nA
  (+1 nA/C each), sensitivities S(voff) = 5, S(ibn) = -R2 = -40000 ohm, S(ibp) = Rs*Ka = 2500 ohm.
- ADC LSB: 5/4095 = 1.22 mV; Ka (amp gain) = 5; Kadc = 4095/5 = 819 per volt.

## PUBLISHED ANSWER
1. Offset error, worst case, referred to input: 2.2 mV; budget 5 mV -> PASS.
2. Gain error, worst case: 1.4 %; budget 1.0 % -> FAIL. Its terms (picture gain_err.JPG): R2 0.08 + 0.24 %, R1 0.08 +
   0.24 % (sensitivity 0.8 each), ADC gain 0.05 + 0.06 %, Vref 0.5 + 0.15 % (sensitivity -1) = 1.40 %.
3. The page then invites the reader to try tighter resistor tempco (50/25/10 ppm/C) and Vref tolerance 0.1 %; it
   states no result for these.
The sums are FIRST-ORDER (sensitivity x error, added in absolute value). The page does not claim they are the exact
extremes of the real, nonlinear transfer function.

## What the source left open / I had to assume
- Offset: two inconsistent op-amp parameter sets (prose table vs sheet picture) and two ADC offset drifts (0.05 vs 0.04
  LSB/C). I found that sheet op-amp values + 0.05 LSB/C add (my reading of the picture's digits) to 2.205 mV, i.e. the
  published 2.2 mV; with 0.04 they add to 2.13 mV. So the main brick uses: sheet op-amp values, ADC drift 0.05.
  A second brick uses the prose table's op-amp values (voff 1 mV; Ibn/Ibp = Ib +- Ios/2 = 7.5 nA, drift (1 + 0.5) nA/C
  = 45 nA over 30 C, my reading of the table).
- The 30 C change: read as dT in [-30, +30] C with every tempco free in sign up to its stated size (equivalent to the
  source's "all errors either polarity"); each drift is therefore a box +-(tempco x 30).
- The page splits offset (judged at zero input) and gain (judged at the reading); I judge them at vin = 0 V and vin =
  1 V, and also the page's combined form "offset + gain x reading" at 1 V (15 mV = 5 mV + 1 % of 1 V).
