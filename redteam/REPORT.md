# Red team, structural part — 2026-11-02/03

Target: a FALSE EARNED (or a false proved bound) in ztl-stand's structural modules. Stand at `c4e9696`, ZTL at
`6d1f7ea`, Python 3.13, 4 CPUs, scikit-sparse 0.5.0 (CHOLMOD) installed and exercised. Nothing in `ustand/` or ZTL
was modified; every file of this work is under `redteam/`. Mutations use only `_MUTANT` test switches, or wrap the
stand's output in the check script.

**Smoke (before the hunt).**
- `python3 -m tests.run_parallel --jobs 3`: 392 ok, 0 failed, **USTAND GREEN** (613 s).
- `bench/night/verify_all.py --jobs 3 --scale 0.2`: sweeps A–J show 0 violations, and every `-MUT` row shows
  violations (A-MUT, A-MUTG, B-MUT, B-MUTG, G-MUTG3, G-MUTM3, H-MUTA, I-MUTL, J-MUTA).

**Result: 1 confirmed finding (one root cause, four false outputs, including a false EARNED and a false REFUTED).
Every other class I tried held.**
I stopped with one finding, after the classes below were covered and before the 3-hour limit, not at 3 findings.

---

## FINDING 1 — the space frame's geometric stiffness ignores END RELEASES (false stability bound, false EN 6.3.1 EARNED, false second-order displacement bound, false REFUTED)

### Cause

`frame3d.energy_system` gives a released member end its own rotation unknown, `(("IR", k, end), ax)`. The ELASTIC
stiffness uses it, through `rot()`. But the following are built with `_form3` and `_glob3`, which read the NODE's
rotation DOFs `(n, "RX"|"RY"|"RZ")` and know nothing of releases:

- `stability_lower`'s G, Q and B forms, and the axial-load split;
- `second_order_disp`'s K_G and continuum correction;
- `second_order_stress`'s end-moment G rows and end-slope rows.

So in buckling and P-delta a released member behaves as if rigidly connected: its geometric energy is evaluated with
the node's rotation instead of its own end slope. Where the node's rotation is restrained (supports, stiff
connections), the released member is treated as clamped for buckling. The stand accepts these decks without comment;
RELEASE is tested in the suite in first order only.

### 1a. A false proved lower bound on the critical factor (×1.95)

- **Deck:** `redteam/decks/rel-column-fixed-pinned.txt`. A 4 m column, base fixed (`D, 1, ALL`), top held
  laterally and rotationally by supports, and `RELEASE, 1, J, MZ, MY`: a hinge at the column's top. The column is
  FIXED–PINNED. Load `F, 2, FZ, -1e7`, tolerance 0, so the box is one point.
- **Command:** `PYTHONPATH=. python3 -c "from ustand import frame3d as F3; print(F3.stability_lower(open('redteam/decks/rel-column-fixed-pinned.txt').read(), '0'))"`
- **Proved:** `lam_low = 4.14375`. This is the clamped–clamped value 4π²EI/(L²P) = 4.14523, minus the stand's slack.
- **Independent:** λ_cr = 20.1907·EI/(L²P) = **2.12002** (fixed–pinned Euler). `redteam/ref_hinged.py` (200 Hermite
  elements, the hinge a free end rotation) gives 2.120026; the closed form gives 2.1200235.
- **Size:** the "lower bound" is **1.95× the true critical factor**. The reference's own error is about 1e-6
  relative.

### 1b. A FALSE EARNED from EN 1993-1-1 6.3.1: a strut that buckles under its own load

- **Deck:** `redteam/decks/rel-strut-12m.txt`. A 12 m strut, `RELEASE` at both ends (pin-ended), between nodes whose
  rotations are held. N_Ed = 1.3 MN (130 MPa), fy = 235 MPa, curve b.
- **Command:** `PYTHONPATH=. python3 -c "from ustand import frame3d as F3; print(F3.judge_buckling(open('redteam/decks/rel-strut-12m.txt').read(), '0', 235e6, 'b', 'b'))"`
- **Stand:** **EARNED**, utilisation_max **0.7133**, with α_cr proved ≥ **3.5417**.
- **Independent:**
  - the true critical factor is π²EI/(L²·N_Ed) = **0.88573**: the strut buckles elastically under the design load;
  - EN 6.3.1 with the true N_cr gives λ̄ = 1.4286, χ_b = 0.36985, N_b,Rd = 869.1 kN < 1300 kN, so the true
    utilisation is **1.496**.
- **Size:** α_cr is overstated 4.00× (pinned–pinned against clamped–clamped). The violation is about 40 % of the
  resistance, against solver errors of 1e-8.
- **With 2 elements per member** the bound is still false (0.88749 against 0.88573). With 4 or 8 elements it falls
  below the truth, because the inner nodes are correct; only the released end elements are wrong.

