"""GROUP PRUNING — refute whole blocks of the catalog at once (blind test 3, c11: 2 M panel-count triples
were killed at 15 min, the round-2 gearbox at 54 000; approved by the curator 2026-10-10).

A GROUP is, per slot, a contiguous run of its items (in catalog order). Its HULL replaces every field by the
box that covers all items of the run (with their tolerances). A requirement read over the hull and found
wholly past its bound is violated by every design of the group, at every point of its box: every design in it
is REFUTED, at once. Undecided groups are halved (the slot with the most items) down to single designs, which
go to the ordinary judging.

The proof of a pruned group is TWO enclosures, both wholly past the bound: ZTL's reading of the laws over the
hull, and the checker's own interval reading (shares no code with ZTL). Version 1 prunes only where both can
read: every derived quantity defined explicitly (`X == expression`, or an implicit law) — or a LINEAR SYSTEM, the
checker reading each requirement quantity through its own Cramer solution (2026-10-10) — numeric requirement
bounds, no `computed`. Anything else is simply not pruned — the designs are judged one by one as before.
"""
from __future__ import annotations

import ast
import itertools
from fractions import Fraction as F

from . import bricks as B
from . import checker as C
from . import forward as W
from . import judge_ztl as J
from . import units as U

PRUNE_MIN = 2000          # combinations below this are judged one by one (pruning would only add cost)
MAX_GROUPS = 200000
GIVE_UP_AFTER = 1000     # groups read with nothing pruned: pruning is not paying here
MIN_READ = 128           # a group smaller than this goes to the ordinary judging unread. MEASURED 2026-10-10,
                         # seconds at MIN_READ 2 / 32 / 128 / 512 / 2048 (2 = the old rule, every group read):
                         #   T-network 110k (linear system)  76.4 / 14.5 / 11.1 / 12.0 / 13.9  (unpruned 15.1)
                         #   s1 divider 57.6k                17.4 /  9.5 /  7.6 /  8.6 / 10.9
                         #   s2 three resistors 885k        260.8 / 78.9 / 81.1 / 91.7 / 101.9
                         #   s3 acoustics 2M                 18.0 / 19.8 / 20.1 / 19.0 / 18.3
                         # a group read costs ~ms; a small group's designs are cheaper judged one by one
COUNT_EXACT = 20000      # a pruned group larger than this is reported as 'up to n' designs under "where"
GIVE_UP_SECONDS = 60     # and by TIME: nothing pruned in this long, the plain enumeration takes over (blind test 5,
                         # c04: four implicit laws per group read, 5-16 min of silence before the first design)
PROGRESS_EVERY = 30      # seconds between progress lines on stderr while groups are read


def _scale(unit):
    return U.parse(unit)[0] if unit else F(1)


def _field_box(spec, scale):
    """An item's field as (lo, hi) in SI, or None for a label."""
    if spec[0] == "label":
        return None
    if spec[0] == "range":
        return spec[1] * scale, spec[2] * scale
    nom, tol = spec
    a, c = nom * scale * (1 - tol), nom * scale * (1 + tol)
    return min(a, c), max(a, c)


def hull_frame(b, options, group):
    """fixed, boxes for a group: givens as in stand.frame, every slot field the hull of its run's items."""
    from .stand import frame
    first = {s: options[s][lo] for s, (lo, hi) in group.items()}
    fixed, boxes, derived, grounds = frame(b, first, with_computed=False)
    for s, (lo, hi) in group.items():
        if hi == lo:
            continue
        cats = {options[s][i][0] for i in range(lo, hi + 1)}
        if len(cats) != 1:
            return None                       # a run across two catalogs: split it first
        cat = cats.pop()
        fu = B.field_units(b["catalog"][cat])
        for f in options[s][lo][1]:
            name = B.ident(f"{s}.{f}")
            los, his = [], []
            for i in range(lo, hi + 1):
                bx = _field_box(options[s][i][1][f], _scale(fu.get(f)))
                if bx is None:
                    break
                los.append(bx[0]); his.append(bx[1])
            else:
                a, c = min(los), max(his)
                fixed.pop(name, None); boxes.pop(name, None)
                if a == c:
                    fixed[name] = a
                else:
                    boxes[name] = (a, c)
    return fixed, boxes, derived, grounds


def _explicit(laws, derived):
    """{X: rhs} when EVERY derived quantity has its own law `X == rhs` (X not in rhs), else None."""
    out = {}
    for law in laws:
        tree = ast.parse(law, mode="eval").body
        l, r = tree.left, tree.comparators[0]
        if not (isinstance(l, ast.Name) and l.id in derived and l.id not in
                {n.id for n in ast.walk(r) if isinstance(n, ast.Name)}) or l.id in out:
            return None
        out[l.id] = law
    return out if set(out) == set(derived) else None


_DEFS = {}


