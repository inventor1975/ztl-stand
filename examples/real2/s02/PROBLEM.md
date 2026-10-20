# s02 problem: M12 8.8 bolt tightened by torque, preload and bolt stress under friction scatter

## Source
- Wuerth Industrie technical portal, "Chapter 6: Dimensioning metric screw assemblies" (a PDF in the DINO
  technical handbook, based on VDI 2230), freely readable:
  https://prueflabor.wuerth-industrie.com/web/media/en/pictures/wuerthindustrie/technikportal/dinokapitel/Kapitel_06_DINO_techn_Teil.pdf
- Pieces used: Tab. 2 (reference values for the tightening factor alpha_A, with the stated scatter band for each
  tightening method), Tab. 3 (friction-coefficient classes with ranges, by surface and lubricant),
  Tab. 5 (assembly preload F_M,Tab and tightening torque M_A for mu = 0.08 ... 0.24, 90 % yield utilisation),
  section 6.7 (the worked example "How to use the tables").
- (A manufacturer page by Bossard has the same M12 numbers; its site returned 404 to my fetches, so I did not use it.)

## The problem in my words (section 6.7 example)
A hexagon bolt M12x50, strength class 8.8, zinc-plated, no lubricant, is tightened with a torque wrench.
1. Friction: the table of friction classes gives the zinc, no-lubricant case a range; the example picks the
   LOWEST probable value, mu = 0.14, "so the screw is not overloaded".
2. Torque: from Tab. 5 at mu = 0.14 the maximum tightening torque for M12 8.8 is M_A,max = 93 Nm, and the
   assembly preload that goes with it is F_M,max = 41.9 kN (this torque uses 90 % of the yield point).
3. Tightening factor: for a modern electronic-display torque wrench the example selects alpha_A = 1.4
   (it says the range for that situation is 1.4 to 1.6).
4. Minimum preload: F_M,min = F_M,max / alpha_A = 41.9 / 1.4 = 29.92 kN.
5. Then check: is F_M,min enough for the largest working forces (the example gives no working force for this bolt).

Numbers used from the source:
- Tab. 3, class C (zinc/galvanic coatings, delivered without lubricant): mu_G = mu_K in [0.14, 0.24];
  class B [0.08, 0.16]; class A [0.04, 0.10]; class D [0.20, 0.35].
- Tab. 5, M12 8.8 (mu: F_M,Tab kN / M_A Nm): 0.08: 45.2/63; 0.10: 44.1/73; 0.12: 43.0/84; 0.14: 41.9/93;
  0.16: 40.7/102; 0.20: 38.3/117; 0.24: 35.9/130. M12 10.9 at 0.14: 61.5/137; M12 12.9 at 0.14: 72.0/160.
- Tab. 2, torque wrench, friction estimated from surface class: alpha_A 1.6-2.0 (class B, distribution +-23 % to
  +-33 %), 1.7-2.5 (class A); torque wrench with experimentally determined target torque: 1.4-1.6 (+-17 % to
  +-23 %), with the note that the lower values need a small torque scatter "(e.g. +-5 %)".

## PUBLISHED ANSWER
M_A,max = 93 Nm; F_M,max = 41.9 kN; F_M,min = 29.92 kN (with alpha_A = 1.4). The claim is: with this method the
preload on assembly is between 29.92 and 41.9 kN, and the bolt is not overloaded because the torque was chosen
at the lowest probable friction (table basis: 90 % of yield).

## What I had to assume (source leaves open)
- The source prints no formulas. I used the standard VDI 2230 closed forms:
  M_A = F * (P/(2 pi) + 0.5775 d2 mu_G + (Dkm/2) mu_K), mu_K = mu_G;
  sigma_red = F/As * sqrt(1 + 3 r^2), r = 1.5 (d2/d0) (P/(pi d2) + 1.155 mu_G).
  I checked them against the source's own Tab. 5 (calc2.py in this folder): F from M_A agrees within 0.9 %,
  and the stress utilisation comes out 0.896...0.907 of Rp0.2 for every table cell (the table says 0.90).
- M12 geometry (ISO 724): P = 1.75, d2 = 10.863, d0 = 10.358 mm; Dkm = 15.065 mm (ISO 4017 bearing diameter
  16.63 and a 13.5 mm "medium" hole -- the source names the medium bore but gives no number).
- Rp0.2 min of 8.8 / 10.9 / 12.9 = 640 / 940 / 1100 MPa (ISO 898-1), not in the source.
- The source gives no required clamp load for this bolt, so there is no "pass/fail" in the source itself.
