"""markov — PROVED bounds on reliability measures of a continuous-time Markov chain whose rates are known only as
ranges, judged by ZTL (2026-11-03, the curator: "Да. Звучит как хорошее расширение для стенда").

    python3 -m ustand.markov model.json [--need-mttf 8760] [--need-availability 0.99]
    python3 -m ustand.markov --solar spec.json --need-outage 0.01

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


# ------------------------------------------------------------------------------- REACH WITHIN N STEPS (DTMC, 2026-11-03)
def _greedy_row(succ, v, maximise):
    """The extreme of sum_j p_j v_j over {lo_j <= p_j <= hi_j, sum p_j = 1} (exact): every p_j at lo, the rest of the
    mass to the successors with the largest v first (maximise) or the smallest first — a linear program over a box cut
    by one equality, whose optimum this greedy order reaches exactly."""
    rest = 1 - sum(lo for _j, (lo, _hi) in succ)
    tot = sum(lo * v[j] for j, (lo, _hi) in succ)
    order = sorted(succ, key=lambda t: v[t[0]], reverse=maximise)
    if MUTANT.get("greedy_wrong_end"):                    # sabotage (tests only): the rest of the mass to the wrong end
        order = order[::-1]
    for j, (lo, hi) in order:
        take = min(hi - lo, rest)
        if take > 0:
            tot += take * v[j]
            rest -= take
    return tot


def _round(x, up, bits=60):
    """Outward to a dyadic with `bits` fractional bits (the operator is monotone: rounding up stays an upper bound)."""
    q = x * 2 ** bits
    n = q.numerator // q.denominator
    if up and n * q.denominator != q.numerator:
        n += 1
    return F(n, 2 ** bits)


def reach_bounds(model):
    """PROVED [low, high] of the probability that a discrete-time chain, started at `start`, enters `target` within
    `steps` steps — for EVERY chain whose transition probabilities lie in the stated ranges, even one that changes
    them from step to step (the bounds are the robust values: nature picks the worst / best row at every step).
    model: {"states", "start", "target": [...], "steps": N, "probs": [{"from", "to", "p": [lo, hi]}, ...]}; each row
    must admit a distribution (sum lo <= 1 <= sum hi). Exact rationals, rounded outward each step."""
    st = list(model["states"])
    ix = {x: k for k, x in enumerate(st)}
    tgt = {ix[x] for x in model["target"]}
    start, N = ix[model["start"]], int(model["steps"])
    rows = {k: [] for k in range(len(st))}
    for r in model["probs"]:
        rows[ix[r["from"]]].append((ix[r["to"]], _box(r["p"], f"probability {r['from']} -> {r['to']}")))
    for k, succ in rows.items():
        if k in tgt:
            continue
        lo, hi = sum(a for _j, (a, _b) in succ), sum(b for _j, (_a, b) in succ)
        if not succ or lo > 1 or hi < 1:
            raise ValueError(f"state {st[k]}: its probabilities admit no distribution (sum lo {lo}, sum hi {hi})")
    out = []
    for maximise in (False, True):
        v = [F(1) if k in tgt else F(0) for k in range(len(st))]
        for _ in range(N):
            v = [F(1) if k in tgt else _round(_greedy_row(rows[k], v, maximise), up=maximise)
                 for k in range(len(st))]
        out.append(min(max(v[start], F(0)), F(1)))
    return out[0], out[1]


def solar_outage(capacity_wh, load_wh, gain_wh, weather, start_charge_wh, start_weather, days, unit_wh):
    """PROVED [low, high] of the probability that an off-grid solar battery runs short on at least one of `days` days.
    Each day: the weather moves to w' (probabilities in ranges, `weather` = {w: {w': [lo, hi]}}); the battery gains
    gain_wh[w'] (a range) and pays load_wh (a range); charge = min(capacity, charge + gain - load); a day whose need
    is not covered is an OUTAGE (the target). The outage probability does not decrease as the charge, the gains or the
    load's complement decrease, so the HIGH bound takes the chain with every gain at its low end rounded DOWN to whole
    units and the load at its high end rounded UP (the charge rounded down), and the LOW bound the reverse; both by
    reach_bounds (every chain in the ranges, day-varying included). Exact rationals."""
    unit = F(unit_wh)
    cap_u = int(F(capacity_wh) / unit)                    # the capacity rounded DOWN to units: a smaller battery
    W = list(weather)
    def chain(worst):
        rd = (lambda x: (F(x) / unit).__floor__()) if worst else (lambda x: (F(x) / unit).__ceil__())
        ru = (lambda x: (F(x) / unit).__ceil__()) if worst else (lambda x: (F(x) / unit).__floor__())
        cap = cap_u if worst else (F(capacity_wh) / unit).__ceil__()
        if MUTANT.get("solar_round_wrong") and worst:     # sabotage (tests only): the worst chain rounded favourably
            rd, ru = ru, rd
        g = {w: rd(_box(gain_wh[w], f"gain {w}")[0 if worst else 1]) for w in W}
        L = ru(_box(load_wh, "load")[1 if worst else 0])
        c0 = min(cap, rd(start_charge_wh))
        states = [f"{c}|{w}" for c in range(cap + 1) for w in W] + ["OUT"]
        probs = []
        for c in range(cap + 1):
            for w in W:
                for w2, pr in weather[w].items():
                    nc = c + g[w2] - L
                    to = "OUT" if nc < 0 else f"{min(cap, nc)}|{w2}"
                    probs.append({"from": f"{c}|{w}", "to": to, "p": pr})
        # merge parallel edges (two weathers can land on the same state): sum their ranges
        merged = {}
        for r in probs:
            k = (r["from"], r["to"])
            lo, hi = _box(r["p"], "probability")
            a, b = merged.get(k, (F(0), F(0)))
            merged[k] = (a + lo, b + hi)
        probs = [{"from": a, "to": b, "p": [lo, hi]} for (a, b), (lo, hi) in merged.items()]
        return {"states": states, "start": f"{c0}|{start_weather}", "target": ["OUT"], "steps": days, "probs": probs}
    lo, _ = reach_bounds(chain(worst=False))
    _, hi = reach_bounds(chain(worst=True))
    return lo, hi


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


def clinic_joint(spec):
    """PROVED [low, high] of the probability that a clinic on ONE solar battery has at least one bad day in `days`:
    the battery feeds the FRIDGE first and the WATER PUMP only from what is left (the pump skips a day it cannot be
    paid for); the tank gets the pump's water and pays the clinic's daily need; one weather drives both.
    spec: {"battery_wh", "fridge_wh", "pump_wh", "pump_m3", "need_m3": [lo, hi] each, "tank_m3",
           "gain_wh": {w: [lo, hi]}, "weather": {w: {w2: [lo, hi]}}, "start_charge_wh", "start_tank_m3",
           "start_weather", "days", "unit_wh", "unit_m3", "fail": "any" | "power" | "water"}
    2026-11-03 FIX: the first version took every datum at its 'unfavourable end' — WRONG: the pump that runs only on
    what is left makes the failure non-monotone (a lighter pump runs more often and drains the battery; MEASURED
    counterexample: battery 1500 Wh, sun 1400-1700, cloud 500, fridge 400, pump 400-600 Wh, 6 days — the worst fixed
    data is the pump at 500 Wh, exact 0.26924, while the old 'high' bound said 0.25240). Now a stocks brick
    (ustand.stocks): every amount chosen by an adversary on the unit grid, no monotonicity assumed; amounts must be
    whole units (refused otherwise)."""
    from . import stocks as SK
    rg = lambda k: [F(x) for x in _box(spec[k], k)]
    if MUTANT.get("ends_fixed"):                          # sabotage (tests only): the first version's 'unfavourable
        lo_, hi_ = (lambda k: [F(_box(spec[k], k)[0])] * 2), (lambda k: [F(_box(spec[k], k)[1])] * 2)   # ends'
        spec = dict(spec, fridge_wh=hi_("fridge_wh"), pump_wh=hi_("pump_wh"), pump_m3=lo_("pump_m3"),
                    need_m3=hi_("need_m3"), gain_wh={w: [F(_box(v, "gain")[0])] * 2 for w, v in spec["gain_wh"].items()})
    pump = {"take": "battery", "amount": rg("pump_wh"), "then": [{"add": "tank", "amount": rg("pump_m3")}]}
    if MUTANT.get("clinic_pump_free"):                    # sabotage (tests only): the pump not paid from the battery
        pump = {"add": "tank", "amount": rg("pump_m3")}
    system = {"driver": {"start": spec["start_weather"], "p": spec["weather"]},
              "stocks": {"battery": {"capacity": spec["battery_wh"], "start": spec["start_charge_wh"],
                                     "unit": spec["unit_wh"]},
                         "tank": {"capacity": spec["tank_m3"], "start": spec["start_tank_m3"], "unit": spec["unit_m3"]}},
              "steps": [{"add": "battery", "amount": {w: [F(x) for x in _box(v, "gain")] for w, v in spec["gain_wh"].items()}},
                        {"take": "battery", "amount": rg("fridge_wh"), "fail": "power"}, pump,
                        {"take": "tank", "amount": rg("need_m3"), "fail": "water"}],
              "days": spec["days"],
              "fail_on": {"any": [], "power": ["power"], "water": ["water"]}[spec.get("fail", "any")]}
    return SK.fail_bounds(system)


def judge_solar(spec, need_outage_at_most):
    """'P(at least one short day) <= need' by ZTL over solar_outage's proved bracket. spec: {"capacity_wh",
    "load_wh": [lo, hi], "gain_wh": {w: [lo, hi]}, "weather": {w: {w2: [lo, hi]}}, "start_charge_wh",
    "start_weather", "days", "unit_wh"}."""
    from . import judge_ztl  # noqa: F401
    from znumjudge import parse_quantities, judge_sheet_claim
    lo, hi = solar_outage(spec["capacity_wh"], spec["load_wh"], spec["gain_wh"], spec["weather"],
                          spec["start_charge_wh"], spec["start_weather"], spec["days"], spec["unit_wh"])
    f = lambda x: f"{x.numerator}/{x.denominator}"
    qs, mk = parse_quantities(f"pout=[{f(lo)},{f(hi)}] earned:markov")
    r = judge_sheet_claim(f"pout <= {f(F(need_outage_at_most))}", qs, mk)
    return {"outage_probability": [float(lo), float(hi)],
            "verdict": r["disposition"] + (f" ({r['polarity']})" if r.get("polarity") else ""),
            "premise": "daily steps; weather a Markov chain with transition probabilities in the stated ranges (any "
                       "day-varying choice inside them); daily gain per weather and load in their ranges; the battery "
                       "counted in whole units of unit_wh, rounded against the claim on each side"}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    if argv[0] == "--solar":                              # python3 -m ustand.markov --solar spec.json --need-outage 0.01
        spec = json.load(open(argv[1]))
        need = argv[argv.index("--need-outage") + 1] if "--need-outage" in argv else "1"
        print(json.dumps(judge_solar(spec, need)))
        return 0
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
