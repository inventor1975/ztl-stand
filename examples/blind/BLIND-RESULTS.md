# Blind test of the input format — results (2026-10-10)

**Setup.**

- One agent that never saw the format wrote 12 problems, one each from 12 domains: `PROBLEMS.md`.
- Twelve independent blind authors (Sonnet) each got BRICKS.md, the examples and one problem. They had no
  access to the code.
- Each author wrote a JSON brick (`bNN.json`), ran it, and reported what went in as stated, what was
  approximated and what could not be expressed (`bNN.report.md`).
- All 12 bricks were re-run afterwards by Logik1 from the repository root.

## Outcome

| # | domain | verdict | authors' hand check | approximations the author made OUTSIDE the stand |
|---|---|---|---|---|
| 1 | valve spring | EARNED S2, optimal | 2 numbers match | pi as a bracketed given |
| 2 | fan, 2 modes | EARNED F3, optimal (32 s) | true root: F3 54.97 °C vs limit 55 | the fan operating point (implicit quadratic) replaced by a 7-fold fixed-point lower bound |
| 3 | pump | EARNED P2, optimal | Q² bound matches | Swamee–Jain friction (log10, Re^0.9) bounded offline; the Q–f coupling broken by hand |
| 4 | CSTR | EARNED R3, optimal | X and q bounds match | Arrhenius exp() enclosed by hand; T not in the brick |
| 5 | battery, 2 modes | EARNED B3, optimal | worst-corner script agrees | Peukert x^k replaced by a tangent lower bound |
| 6 | RC filter, 2 modes | REFUTED (gain) | 10.3366 by hand | log10/sqrt converted to f/fc ≥ 8.8563 |
| 7 | beam | EARNED IPE270, optimal | σ 99.44 by hand | sqrt removed (f1² ≥ 64); cm converted by hand |
| 8 | lens | EARNED L4, optimal | W and s match | atan/tan replaced by the identity W = D·w/f |
| 9 | mortgage | EARNED L2 | hand check refutes L1, L3, L4 | (1+r)^n precomputed; the cap (min) by hand; worst-case objective by hand |
| 10 | servers, 2 modes | EARNED I2×7, optimal=false (truly optimal) | rho and p99 by hand | ln(100) as a given; modes written by hand (the modes form crashed) |
| 11 | rocket motor | REFUTED (v_rail, a_max) | witness matches | ln → a rigorous series lower bound; sqrt → squared requirement |
| 12 | dosing | REFUTED | corner scan with true exp agrees | exp() → hand-proved Taylor bounds |

**No author found a wrong verdict.** Every number that was checked by hand agreed with the stand.

This is less than it sounds. In 9 of 12 problems, the hard part of the physics was approximated by the
author OUTSIDE the stand, and the stand did not check that step.

## What the test says about the format

**The STRUCTURE held in all 12 domains.** No author lacked a place for any of these:

- quantities with tolerances or ranges;
- catalog choices;
- integer choices;
- laws;
- requirements;
- modes;
- an objective.

**The VOCABULARY and the ROBUSTNESS did not hold.** These are the gaps, by how many problems hit each one:

| gap | problems | kind |
|---|---|---|
| G1. No math functions: exp, ln, log10, sqrt, powers with a non-integer or variable exponent, atan/tan, min/max | 2,3,4,5,6,7,8,9,10,11,12 (11 of 12) | vocabulary (needs ZTL) |
| G2. Python tracebacks instead of BRICK ERROR. Triggers: unknown units (mol, h, min, L, Ah, EUR, dBA); parentheses in units; `/` or `(` in `source` or `ground` strings; a derived quantity as a requirement bound; two laws defining one quantity; a nonlinear definition beside an implicit law; MODES with an undecided design or a denominator spanning zero; a zero nominal denominator | 2,3,4,5,9,10,12 | robustness (bugs) |
| G3. Units: hour, minute, litre, mol, A·h, any currency, dB, the `c` prefix | 3,4,5,7,9,10,12 | vocabulary |
| G4. A requirement bound cannot be an expression or a derived quantity, so authors had to add slack or dummy quantities | 1,7,8,9 | vocabulary |
| G5. The output does not answer "which designs pass, and why does each fail": it stops at the first EARNED, or shows only the closest REFUTED | 1,7,9,11 | output |
| G6. Implicit laws (an operating point where curves meet; a quantity on both sides) | 2,3 | vocabulary (needs ZTL) |
| G7. No built-in constants: pi, ln(100), g0 written as bracketed givens | 1,7,10,11 | vocabulary |
| G8. A law's domain cannot be stated (M/M/1 holds only for mu > lambda). Without an explicit requirement, a design with negative latency was accepted: the stand solved the formula correctly, outside the formula's domain | 10 | vocabulary |
| G9. Mode-specific laws, or a catalog field that differs per mode (capacitor drift cold vs hot) | 5,6,10 | vocabulary |
| G10. Speed: a relaxed dosing brick (12) ran over 3 minutes and was killed | 12 | performance |
| G11. The objective is evaluated at nominal values only; "worst case" had to be written by hand | 9 | vocabulary |
| G12. Equivalent forms decide differently: `fc*(2*pi*R*C) == 1` gave OPEN with no reason; the `tau` form decided | 6 | robustness / doc |
| G13. Doc gaps: which functions exist, that defines may chain, that division by a toleranced quantity is fine, what "outer range" means, that "nominal" is the range midpoint | most | doc |

**Reading.**

- The core shape of the brick is universal across these 12 domains. It needs no redesign.
- What is not universal yet is the expression language and how robust the stand is:
  - G1 alone affected 11 of 12 problems;
  - G2 means a newcomer meets a traceback within minutes.
- Both gaps are EXTENSIONS of the existing format, not changes to it. A function call is a new node in an
  expression, and a unit is a new table entry. Nothing written so far would have to be rewritten.
- A third finding: the stand never checks the authors' hand approximations. A brick earned on a hand-made
  bound is only as good as that bound. Every gap closed in G1 or G6 moves one of those steps back under
  ZTL's check.

## Cost

The test used 13 agents, about 1.07M tokens in all:

- the problem writer, 79,593 tokens;
- 12 blind authors, 994,700 tokens (from 72,341 to 100,833 each).

Not counted: Logik1's own context.
