"""markov — PROVED bounds on reliability measures of a continuous-time Markov chain whose rates are known only as
ranges, judged by ZTL (2026-11-03, the curator: "Да. Звучит как хорошее расширение для стенда").

    python3 -m ustand.markov model.json [--need-mttf 8760] [--need-availability 0.99]

THE MODEL (a premise, stated in every output): a continuous-time Markov chain — exponential holding times; states;
transitions i -> j with a rate known to lie in [lo, hi] (each rate independently anywhere in its range); the set of
UP states; for the time to failure, a start state. model.json:
    {"states": ["2up", "1up", "down"], "up": ["2up", "1up"], "start": "2up",
     "rates": [{"from": "2up", "to": "1up", "rate": [0.002, 0.003]}, ...]}

MTTF (mean time from the start to the first DOWN state): t solves A t = 1 on the up states, A = -Q restricted to them
(a nonsingular M-matrix when a down state is reachable from every up state). A CERTIFICATE T (rationals) is checked
for EVERY rate in the box at once: (A T)_i = sum_j q_ij (T_i - T_j) (T_j = 0 for down j) is linear in each q_ij,
so its minimum over the box sits at the vertex q_ij = lo if T_i - T_j > 0 else hi — one exact check per state.
    min_box (A T)_i >= 1 for all i  =>  A (T - t) >= 0  =>  T >= t (A^-1 >= 0)    : an UPPER bound for every rate;
    max_box (A T)_i <= 1 for all i  =>  T <= t                                    : a LOWER bound.
AVAILABILITY (the long-run fraction of time in UP; r = 1 on up, 0 on down): a certificate (g, h) with
    r_i + sum_j q_ij (h_j - h_i) <= g for all i and every rate in the box (max at the vertex by the sign of h_j - h_i)
gives, for ANY stationary distribution pi of ANY chain in the box (pi >= 0, pi Q = 0, sum 1),
    pi r = pi (r + Q h) <= g : an UPPER bound; >= g with the inequalities reversed: a LOWER bound.
The certificates are FOUND in floats (policy iteration over the box's vertices), loosened by a hair, rounded to
rationals and CHECKED exactly; the search cannot make a bound wrong, only loose.
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction as F

import numpy as np

MUTANT = {}       # TEST-ONLY sabotage switches; empty = the real bounds


def _box(v, what):
    lo, hi = (F(v[0]), F(v[-1])) if isinstance(v, (list, tuple)) else (F(v), F(v))
    if lo > hi:
        raise ValueError(f"{what}: the range [{v[0]}, {v[-1]}] is written high-to-low — write it [low, high]")
    if lo < 0:
        raise ValueError(f"{what}: a rate is >= 0")
    return lo, hi


def load(model):
    """-> (states, up set, start, {(i, j): (lo, hi)}) with states as indices."""
    st = list(model["states"])
    ix = {s: k for k, s in enumerate(st)}
    if len(ix) != len(st):
        raise ValueError("states: names repeat")
    up = {ix[s] for s in model["up"]}
    R = {}
    for r in model["rates"]:
        i, j = ix[r["from"]], ix[r["to"]]
        if i == j:
            raise ValueError(f"rate {r['from']} -> itself")
        if (i, j) in R:
            raise ValueError(f"rate {r['from']} -> {r['to']} given twice")
        R[(i, j)] = _box(r["rate"], f"rate {r['from']} -> {r['to']}")
    start = ix[model["start"]] if "start" in model else None
    return st, up, start, R


def _pick(R, i, diff, want_min):
    """The vertex rates of state i's outflows minimising (want_min) or maximising sum_j q_ij diff_j."""
    out = {}
    for (a, j), (lo, hi) in R.items():
        if a != i:
            continue
        d = diff(j)
        if MUTANT.get("vertex_flip"):                     # sabotage (tests only): the wrong vertex
            want = not want_min
        else:
            want = want_min
        out[j] = (lo if d > 0 else hi) if want else (hi if d > 0 else lo)
    return out


# ------------------------------------------------------------------------------------------------------------ MTTF
def _mttf_policy(n, up, R, upper):
    """Policy iteration in floats: the extreme expected time to DOWN over the box (upper: the slowest way down)."""
    U = sorted(up)
    pos = {s: k for k, s in enumerate(U)}
    T = np.ones(len(U))
    for _ in range(200):
        Tget = lambda j: T[pos[j]] if j in pos else 0.0
        A = np.zeros((len(U), len(U)))
        for i in U:
            q = _pick(R, i, lambda j: Tget(i) - Tget(j), want_min=upper)    # upper: the smallest (A T)_i
            for j, v in q.items():
                A[pos[i], pos[i]] += float(v)
                if j in pos:
                    A[pos[i], pos[j]] -= float(v)
        try:
            Tn = np.linalg.solve(A, np.ones(len(U)))
        except np.linalg.LinAlgError:
            return None
        if np.allclose(Tn, T, rtol=1e-13, atol=0):
            return Tn
        T = Tn
    return T


def _mttf_check(up, R, Tq, upper):
    """Exact: (A T)_i over the whole box >= 1 (upper) / <= 1 (lower) for every up state."""
    get = lambda j: Tq.get(j, F(0))
    for i in up:
        q = _pick(R, i, lambda j: get(i) - get(j), want_min=upper)
        AT = sum((v * (get(i) - get(j)) for j, v in q.items()), F(0))
        if (upper and AT < 1) or (not upper and AT > 1):
            return False
    return True


