"""Red team: ZTL zenergy.pd_ieee_float on its CHOLMOD path (n >= SPARSE_CHOL_FROM) against matrices with an EXACTLY
known lambda_min (shifted 1D Laplacians, scrambled numbering): the returned bound must never exceed lambda_min, and
every mu above lambda_min must be refused.  --mutant: CHOLMOD replaced by a "factorization" that always succeeds (a
broken PD test) — the check must then report false bounds.
    PYTHONPATH=. python3 redteam/check_cholmod.py [--mutant]"""
import math
import random
import sys
from fractions import Fraction as Fr

from ustand import judge_ztl  # noqa: F401
import zenergy as ZE

if "--mutant" in sys.argv:
    ZE._chol_sparse = lambda n, hi, lo, vals: 3
assert ZE._have_cholmod(), "CHOLMOD (scikit-sparse) not installed"
bad = tested = refused = 0
rng = random.Random(5)
for trial in range(40):
    n = rng.choice([1600, 2000, 3001])
    s = rng.choice([1e-6, 1e-3, 0.5, 3.0])
    lam_true = 2 - 2 * math.cos(math.pi / (n + 1)) + s
    rows = list(range(n)) + list(range(1, n)); cols = list(range(n)) + list(range(n - 1))
    vals = [2.0 + s] * n + [-1.0] * (n - 1)
    perm = list(range(n)); rng.shuffle(perm)
    r2 = [max(perm[a], perm[b]) for a, b in zip(rows, cols)]; c2 = [min(perm[a], perm[b]) for a, b in zip(rows, cols)]
    for mu_rel in (0.5, 0.9, 0.999, 1.001, 1.1):
        res = ZE.pd_ieee_float(n, r2, c2, vals, Fr(0), Fr(lam_true * mu_rel))
        tested += 1
        if res is not None and float(res) > lam_true * (1 + 1e-12):
            bad += 1
        if mu_rel > 1 and res is None:
            refused += 1
print(f"{'MUTANT ' if '--mutant' in sys.argv else ''}{tested} calls, {bad} false bounds, {refused} of 80 refusals above lambda_min")
