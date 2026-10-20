# s01 problem: static face-seal O-ring, squeeze and gland fill over tolerances

## Source
- URL: https://jlcmc.com/blog/o-ring-groove-design-guide ("O-Ring Groove Design Guide: Squeeze, Stretch and Gland Fill", JLCMC blog, section 11 "Tolerance Stack: A Worked Example"; sections 4 and 6 for the formulas and preliminary limits). Author not named; a supplier's blog.
- Read on 2026-10-12. The page's formulas are images/markup that did not survive text extraction; I rebuilt them from the numbers (see "assumed").

## Problem (my words)
A static face seal: an O-ring is squeezed in a rectangular groove. Three dimensions each come with a min-max range in the source's table:
- O-ring cross-section d: nominal 3.00 mm, range 2.90 to 3.10 mm
- groove depth h (assembled gland height): nominal 2.25 mm, range 2.20 to 2.30 mm
- groove width w: nominal 4.20 mm, range 4.10 to 4.30 mm

Squeeze = (d - h)/d. Gland fill = cross-section area / groove area. The source asks: what squeeze and fill does the worst case give, and is it acceptable against its general limits (squeeze 20-30 % for a static face seal; fill designed within about 60-85 %, and "below 85 %").

## Published answer
- Nominal squeeze 25 %, nominal fill 74.8 %.
- Minimum squeeze (smallest d, deepest groove, i.e. h = 2.30): (2.90 - 2.30)/2.90 = about 20.7 %.
- Maximum squeeze (largest d, shallowest groove, h = 2.20): (3.10 - 2.20)/3.10 = 29.0 %.
- Summary claim: the manufactured range is about 20.7 to 29.0 % squeeze.
- Maximum fill (largest d, shallowest groove, narrowest width): about 83.7 %; "remains below 85 %" before swelling. With a 10 % volume swell "the effective fill could exceed 90 %".
- (One line in the page is mislabelled: the "nominal" squeeze line is attached to the smallest-section case; the numbers 25 %, 20.7 %, 29.0 % are consistent.)
- Minimum fill is listed as something to calculate but no number is given.

## Assumed (source left it open)
- Gland fill formula: pi*d^2/4 divided by w*h. Checked: with 3.00, 2.25, 4.20 it gives 74.80 %, matching the source's 74.8 %; with 3.10, 2.20, 4.10 it gives 83.68 %, matching 83.7 %.
- Squeeze and fill limits (20-30 %, 60-85 %) are the source's own "common preliminary" ranges, which the source itself says are not universal specifications. The lower fill limit 60 % is read from "approximately 60-85 %".
- Stretch, swell, temperature: not in the base case (the source also leaves them out of its numbers).
- Extra variants (my additions, separate files): swell 0 to 10 % as a given range (the source's illustration, not a tolerance), and the largest swell that keeps fill <= 85 % (my criterion).
