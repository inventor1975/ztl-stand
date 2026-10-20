# k01 PROBLEM: worst-case output error of an adjustable regulator (reference + feedback divider)

## Source
- Texas Instruments Application Report SNVA112A (AN-1378), "Method for Calculating Output Voltage Tolerances in
  Adjustable Regulators", July 2005, revised May 2013. https://www.ti.com/lit/pdf/snva112 (read as PDF, free).
  (Author not named in the document; it is a TI/National Semiconductor application note.)

## The problem, in my words
An adjustable linear regulator has a reference Vref (nominal 1.275 V in the tables) and two feedback resistors, so that
Vout = Vref * (R1 + R2) / R1 (the note's Eq. 1, valid for both common topologies). The note asks: if Vref is off by
+-dVref and each resistor by +-dR, all independent and all at once at their worst ends, how far can Vout be from its
nominal value? It tabulates this "worst case" error for six target outputs (1.8, 2.5, 3.3, 5, 12, 15 V), four Vref
tolerances (+-0.5, 1, 2, 5 %) and three resistor tolerances (0.5, 1, 5 %). A second part (Eq. 20, 21, Table 5)
adds the adjust-pin current: Vout gets an extra Iadj*R2, and the largest R2 for which this adds no more than a
chosen share (0.1, 0.5, 1 %) of Vout is Vout*share/Iadj.

## Numbers used (all from the source)
- Vref nominal 1.275 V (Table 1 and 4 captions). Vref tolerance +-0.5/1/2/5 %, resistor tolerance 0.5/1/5 % (table axes).
- 3.3 V block of Table 1 (the one I used), worst-case error of Vout in %, rows dVref, columns resistor tolerance 0.5/1/5 %:
  - +-0.5: 1.13 / 1.77 / 7.14
  - +-1.0: 1.64 / 2.28 / 7.67
  - +-2.0: 2.64 / 3.29 / 8.73
  - +-5.0: 2.64 (apparent misprint: it repeats the +-2.0 cell, the neighbours are 5.4-5.8 for other blocks) / 6.33 / 11.93
- Other blocks (1.8, 2.5, 5, 12, 15 V) of Table 1 were used only for the hand cross-check in hand.py.
- Table 5 (Iadj 0.01 / 0.1 / 1 / 10 uA; 0.1 / 0.5 / 1 % extra error): 3.3 V column, e.g. 0.1 %: 330 k / 33 k / 3.3 k / 330 ohm;
  0.5 % at 1 uA: 16.5 k; 1 % at 1 uA: 33 k.

## PUBLISHED ANSWER (what it claims)
- Table 1: the maximum deviation of Vout from nominal ("worst case always occurs on the maximum side"), in percent,
  with R1 and R2 set so nominal Vout is the target. The text's own example: Vout 3.3 V, dVref +-1 %, dR +-1 % -> 2.28 %.
- Table 5: "for no more than X % additional error select R2 less than" the tabulated values (Eq. 21: R2max = X/100 * Vout / Iadj).

## What I had to assume (source left it open)
- The note does not print R1, R2 for the 3.3 V block. I took the ideal pair giving exactly 3.3 V: R2/R1 = 3.3/1.275 - 1 = 27/17,
  so R1 = 17 kohm, R2 = 27 kohm (only the ratio matters). The note (Sec. 3) says real E-series values would add a static
  offset; the table evidently excludes it.
- Each of Vref, R1, R2 varies independently inside its own +-box (the note's Eq. 2, 3 do the same).
- The 12-design question (which Vref grade x resistor grade keeps Vout inside +-3 %) and the ordinal "cost" are MINE;
  the +-3 % window and the cost ranks are not in the source. They are not tolerances.
