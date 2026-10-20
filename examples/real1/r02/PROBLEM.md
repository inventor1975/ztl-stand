# r02 PROBLEM: package and heatsink choice for a 5 V linear regulator (worst-case junction temperature)

## Source
- Kieran O'Malley, "Thermal Management for Linear Regulators", Smart Regulator Packaging Application Note, ON Semiconductor (Cherry Semiconductor lineage), Feb 1999 / (c) 2000.
- Read at https://www.thierry-lequeu.fr/data/SR006AN.pdf (a mirror of the PDF; free to read). Another listing of the same text: https://www.allaboutcircuits.com/technical-articles/thermal-design-with-linear-voltage-regulators/ (403 to my fetcher, not used).

## The problem, in my words
A 5 V-class linear regulator (CS8121) must never let its junction exceed 150 C. The note's method: worst-case power
P = (Vin_max - Vout_min)*Iout_max + Vin_max*IQ, then the largest allowed junction-to-ambient resistance
RthJA = (150 - Ta_max)/P, then compare with the packages' RthJA.

Example 1 (choose a package): Vin_max 10 V, Vout_min 4.8 V, Iout_max 200 mA, Ta_max 85 C,
IQ = 2.25 mA read from a curve (that is the 25 C value; the 125 C value is 1.7 mA; the note takes the larger).
Packages (RthJA / RthJC): TO220 50 / 3.5 C/W; 14-lead SO narrow 125 / 30; 8-lead PDIP 100 / 52.

Example 2 (package + heatsink): same part, Vin_max raised to 12 V, the rest as in example 1.
A heatsink is then needed on the TO220. RthJA = RthJC + RthCS + RthSA. The AAVID 504222 low-profile heatsink curve is
used (the note says: about 20 C rise at 2 W) with a thermal pad of RthCS = 0.021 C/W.

## PUBLISHED ANSWER
- Ex.1: PD = 1.0625 W; max RthJA = 61.2 C/W; only the TO220 (50 C/W) qualifies; SO14 (125) and PDIP (100) do not.
- Ex.2: PD = 1.83 W; max RthJA = 35.5 C/W; RthCS+RthSA <= 35.5 - 3.5 = 32 C/W; with the pad, RthSA ~ 32 C/W is
  allowed; the AAVID 504222 (curve well below the allowed 58.56 C rise at 1.83 W) "will work". Bare TO220 (50) does not suffice.
- (Dual-output and SMD copper-foil examples in the note: not used.)

## Inconsistencies in the source (found while checking)
- Ex.2 states Iout_max = 200 mA, but its PD arithmetic uses 250 mA: 7.2 V * 0.25 A + 12*2.25 mA = 1.827 W (=1.83 W).
  With the stated 200 mA the sum is 1.467 W and the limit is RthJA 44.3 C/W, not 35.5.
- The dual-output example multiplies IQ by 12 V though its Vin_max is 10 V.

## Assumed (source silent)
- Lower ends of all ranges (Vin 7 V, Vout top 5.2 V, Iout 0, Ta -40 C): irrelevant to the worst case but a box needs two ends. IQ taken as the range 1.7 .. 2.25 mA (the two curve readings).
- The heatsink: I read "20 C rise at 2 W" as 10 C/W, plus 3.5 (RthJC) + 0.021 (pad) = 13.521 C/W, with +-20 % tolerance (my invention).
- Prices (to order the designs): invented labels.
- Two "boundary probe" items (RthJA 44 and 45 C/W) are my invention, to test where the stand's pass/fail line sits relative to hand arithmetic.
- Datasheet thermal resistances treated as exact (the note does so).