def mttf_bounds(model):
    """PROVED [low, high] of the mean time from the start to the first DOWN state, for every rate in the box."""
    st, up, start, R = load(model)
    if start is None or start not in up:
        raise ValueError("MTTF needs a start state among the up states")
    U = sorted(up)
    out = []
    for upper in (False, True):
        T = _mttf_policy(len(st), up, R, upper)
        if T is None or not np.all(np.isfinite(T)) or np.any(T <= 0):
            return None, None, "no proof: a down state is not reached from every up state at some rate in the box"
        for k in range(60):
            slack = 1 + (2.0 ** -40) * (2 ** k) * (1 if upper else -1)
            Tq = {s: F(float(T[p]) * slack) for p, s in enumerate(U)}
            if _mttf_check(up, R, Tq, upper):
                out.append(Tq[start])
                break
        else:
            return None, None, "no certificate found"
    return out[0], out[1], "ok"


# ---------------------------------------------------------------------------------------------------- AVAILABILITY
def _avail_policy(n, up, R, upper):
    """Policy iteration (average reward, unichain) in floats: the extreme long-run fraction of time UP."""
    r = np.array([1.0 if i in up else 0.0 for i in range(n)])
    h = np.zeros(n)
    g = 0.0
    for _ in range(200):
        Q = np.zeros((n, n))
        for i in range(n):
            q = _pick(R, i, lambda j: h[j] - h[i], want_min=not upper)     # upper: the largest r + Q h
            for j, v in q.items():
                Q[i, j] += float(v); Q[i, i] -= float(v)
        # r + Q h = g 1, h_0 = 0: unknowns (g, h_1..h_{n-1})
        M = np.zeros((n, n)); M[:, 0] = -1.0; M[:, 1:] = Q[:, 1:]
        try:
            x = np.linalg.lstsq(M, -r, rcond=None)[0]
        except np.linalg.LinAlgError:
            return None
        gn, hn = x[0], np.r_[0.0, x[1:]]
        if np.allclose(hn, h, rtol=1e-13, atol=1e-15) and abs(gn - g) < 1e-15:
            return gn, hn
        g, h = gn, hn
    return g, h


def _avail_check(n, up, R, g, h, upper):
    for i in range(n):
        q = _pick(R, i, lambda j: h[j] - h[i], want_min=not upper)
        val = (1 if i in up else 0) + sum((v * (h[j] - h[i]) for j, v in q.items()), F(0))
        if (upper and val > g) or (not upper and val < g):
            return False
    return True


def availability_bounds(model):
    """PROVED [low, high] of the long-run fraction of time in the UP states, for every rate in the box."""
    st, up, _start, R = load(model)
    n = len(st)
    out = []
    for upper in (False, True):
        res = _avail_policy(n, up, R, upper)
        if res is None:
            return None, None, "no certificate found"
        g, h = res
        hq = [F(float(x)) for x in h]
        for k in range(60):
            gq = F(float(g)) + F(1, 2 ** 40) * 2 ** k * (1 if upper else -1)
            if _avail_check(n, up, R, gq, hq, upper):
                out.append(min(max(gq, F(0)), F(1)))
                break
        else:
            return None, None, "no certificate found (a chain with several closed classes: not modelled)"
    return out[0], out[1], "ok"


PREMISE = ("continuous-time Markov chain (exponential holding times), each rate anywhere in its stated range "
           "independently; long-run availability over any stationary distribution")


def judge(model, need_mttf=None, need_availability=None):
    from . import judge_ztl  # noqa: F401
    from znumjudge import parse_quantities, judge_sheet_claim
    f = lambda x: f"{x.numerator}/{x.denominator}"
    out = {"premise": PREMISE}
    if need_mttf is not None or "start" in model:
        lo, hi, note = mttf_bounds(model)
        out["mttf"] = [float(lo), float(hi)] if lo is not None else None
        out["mttf_note"] = note
        if need_mttf is not None:
            if lo is None:
                out["verdict_mttf"] = "OPEN"
            else:
                qs, mk = parse_quantities(f"mttf=[{f(lo)},{f(hi)}] earned:markov")
                r = judge_sheet_claim(f"mttf >= {f(F(need_mttf))}", qs, mk)
                out["verdict_mttf"] = r["disposition"] + (f" ({r['polarity']})" if r.get("polarity") else "")
    lo, hi, note = availability_bounds(model)
    out["availability"] = [float(lo), float(hi)] if lo is not None else None
    out["availability_note"] = note
    if need_availability is not None:
        if lo is None:
            out["verdict_availability"] = "OPEN"
        else:
            qs, mk = parse_quantities(f"av=[{f(lo)},{f(hi)}] earned:markov")
            r = judge_sheet_claim(f"av >= {f(F(need_availability))}", qs, mk)
            out["verdict_availability"] = r["disposition"] + (f" ({r['polarity']})" if r.get("polarity") else "")
    return out


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    model = json.load(open(argv[0]))
    nm = na = None
    i = 1
    while i < len(argv):
        if argv[i] == "--need-mttf":
            nm = argv[i + 1]; i += 2
        elif argv[i] == "--need-availability":
            na = argv[i + 1]; i += 2
        else:
            raise SystemExit(f"unknown argument {argv[i]}")
    print(json.dumps(judge(model, nm, na)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
