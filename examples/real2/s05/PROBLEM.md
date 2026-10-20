# s05 problem: NTC thermistor + parallel resistor on a battery-charger TS pin, worst-case trip temperatures

## Source
- Texas Instruments application note SPVA059 (dated June 2026), "Designing the TS Pin Network for Battery Chargers with
  Current-Based Battery NTC Temperature Sensing", author Alec Lehman. Freely readable PDF: https://www.ti.com/lit/pdf/SPVA059
- Used: Example 1 (section 3.1, BQ25190, 10 C to 45 C) and its worst-case analysis (section 4.2), equations 1, 4, 10, 11, 14-16.
  Underlying part values come from the BQ25190 charger datasheet, as quoted by the app note.

## The problem in my own words
A battery charger biases an NTC thermistor on its TS pin with a constant current. The pin voltage is compared with a HOT
threshold and a COLD threshold; charging stops when the NTC is hotter than ~45 C or colder than ~10 C. The designer puts a
resistor RP in parallel with the NTC (and a series resistor RS, here a plain short, 0 ohm) so the thresholds land at 45 C and 10 C.
The question the source then asks: with all device and component tolerances, between which temperatures can the HOT trip
and the COLD trip actually occur?

Numbers (all taken from the source):
- NTC: 10 kohm at 25 C, beta(25/85C) = 3435 K, beta equation R(T) = R25 * exp(beta * (1/T - 1/298.15)), T in kelvin.
  The source gives NO tolerance for R25 or beta in this example.
- RS = 0 ohm (short). RP = 12 kohm, tolerance 1 %.
- TS bias current IBIAS: 76.8 uA min, 80 uA typ, 83.2 uA max.
- HOT threshold VHOT: 0.272 V min, 0.276 typ, 0.280 V max.
- COLD threshold VCOLD: 0.576 V min, 0.580 typ, 0.584 V max.
- TS pin voltage: VTS = IBIAS * (RP || (RS + RNTC)). Charging is suspended HOT when VTS falls to VHOT, COLD when VTS rises to VCOLD.
- Targets: THOT = 45 C, TCOLD = 10 C.

## PUBLISHED ANSWER
Worst-case NTC resistance at the trip points (eq. 10, 11 of the source):
- HOT: RNTC max = 5,260 ohm, RNTC min = 4,477 ohm.
- COLD: RNTC max = 21,127 ohm, RNTC min = 16,146 ohm.
Converted to temperature with the beta equation (eq. 14):
- HOT entry temperature: lowest 42 C, highest 48 C (typical 45 C).
- COLD entry temperature: lowest 6 C, highest 14 C (typical 10 C).
(Whole degrees; the same table appears as the charger-GUI calculator output.) The source claims these are the extremes of
the trip temperatures over all the listed tolerances.

## What I had to assume (the source left it open)
- The NTC itself is taken at nominal R25 and beta (the example lists no NTC tolerance; the published RNTC numbers and
  temperatures are reproduced by hand with nominal values, see report.md).
- The source works inversely (from a threshold to the NTC resistance). I state the same thing forward, as a
  guarantee over a range of NTC temperatures: "for every NTC temperature from a up to <end>, the pin voltage is below the lowest
  HOT threshold under every tolerance" and find the smallest such a, and the three mirror statements. Mathematically
  equivalent, but not literally the source's computation.
- Rounding of the source's whole degrees is not stated (appears to round outward).
- No tolerances added by me.
