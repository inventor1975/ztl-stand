# s09 problem: maximum attenuation of a 20.5 km optical link vs. optical card power budget

## Source
- Cisco, "Calculate the Maximum Attenuation for Optical Fiber Links", document ID 27042 (support doc, ONS 15454 section).
  https://www.cisco.com/c/en/us/support/docs/optical-networking/ons-15454-sonet-multiservice-provisioning-platform-mspp/27042-max-att-27042.pdf
- Read as a PDF via text extraction. The document has a field-link figure that I could NOT see (images are not in the text);
  the link layout (20.5 km, 2 connectors, 4 splices) is taken from the numbers in the worked formulas.

## The problem in my words
A single-mode link of 20.5 km has 2 optical connectors (the ends) and 4 splices (joints). Total attenuation of a cable section is
TA = n*C + c*J + L*a + M, with n connectors at C dB each, c splices at J dB each, L km at a dB/km, plus a system margin M
(patch cords, bends, unforeseen events) of "around 3 dB".
The document gives, for 1310 nm, a table with three rows (best / normal / worst conditions):
- fibre attenuation a: min 0.3, average 0.38, max 0.5 dB/km
- per connector C: min 0.4, average 0.6, max 1 dB
- per joint J: min 0.02, average 0.1, max 0.2 dB
(1550 nm table also given: a 0.17/0.22/0.4, C 0.2/0.35/0.7, J 0.01/0.05/0.1; not used in the brick.)
The optical card (assumed in the example) at 1310 nm: transmit power -3 to 0 dBm; receiver (sensitivity) -20 to -27 dBm.
Hence the power budget (Tx - Rx sensitivity) lies between 17 dB (worst card: Tx -3, sens -20) and 27 dB (best card).
Question: does the link work with the worst card under the worst field conditions?

## Published answer
- 1310 nm normal: TA = 12.39 dB; 1310 nm worst: TA = 16.05 dB (1550 nm: 8.41 normal, 13 worst).
- Card power budget 17 .. 27 dB. Worst card 17 dB vs worst link 16.05 dB: the link "works without any problem"
  (author adds: measure the link in the field). Implied margin of the worst/worst case: 17 - 16.05 = 0.95 dB.
I re-did the arithmetic by hand: 2*1+4*0.2+20.5*0.5+3 = 16.05; 2*0.4+4*0.02+20.5*0.3+3 = 10.03 (the source does not print this best-case number).

## What the source left open (my assumptions)
- Which of the min/avg/max values vary independently: I treat all as independent ranges (the source does not say). Avg row is not used (it lies inside the range).
- "Rx = -20 to -27 dBm" read as the receiver sensitivity varying between cards from -27 (best) to -20 (worst), as the source's own 17..27 dB budget implies.
- The 3 dB margin M is a fixed 3 dB (source: "around 3 dB", no tolerance given). I added NO tolerance of my own.
- The link layout (n=2, c=4, L=20.5 km) from the formulas, not from the figure.
- dBm values are written with unit dB in the brick (the stand has no dBm unit).
