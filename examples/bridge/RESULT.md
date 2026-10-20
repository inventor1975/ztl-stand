# Bridge girder — the measurement (2026-10-20)

`pratt36.json` (from `gen_pratt.py`): a 36 m Pratt truss, 12 panels of 3 m, 4 m deep; 45 bars, 24 nodes; 11 deck loads of
150 kN each within ±10 % (independently); every bar's modulus 210 GPa within ±0.5 %; S355; five groups of square hollow
sections from one catalogue of 8 (IDEALISED sharp-corner sections, not EN 10219 values); requirements: every stress
within fy, flexural buckling by EN 1993-1-1 curve c, mid-span deflection L/500 under characteristic loads (taken as the
factored ones / 1.35); objective: the least steel. 8^5 = 32 768 designs, 91 requirements, 141 linear unknowns.

    python3 -m ustand.stand examples/bridge/pratt36.json --jobs 16

| | |
|---|---|
| verdict | **EARNED, optimal** — every cheaper design refuted |
| design | bottom chord SHS 220×12, top chord 250×12, verticals 120×8, end posts 180×10, diagonals 150×8 |
| steel | 1 155 040 mm²·m ≈ 1.155 m³ |
| worst mid-span deflection | −96.10 mm (limit −97.2 under the factored loads), proved over every load and modulus |
| designs | 19 056 tried in cost order: 18 984 failed at the nominal point, 72 judged in full, 0 open |
| time | 755 s on 16 workers (i9-14900F); one design 2–4 s |

How it got there (all general, each measured on this brick):
- ZTL b32300c, superposition (lean/ZSuperpose.lean): a constant matrix with the loads on the right-hand side is solved
  exactly for any number of loads — before, 11 loads were over the corner cap of 10, and one design took > 30 min;
- ZTL f8ea3fe: the deflection, a definition linear in the bar forces, is read through their dependence on the loads, not
  their separate ranges — before, the designs at the limit stayed OPEN, and they are the optimum;
- the stand: a requirement's bound that varies with one or two quantities is read piece by piece (the EN 1993 bound
  reads one modulus a dozen times); caches of the checker's elimination and of ZTL's answers; parallel listings.

NOT a bridge design: no load model (EN 1991-2), no combinations, no joints, no lateral bracing, no fatigue, no dynamics,
and the data (loads, tolerances, sections) is taken as stated.
