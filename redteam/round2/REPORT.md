# Red team, round 2 — 2026-11-03

Target: a FALSE BOUND or a FALSE VERDICT in the code added since round 1 — mainly `ustand/elastic3d.py` (3D
elasticity, both bounds) and `ustand/kuhn_split.py`, plus RELEASE on whole frames after the fix dc0367f.
- Stand at `6faeec1`, ZTL at `6d1f7ea`.
- Python 3.13, 4 CPUs, pyamg 5.4.1.
- Nothing in `ustand/` or ZTL was modified; every file of this round is under `redteam/round2/`.

**Smoke.**
- `python3 -m tests.run_parallel --jobs 2`: 396 ok, 0 failed, **USTAND GREEN** (809 s).
- `bench/night/verify_all.py --jobs 2 --scale 0.2`: sweeps A–L show 0 violations, and every `-MUT` row shows
  violations, including K-MUTR, L-MUTE and L-MUTU.
- Logs: `results/smoke-*`.

**Result: 1 confirmed finding** (an input-validation hole that yields false bounds and a false EARNED). Every other
class I tried held. The mathematics of the two elasticity bounds held everywhere I could test it:
- the element was re-derived independently;
- the exact phase was read line by line and probed with adversarial maps;
- hundreds of samples were checked against an independent FE.

I stopped with one finding, after the brief's targets were covered and before the 3-hour limit, not at 3 findings.

---

## FINDING 1 — an E box written high-to-low is accepted, and the proved bounds are false (a false EARNED)

**Cause.**
- `elastic3d` reads a phase's modulus box as `E[0]` .. `E[-1]` with no ordering check:
  - `_lame_hi` takes `E_hi = E[-1]` for the UPPER bound;
  - `_phase_soft` takes `E_lo = E[0]` for the LOWER bound;
  - `material()` tests `E[1] == 0` for a pore.
- Poisson's ratio is checked (`-1 < nu_lo <= nu_hi < 1/2`; a reversed ν box is refused); E is not.
- Both the API (`phases={k: {"E": [205, 200]}}`) and the CLI (`--e 1:205,200`) accept a reversed E box. The upper
  bound is then computed at the box's LOW end and the lower bound at its HIGH end.
- `conduction3d.judge` reads its phase box the same way (`s[0]`, `s[-1]`).

### 1a. False bounds (homogeneous sample, truth exact)

- **Sample:** `redteam/round2/samples/homog-3x2x2.npy`, all phase 1, so E_app = E exactly. The box E ∈ [100, 200]
  has true E_app over it = [100, 200].
- **Command:** `PYTHONPATH=. python3 -m ustand.elastic3d redteam/round2/samples/homog-3x2x2.npy --e 1:200,100 --nu 1:0.3 --need-max 150`
- **Stand:** upper **100.00**, lower **200.00**: both false over the box.
- **Box written ascending** (`1:100,200`): [100.00, 200.00], which is correct.
- **Verdict here:** ZTL's "E" (the bracket is inverted). The API's `upper()` and `lower()` return the false values
  as proved bounds.
- **conduction3d:** the same, lower 2.0 and upper 1.0 on a box whose truth spans [1, 2].

### 1b. A FALSE EARNED (a narrow reversed box: the bracket does not invert)

- **Sample:** `redteam/round2/samples/pore-3x3x3.npy`, a 3³ cube with a central cubic pore.
- **Phases:** phase 1 with E written `[205, 200]` (the box E ∈ [200, 205]) and ν = 0.3; phase 0 is a pore.
- **Stand:** with earned phases, `E3.judge(V, phases, need_min=188)`: **E_app ≥ 188 EARNED** with the bracket
  [188.18, 191.32].
  - The lower bound is computed at E = 205: 183.594 × 205/200 = 188.18.
  - Through the CLI the same input gives "ON CREDIT (toward T)", only because the CLI marks every phase unearned.
