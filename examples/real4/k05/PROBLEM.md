# k05 problem: gearhead ratio for an induction-motor belt conveyor (Oriental Motor worked example)

## Sources
1. Oriental Motor, "Technical Reference - Motor Sizing Calculations" (9-page PDF, section "Belt and Pulley Using Standard AC Motors", printed page F-8).
   https://www.orientalmotor.com/products/pdfs/F_TecRef/TecMtrSiz.pdf  (manufacturer technical reference; undated in the copy read)
2. Oriental Motor General Catalog 2000-2001, page A-53, induction motors 40 W, 3.54 in. frame (5IK40GN-AWU / -AUL ...).
   https://www.orientalmotor.com/products/pdfs/2000-2001/5IK40GN-AUL.pdf  (manufacturer catalog data sheet)
   The catalog is an older edition than the tech reference; I used it only for data the tech reference leaves out.

## The problem in my words
A horizontal belt conveyor is driven by a single-phase 115 V, 60 Hz, 4-pole induction motor (40 W) through a parallel-shaft gearhead.
Belt plus work weigh 30 lb, sliding friction coefficient 0.3, drive drum diameter 4 in (the text says "radius" but every number
in it uses 4 in as the DIAMETER), belt/roller efficiency 0.9. Required belt speed: 7 in/s, tolerance +-10 % (so 6.3 ... 7.7 in/s).
Choose the gear ratio and check that the motor can start the load.

Numbers the source gives:
- Drum speed needed: 7*60/(pi*4) = 33.4 r/min (+-10 %: 30.1 ... 36.7).
- Rated speed of a 4-pole motor at 60 Hz: "1450 to 1550 r/min" (stated as a range).
- Gear ratio range from these: 1450/36.7 = 39.5 up to 1550/30.1 = 51.5. Ratio 50 is picked.
- Friction force 0.3*30 lb = 9 lb (144 oz); load torque at the gearhead shaft 144*4/(2*0.9) = 320 oz-in.
- Gearhead efficiency 0.66 (for 50:1; an other example in the same document uses 0.81 for 9:1).
- Torque at the motor shaft 320/(50*0.66) = 9.7 oz-in; times a safety factor 2 (for supply-voltage fluctuation) = 19.4 oz-in
  needed as STARTING torque. Motor 5IK40GN-AWU (rated torque 36.1 oz-in) with gearhead 5GN50KA.
- Because the load (9.7 oz-in) is far below the rated torque, the motor runs near its no-load speed, about 1740 r/min.
  Final check with that speed: V = 1740*pi*4/(60*50) = 7.3 in/s, "meets the specification".

Catalog data (source 2) used besides:
- Starting torque of 5IK40GN-AWU: 27.8 oz-in; rated torque 36.1 oz-in; rated speed 1500 r/min (115 V, 60 Hz).
- Gear ratios offered for the 5GN..KA gearhead: 3, 3.6, 5, 6, 7.5, 9, 12.5, 15, 18, 25, 30, 36, 50, 60, 75, 90, 100, 120, 150, 180.
- Permissible torque per ratio (lb-in): 5.5, 6.6, 9.1, 11, 14, 16, 23, 27, 33, 41, 49, 59, 74, 87, 87 ... 87 (same order as the ratios).
- A footnote: displayed gearhead speed = synchronous speed (60 Hz: 1800 r/min) / ratio, and the actual speed is 2 to 20 % lower,
  depending on the size of the load.

## PUBLISHED ANSWER (what exactly it claims)
- Gear ratio 50 (gearhead 5GN50KA on motor 5IK40GN-AWU).
- Belt speed with that ratio at the motor's no-load speed 1740 r/min: 7.3 in/s, inside 7 +-10 %.
- Starting torque need 19.4 oz-in <= motor's starting torque (the text gives no number; the catalog says 27.8 oz-in).
- Load inertia check passes (2061 oz-in^2 against 10000 oz-in^2 permitted) -- not used here.
It does NOT claim that ratio 50 works for every motor speed between 1450 and 1550 r/min; its own ratio range 39.5...51.5 pairs the
slowest motor with the slowest drum and the fastest motor with the fastest drum (an "exists" reading).

## What the source left open / what I had to assume
- Speed of the motor at the actual load: the source says "about 1740 r/min" (no-load) and "1450-1550" (rated). Nothing between.
  My assumption: a straight line in torque from the no-load speed to the rated speed (listed in report.md).
- Gearhead efficiency for ratios other than 50 (and 9): not given; I use the range 0.66 ... 0.81 (the two published values) for every ratio.
- 1740 is "approximately": taken exact, no tolerance added.
- Supply-voltage fluctuation: only covered by the factor 2; no voltage range is stated in the sources.
- Drum "radius" read as diameter (see above). Weight 30 lb read as force 30 lbf.
