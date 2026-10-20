# Real problems, round 3 — results (2026-10-12)

**Setup.** As round 2 (six Sonnet agents, one real published problem each, uncertainty from the source itself), with
the new vocabulary available: `network` (BRICKS 7c), `find` lists, `each_requirement`. Two areas were chosen for
networks. The stand was frozen at ztl-stand 54f72b1, ZTL 2a24683.

| # | area | source | published answer vs the stand | who is right |
|---|---|---|---|---|
| n01 | bridge sensor offset | Analog Dialogue 48-1 (2014), via eeNews Europe | AGREE: worst offset TOL x VEX = 5 mV; the stand proves 4.99995 mV (a 1 Gohm detector loads it) and refutes 4.999 mV at a concrete corner; --dev: all 16 corners exact, inside | — (a voltage had to be turned into a current: see gaps) |
| n02 | MOSFET thermal chain, max current | DigiKey TechForum, "A Thermal Management Example" parts 1-2 | AGREE on all five limits (58.86 / 51.59 / 48.59 / 33.07 / 24.72 A vs 58.9 / 51.6 / 48.6 / 33.1 / 24.7), one find list | — (the source's uncertainty is one-sided maxima) |
| s07 | tube pressure rating, ASME B31.3 | Swagelok MS-06-117 Rev D | AGREE: 1/2 x 0.065 904L proved 5106 psig, 5107 refuted (hand 5106.9; printed 5100, rounded down); 400 F: 3472 proved (the sheet's rule 3468) | — (checked by Logik1: 2*20000*0.0585/(0.505-0.0468) = 5106.9) |
| s08 | RTC coin-cell lifetime | congatec AN9 rev 1.3 (2024) | at the centre factors AGREE (473.04 mAh, 8.4 y); over the source's own factor ranges only 512.46 mAh and 7.35 y are guaranteed; the note's two formulas disagree (492.75 vs 473.04 mAh) | NOT COMPARABLE (the note claims no guarantee); the stand's numbers checked by Logik1 |
| s09 | fiber link budget | Cisco support doc 27042 | AGREE: worst margin 0.95 dB; find: largest length 22.4 km (hand (17-5.8)/0.5) | — (a corner problem: easy) |
| s10 | current-limit resistor choice | TI TPS25221 datasheet (SLVSDT3D) | exact resistors AGREE (49.9 k, 124 k); with the 1 % tolerance the datasheet itself assumes, 49.9 k does NOT guarantee 1000 mA (991 mA at 50.4 k); limit 49.47 k nominal -> 48.7 k (E96); 6 of 17 Table-3 rows refuted by < 0.5 mA (the table's rounding) | **the stand** on case A (checked by Logik1: 56850/50.399^1.033 = 991.1 mA) |

**No wrong verdict.** Every number was checked by the authors' hand scripts; Logik1 re-checked s07, s08 and s10.
Work and --dev agreed on every brick run in both. `find` was used in all six (find lists in n02, s08, s10).

**What this round shows.**
- The networks the real problems bring are DRIVEN BY A CURRENT and ASK A POTENTIAL: a bridge's offset voltage (n01),
  a junction temperature under a dissipated power (n02). Version 1 has a voltage source and branch currents only:
  n01 worked around it with a 1 Gohm detector, n02 could not use the network at all.
- Datasheets round their headline numbers to the safe side (s07) — or not (s10 case A: a 0.14 % margin eaten by the
  1 % resistor tolerance the same page assumes).
- Point formulas with stated factor ranges are not guarantees (s08): the stand states the guaranteed value.

**Gaps found.**
- VOCABULARY (word-first with the curator):
  - network: node potential requirements `V(n)` / `V(a,b)`, and a current source (injected power) — n01, n02;
  - units: psi, inch, ft (s07, n02); temperature in F is affine (s07); dBm is logarithmic (s09);
  - a tolerance that names a given quantity, so `find` can search it (n01).
- DOCS (BRICKS.md): `where` on a toleranced field needs `nominal(...)` (s10); a series' decades are in the field's
  unit (s10); two finds may search one quantity (s10); a negative power in `pow` (s10); what the verdict of a find
  list means and that `proved` is a grid value (s08, n02); one find list over scenarios with different givens (n02,
  s08); whether different givens vary independently (s09: they do).

**Cost.** 6 agents, 782 134 tokens (96 184 to 178 144 each).
