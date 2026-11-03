# ztl-stand

(Named universal-stand until 2026-10-11; renamed by the curator. The package stays `ustand`, and bricks
written as `universal-stand/1` are read as before.)

**Start with SPEC.md** — the contract, how an AI agent should call the stand, what was measured against Z3, cvc5,
dReal and SCIP, and the limits. The full brick syntax: **BRICKS.md**. Licence: Apache-2.0 OR MIT (NOTICE). Needs ZTL
(github.com/inventor1975/ZTL) cloned beside this repository, or `USTAND_ZTL` pointing to it.

A foundation, not a product aimed at one goal. The far horizon: "here are the requirements and the factory's
capabilities — give me a realisation, or tell me why it is impossible". The start is the minimum that can be
leaned on.

## Bricks in (JSON)

The full reference for writing them, with pitfalls: **BRICKS.md**. Gaps found so far: **GAPS.md**.

| Brick | Carries |
|---|---|
| quantity | a name, a unit and a role: `given` (fixed by the world, optionally with a tolerance — must hold for every value in it) or `derived` (follows from the laws) |
| slot | a place in the design (`R1`) and the catalogs it may take an item from — the choice (there exists) |
| catalog | what the factory has: ITEMS, each with several FIELDS, each field with its own nominal and tolerance (resistance 1k ±1%, power rating 0.25 W). An item in a slot creates the quantities `R1.R`, `R1.P`. Rows are listed, or generated from an E-series |
| law | one equality in ZFL syntax, with its source (`"Vin - Vout == I*R1.R"`, "Ohm's law"; `"P1 == I*I*R1.R"`, "Joule heating") |
| requirement | a derived quantity, `within` / `<=` / `>=`, and a bound: a number, or a quantity such as `R1.P` (its least favourable value; at a witness point, its value there) |

Numbers are strings read as exact fractions.

## Verdict out (JSON)

- **EARNED**: a design (an item in every slot) whose required quantities stay inside the requirements for every value
  the tolerances allow, shown by SOUND ranges (a sound outer range suffices; exactness is needed only to refute), and
  confirmed by the checker: every corner inside, exact ranges equal, each nonlinear definition inside by its own bound.
- **REFUTED**: every design fails at a concrete point (its nominal, or a corner of its box). The closest design, its
  violating point and the overshoot are returned, and the point is recomputed by the checker.
- **OPEN**: neither could be shown.
- **STAND FAULT**: the judge and the checker disagree. The stand reports it instead of a verdict.

## Who does what

- **Judge: ZTL** (`ustand/judge_ztl.py` calls `ZTL/znumsolve.py` as it is). Its ranges are sound (never too narrow),
  which is enough to EARN; a range ZTL itself marks exact is also attained, which a refutation relies on. Whatever
  mathematics ZTL learns to prove, the stand inherits.
- **Checker** (`ustand/checker.py`) shares no code with the judge. It parses the laws itself and does exact rational
  arithmetic.
  - It always confirms a witness point.
  - It confirms a range by enumerating corners. That is the true range only in the class where every derived
    quantity is monotone in each single toleranced quantity, which is the judge's own exact class.
  - Corner enumeration is 2^n, so it is for small cases only.
- **Definitions** (`P1 == I*I*R1.R`): since ZTL 3a296b5 the judge bounds them itself (interval reading, sound, may be
  wide). The stand sends ZTL the linear laws first, then the definitions with the linear unknowns as the boxes ZTL
  gave them.
- **Forward step** (`ustand/forward.py`): a fallback, used only where ZTL leaves a quantity unbounded. It bounds by
  interval arithmetic and labels the result "outside ZTL". It is written separately from the checker.
- **Stand** (`ustand/stand.py`):
  - enumerates designs over the catalog;
  - drops a design whose nominal point already fails (that point is its witness);
  - judges the rest and compares the result with the requirements.

## Limits

The first version (2026-10-09) was linear-only and named no conflicts; both have changed (nonlinear laws
with functions, implicit laws, continuous amounts, certificates for an extreme inside the box, `minimal_conflicts`,
optimality). The current limits are in SPEC.md §7 and GAPS.md.

## Structures (2026-10/11): ANSYS-style decks judged by ZTL zenergy

Every verdict says its LEVEL (`scope` in the output) — a proof about a mesh is not a proof about a plate.

