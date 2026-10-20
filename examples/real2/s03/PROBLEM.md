# s03 PROBLEM

## Source
- eCircuit Center, "Error Budget Analysis: Basic Amplifier and ADC" (op amp, 12-bit ADC, +5 V reference):
  https://www.ecircuitcenter.com/EBA/ADC/amp-ADC-1.html (2002; author site eCircuit Center, no named author)
- Companion page for the op-amp bias-current formulas (sensitivity Rs*K-R2 for ib, (Rs*K+R2)/2 for iboff):
  https://www.ecircuitcenter.com/EBA/amp1/amp_advanced1.html
- Not downloaded: the Excel files the pages link to.

## The problem in my words
A non-inverting op amp (gain K = 1+R2/R1, R1 = 10 kohm, R2 = 40 kohm, so K = 5, source resistance Rs = 500 ohm)
feeds a 12-bit ADC with a 5.0 V reference (LSB = 5/4095 V, about 1.22 mV). Ambient 25 C, the temperature may move by
up to 30 C. Every error is +- (either polarity). All errors are referred to the input (RTI) and added as a worst
case (sum of absolute values). Two budgets: offset error at most 5 mV; gain error at most 1 % of reading.

Offset sources (initial value, drift): U1 input offset voltage (table says 1 mV, 10 uV/C); U1 bias current ib
(5 nA, 1 nA/C); U1 offset current iboff (5 nA, 1 nA/C); ADC offset (3 LSB, 0.05 LSB/C in the table, 0.04 LSB/C
= 49 uV/C in the worked line); ADC resolution error (1/2 LSB); ADC INL (1 LSB).
Gain sources (tolerance, tempco): R1 (0.1 %, 100 ppm/C); R2 (0.1 %, 100 ppm/C); ADC gain (2 LSB = 0.05 %,
0.08 LSB/C = 20 ppm/C); Vref (0.5 %, 50 ppm/C). Sensitivities: S = +0.8 for R2, -0.8 for R1, +1 for ADC gain, -1
for Vref. (Op-amp open-loop gain is not included on this page.)

## PUBLISHED ANSWER
- Offset: worst case total 2.2 mV, below the 5 mV budget: PASS.
- Gain: worst case total 1.4 %, above the 1.0 % budget: FAIL. (The page then suggests: better tempcos on R1/R2,
  Vref tolerance 0.1 % instead of 0.5 %; no numerical answer is given for those.)
- Gain contributions in the page's own lines: R2 0.08 % + 0.24 %; R1 0.08 % + 0.24 %; ADC 0.05 % + 0.06 %;
  Vref 0.5 % + 0.15 %.
- The published figures are first-order sums of |sensitivity x error|, not the exact worst case of the nonlinear
  gain formula.

## What I had to assume / source inconsistencies
1. The table says U1 offset voltage 1 mV, but the published 2.2 mV total only comes out with 0.1 mV (the companion
   page uses 0.1 mV). I checked: with 1 mV the sum is 3.10 mV. Base brick uses 0.1 mV; a variant uses 1 mV.
2. ADC offset drift: table 0.05 LSB/C, worked line 0.04 LSB/C; 2.2 mV needs 0.04 (0.05 gives 2.28 mV). Base: 0.04.
3. The budget "5 mV" is compared by the source with the RTI total; I do the same.
4. Gain errors taken as the source's rounded percentages (ADC gain 0.05 %, 20 ppm/C), not 2/4095 exactly.
5. Temperature change fixed at the stated 30 C (tempcos are +- so the sign of the change does not matter).
6. Resistor values in the OFFSET formulas are nominal (the source does that too).
7. Nothing was added by me: no invented tolerances.
