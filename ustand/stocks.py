"""stocks — PROVED probability of failure of a system of STOCKS and FLOWS under a shared random driver (2026-11-03, the
curator: "Мы можем это масштабировать на весь стенд?… Делай.").

    python3 -m ustand.stocks system.json [--need-fail-at-most 0.01]

THE BRICK (a premise, stated in every output: amounts and stocks counted in whole units of each stock's `unit`):
    {"driver": {"start": "sun", "p": {"sun": {"sun": [lo, hi], "cloud": [lo, hi]}, ...}},   # e.g. the weather
     "stocks": {"battery": {"capacity": 2000, "start": 2000, "unit": 100}, "tank": {...}},
     "steps": [                                                   # applied in order every step, after the driver moves
        {"add": "battery", "amount": {"sun": [1800, 1800], "cloud": [500, 500]}},   # inflow by driver state (or [lo, hi])
        {"take": "battery", "amount": [400, 400], "fail": "power"},               # MUST: short -> a failure named
        {"take": "battery", "amount": [600, 600], "then": [{"add": "tank", "amount": [2, 2]}]},   # MAY: only if there is
        {"take": "tank", "amount": [1.5, 1.5], "fail": "water"}],                 #   enough, and then its consequences
     "days": 30, "fail_on": ["power", "water"]}                   # which named failures count (default: all)
An inflow is capped at the capacity. The probability asked: at least one counted failure within `days` steps.

THE PROOF. A step's driver row may be any distribution within its ranges (exactly: the greedy of markov.reach_bounds),
and every amount any multiple of its unit within its range — chosen ANEW each step by an adversary who has seen the
driver's move (max for the HIGH bound, min for the LOW). Robust Bellman over the finite state space (stock levels x
driver state), exact rationals rounded outward each step. So the bounds hold for every real system whose data lie in
the ranges (on the unit grid), fixed or varying from day to day — with NO monotonicity assumed: a MAY action (a pump
that runs only on what is left) makes the failure non-monotone in the data (more sun today can empty the battery for
tomorrow), and taking every datum at its 'unfavourable end' is then not the worst case.
"""
from __future__ import annotations

import itertools
import json
import sys
from fractions import Fraction as F

from .markov import _box, _greedy_row, _round

MUTANT = {}       # TEST-ONLY sabotage switches; empty = the real bounds
MAX_CHOICES = 4096


def _units(x, unit, what):
    q = F(x) / unit
    if q.denominator != 1:
        raise ValueError(f"{what}: {x} is not a whole number of units of {unit} — choose a unit that divides it "
                         "(the brick counts in whole units)")
    return int(q)


def compile_system(sys_):
    """-> (states, start index, transition function, driver rows); the transition of (state, next driver) is the SET
    of possible outcomes (next state index or 'BAD'), over every grid choice of every ranged amount."""
    drv = sys_["driver"]
    D = list(drv["p"])
    stocks = sys_["stocks"]
    names = list(stocks)
    unit = {k: F(v["unit"]) for k, v in stocks.items()}
    cap = {k: _units(v["capacity"], unit[k], f"{k} capacity") for k, v in stocks.items()}
    st0 = tuple(_units(stocks[k]["start"], unit[k], f"{k} start") for k in names)
    fail_on = set(sys_.get("fail_on") or [])
    def amount_choices(spec, stock, w2):
        a = spec["amount"]
        if isinstance(a, dict):
            a = a[w2]
        lo, hi = _box(a, f"amount on {stock}")
        lo_u, hi_u = _units(lo, unit[stock], f"amount on {stock}"), _units(hi, unit[stock], f"amount on {stock}")
        if MUTANT.get("endpoint_only"):                   # sabotage (tests only): the ends of each range only
            return sorted({lo_u, hi_u})
        return list(range(lo_u, hi_u + 1))
    # flatten the steps into a list of (kind, stock, spec, then-list); every ranged amount is a choice dimension
    def leaves(steps):
        out = []
        for s in steps:
            out.append(s)
            out += leaves(s.get("then", []))
        return out
    every = leaves(sys_["steps"])
    def outcomes(levels, w2):
        dims = [amount_choices(s, s.get("add") or s.get("take"), w2) for s in every]
        n = 1
        for d in dims:
            n *= len(d)
        if n > MAX_CHOICES:
            raise ValueError(f"{n} combinations of ranged amounts in one step (cap {MAX_CHOICES}): narrow the ranges "
                             "or coarsen the units")
        res = set()
        for combo in itertools.product(*dims):
            amt = {id(s): c for s, c in zip(every, combo)}
            lv = dict(zip(names, levels))
            bad = False
            def run(steps):
                nonlocal bad
                for s in steps:
                    if bad:
                        return
                    if "add" in s:
                        k = s["add"]
                        lv[k] = min(cap[k], lv[k] + amt[id(s)])
                    else:
                        k = s["take"]
                        need = amt[id(s)]
                        if lv[k] >= need:
                            lv[k] -= need
                            run(s.get("then", []))
                        elif "fail" in s:
                            if not fail_on or s["fail"] in fail_on:
                                bad = True
                            else:
                                lv[k] = 0                 # an uncounted failure: the stock is simply empty
            run(sys_["steps"])
            res.add("BAD" if bad else tuple(lv[k] for k in names))
        return res
    return names, cap, st0, D, outcomes


