# s04 problem: register-to-register timing with min/max delays and clock skew

## Source
- URL: https://cseweb.ucsd.edu/classes/sp17/cse140-a/slides/lec10timing.pdf
- "CSE 140: Components and Design Techniques for Digital Systems, Lecture 10: Sequential Networks: Timing and Retiming",
  CK Cheng, Dept. of Computer Science and Engineering, UC San Diego, spring 2017 (lecture slides, slides 34-44,
  "Timing Analysis: Example", "Fix Hold Time Violation", "Timing Analysis with Clock Skew", "Retiming").
- Read via the PDF text (pdftotext). The numbers are the usual textbook ones (they match the Harris & Harris style
  example), but I only checked this lecture PDF.

## The problem, my words
Two registers R1 -> combinational block -> R2 on a common clock. The block is a small gate network with four
inputs; its LONGEST path passes through three gates in series, its SHORTEST path through one gate. The lecture gives
each timing parameter as a min and a max (all in ps):
- clock-to-Q of the register: contamination (min) 30, propagation (max) 50
- delay of one gate: contamination (min) 25, propagation (max) 35
- register setup time 60, hold time 70 (single values)
- clock skew between the two registers: 50 (worst case; the slides take the capture clock EARLIER for setup, LATER
  for hold)

Questions asked and answered in the slides:
1. Smallest clock period (largest frequency) with no skew.
2. Does hold hold with no skew?
3. After adding one buffer (a second gate) on the short path, does hold hold?
4. Smallest clock period with a 50 ps skew.
5. With the buffer and a 50 ps skew, does hold hold?

## Published answers
1. Tc >= 50 + 105 + 60 = 215 ps, fc = 4.65 GHz.
2. Violated: 30 + 25 = 55 is not greater than 70.
3. Satisfied: 30 + 50 = 80 > 70.
4. Tc >= 265 ps, fc = 3.77 GHz.
5. Violated: 80 is not greater than 70 + 50 = 120 (the slide writes the question mark, the later "retiming" slide
   implies it is violated; the slide with the check leaves the verdict to the reader).

The slides do NOT state the largest tolerable skew; it follows from the same formula: 30 + 50 > 70 + skew, i.e. skew < 10 ps.

## Assumed / left open by the source
- The source gives min and max but no distribution: I take every parameter anywhere in [min, max] independently
  (each gate is a separate quantity, so the 3-gate path is not forced to have all three at the max). This is a
  superset of the slides' single corner and gives the same worst case.
- Skew: the slides give one number (50) and say which direction is the worst for each check. I model the skew as
  one quantity sk in [-50, 50] (capture clock lag minus launch clock lag) and let the stand find the worst sign.
  This is my reading of "worst case".
- Strict ">" in the hold rule: the stand's requirements are ">=" (a bound met exactly counts as met). I used
  slack >= 0. No quantity in the numbers lands exactly on the boundary except the derived skew limit (10 ps).
- The slides' register setup/hold values are single numbers; I kept them exact. No tolerances were added by me.
