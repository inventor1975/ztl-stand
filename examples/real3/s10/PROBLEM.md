# s10 PROBLEM: choosing the current-limit resistor of a USB power switch (TI TPS25221)

## Source
- Texas Instruments, datasheet "TPS25221" (SLVSDT3D, Jan 2018, rev. Dec 2019), https://www.ti.com/lit/ds/symlink/tps25221.pdf
  (also the HTML viewer, https://www.ti.com/document-viewer/ja-jp/lit/html/JAJSEL2D/37-JAJSEL2D).
- Parts used: sec 7.3 (recommended RILIM range), sec 9.5.1 eq.(1) (current-limit curves), sec 10.2.1.1-10.2.1.2.3
  (design requirements, two worked selections, the resistor-tolerance step and Table 3), electrical-characteristics IOS rows.
- Kind: manufacturer datasheet design example. Published answer is TI's own arithmetic, very probably produced by the same curves.

## The problem, my words
A power switch limits its output current to a threshold IOS set by one resistor RILIM (kohm) from the ILIM pin to ground.
The guaranteed spread of IOS (temperature and process) is given as two curves in RILIM:
  IOS_min = 56850 / RILIM^1.033  mA,   IOS_max = 52640 / RILIM^0.97  mA   (RILIM in kohm, valid 20..210 kohm).
(A nominal curve 55960 / RILIM^1.004 also exists; not needed.) The equations do NOT include the resistor's own tolerance.

Two design questions in the datasheet (supply 5 V):
- A: current limiting must never start below 1000 mA, i.e. IOS_min >= 1000 mA. Pick a 1% resistor.
- B: current limiting must always start below 500 mA, i.e. IOS_max <= 500 mA. Pick a 1% resistor.
Then sec 10.2.1.2.3 says: account for the resistor tolerance by evaluating the curves at the resistor's low and high bound
(assumed 1% resistors), and Table 3 lists 17 nominal-limit rows with the resulting IOS_min / IOS_nom / IOS_max.

## Published answer
- A (resistor treated as exact): ideal RILIM = 50 kohm; "closest 1% resistor less than" it = 49.9 kohm; then IOS_max = 1186 mA.
  Claim: this sets the minimum threshold at 1 A.
- B (resistor treated as exact): ideal RILIM = 121.6 kohm; closest 1% resistor greater = 124 kohm; then IOS_min = 391 mA.
  Claim: this sets the maximum threshold at 500 mA.
- Sec 10.2.1.2.3 / Table 3: for each row the 1% low/high resistor bounds are put into the curves. Examples (I give three of 17):
  nominal 1000 mA: 54.9 kohm (54.4 .. 55.4) -> 898 / 1003 / 1092 mA;  500 mA: 110 (108.9 .. 111.1) -> 438 / 499 / 556;
  275 mA: 200 (198 .. 202) -> 236 / 274 / 312. (min / nom / max.) The text does not redo A and B with the tolerance.
- Electrical-characteristics table (used only as a side check): IOS over -40..125 C at RILIM = 20 / 30 / 80 / 210 kohm is
  2560..2880 / 1700..1945 / 610..790 / 210..370 mA.

## What I had to assume (source left open)
- 1% = exactly +-1% of the nominal value (source: "assuming 1% resistor values"); Table 3 shows the bounds rounded to 0.1 kohm.
- The 1% resistor is taken from the E96 series (all resistors in the datasheet's examples are E96 values), range 20..210 kohm
  (the recommended range, sec 7.3). Nothing else was added: no tolerance of mine anywhere.
- The datasheet writes the coefficients with a unit "V" (a typo-like unit); I treat 56850 and 52640 as mA with RILIM in kohm,
  which reproduces the published 1186, 391 and every Table 3 row to +-1..4 mA.
