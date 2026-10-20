# n02 problem: how much continuous current can a power MOSFET really carry, thermally?

## Source
- DigiKey TechForum, "A Thermal Management Example (Part 2: When Datasheets Attack)", author rick_1976, 2021-03-31.
  https://forum.digikey.com/t/a-thermal-management-example-part-2-when-datasheets-attack/13252
- Part 1 (the thermal pieces: pad, heat sink): https://forum.digikey.com/t/a-thermal-management-example-part-one/13243
- The numbers in the source come from three vendor documents quoted as screenshots: the IRL3713 datasheet (International
  Rectifier, 2013-06-21, page 1 thermal table), the Bergquist Sil-Pad 900S table (part BER183-ND), the Aavid heat-sink
  chart (HS278-ND / 530614).

## The problem, in my words
A 30 V MOSFET (IRL3713, TO-220, or D2PAK) must run at a steady current ID. Its junction must stay under a temperature
limit Tj_max. The heat is P = ID^2 * RDS(on), and it flows through a series chain to the air: junction-to-case, case-to-
heat-sink interface, heat sink to air. What is the largest ID for each of five practical set-ups (ambient 40 C)?

Numbers the source uses (its Figure 11 table):

| id | set-up | Tj_max C | RthJC | interface | sink-air | RDS(on) at Tj_max |
|---|---|---|---|---|---|---|
| s2 | forced air (500 ft/min), greased | 175 | 0.45 | 0.5 | 7 | 4.9 mohm |
| s3 | forced air, electrically insulating pad (50 psi) | 175 | 0.45 | 2.9 | 7 | 4.9 mohm |
| s4 | same, lower limit | 150 | 0.45 | 2.9 | 7 | 4.5 mohm |
| s5 | natural convection | 150 | 0.45 | 2.9 | 19 | 4.5 mohm |
| s6 | D2PAK on a PCB, one lumped RthJA | 150 | (total) 40 | | | 4.5 mohm |

(units: C/W for resistances.) RDS(on) at Tj_max = datasheet maximum 3.0 mohm (25 C, 10 V) times a temperature factor read
from the datasheet's normalized curve (about 1.5 at 150 C; 4.9 mohm at 175 C is the source's back-calculation).

## PUBLISHED ANSWER
Maximum continuous drain current ID, per Figure 11 of the source (all with the numbers above):
s2 58.9 A (P 17.0 W), s3 51.6 A (13.0 W), s4 48.6 A (10.6 W), s5 33.1 A (4.9 W), s6 24.7 A (2.8 W).
The source's claim: these are far below the datasheet headline of 260 A (23 %, 20 %, 19 %, 13 %, 10 % of it), which
only holds with the case held at 25 C (an impossible 333 W removal). It does not claim a tolerance band; each figure
is the limit at the stated (max) values.

## What the source left open / what I assumed
- RDS(on)(T): taken as the source's own numbers (4.9 and 4.5 mohm); held at the value at Tj_max for all currents below
  (conservative below the limit, exact at the limit).
- The heat-sink "7 C/W" is "a bit under 7" read from a chart; natural convection 19 C/W is the source's table value
  (read from a power-dependent curve; I hold it constant).
- Pad value 2.9 C/W is the Sil-Pad table (TO-220 test) at 50 psi: 10 psi 3.96, 25 psi 3.41, 50 psi 2.90, 100 psi 2.53,
  200 psi 2.32. Clamp pressure of the real assembly is not given beyond "50 psi, about 12 lb".
- Ambient 40 C: a design assumption of the source ("a figure around 40"), taken as exact.