### 1c. A false proved upper bound on a second-order displacement (stable structure, α_cr = 2)

- **Deck:** `redteam/decks/rel-strut-second-order.txt`. The same strut in 2 elements, pin-ended by RELEASE,
  compression P = π²EI/(2L²) (true α_cr = 2), and a lateral 5 kN at mid-span.
- **Command:** `PYTHONPATH=. python3 -c "from ustand import frame3d as F3; print(F3.second_order_disp(open('redteam/decks/rel-strut-second-order.txt').read(), '0', ['U(2,Y)']))"`
- **Proved:** U(2,Y) in **[0.0210394, 0.0212661]**.
- **Independent:** the closed form for a pin-ended beam-column under a central point load,
  Q/(2Pk)·(tan(kL/2) − kL/2), gives **0.0212817**. `ref_hinged` gives 0.02128166 at n = 400 and 0.02128168 at
  n = 800.
- **Size:** the proved upper end is **0.073 % below the truth**, against a reference uncertainty below 1e-6 relative.

### 1d. A FALSE REFUTED (a proved lower bound above the true value), by the same cause

- **Deck:** the same as 1c, `redteam/decks/rel-strut-second-order.txt`.
- **Command:** `PYTHONPATH=. python3 -c "from ustand import frame3d as F3; print(F3.second_order_stress(open('redteam/decks/rel-strut-second-order.txt').read(), '0', 91.7e6)['verdict'])"`
- **Stand:** max |σ| proved in [**91.750**, 94.620] MPa, so with fy = 91.7 MPa the verdict is **REFUTED**.
- **Independent:** the true maximum is P/A + M_mid/W with M_mid = (Q/2k)·tan(kL/2) = 27,252 N·m, giving
  **91.638 MPa ≤ 91.7 MPa: it passes.**
- **Size:** the proved "lower bound of max |σ|" is 0.12 % above the true maximum, in closed form.

All four are reproduced, with the numbers above, by `PYTHONPATH=. python3 redteam/check_release.py` (output:
`redteam/results/release.json`). `judge_ltb` and `judge_interaction` on released members take the same α_cr and end moments and are suspect by
the same cause; I did not build separate cases for them.

**Suggested repair (not done):** route `_form3` and `_glob3` through the same `rot()` mapping `energy_system` uses for
the elastic terms, or refuse RELEASE in every second-order and stability path until they do. A regression test:
`rel-strut-12m.txt` must give α_cr ≤ 0.8857.

---

## Classes tried that held (with counts and the mutation that shows each check can see a broken bound)

