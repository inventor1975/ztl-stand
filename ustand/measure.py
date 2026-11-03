"""measure — WHAT TO MEASURE NEXT: the backward pass of the stand over its numeric inputs (2026-11-03, the curator's
"а мы что не используем это в стенде? … делаем сейчас именно это").

    python3 -m ustand.measure brick.json

A verdict over ranges answers "for every value the ranges allow". When it is not EARNED, the useful question is which
input to measure, and what the measurement must show. For every given stated as a RANGE, and when no single one
settles it for PAIRS of them, this module finds

    SETTLES        a sub-range of the input (anchored at one end of its range) on which the brick, with that input
                   narrowed and every other range as stated, is EARNED: "measure q; if the measured interval lies
                   within [a, b], the claim is EARNED";
    FAILS FOR SURE a sub-range on which the brick with its requirement NEGATED is EARNED — every value of every other
                   range then violates the requirement: "if q is measured within [a, b], it fails whatever the rest
                   turns out to be" (single-requirement bricks only: the negation of several is a disjunction).

SOUNDNESS: every reported region is the stand's own verdict on the narrowed brick (the same proved machinery as any
EARNED); the search (bisection along the range, from each end) only CHOOSES which regions to try — a region it fails
to find is a region not reported, never a wrong one. The regions are sufficient, not the whole picture: an EARNED
region strictly inside a range, or a pair region off the proportional diagonal, may exist unreported.
"""
from __future__ import annotations

import copy
import json
import sys
from fractions import Fraction as F

from . import stand as S

MUTANT = {}       # TEST-ONLY sabotage switches; empty = the real regions
STEPS = 14        # bisection steps per search (the range / 2^14)
NEG = {">=": "<", ">": "<=", "<=": ">", "<": ">="}


def _ranged(b):
    return [q for q, d in b["quantities"].items() if d.get("role") == "given" and "range" in d]


def _with(b, ranges, negate=False):
    bb = copy.deepcopy(b)
    for q, (lo, hi) in ranges.items():
        d = bb["quantities"][q]
        d["range"] = [str(lo), str(hi)]
    if negate:
        bb["requirements"] = [dict(r, op=NEG[r["op"]]) for r in bb["requirements"]]
    return bb


def _earned(bb):
    try:
        return S.run(bb).get("verdict") == "EARNED"
    except Exception:                                    # a brick the stand refuses is not a region
        return False


def _search(b, qs, anchors, negate):
    """The widest proportional narrowing s in (0, 1] of the inputs qs, each from its anchor end, on which the brick is
    EARNED (negate: the negated requirement). Returns the verified ranges or None."""
    box = {q: (F(b["quantities"][q]["range"][0]), F(b["quantities"][q]["range"][1])) for q in qs}
    def rng(s):
        out = {}
        for q, a in zip(qs, anchors):
            lo, hi = box[q]
            out[q] = (lo, lo + s * (hi - lo)) if a == "low" else (hi - s * (hi - lo), hi)
        return out
    if _earned(_with(b, rng(F(1)), negate)):
        return rng(F(1))
    good, bad = None, F(1)
    s = F(1, 2)
    lo_s = F(0)
    for _ in range(STEPS):
        if _earned(_with(b, rng(s), negate)):
            good, lo_s = s, s
        else:
            bad = s
        s = (lo_s + bad) / 2
    if good is None:
        return None
    found = rng(good)
    if MUTANT.get("no_recheck"):                          # sabotage (tests only): the region widened past the last proof
        found = rng(min(F(1), good * F(5, 4)))
        return found
    return found if _earned(_with(b, found, negate)) else None


def what_to_measure(b, pairs=True):
    """{'verdict': the brick's own, 'settles': [...], 'fails_for_sure': [...], 'note': ...} — see the module doc."""
    v0 = S.run(b).get("verdict")
    qs = _ranged(b)
    single_req = len(b.get("requirements", [])) == 1 and b["requirements"][0]["op"] in NEG
    out = {"verdict": v0, "inputs_with_ranges": qs, "settles": [], "fails_for_sure": []}
    if v0 == "EARNED":
        out["note"] = "already EARNED: nothing to measure"
        return out
    def regions(group, negate):
        found = []
        for anchors in ([("low",), ("high",)] if len(group) == 1 else
                        [("low", "low"), ("low", "high"), ("high", "low"), ("high", "high")]):
            r = _search(b, group, anchors, negate)
            if r:
                found.append({q: [S._s(lo), S._s(hi)] for q, (lo, hi) in r.items()})
        return found
    for q in qs:
        out["settles"] += regions([q], False)
        if single_req:
            out["fails_for_sure"] += regions([q], True)
    if pairs and not out["settles"]:
        for i in range(len(qs)):
            for j in range(i + 1, len(qs)):
                out["settles"] += regions([qs[i], qs[j]], False)
    if not out["settles"]:
        out["note"] = ("no single measurement (and no pair, on the searched diagonals) settles it: several inputs must "
                       "be narrowed together, or the claim fails")
    out["premise"] = ("each region is the stand's own EARNED verdict on the brick with those inputs narrowed and every "
                      "other range as stated; regions are sufficient, not exhaustive")
    return out


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    print(json.dumps(what_to_measure(json.load(open(argv[0]))), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
