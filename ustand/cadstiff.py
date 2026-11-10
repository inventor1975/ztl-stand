# -*- coding: utf-8 -*-
"""
cadstiff — the stand's verdict on a part's STIFFNESS requirement from a PROVED displacement bracket (2026-11-10,
CAD/FEA; design in research/cad/PLAN-level2.md "The STAND BRICK for a part's stiffness").

    judge(d_lo, d_hi, E_deck, E_range, E_ground, d_max=None, d_min=None, rests_on=...)

d = C / |F|, the load's work-conjugate displacement (mm; a rotation for a moment), proved in [d_lo, d_hi] at the
deck's modulus E_deck (d_lo: tetfea, minimum potential energy; d_hi: equil + the exact finish, complementary energy).
For a fixed pair of fields both bounds scale as 1 / E, so with E in [E_lo, E_hi]:
    d in [d_lo E_deck / E_hi, d_hi E_deck / E_lo]            (nu as given: a stated premise of this version)
The verdict is ZTL's numeric judge on `d <= d_max` / `d >= d_min`, with d's bracket at E_deck an EARNED quantity of
the mesh (its sha256 in rests_on) and E with ITS ground ("earned" for a test of the material, "credit" for a
datasheet). REFUTED / EARNED / ON CREDIT (+ polarity, next_check) / OPEN come from the judge, not from this file.
"""
from __future__ import annotations

import os
import sys
from fractions import Fraction as Fr


def _ztl():
    return os.environ.get("USTAND_ZTL") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "ZTL")


def _num(x):
    # a requirement typed as a float (1.4) is read as its DECIMAL (7/5), not its binary64 value
    x = Fr(str(x)) if isinstance(x, float) else Fr(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def judge(d_lo, d_hi, E_deck, E_range, E_ground="credit", d_max=None, d_min=None, rests_on=None):
    """-> {"d_bracket_at_deck_E", "d_bracket_over_E", "verdicts": {...}, "rests_on": [...]}.
    The float inputs are taken as the exact binary64 values they are; d_lo must be a proved LOWER and d_hi a proved
    UPPER bound (the caller's); E_range (lo, hi) contains E_deck."""
    sys.path.insert(0, _ztl())
    import znumjudge as ZJ
    lo, hi = Fr(d_lo), Fr(d_hi)
    if not lo <= hi:
        raise ValueError(f"not a bracket: {d_lo} > {d_hi}")
    Ed = Fr(E_deck)
    El, Eh = Fr(E_range[0]), Fr(E_range[1])
    if not El <= Ed <= Eh:
        raise ValueError("the deck's E lies outside its own range")
    # d(E) = d(E_deck) * E_deck / E: the sheet carries the bracket at E_deck (earned: of THIS mesh) and E's ground
    sheet = (f"dd=[{_num(lo)},{_num(hi)}] earned, Ed=[{_num(Ed)},{_num(Ed)}] earned, "
             f"E=[{_num(El)},{_num(Eh)}] {E_ground}")
    qs = ZJ.parse_quantities(sheet)[0]
    out = {"d_bracket_at_deck_E": [float(lo), float(hi)],
           "d_bracket_over_E": [float(lo * Ed / Eh), float(hi * Ed / El)], "verdicts": {}}
    for name, claim in (("d_max", f"dd*Ed/E <= {_num(Fr(d_max))}" if d_max is not None else None),
                        ("d_min", f"dd*Ed/E >= {_num(Fr(d_min))}" if d_min is not None else None)):
        if claim:
            r = ZJ.judge_sheet_claim(claim, dict(qs), {})
            out["verdicts"][name] = {"claim": claim, "disposition": r["disposition"], "polarity": r.get("polarity"),
                                     "next_check": r.get("next_check")}
    out["rests_on"] = list(rests_on or []) + [
        "linear isotropic elasticity on the solid the tet mesh fills (the mesh IS the part: EARNED IF STABLE on its "
        "revision)", "the load: the traction whose consistent nodal loads are the RBE3 distribution",
        "nu as given (this version brackets E only)"]
    return out
