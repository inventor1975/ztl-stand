# k03 problem: LT1083-5CP on a heat sink, two junctions

## Source
- Linear Technology (now Analog Devices), datasheet "LT1083/LT1084/LT1085 Fixed, 3A, 5A, 7.5A Low Dropout Positive
  Fixed Regulators", revision code 1083ffd. Sections: Absolute Maximum Ratings, Electrical Characteristics
  (Output Voltage row for LT1083/4/5-5, Thermal Resistance row), Applications Information (the thermal example).
- Read as a PDF copy: https://www.logosfoundation.org/instrum_gwr/zi/1083ffd.pdf (the manufacturer's own copy is on
  analog.com, but it timed out for me). Search snippets of other copies of the same datasheet (alldatasheet.com,
  LT1085 page) quote the same example for the K package, with 0.6 C/W instead of 0.5.

## The problem, in my words
A 5 V fixed regulator in the plastic TO-3P package (LT1083-5CP, commercial grade) delivers 6 A while its input is at
most 9 V. Ambient is 75 C. It sits on a heat sink of 1 C/W, with 0.2 C/W between case and heat sink (thermal compound).
The chip has two heat sources with different paths: a control section (junction-to-case 0.5 C/W) and the power
transistor (1.6 C/W), and each has its own maximum junction temperature: 125 C and 150 C (commercial grade). The
datasheet says: compute both, because a single averaged figure can hide an over-temperature.

Numbers used:
- dissipation PD = (VIN - VOUT) * IOUT = (9 - 5) * 6 = 24 W
- TJ = TA + PD * (heat sink + case-to-sink + junction-to-case)
- Rth junction-to-case (table "Thermal Resistance, Control Circuitry/Power Transistor"): LT1083 P package 0.5 / 1.6 C/W;
  K package 0.6 / 1.6; LT1084 P 0.65 / 2.3; LT1085 T 0.7 / 3.0 etc.
- Operating junction range, C grades: control section 0..125 C, power transistor 0..150 C (M grades 150 / 200 C).
- VOUT of the 5 V part for 0 <= IOUT <= IFULLLOAD and 6.5 V <= VIN <= 20 V: MIN 4.900, MAX 5.100 V
  (at 25 C, IOUT = 0, VIN = 8 V: 4.950..5.050).
- Rated currents: LT1083 7.5 A, LT1084 5 A, LT1085 3 A. Dropout at full load: 1.3 typ / 1.5 max V.

## Published answer
Control section: TJ = 75 + 24*(1 + 0.2 + 0.5) = "118 C", below 125 C. Power transistor: 75 + 24*(1 + 0.2 + 1.6) = "142 C",
below 150 C. Conclusion printed: both are below their limits, reliable operation. (A claim of PASS at the nominal point
VIN = 9 V, VOUT = 5 V; no tolerances in the example.)

## What the source left open / what I assumed
- The example is a nominal point. The uncertainty I use is only what the datasheet itself states: the VOUT window
  4.9..5.1 V, and VIN between 6.5 V (the lower end of the VIN range of that VOUT row and of the 5 V application) and
  9 V (the example's maximum). Nothing was invented. The lower VIN end does not matter for the maximum temperature.
- The junction-to-case figures are single numbers in the table; the text extraction put them under the right-hand
  column (MAX?), but I could not verify the column label. I treated them as exact values (as the example does). If they
  are typical values, the worst-case claim would be weaker (not tested; no source for a tolerance).
- Ambient 75 C, IOUT 6 A, heat sink 1 C/W, case-to-sink 0.2 C/W are taken as exact, as in the example.
- The K package (and the other devices in brick_choice.json) have no case-to-sink figure in the source; I used 0.2
  as my assumption (labelled in the brick).
- "Cheapest sink" = "largest sink resistance" is my assumption, not the source's (the source has no sink price).
