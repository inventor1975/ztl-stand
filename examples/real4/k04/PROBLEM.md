# k04 problem: smallest output inductor of a 3 A buck converter (TPS54331 design example)

## Source
- Texas Instruments, TPS54331 datasheet "3-A, 28-V Input, Step Down DC-DC Converter With Eco-mode", SLVS839H (rev. Oct 2023),
  https://www.ti.com/lit/ds/symlink/tps54331.pdf
  - section 8.2 (Typical application: Table 8-1 design parameters, 8.2.2.3 divider, 8.2.2.5.1 inductor selection with Eq. 8-11, 8.2.2.6 output capacitors)
  - section 6.5 Electrical Characteristics (voltage reference 0.772 / 0.8 / 0.828 V)
  - section 6.6 Switching Characteristics (switching frequency 456 / 570 / 684 kHz)
- Kind of source: manufacturer datasheet design example. Read as PDF text only (no login, nothing downloaded beyond the fetched PDF).

## The problem in my own words
A 3 A step-down converter runs from an input between 7 V and 28 V and makes about 3.3 V. The output voltage is set by a
divider (10.2 kohm over 3.24 kohm) on a reference of 0.8 V. The designer wants the smallest output inductance that keeps the
inductor ripple current to a chosen fraction of the load current. The datasheet's rule: the ripple current peak-to-peak is
KIND times the load current, with KIND = 0.3 for low-ESR (ceramic) output capacitors. The ripple is largest at the highest input voltage.
The chosen inductor must also stay under its own saturation current (peak) and RMS current rating.

Numbers in the source:
- Vin range 7 to 28 V; Vout 3.3 V (3.31 V with the real divider); Iout 3 A; fsw 570 kHz (typical; min 456, max 684 kHz in 6.6);
  output ripple limit 30 mV; KIND = 0.3.
- Inductor chosen: Sumida CDRH103-6R8, 6.8 uH, saturation current 3.84 A, RMS rating 3.6 A.
- Output capacitors: two 47 uF ceramic, max ESR 2 mohm each.

Equations used (datasheet numbering):
- Eq. 8: Lmin = Vout*(Vinmax - Vout) / (Vinmax * KIND * Iout * fsw)
- Eq. 9: ILPP = Vout*(Vinmax - Vout) / (Vinmax * L * fsw * 0.8)   (the 0.8 is not explained in the text)
- Eq. 10: ILrms = sqrt(Iout^2 + ILPP^2/12);  Eq. 11: ILpk = Iout + ILPP/2
- Eq. 5: Vout = Vref*(R5/R6 + 1)

## PUBLISHED ANSWER
- Minimum inductor value 5.7 uH (Eq. 8 at Vin 28 V, Vout 3.3 V, fsw 570 kHz, KIND 0.3); a larger value, 6.8 uH, is chosen.
- For 6.8 uH: peak inductor current 3.47 A, RMS 3.01 A, both under the part's 3.84 A and 3.6 A.
- It claims a point calculation at nominal values. It does NOT state a worst case over the reference or frequency spread.
- Also published: output-capacitor numbers (max ESR 43 mohm required, RMS ripple current 161 mA) -- I could not reproduce these from the datasheet's own Eq. 13-15 (see report), so I do not use them as a comparison.

## What I had to assume (source left open)
- The question I ask the stand: the SMALLEST nominal inductance L such that the requirement holds for EVERY value of the source's own spreads: Vin 7-28 V (Table 8-1), Vref 0.772-0.828 V (6.5), fsw 456-684 kHz (6.6). Three limits, each searched separately: ripple ratio <= 0.3, peak <= 3.84 A, RMS <= 3.6 A.
- The 0.8 in Eq. 9: I read it as the inductor's inductance falling to 80 % of nominal (my reading; the datasheet does not say). Handled as kL in [0.8, 1], and a run WITHOUT it.
- R5 and R6 are taken as exact (the source gives no resistor tolerance); I added no tolerance to them.
- Output capacitors: Eq. 13 of the source has a (D-0.5) term that is negative for D < 0.5 (here D <= 0.47), giving a negative ripple; so the chain's capacitor stage uses the standard form ILPP*(1/(8 fsw C) + ESR), my substitution. Capacitance 94 uF with no tolerance (the source only says the actual value "may be less").
