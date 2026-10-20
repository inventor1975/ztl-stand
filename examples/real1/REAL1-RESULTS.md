# Real problems, round 1 — results (2026-10-11)

**Setup.** The curator, 2026-10-11: "let Sonnet find the problems and use the stand — more realistic". Six agents
(Sonnet), one area each, each found ONE small real problem with a published answer on the internet, restated it in
its own words with the source, wrote a brick (BRICKS.md and the examples only, no code), ran the stand (work mode,
then --dev once) and compared with the published answer. The stand was frozen at ztl-stand 6b3a690, ZTL 2a24683.

| # | area | source | published answer vs the stand | who is right |
|---|---|---|---|---|
| r01 | regulator divider, tolerances | TI application report SLVA423 (2010), Sec. 4 | DISAGREE: published worst case +-2.28 % (3.3 V rail), exact +2.303 % / -2.252 % | **the stand** (the note's small-T approximation and linear sum; checked by hand) |
| r02 | linear regulator thermal, package/heatsink | ON Semi "Thermal Management for Linear Regulators" (1999) | AGREE on every choice (TO220 alone for ex. 1, heatsink needed for ex. 2) | the note's own 1.83 W uses 250 mA where its text says 200 mA; the stand matches the honest arithmetic |
| r03 | heatsink limit | LibreTexts, Fiore, Example 4.6.1 | case A AGREE (7.15 C/W); case B the source rounds 1.525 up to 1.53 — a 1.53 sink gives Tj 175.2 C | **the stand** |
| r04 | bearing selection | Koyo/JTEKT, applied calculation example 6 | AGREE (6309 passes, 6308 fails at 11 494 h) | — (6309's Cr inferred by the author) |
| r05 | pump operating point | BYU ChEn 374, lecture 30, slide 12 | v and H AGREE to 6 digits; the slide's Q 0.055 and 89.35 kW are wrong: Q = A v = 0.0560, 91.0 kW | **the stand** (checked by hand) |
| r06 | chlorine dosing pump | California SWRCB/DDW dosage examples (2018) | every published number AGREES (0.2307 %, 103 mL/min); the choice (pump window) was the author's | the handout's Eq. 1C drops the 0.9525 Cl2/NaOCl factor its own table uses |

**No wrong verdict.** In five of the six sources the published text itself has a slip (r01 an approximation, r02 a
current, r03 a rounding, r05 the flow and the power, r06 a missing factor); where it touches a verdict, the stand's
answer is the exact one, confirmed by the authors' hand arithmetic and, for r01 and r05, by Logik1's. Work and --dev
agreed on every run.

**What real problems show.**
- Real worked examples are mostly NOMINAL point calculations: every tolerance in these bricks was the authors'
  addition. The stand's worst-case power is used on assumptions the source does not make.
- INVERSE questions ("the largest Rsa that still works", r03) cannot be asked directly: the stand judges listed parts;
  the authors bracketed the threshold with invented catalogs.
- Physical curves given only as figures (r02 heatsink, r05 friction correlation) are inferred by the authors.

**Gaps found (format / output) — to fix after the freeze:**
- `table(...)` inside an `if(...)` condition: BRICK ERROR "not a readable expression" with no reason (r04).
- With modes, REFUTED names only the first failing mode (r01, r02).
- `rests_on` says "tolerances are the catalog's (datasheet) word" although they were givens (r06).
- With `report: "all"`, the second EARNED design shows no range (r06); BRICKS.md's "outside ZTL" wording is stale (r06).
- `how` says "may be wide" for a single-point range; a REFUTED witness shows a `pi` bracket corner (r05).
- An OPEN under tolerances (r05, v and H within 3 %) — a loss of power, the true ranges hold (the author's scan).
- A label field needs `"name": {"unit": ""}` to avoid "units: not checked" (r04); a `<=` met exactly counts as EARNED,
  not documented (r03).

**Cost.** 6 agents, 772 144 tokens (96 171 to 163 077 each).
