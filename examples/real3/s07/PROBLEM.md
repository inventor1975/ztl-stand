# s07 PROBLEM: working pressure of a 1/2 in stainless tube, hot, with the datasheet's own tolerances

## Source
- Swagelok, "Tubing Data - Engineered Combinations", MS-06-117 Rev D, January 2021 (manufacturer datasheet, freely readable PDF):
  https://www.swagelok.com/-/media/distributor-media/o-s/pittsburgh/pdfs/catalogtubing-data-ms06117-revd.ashx
  (read via a plain HTTP fetch; the PDF is not kept here). Pages used: p.3 (calculation basis, Table 1, Examples 1-2) and p.5 (Table 4, Type 904L tubing).

## The problem in my words
How much internal pressure may a 1/2 in OD tube of Type 904L stainless take, when the maker's own rules are used:
- Pressures follow the ASME B31.3 thin-wall pressure formula, with the allowable stress capped at S = 20 000 psi (Table 4 text, 904L).
- The rating is computed at the WORST tube the specification allows: largest OD and thinnest wall. The datasheet's own example for ASTM A269 tubing: OD tolerance +-0.005 in, wall tolerance +-10 %; a 1/2 in x 0.035 in tube is therefore evaluated as 0.505 in OD with 0.0315 in wall.
- For hot service the room-temperature rating (rated range -20..100 degF) is multiplied by the datasheet's elevated-temperature factor (Table 1). For Type 904L the factors are 0.82 at 200 degF, 0.68 at 400 degF, 0.58 at 600 degF. The factors come from the code allowable stress, so they act on S.

Numbers I use:
- Tube: nominal OD 0.500 in, OD in [0.495, 0.505]; wall nominal 0.065 in, in [0.0585, 0.0715] (+-10 %). Other walls offered for 1/2 in: 0.035, 0.049, 0.083 in.
- S = 20 000 psi, E = W = 1 (seamless), Y = 0.4 (B31.3 coefficient for these thin walls).
- Table 1 (904L column): 100 degF -> 1.00 (room-temperature rating is for -20..100), 200 -> 0.82, 400 -> 0.68, 600 -> 0.58.
- Service temperature: 200..400 degF (between two published knots).

## PUBLISHED ANSWER
- Table 4: for 1/2 in OD 904L tube, working pressure at room temperature is 2600 / 3700 / 5100 / 6700 psig for wall 0.035 / 0.049 / 0.065 / 0.083 in (values appear rounded down to the next 100 psi).
- Hot rule (stated in the worked Examples 1-2, p.3 - there for other alloys): working pressure at temperature = room rating x Table-1 factor. Applied to 1/2 x 0.065 904L: 5100 x 0.68 = 3468 psig at 400 degF; 5100 x 0.82 = 4182 at 200 degF. THE 904L HOT NUMBER IS MY APPLICATION of the datasheet's rule; the datasheet prints the worked example only for 6Mo/316/2507 (e.g. 5100 x 0.67 = 3417 psig, 6Mo, 600 degF).
- The claim: a tube of that size and wall, worst-case dimensions, may be used up to that pressure.

## What I had to assume (source left open)
- Y = 0.4 is not printed in this datasheet ("equations in ASME B31.3"); I took the B31.3 value and CHECKED it by recomputing 26 of the printed Table-4 entries (1/2 in and larger): all agree after rounding down to 100 psig. For 1/4 and 3/8 in the printed values are lower than this formula gives, so the datasheet uses another basis there (not used).
- Linear interpolation of the Table-1 factor between its knots (the datasheet gives none). Added by me; the brick is also run with T = 400 degF exactly, which needs no interpolation.
- OD tolerance +-0.005 in is the datasheet's example for ASTM A269 tubing; I apply it to the 1/2 in and the 3/4 in size.
- Pressure unit psi is not in the stand's unit list; I wrote it as the number-unit "6894.757293168Pa" (psi, 13 digits) and inches as "25.4mm" (exact). Temperature in degF is a dimensionless number (no F unit).