| # | Class | Script / data | Cases | Violations | Mutation → seen |
|---|---|---|---|---|---|
| 1 | 2D second-order member STRESSES with axial member loads (`frame.second_order_case`): whole frames of 5 families (portal 138, pitched rafters with oblique QLOAD 65, single/inclined columns 62, braced with a self-weighted diagonal 49, hangers in tension or mixed N 47); element orientation flipped at random; 1–3 elements per member; tolerance 0 or 0.5 % (181 decks, 7 box vertices each). Checks: \|σ\| upper bound per element, and both end-moment intervals | `hunt2d.py` vs `ref2d.py` (own parser and matrices, 64/128 sub-elements, N from the first-order solve; validated to 1e-9 against the closed beam-column forms); `results/hunt2d-a.jsonl` | 361 decks, **21,957** checks | **0** (closest: reference = 0.99986 of the bound) | `axial_const_moment`: 100 in 16/37 decks; `no_geo_moment`: 96 in 17/37; `ends_only`: 34 in 10/37; **`axial_no_slope`: 0 — not visible**, here and again on 51 single columns under heavy self-weight (`results/mut2d-axial_no_slope-columns.jsonl`): the interior bound's own slack absorbs the N′v′ term, so this check cannot vouch for that term |
| 2 | 2D stability brackets λ_low ≤ λ_cr ≤ λ_high on the same families (tension members, axial loads, inclined) | `hunt2d_stab.py`, `results/stab2d.jsonl` | 259 decks: 258 lower and 256 upper bounds, box vertices | **0** (max λ_low/ref 0.9908; max ref/λ_high 0.99988) | ±5 % on the bracket: 46 of 56 decks |
| 3 | Stability of LARGE 2D frames on the CHOLMOD path (1875, 1920, 1980 unknowns) and one banded frame | `check_large_stability.py` vs a sparse shift-invert reference at 2 and 4 sub-elements; `results/large_stability.txt` | 4 frames | **0** (λ_low 0.3–0.4 % below the reference) | λ_low × 1.02: 4 of 4 |
| 4 | ZTL `zenergy.pd_ieee_float` on the CHOLMOD path directly: shifted 1D Laplacians, exactly known λ_min, n = 1600–3001, scrambled numbering, μ from 0.5 to 1.1 λ_min | `check_cholmod.py`, `results/cholmod.txt` | 200 calls | **0** false bounds; 80 of 80 refusals for μ > λ_min | a factorization that always succeeds: 80 false bounds |
| 5 | `conduction3d` two-sided bracket: closed forms (uniform; series layers = harmonic mean; parallel columns = arithmetic mean; a 1-voxel straight channel through an insulator), refine 1 and 2; random volumes with insulators and 3D checkerboards, where brackets at refine 1, 2, 3 must overlap | `check_conduction3d.py`, `results/conduction3d.txt` | 320 exact + 40 overlap | **0** | upper × 0.97: 320 exact + 10 overlap |
| 6 | `ltb.alpha_lower` / `alpha_upper` against the EXACT forked-member factor under uniform moment with constant N, (λM)² = i₀²(N_cr,z + λN)(N_cr,T + λN). Compression **and tension** (sweep I has N ≤ 0 only), I_w = 0 in 30 %, boxes of N and M, 2/4/8 sub-elements | `check_ltb.py`, `results/ltb.txt` | 130 (43 in tension) | **0** (closest lower/exact 0.99997) | lower × 1.05, upper × 0.95: 18 + 12 of 30 |
| 7 | EN 6.3.1 (`frame.judge_buckling_case`) at the verdict boundary: pin-ended columns with exact utilisation 0.9–1.1, all five curves, against a hand EN computation with Euler's N_cr. Both directions: false EARNED and false REFUTED | `check_en631.py`, `results/en631.txt` | 60 (29 EARNED, 31 REFUTED) | **0** | utilisation × 0.97: 40 of 40 |
| 8 | 3D second-order displacements (every free node, X/Y/Z), member \|σ\| from BOTH sides, and the stability bracket on random space frames (columns under axial self-weight, 1–2 elements per column, loaded beams, an inclined brace, THETA 0/90, IZZ ≠ IYY, flipped orientation, tolerance 0/0.5 % with box vertices) | `hunt3d.py` vs `ref3d.py` (own 12-DOF element, both planes, validated on cantilevers in both planes, an inclined member and Euler about the weak axis, to 1e-7); `results/hunt3d.jsonl` | 59 frames judged (29 with the 0.5 % box, up to 6 vertices each), **3,779** checks; 11 more OPEN (8 "critical factor not proved above 1", 2 "too slender between its nodes") | **0** | `no_geo_moment`: 32 in 5/19 frames; `axial_const_moment`: 3 in 1/19 (weakly visible) |
| 9 | `judge_ltb`'s moment convention at frame level: equal-and-opposite end moments read as uniform moment (α_LT,low 2.09177 ≤ exact 2.09356), equal moments as double curvature; the member-load parabola's sign (M_Ed equals the reference's max \|M_z\| for both signs of w: 95,000 and 50,000) | interactive, numbers here | 4 | 0 | none (a by-hand comparison, not a battery) |
| 10 | 2D sway imperfection with only member loads (QLOAD FY): suspected missing, but `read_deck` folds QLOADs into nodal loads; both ±1/200 cases ran, and the stand's REFUTED is correct (bound 215 MPa; reference 153.3 MPa > 130 MPa) | `decks/imp2d-column-selfweight*.txt` | 1 | 0 | — |
| 11 | Read only, not run: `frame3d.judge_interaction` (Annex B caps, k_yz = k_zz, k_zy = 0.8 k_yy, the strong-axis swap applied to n, m and k together, C_m = 1 as Table B.3's maximum); `with_imperfections` with LCOMB (`read_deck` materialises the combinations, so the imperfection decks judge the combinations) | — | — | nothing found | — |

### Notes

- **References.** `ref2d.py` and `ref3d.py` follow the stand's named premises: first-order axial forces in second
  order, Euler–Bernoulli, no torsional geometric term. A difference from the stand within those premises is a
  finding; a difference in a premise is not.
- **Tolerances.** A violation is counted only beyond 20× (stresses, moments, displacements) or 5–10× (eigenvalues)
  the reference's own convergence error, measured per deck by doubling its sub-elements.
- **Not done (time).** Plate brackets (`hypercircle.py`) beyond the battery's sweep F; 3D second-order STRESSES with
  RELEASE (the same cause as finding 1); `judge_interaction` runs.

## Files

    redteam/REPORT.md                 this report
    redteam/ref2d.py, ref3d.py        independent 2D / 3D second-order and buckling references
    redteam/ref_hinged.py             a straight member with hinges (finding 1's reference)
    redteam/check_release.py          finding 1, all three parts, with the independent values
    redteam/decks/                    the decks of finding 1 and of the imperfection check
    redteam/hunt2d.py, hunt2d_stab.py, hunt3d.py, check_*.py   the batteries and their mutations
    redteam/results/                  raw outputs (JSONL / text)
