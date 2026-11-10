# -*- coding: utf-8 -*-
"""
errfloat — binary64 arrays that CARRY a proved bound on their error (2026-11-10, CAD/FEA: the exact energy in
Fractions took ~30+ min for 82k tets; this makes a rigorous upper bound vectorised).

An Ev is (v, e): numpy arrays, with the claim |true - v| <= e entrywise. Each operation returns a new Ev whose claim
follows from its inputs' claims and the IEEE rounding of the operation (round to nearest, |fl(x) - x| <= U |fl(x)|
(1 + U) for normal results; U = 2^-53) plus an underflow allowance:
    a + b : v = fl(va + vb),   e = ea + eb + U |v| (1 + 2U) + TINY
    a * b : v = fl(va * vb),   e = |va| eb + |vb| ea + ea eb + U |v| (1 + 2U) + TINY   (the error terms rounded up by
                                                                                     the final (1 + 4U) factor)
    a / b : requires |vb| > eb;  |a/b - va/vb| <= (ea + |va/vb| eb) / (|vb| - eb), plus the rounding of the quotient
    const c (exact binary64): (c, 0);  from a Fraction x: (fl(x), U |fl(x)| (1 + U))
Every error expression is evaluated in floats and then raised by (1 + 4U) plus TINY so that its OWN rounding cannot
make it an underestimate (all its terms are nonnegative: relative error <= ~4U per op chain of length <= 4).
upper(x) = v + e, lower(x) = v - e, both stepped outward by one ulp.
"""
from __future__ import annotations

import numpy as np

U = 2.0 ** -53
TINY = 2.0 ** -1000          # covers subnormal/underflow absolute rounding (|x| < 2^-1022 rounds by <= 2^-1075)
_R = 1 + 4 * U


class Ev:
    __slots__ = ("v", "e")

    def __init__(self, v, e=None):
        self.v = np.asarray(v, dtype=np.float64)
        self.e = np.zeros_like(self.v) if e is None else np.asarray(e, dtype=np.float64)

    # ---- construction
    @staticmethod
    def exact(c):
        """values exactly representable in binary64 (integers < 2^53, dyadics)"""
        return Ev(c, None)

    @staticmethod
    def rounded(c):
        """values that were rounded once to binary64 (a Fraction, a decimal string's float)"""
        v = np.asarray(c, dtype=np.float64)
        return Ev(v, (U * np.abs(v) * (1 + U) + TINY) * _R)

    # ---- arithmetic
    def _lift(self, o):
        return o if isinstance(o, Ev) else Ev(o)

    def __add__(self, o):
        o = self._lift(o)
        v = self.v + o.v
        return Ev(v, (self.e + o.e + U * np.abs(v) * (1 + 2 * U) + TINY) * _R)

    __radd__ = __add__

    def __neg__(self):
        return Ev(-self.v, self.e)

    def __sub__(self, o):
        return self + (-self._lift(o))

    def __rsub__(self, o):
        return self._lift(o) + (-self)

    def __mul__(self, o):
        o = self._lift(o)
        v = self.v * o.v
        e = np.abs(self.v) * o.e + np.abs(o.v) * self.e + self.e * o.e + U * np.abs(v) * (1 + 2 * U) + TINY
        return Ev(v, e * _R)

    __rmul__ = __mul__

    def __truediv__(self, o):
        o = self._lift(o)
        den = np.abs(o.v) - o.e
        if not (den > 0).all():
            raise ZeroDivisionError("errfloat: a divisor's error interval contains 0")
        q = self.v / o.v
        e = (self.e + np.abs(q) * o.e) / den * (1 + 2 * U) + U * np.abs(q) * (1 + 2 * U) + TINY
        return Ev(q, e * _R)

    def sq(self):
        return self * self

    def sum(self, axis=None):
        """a sum of n terms: each partial sum's rounding bounded by U |partial| <= U sum |terms| — so the total
        rounding error <= (n - 1) U sum |v_i| (1 + n U) (a crude, valid bound for any summation order)."""
        v = self.v.sum(axis=axis)
        n = self.v.size if axis is None else self.v.shape[axis]
        a = np.abs(self.v).sum(axis=axis)
        e = self.e.sum(axis=axis) * (1 + n * U) + (n * U * a * (1 + n * U) + n * TINY)
        return Ev(v, e * _R)

    def __getitem__(self, k):
        return Ev(self.v[k], self.e[k])

    # ---- readout
    def upper(self):
        return np.nextafter(self.v + self.e * (1 + 2 * U), np.inf)

    def lower(self):
        return np.nextafter(self.v - self.e * (1 + 2 * U), -np.inf)