| Module | Deck | Proved, for every modulus in E(1 ± t) |
|---|---|---|
| `ustand.truss` | LINK1/LINK180 bars | displacements; `verdict` second order (the joints' P-delta, bars straight), `verdict_first_order` linear |
| `ustand.frame` | BEAM3 + `QLOAD` (uniform per length) | displacements and member stresses in SECOND-order theory of the Euler-Bernoulli continuum (`verdict`) and by EN 1993-1-1 5.2.2 (`verdict_en_method`); the critical load factor bracketed (`--stability`); EN 6.3.1 (`--buckling`), 6.3.3 (6.61) in-plane (`--interaction`); sway imperfection ±1/200 both ways |
| `ustand.plate` | CST triangles | displacements and stresses of the MESH (scope MESH) |
| `ustand.hypercircle` | plate + `TRAC` | the CONTINUUM plate: compliance, mean deflection, any boundary-segment average (Prager–Synge, τ checked exactly) |
| `ustand.adapt` | as hypercircle | refinement where the hypercircle's exact local error is large |
| `ustand.frame3d` | BEAM4 (12 DOF per member, N x y z; materials and sections by id, MAT / REAL; end releases RELEASE; uniform member loads QLOAD — displacements and first-order member stresses; EN 5.3.2 sway imperfections `with_imperfections`) | **3D phase, track 2, version 1**: SPACE FRAMES — every displacement as a proved range for every modulus in the box, FIRST ORDER; exact against the cantilever formulas in two planes and torsion, bit-identical to the 2D frame for a plane frame laid in 3D; LOAD CASES and combinations (`LC`, `LCOMB`) judged together, one factor and one proved lambda_min for all (20 cases on 7500 unknowns: 15 s instead of 72 s); member STRESSES at the 8 section corners and the elastic check |sigma| <= fy/gamma_M0 in every case (`judge_stress`); the critical load factor's PROVED lower bound in both bending planes (`stability_lower`, with axial member loads too; premise: no torsional / flexural-torsional buckling); PHYSICAL SECOND-ORDER displacements (with transverse member loads too) and member stresses of the continuum members (`second_order_disp`, `second_order_stress`); EN 6.3.1 flexural buckling with alpha_cr from the 3D stability (`judge_buckling`); EN 6.3.3 biaxial interaction (6.61) and (6.62), Annex B (`judge_interaction`, with member loads and, by default, EN 5.3.2's sway imperfection +-phi along X and Y since 2026-11-02; premise: no lateral-torsional buckling); EN 6.3.2 LATERAL-TORSIONAL buckling (`judge_ltb`, 2026-11-02: each member's alpha_LT PROVED from below, `ustand.ltb`, forks at the member ends — a named premise; I_w as R's 11th value) |
| `ustand.conduction3d` | a 3D voxel map (`.npy`) + phase conductivities | **the stand's 3D phase, track 1 (2026-11-02)**: the CONTINUUM conductance of the volume (ionic, electrical, thermal), two-sided and proved — upper from any piecewise-linear potential, lower from a face-flux field made EXACTLY conservative in integers (insulators of any topology allowed); `s_eff >= need` judged by ZTL |

Large systems: if `scikit-sparse` (CHOLMOD) is installed — optional; it needs the system's SuiteSparse headers,
`libsuitesparse-dev` — ZTL's positive-definiteness proofs use its supernodal Cholesky from 1500 unknowns, the same
theorem (Higham over any summation tree, ZTL lean/ZHigham); without it, the banded Cholesky (MEASURED 2026-11-02: a
2940-unknown space frame's stability 101 -> 35 s, the bound identical).

Named premises (said in the outputs): linear elasticity, Green's formula, IEEE 754 for the floating Cholesky,
second-order axial forces from the first-order analysis, straight truss bars, out-of-plane restraint for 6.3.3.
Axial member loads: stability and second-order DISPLACEMENTS (2D and 3D, since 2026-11-02); second-order member
STRESSES in 2D (2026-11-03: end moments with N_a G_a + N_b G_b, brackets < 0.01 % around an independent continuum
solve; the interior by a Dirichlet bound on M'' = N'v' + (N/EI)M, MEASURED 3-29 % above the reference on 1-2 elements
per member, 0.07-0.18 % on 8-16; in 3D per bending plane, the same brackets), also with a transverse load on the same
member (2026-11-03; battery sweep J: 1614 checks vs solve_bvp, 0 violations). Not yet: plate buckling. Lateral-torsional buckling: member level, 3D (`judge_ltb`, DESIGN-LTB.md).
3D phase: track 1 (conduction) in; track 2 (space frames, 6 DOF per node) in; track 3 (3D elasticity) in
(2026-11-03): `python3 -m ustand.elastic3d volume.npy --e 1:200e9 --nu 1:0.3 --need-max 150e9 --need-min 9e10` —
PROVED two-sided bounds on a voxel sample's apparent modulus (upper: P1 displacements; lower: an exactly admissible
Alfeld-split stress, hybridized + AMG: 32^3 voxels in 106 s, 15.6 GB; DESIGN-3D.md). Measured
(conduction3d, 2026-11-02): 16^3 random 50 % electrolyte in 0.5 s; voxel edge/corner contacts make the bracket close
slowly under uniform refinement (3D checkerboard: ratio 2.3 -> 1.4 at x4) — adaptive refinement is the next step.
Contacts by an edge or a corner only, where the other voxels insulate, carry no current in the continuum: since
2026-11-03 the potential is split there (an insulator/conductor checkerboard: upper 0.47 -> ~0, the truth; a 50 %
random 8^3 map: ratio upper/lower 4.0 -> 2.0).
Solver: smoothed-aggregation multigrid if `pyamg` is installed (optional; 64^3 voxels 141 s -> 22 s), Jacobi CG
otherwise — the solver only chooses the fields, the bounds stay proved either way.
The algebra of every bound is in ZTL's Lean (zero axioms): ZNet, ZEnergy, ZRound, ZHigham, ZFloatPath, ZStability,
ZChi, ZHypercircle.

## Run

    python3 -m ustand.stand examples/divider-1pct-req-1pct.json
    PYTHONPATH=. python3 -m tests.run_parallel --jobs 24     # USTAND GREEN — the suite on 24 cores (~10 min)
    PYTHONPATH=. python3 tests/test_stand.py                 # the same, one core (~21 min)

The examples are a 5 V → 2.5 V divider from the E24 series:

| Requirement | Parts | Verdict |
|---|---|---|
| ±1% | 1% | EARNED |
| ±0.5% | 1% | REFUTED |
| ±0.5% | 1% or 0.1% | EARNED on 0.1% parts |
| ±1%, ≥ 24 mA, each R within its power rating | 1% at 1/16 W | REFUTED: at R1 = R2 = 99 Ω, P1 = 25/396 W > 1/16 W |
| the same | 1% at 1/16 W or 1/4 W | EARNED: 27 Ω / 27 Ω at 1/4 W, P ≤ 0.2385 W |
