# s08 problem: RTC backup coin-cell lifetime and required capacity

## Source
- congatec GmbH, Application Note AN9 "RTC Battery Know-How and Calculations", revision 1.3 (2024-01-17), public.
  URL: https://www.congatec.com/fileadmin/user_upload/Documents/Application_Notes/AN9_RTC_Battery_Lifetime.pdf
  (sections 2.1-2.4; read as PDF, 11 pages)
- Kind: a board manufacturer's application note with two worked examples. Not peer reviewed.

## The problem in my words
A real-time-clock circuit is kept alive by a lithium coin cell when mains is off. The note gives two rules of thumb,
both using the RTC's MAXIMUM battery current I (A), the cell's NOMINAL capacity C (Ah), and 24*365 = 8760 h per year:

- Eq 2.1 (lifetime): t_max [years] = C / (8760 * I) * f, where f = 0.8 is an allowance for "external impacts".
  The note says f "can vary from 0.7 to 0.9" with the battery and operating conditions.
- Eq 2.2 (required capacity): C = t_min * 8760 * I * k, with k = 1.2, an allowance that "can vary from 1.1 to 1.3".

Example 2.3 (lifetime): CR2032, 3 V, nominal 230 mAh, max RTC battery current 2.5 uA, f = 0.8.
Example 2.4 (capacity): required service time 15 years, max RTC battery current 3 uA, k = 1.2.

The note says the values in the examples are "typical". It also says the cell loses about 1 % of capacity per year on
the shelf (not put into the formulas), and that the RTC current should be measured at the highest ambient temperature
with a new battery (no temperature table is given).

## PUBLISHED ANSWER
- Ex 2.3: t_max = 8.4 years.
- Ex 2.4: C = 0.47304 Ah = 473.04 mAh; "the battery should have a nominal capacity equal to or greater than 473.04 mAh
  (e.g., the Panasonic CR2477)".
Both are point values computed with f = 0.8 and k = 1.2. The note itself states the ranges f in [0.7, 0.9], k in [1.1, 1.3]
but does not carry them into the answers.

## What I had to assume (the source left it open)
- 365-day year (the note's own 24 x 365).
- Whether the 8.4 y and 473.04 mAh are meant as guarantees over the stated ranges: the source does not say. I test
  exactly that question ("does the claim hold for every factor in the source's own range?") and also the nominal point.
- f in Eq 2.1 and k in Eq 2.2 are independent allowances (no correlation given).
- The CR2477 capacity is not given in the source, so no part-picking from a catalog; I ask for the limiting capacity instead.
- No tolerance of mine was added anywhere. All uncertainty is the source's two stated ranges.
