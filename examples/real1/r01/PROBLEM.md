# r01 problem: output accuracy of an adjustable regulator with 1% divider resistors

## Source
- Maxwell Robertson, "Effect of Resistor Tolerances on Power Supply Accuracy", Texas Instruments
  Application Report SLVA423, June 2010. https://www.ti.com/lit/slva423 (free PDF, read directly).
- Worked example is Section 4 (TPS79901 low-dropout regulator).

## Problem (my words)
An adjustable regulator compares a feedback divider against an internal reference.
Vo = (1 + R1/R2) * Vref. The part used has Vref = 1.193 V (typical) and a rated output
accuracy of +-1%. The divider resistors are both +-1%.
Two rails are designed with the same part:
- Rail A: nominal 3.3 V (divider ratio Vref/Vo = 0.362).
- Rail B: nominal 1.8 V (ratio 0.663).
Question: what is the worst-case total output accuracy of each rail?
The note's method: resistor-caused error (relative) = +-2T*(1 - Vref/Vo) with T = 0.01
(it drops the factors 1+-T in the denominator, "valid for T <= 1%"), then ADDS the device's rated accuracy.

## Published answer
- Rail A: resistor error +-1.28%; device +-1%; total accuracy +-2.28%.
- Rail B: resistor error +-0.674% (printed 0.00674); device +-1%; total +-1.674%.
- Claim: these are the worst-case total accuracies (resistor error "added to" device accuracy), and the
  accuracy improves as Vo approaches Vref.

## Numbers used in the brick
- Vref = 1.193 V +-1% (my reading of "rated accuracy +-1%" as a 1% tolerance on the reference).
- R1, R2 each +-1%, independent.
- Nominal R1/R2 = Vo/Vref - 1 (1.766136 for 3.3 V; 0.508801 for 1.8 V), i.e. the ideal ratio that gives exactly the
  nominal rail. R2 = 10 kOhm, R1 = 10 kOhm * ratio.

## Assumptions I had to make (source silent)
1. Absolute resistor values are not given: only the ratio matters; I chose R2 = 10 kOhm and non-standard R1
   (17661.357921 and 5088.013412 ohm) so the nominal rail is exactly 3.300 / 1.800 V. A real design would pick
   E96 values and have a nominal offset the note ignores.
2. "Device accuracy +-1%" is modelled as Vref +-1% (relative), independent of the resistors. In reality the
   datasheet accuracy also covers load/line/temperature; the note treats it as one additive 1%.
3. Resistor temperature coefficient, ageing, error-amp input current: ignored (note itself ignores them in the
   example, Section 5 only warns).
4. The note says "total = sum"; the true worst case of the product (1+e_ref)(1+e_div) is slightly larger than the
   sum. I did not assume which one holds: that is exactly what the brick tests.