- **Independent value:** at E = 200, a point of the box, the true E_app is **≤ 185.974**. That is the energy of a
  conforming trilinear displacement on the 3³ sample with every voxel cut into 8³ cubes
  (`redteam/round2/ref_elastic.py`). A conforming field's energy is ≥ the true energy at any mesh. The sequence
  converges from above: 187.751 (r = 2), 186.525 (r = 4), 185.974 (r = 8).
- **Size:** the requirement fails at E = 200 by at least **2.03 (1.1 %)**. The same box written `[200, 205]` gives
  [183.59, 196.10] and OPEN.
- **Reproduce:** `PYTHONPATH=. python3 redteam/round2/check_box_order.py` (output `results/box_order.json`).

**Severity.** This needs an input written high-to-low. But the stand accepts it silently, and for ν refuses the
same thing aloud. Every other module's input checks refuse malformed boxes with a BRICK ERROR.

**Suggested repair (not done):** refuse (or sort) `E[0] > E[-1]` in `material`, `_lame_hi` and `_phase_soft`, and
`s[0] > s[-1]` in `conduction3d.judge`.

---

## Classes tried that held (counts, and the mutation that shows each check can see a broken bound)

| # | Class | Script / data | Cases | Violations | Mutation → seen |
|---|---|---|---|---|---|
| 1 | **The Alfeld-split element, re-derived independently.** numpy SVD nullspace, my own constraint assembly and a degree-2 exact quadrature (not sympy). On all 6 Kuhn types: space dimension 30, trace rank 30 (a bijection), every trace balanced (my own force/moment and the JSON's BAL, about 1e-15), and gᵀS₁g = ∫τ:τ, gᵀS₂g = ∫(tr τ)² to about 1e-14. The outward n2 = twice the area, as listed | `check_kuhn.py`, `results/kuhn.txt` | 6 types × 25 random element stresses | **0** | S₁ × 0.999: caught on 6/6 types |
| 2 | **elastic3d, random small samples** (KKT path): 2–4 voxels a side, pores, 1–3 solid phases, contrast up to 10⁴, E boxes up to ×10, ν boxes [0.45, 0.499], [−0.9, −0.5], [−0.3, 0.49] and others. LOWER ≤ Q1 at every soft corner of the box (r = 1, 2; Q1 ≥ truth, a hard check); UPPER ≥ the Aitken-extrapolated truth at every stiff corner (r = 1, 2, 4; a flag) | `hunt_elastic.py` vs `ref_elastic.py` (own Q1 hex FE, exact on homogeneous / Voigt / Reuss to 1e-14); `results/hunt_elastic.jsonl` | 150 samples | **0** | `e_low` (upper at E_lo): 10 upper violations in 30; `lower_e_high`: 72 lower violations in 30 |
| 3 | **Larger samples, the HYBRIDIZED path, refine 2.** 4–7 voxels a side, half with `force_hybrid`, some at refine 2 | `hunt_elastic_big.py`, `results/hunt_elastic_big.jsonl` | 40 samples | **0** | `lower_e_high`: 6 of 15 |
| 4 | **Adversarial maps for the exact phase:** an island without a grip, a stub on one grip only, two spanning components, a corner-only staircase, an edge-contact zigzag (lower = 0, as the continuum: an edge carries no force), a 3D checkerboard at contrast 10⁶ with ν ∈ [−0.5, 0.49], a stiff channel at SI scale (2×10¹¹ / 10⁵ Pa) | `check_elastic_special.py`, `results/elastic_special.txt` | 7 | **0** | lower × 1.5: caught on 5/7 (not on the two whose lower is 0 or far below) |
| 5 | **Refinement and the hybrid path on one sample** (central pore 3³): refine 1, 2, 2-hybrid, 3 give [183.59, 191.32], [184.80, 189.20], the same, [185.11, 188.01]; every lower ≤ Q1(r = 8) = 185.974 | interactive, numbers here | 4 | 0 | (covered by 2–3) |
| 6 | **`judge` verdicts at the boundary** on exact-truth samples over boxes (homogeneous E ∈ [100, 200]; Voigt; Reuss), need_max / need_min at the true extremes × (1 ∓ 1e-9, 1e-6, 1e-3) and beyond the range: EARNED must hold at every box point, REFUTED fail at every one | `check_judge.py`, `results/judge.txt` | 54 verdicts (EARNED, OPEN, REFUTED) | **0** wrong | bracket narrowed by 1e-5 relative: 8 wrong |
| 7 | **Extreme scales:** E = 1e-300 gives valid, wide bounds; subnormal E (3e-320, 5e-324) raises, not a false bound | interactive | 4 | 0 | — |
| 8 | **RELEASE on WHOLE space frames after dc0367f:** second-order displacements (every free node), member \|σ\| from both sides, the stability bracket; random hinges on beams (MZ, MY or both, one or both ends) and on column ends; tolerance 0 / 0.5 % with box vertices | `hunt3d_rel.py` vs `ref3d_rel.py` (own 3D FE with member-owned released rotations; Euler 0.88573 and fixed–pinned 2.12003 reproduced); `results/hunt3d_rel.jsonl` | 48 frames, 336 hinges, **3,558** checks (26 frames with the box) | **0** | `drop_release` (round 1's bug): 201 in 11/11 frames; `no_geo_moment`: 7 in 2/8 |
| 9 | **EN 6.3.3 and LTB inputs on RELEASED members:** `judge_interaction`'s M_a_max, M_b_max, N_Ed_max and `judge_ltb`'s M_Ed_max ≥ the reference's first-order max along the member (φ = 0); with and without the beams' transverse member loads (the clamped-beam end moment and parabola on a hinged beam) | `check_released_en.py`, `results/released_en*.jsonl` | EN_COUNTS | **0** | moments × 0.95: EN_MUT |
| 10 | **Code reading:** dc0367f passes the member to all 11 `_form3`/`_glob3` call sites; `_rel_key`'s planes and signs match `energy_system`'s `rot()`. In `_exact_lower`: shared faces cancel in force and moment, so a root's residual is (F_x, M_y, M_z) only and fits a grip face's normal values; Kuhn-path node ids increase, so both tets index a shared face's vertices alike; free faces, pore walls and grip tangentials are closed slots; islands total 0; Fres is the x = nx resultant | — | — | nothing found | — |

**Notes.**
- **The reference.** `ref_elastic.py` (trilinear hexahedra, 2×2×2 Gauss) reports vᵀKv with the *unshifted* K at a
  field satisfying the grips. That is a conforming displacement, so its value is ≥ the true E_app at every mesh,
  including at voxel edge contacts, which it bridges. This is what makes "lower ≤ Q1" a hard test rather than a
  convergence judgement.
- **The upper-side check** relies on extrapolation; it was used to flag only, and nothing was flagged.
- **The 7 "violations"** in the first run of class 9 were float noise: reference moments of 1e-6 N·m at hinged ends,
  against frame moments of 10⁴–10⁵. They are not counted. The check now uses a noise floor of 1e-9 × the frame's
  largest moment, and the run was repeated.

## Files

    redteam/round2/REPORT.md                      this report
    redteam/round2/ref_elastic.py                 independent Q1 hexahedral elasticity (an upper bound of the truth)
    redteam/round2/ref3d_rel.py                   independent space frame with end releases
    redteam/round2/check_box_order.py             FINDING 1 (both parts)
    redteam/round2/check_kuhn.py                  the element re-derived
    redteam/round2/hunt_elastic*.py, check_elastic_special.py, check_judge.py, hunt3d_rel.py, check_released_en.py
    redteam/round2/samples/                       the .npy samples of the finding
    redteam/round2/results/                       raw outputs, smoke logs