def _defs(laws, derived, qs):
    """The checker's definitions to read: every derived quantity's own law when each has one (_explicit); else,
    for a LINEAR SYSTEM (2026-10-10), each requirement quantity solved by the checker's own Cramer rule
    (checker.explicit_expression — symbolic, no ZTL code). None when neither works: not pruned."""
    d = _explicit(laws, derived)
    if d is not None:
        return d
    key = (tuple(laws), frozenset(derived), tuple(sorted(qs)))
    if key not in _DEFS:
        out = {}
        try:
            for q in qs:
                out[q] = C.explicit_expression(laws, derived, q)     # an ast (its constants are Fractions)
        except (C.CheckError, RecursionError):
            out = None
        _DEFS[key] = out
    return _DEFS[key]


def ztl_ranges(laws, fixed, boxes, derived, grounds):
    """ZTL's enclosures of the derived quantities over the box (implicit laws by zimplicit)."""
    out = {}
    impl = [l for l in laws if "implicit(" in l]
    rest = [l for l in laws if "implicit(" not in l]
    dboxes = dict(boxes)
    for law in impl:
        n = law.split("==")[0].strip()
        got, _how, _ = J.implicit(law.split("==", 1)[1].strip(), fixed, boxes, grounds)
        if got is None:
            return None
        out[n] = got
        dboxes[n] = got
    names = [d for d in derived if d not in out]
    if rest:
        got, _log, _ = J.judge(rest, fixed, dboxes, names, grounds)
        for d, (lo, hi, _) in got.items():
            out[d] = (lo, hi)
    return out


def checker_ranges(defs, fixed, boxes):
    """The checker's own enclosures: each explicit definition read by its interval arithmetic, in dependency
    order (a definition that needs one not yet read waits for the next round)."""
    rng = {n: (v, v) for n, v in fixed.items()}
    rng.update(boxes)
    todo = {d: (law if isinstance(law, ast.AST) else ast.parse(law, mode="eval").body.comparators[0])
            for d, law in defs.items()}
    out = {}
    while todo:
        done = []
        for d, rhs in todo.items():
            try:
                rng[d] = out[d] = C._ivl(rhs, rng)
                done.append(d)
            except (C.CheckError, ZeroDivisionError):
                pass
        if not done:
            break
        for d in done:
            del todo[d]
    return out


def _numeric(r):
    vals = r["value"] if isinstance(r["value"], list) else [r["value"]]
    try:
        [B.num(v) for v in vals]
        return True
    except (ValueError, ZeroDivisionError, TypeError):
        return False


_PROBE = {}


def _probe(bm, laws, fixed, boxes, derived, q):
    """For each SHARED toleranced quantity (not a slot field): does raising it raise q? Read once at the
    centre of the box by the checker's exact solution (search side — any answer is sound, see below)."""
    key = (id(bm), q)
    if key in _PROBE:
        return _PROBE[key]
    mid = {n: (lo + hi) / 2 for n, (lo, hi) in boxes.items()}
    up = {}
    for p in boxes:
        if "__" in p:
            continue
        vals = []
        for end in boxes[p]:
            try:
                v = C.solve_at(laws, dict(fixed, **dict(mid, **{p: end})), derived)[q]
            except (C.CheckError, ZeroDivisionError, KeyError):
                vals = None
                break
            vals.append((v[0] + v[1]) / 2 if isinstance(v, tuple) else v)
        if vals:
            up[p] = vals[1] >= vals[0]
    _PROBE[key] = up
    return up


def _pinned_corner(fixed, boxes, up, raise_q):
    """The shared quantities pinned at the corner that pushes q up (raise_q) or down; slot fields stay boxes."""
    fx, bx = dict(fixed), {}
    for n, (lo, hi) in boxes.items():
        if "__" in n or n not in up:
            bx[n] = (lo, hi)
        else:
            fx[n] = hi if up[n] == raise_q else lo
    return fx, bx


def group_refutes(bm, laws, options, group, reqs_si):
    """A requirement violated by EVERY design of the group: with the shared toleranced quantities pinned at
    one corner p* (the same for every design — they are shared), the requirement's quantity read over the
    hull of the slot fields lies wholly past its bound, by ZTL's reading AND the checker's own. Then each
    design fails at (p*, any of its own values): refuted. (Reading over the whole box instead — all points
    failing — almost never holds: blind test 3, c11, 1000 groups, none cut.) The corner is a guess of the
    search; the proof is the two readings at it."""
    hf = hull_frame(bm, options, group)
    if hf is None:
        return None
    fixed, boxes, derived, grounds = hf
    defs = _defs(laws, set(derived), {r["quantity"] for r, _ in reqs_si})
    if defs is None:
        return None
    for r, iv in reqs_si:
        q = r["quantity"]
        up = _probe(bm, laws, fixed, boxes, derived, q)
        for raise_q in (True, False):
            if (raise_q and iv[1] is None) or (not raise_q and iv[0] is None):
                continue
            fx, bx = _pinned_corner(fixed, boxes, up, raise_q)
            try:
                zr = ztl_ranges(laws, fx, bx, derived, grounds)
            except Exception:               # noqa: BLE001 — a reading that fails decides nothing
                continue
            if not zr or q not in zr or not B.violates(zr[q], iv):
                continue
            cr = checker_ranges(defs, fx, bx)
            if q in cr and B.violates(cr[q], iv):
                return r, zr[q]
    return None


