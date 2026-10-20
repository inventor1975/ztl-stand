# r03 PROBLEM: heat sink rating for a TO-3 power transistor (two power levels)

## Source
- Title: "4.6: Heat Sinks" (Example 4.6.1 on the page; the page's own text numbers it 8.6.1), in "Electronics (Final)",
  chapter "BJT Circuits", Engineering LibreTexts (sandbox copy; the text is from J. M. Fiore, Mohawk Valley
  Community College, "Semiconductor Devices", CC BY-NC-SA 4.0).
- URL: https://eng.libretexts.org/Sandboxes/radwana_at_wwu.edu/Electronics_(Final)/04:_BJT_Circuits/4.06:_Heat_Sinks
- Kind: open textbook, one worked example with two parts (read on 2026-10-11, fetched the page text directly).

## The problem in my words
A power transistor in a TO-3 can must be mounted on a heat sink. Its data sheet gives a maximum junction
temperature of 175 C and a junction-to-case thermal resistance of 1.5 C/W. The transistor will dissipate at most
15 W (part A) or, in a second pass, 40 W (part B), in surrounding air at 40 C. The device is isolated from the sink with a
0.002 inch mica sheet and heat-sink grease. The author reads the case-to-sink resistance off a manufacturer's graph
(the curve for TO-3 with grease) as "approximately" 0.35 C/W. Question: what is the largest sink-to-ambient thermal
resistance a heat sink may have?

Numbers used: Tj_max = 175 C; Rjc = 1.5 C/W; Rcs = 0.35 C/W; Ta = 40 C; P = 15 W (A) and 40 W (B).
Law: Tj = Ta + P*(Rjc + Rcs + Rsa), three resistances in series.

## PUBLISHED ANSWER
- Part A (15 W): Rsa <= 7.15 C/W, called "the maximum acceptable value".
- Part B (40 W): Rsa <= 1.53 C/W.
- Side remarks (not checkable here, they rest on a graph not reproduced): the sink pictured in the text will most
  likely be enough for part A on natural convection; for part B the same sink would need forced air of at least
  700 ft/min.
My arithmetic: A: 135/15 - 1.85 = 7.15 exactly. B: 135/40 - 1.85 = 1.525 exactly; the text rounds it UP to 1.53.

## What the source leaves open (my assumptions)
1. The source gives no list of heat sinks and no tolerances. To make a "pick a part from a list" question I
   INVENTED two small catalogs of sinks (Rsa values placed around the published limits, plus filler). They are not
   from any vendor.
2. The source treats Rcs = 0.35 as exact ("approximately" is its only hedge) and Ta = 40 C as a fixed number.
   brick.json keeps them exact (the faithful form). brick_tol.json (scratch) adds my own tolerances: Rcs 0.35 +-15 %,
   Ta in [40, 45] C, P +5 %; these are NOT in the source.
3. Both power levels are two different applications in the source. In one brick I put two slots (one sink per
   application), so a "design" is a pair of sinks and each application is judged on its own sink.