def fail_bounds(sys_):
    """PROVED [low, high] of P(at least one counted failure within `days`) — see the module doc."""
    names, cap, st0, D, outcomes = compile_system(sys_)
    rows = {w: [(w2, _box(r, f"driver {w} -> {w2}")) for w2, r in sys_["driver"]["p"][w].items()] for w in D}
    for w, succ in rows.items():
        lo, hi = sum(a for _j, (a, _b) in succ), sum(b for _j, (_a, b) in succ)
        if lo > 1 or hi < 1:
            raise ValueError(f"driver state {w}: its probabilities admit no distribution")
    grid = list(itertools.product(*[range(cap[k] + 1) for k in names]))
    if len(grid) * len(D) > 200000:
        raise ValueError(f"{len(grid) * len(D)} states: too many (coarsen the units)")
    S = [(lv, w) for lv in grid for w in D]
    idx = {s: i for i, s in enumerate(S)}
    trans = {}
    for lv in grid:
        for w2 in D:
            trans[(lv, w2)] = [("BAD" if o == "BAD" else o) for o in outcomes(lv, w2)]
    out = []
    for maximise in (False, True):
        v = [F(0)] * len(S)
        pick = max if maximise else min
        for _ in range(int(sys_["days"])):
            after = {(lv, w2): pick(F(1) if o == "BAD" else v[idx[(o, w2)]] for o in trans[(lv, w2)])
                     for lv in grid for w2 in D}
            v = [_round(_greedy_row([(w2, r) for w2, r in rows[w]], {w2: after[(lv, w2)] for w2 in D}, maximise),
                        up=maximise) for (lv, w) in S]
        out.append(min(max(v[idx[(st0, sys_["driver"]["start"])]], F(0)), F(1)))
    return out[0], out[1]


PREMISE = ("discrete steps; the driver a Markov chain with probabilities in the stated ranges (any step-varying choice); "
           "every amount a whole number of its stock's unit anywhere in its range, possibly different every step; "
           "the bounds are the robust worst / best over all of that")


def judge(sys_, need_fail_at_most):
    from . import judge_ztl  # noqa: F401
    from znumjudge import parse_quantities, judge_sheet_claim
    lo, hi = fail_bounds(sys_)
    f = lambda x: f"{x.numerator}/{x.denominator}"
    qs, mk = parse_quantities(f"pfail=[{f(lo)},{f(hi)}] earned:stocks")
    r = judge_sheet_claim(f"pfail <= {f(F(need_fail_at_most))}", qs, mk)
    return {"fail_probability": [float(lo), float(hi)],
            "verdict": r["disposition"] + (f" ({r['polarity']})" if r.get("polarity") else ""), "premise": PREMISE}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    sys_ = json.load(open(argv[0]))
    if "--need-fail-at-most" in argv:
        print(json.dumps(judge(sys_, argv[argv.index("--need-fail-at-most") + 1])))
    else:
        lo, hi = fail_bounds(sys_)
        print(json.dumps({"fail_probability": [float(lo), float(hi)], "premise": PREMISE}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
