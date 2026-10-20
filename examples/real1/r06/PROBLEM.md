# r06 problem: hypochlorite dilution strength and metering-pump feed rate

## Source
- California State Water Resources Control Board, Division of Drinking Water, "Example Calculations of Chlorine
  Dosage" (February 2018; same content at three URLs):
  - https://waterboards.ca.gov/drinking_water/certlic/drinkingwater/documents/publicwatersystems/naocl_examples_final.pdf
  - https://www.waterboards.ca.gov/drinking_water/programs/districts/docs/sonoma/naocl_examples.pdf
  - https://www.waterboards.ca.gov/drinking_water/programs/districts/docs/mendocino/naoci_example.pdf
- A regulator's training handout for small water-system operators. Freely readable PDF, no login.

## The problem in my own words
A small water system dilutes commercial bleach (12.5 % NaOCl by weight, specific gravity 1.2) by adding a measured
volume of it to 10 US gallons of water; the operator picks the volume from a table (4 oz ... 384 oz, 33 rows used
here). A metering pump injects the dilute solution into the line to give a chlorine dose, expressed as mg/L of Cl2,
at a line flow in gpm. The handout gives:
- the strength of the dilute solution (% w/v NaOCl) for each volume of bleach (Table 1);
- the pump feed rate in mL/min needed for a dose of 1 mg/L as Cl2, for each strength and for flows of 10 to 60 gpm
  (Table 2);
- worked examples: 20 oz of bleach in 10 gal gives 0.2307 % w/v; at 40 gpm and a target of 1.5 mg/L as Cl2 the feed
  rate is 103 mL/min (read from Table 2: 68.9 mL/min per mg/L, times 1.5).

## Numbers used
- 12.5 % w/w NaOCl, SG 1.2, 10 gal of water, bleach volume V_b = oz x 29.5735295625 mL (1 US gal = 3.785411784 L).
- Cl2 / NaOCl conversion factor 0.9525 (the handout's Eq. 1A and 2A use 9525 = 10000 x 0.9525, i.e.
  70.906 / 74.442).
- Dose D: 1.0 to 1.5 mg/L as Cl2. Plant flow Q: 10 to 60 gpm (= 37.854 to 227.125 L/min).
- Dilute strength  s = V_b x SG x 0.125 / (V_water + V_b)   (volumes taken additive); feed rate
  Q_f = D x Q / (0.9525 x s).

## PUBLISHED ANSWER
- Table 1: 20 oz -> 0.2307 % w/v (and 33 other rows).
- Table 2: feed rate for 1 mg/L, e.g. 20 oz (0.2307 %): 17.2 mL/min at 10 gpm ... 103.4 mL/min at 60 gpm; 68.9 mL/min
  at 40 gpm. 36 oz (0.4100 %): 9.7 ... 58.2; 40 oz (0.45471 %): 8.7 ... 52.4.
- Example 2: 40 gpm, 0.2307 %, 1.5 mg/L -> 103 mL/min (= 68.9 x 1.5).
- Eq. 1C ("feed mL/min = dose x gpm x 0.3785 / %NaOCl") and its Example 1: 35 gpm, 0.7 %, 1.3 mg/L -> 25 mL/min.
  NOTE (my own arithmetic): Eq. 1C has no 0.9525 factor, so it gives 98.4 mL/min for Example 2, not 103; the two
  parts of the handout disagree by 1/0.9525 = 5 %. Eq. 1A/2A and Table 2 do carry the factor.
- The handout makes NO design claim (no pump, no choice of row). The choice problem below is mine.

## Choice question put to the stand (my addition, not in the handout)
Which table rows (strengths) let one metering pump cover the whole operating box (Q 10 to 60 gpm, D 1.0 to 1.5 mg/L)
for every bleach strength and density in the tolerance, with the pump's range 8 to 100 mL/min?

## ASSUMED because the source left it open
1. The pump (8 to 100 mL/min) is invented; the handout has no pump.
2. Tolerances: bleach strength +-4 % relative (12.0 to 13.0 % w/w), SG +-2 %. The handout treats both as exact.
3. Dose range 1.0 to 1.5 mg/L and flow range 10 to 60 gpm: taken from the handout's table columns/examples,
   but the handout does not say they are the operating envelope.
4. Volumes additive (no contraction on mixing); reproduces Table 1 to 4 digits (my hand check: 20 oz -> 0.2308 %).
5. Which of Eq. 1C or Table 2 is right: I take Table 2 / Eq. 1A (with the 0.9525 factor), because the dose is "as
   Cl2" and the strength is "as NaOCl"; a variant with the factor removed is in the report.
