# r04 PROBLEM: choosing a deep groove ball bearing for a combined radial + axial load

## Source
- Koyo / JTEKT, "Applied calculation examples", section "Basic Bearing Knowledge" (bearing selection chapter), Example 6.
  https://koyo.jtekt.co.jp/en/support/bearing-knowledge/5-7000.html
- Manufacturer's technical page (a vendor's own worked example). Author: JTEKT Corporation.
- Supporting catalogue figures for single sizes: the same page (6308: Cr 50.9 kN, C0r 24.0 kN, f0 13.2, from its Example 2;
  6309: C0r 29.5 kN, f0 13.3 from Example 6 itself); 6307 and 6309 dynamic ratings from distributor pages
  (https://www.simplybearings.co.uk/products/6309-koy : 6309 Cr 48.9 kN, C0r 29.5 kN; a second distributor page lists 6307 as
  33.4 kN / 19.3 kN / f0 13.2).

## The problem (my words)
A shaft carries a steady radial load of 4000 N and an axial load of 2400 N at 1000 rev/min. The bearing must reach a basic rating
life (90 % reliability) of more than 15 000 hours. Pick the smallest deep groove ball bearing of the 63 series that does it.

Method used by the source (ISO 281 style):
1. Equivalent load P = X*Fr + Y*Fa when Fa/Fr > e (else P = Fr). X = 0.56. e and Y depend on f0*Fa/C0r and are
   linearly interpolated from the catalogue table.
2. L10 = (Cr/P)^3 million revolutions; L10h = L10 * 1e6 / (60 * n).
3. Sizing shortcut: guess Y ~ 1.6, P = 0.56*4000 + 1.6*2400 = 6080 N; required Cr = P * (900)^(1/3) = about 58 700 N
   (900 million revolutions in 15 000 h at 1000 rpm).

## PUBLISHED ANSWER (as read from the page's text)
- Required Cr above 58 700 N, so the 63-series bearing chosen is **6309** (45 mm bore, C0r 29.5 kN, f0 13.3).
- Check on 6309: f0*Fa/C0r = 13.3*2400/29500 = 1.082, interpolation gives e = 0.283, Y = 1.54; Fa/Fr = 0.6 > e, so the
  equivalent load and life are recomputed (the resulting numbers are in an image I could not read; I recomputed them).
- The next smaller bearing, **6308**, "using the same steps" has **L10h about 11 500 h**, so it does NOT meet 15 000 h.
- The claim: 6309 is the smallest 63-series bearing that satisfies the life; 6308 fails.

## Numbers used in the brick
- Fr = 4000 N, Fa = 2400 N, n = 1000 rpm, Lreq = 15 000 h, X = 0.56.
- Catalogue (Cr, C0r, f0): 6307 = 41.7 kN, 19.3 kN, 13.2; 6308 = 50.9, 24.0, 13.2; 6309 = 61.1, 29.5, 13.3.
- e/Y table (ISO 281 deep groove, the standard table; I checked it against the source's own interpolated values:
  f0Fa/C0r 1.082 -> e 0.283, Y 1.54 and, in Example 2, 0.55 -> Y 1.82):
  f0Fa/C0r 0.172, 0.345, 0.689, 1.03, 1.38, 2.07, 3.45, 5.17, 6.89 ->
  e 0.19, 0.22, 0.26, 0.28, 0.30, 0.34, 0.38, 0.42, 0.44; Y 2.30, 1.99, 1.71, 1.55, 1.45, 1.31, 1.15, 1.04, 1.00.

## Assumptions the source left open
1. **6309 Cr is not in the page text.** The page only says that the chosen 6309 has Cr above 58 700 N. Distributors list the older
   rating 48.9 kN, which would fail the 58.7 kN test, so the page uses a newer rating. Evidence for a factor 1.25: the page's
   6308 is 50.9 kN, distributors' older 6308 value is 40.7 kN (50.9/1.25); 6307: 33.4 -> 41.7 kN (page-style) = x1.25. So I set
   6309 Cr = 48.9 * 1.25 = **61.1 kN (INFERRED, not published)**. The published verdict on 6309 depends on this being above 58.7.
2. 6307 is not mentioned in the source; I added it (Cr 41.7 kN from the distributor x1.25 rule, C0r 19.3 kN, f0 13.2) to make a
   3-item list. Its result is not comparable to anything published.
3. "Smallest" is read as smallest bore (35 < 40 < 45 mm), as the objective.
4. The source has no uncertainty. Variants with plus/minus 5 % and plus/minus 10 % on both loads are MY additions
   (brick_tol5.json, brick_tol10.json) and have no published answer.