def label(options, group):
    """A pruned group in words: per slot the first and last item of its run."""
    from .stand import _label
    parts = []
    for s, (lo, hi) in group.items():
        a = _label({s: options[s][lo]})
        parts.append(a if lo == hi else f"{a} .. {_label({s: options[s][hi]}).split('=', 1)[1]}")
    return "; ".join(parts)


def prune(b, checks):
    """checks: [(brick, compiled laws, [(requirement, SI interval)])], one per mode (or one).
    -> (survivors [design], pruned [(group, requirement, range, count)], groups read) or None (not applicable)."""
    if b.get("computed"):
        return None
    _PROBE.clear()
    _DEFS.clear()
    slots = list((b.get("slots") or {}).items())
    options = {s: [(c, it) for c in spec["from"] for it in B.items(b["catalog"][c])] for s, spec in slots}
    total = 1
    for s in options:
        total *= len(options[s])
    if total < PRUNE_MIN:
        return None
    for bm, laws, reqs in checks:
        if not reqs:
            return None
        if any("implicit(" in l for l in laws):
            # an implicit law read over a whole group's hull: ZTL's root search ran for minutes inside ONE group read,
            # with no progress and no stop heard (MEASURED 2026-10-11, blind test 5 c04 at 2700 combinations: still
            # in the first group after 6 min); the designs are judged one by one instead
            return None
        from .stand import frame
        first = {s_: options[s_][0] for s_, _ in slots}
        if _defs(laws, set(frame(bm, first, with_computed=False)[2]), {r["quantity"] for r, _ in reqs}) is None:
            return None             # neither explicit nor a linear system the checker solves: not pruned
    from .stand import designs as all_designs_of
    survivors, pruned, read = [], [], [0]
    conds = [B.compile_expr(w) for w in (b.get("where") or [])]

    def leaves(group):
        keys = [s for s, _ in slots]
        for combo in itertools.product(*[range(group[s][0], group[s][1] + 1) for s in keys]):
            yield {s: options[s][i] for s, i in zip(keys, combo)}

    def size(group):
        n = 1
        for lo, hi in group.values():
            n *= hi - lo + 1
        return n

    class GiveUp(Exception):
        pass

    import sys as _sys
    import time as _time
    from .stopflag import check as _stop_check
    t0, last = _time.time(), [_time.time()]

    def go(group):
        _stop_check()               # a stop asked from outside, seen here (blind test 5: timeouts went unheard)
        now = _time.time()
        if now - last[0] > PROGRESS_EVERY:
            last[0] = now
            print(f"[stand] pruning {total} combinations: {read[0]} groups read, "
                  f"{sum(g[3] for g in pruned)} designs refuted in groups, {int(now - t0)} s", file=_sys.stderr, flush=True)
        if not pruned and (read[0] > GIVE_UP_AFTER or now - t0 > GIVE_UP_SECONDS):
            raise GiveUp()          # the readings decide nothing here: the plain enumeration is cheaper
        if read[0] > MAX_GROUPS:
            survivors.extend(leaves(group))
            return
        n = size(group)
        if n >= MIN_READ:
            for k, (bm, laws, reqs) in enumerate(checks):
                read[0] += 1
                hit = group_refutes(bm, laws, options, group, reqs)
                if hit:
                    pruned.append((group, dict(hit[0], _check=k), hit[1], n))
                    return
            s = max(group, key=lambda k: group[k][1] - group[k][0])
            lo, hi = group[s]
            mid = (lo + hi) // 2
            go(dict(group, **{s: (lo, mid)}))
            go(dict(group, **{s: (mid + 1, hi)}))
            return
        survivors.extend(leaves(group))

    try:
        go({s: (0, len(options[s]) - 1) for s, _ in slots})
    except GiveUp:
        return None
    # "where": survivors filtered exactly; a pruned group's count is of its designs that pass "where"
    if conds:
        from .stand import exact_env
        from . import exact as X
        nodes = [X.parse(c) for c in conds]

        def passes(d):
            env = exact_env(b, d)
            return all(X.evaluate(nd, env, "where") for nd in nodes)
        survivors = [d for d in survivors if passes(d)]
        counted = []
        for g, r, rg, n in pruned:
            if n <= COUNT_EXACT:
                k = sum(1 for d in leaves(g) if passes(d))
                if k:
                    counted.append((g, r, rg, k))
            else:
                counted.append((g, r, rg, -n))         # "up to n": too many to count against "where"
        pruned = counted
    return survivors, pruned, read[0], options
