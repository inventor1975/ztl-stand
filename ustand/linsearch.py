"""The SEARCH for zlin's certificates (floating point, trusted for nothing): zlin.py checks what this brings.

On a piece: A and b at its centre (exact readings, then floats), R = inv(A), x = R b, both rounded to fractions over
2^40. An enclosure leaf if it settles the bound; else the signs of d x_k / d p_j guessed at the centre and each tried
by the kernel's own rule (zlin._signs) — the proved ones pinned at their unfavourable end and the search goes on in the
smaller piece; else the piece is split in the name that moves x_k most. When every name is pinned (a point) the kernel solves it
exactly: an exact leaf, or a WITNESS (the stand decides it exactly once more).
The budget (pieces) is the search's, never the kernel's.
"""
from __future__ import annotations

from fractions import Fraction as F

import numpy as np

from . import judge_ztl as _J          # noqa: F401 — puts ZTL on the path
import zlin as Z                        # noqa: E402 — the kernel module, in ZTL since 2026-10-15
import zcertify as ZC                   # noqa: E402

DEN = 1 << 40
MAX_PIECES = 20000      # 10 unknowns, every part +-10 %: 2588 pieces (598 vertex branches) — MEASURED 2026-10-15
ITERS = 0           # refinement rounds asked of the kernel; the verified vectors (zlin step 4c) replaced them


def _q(v):
    """A float to a fraction on the kernel's CURRENT grid (2^-bits): R's far entries of a long ladder are ~1e-17 —
    on 2^-40 they rounded to zero and the search lost its way at 50 unknowns."""
    g = Z.G
    return F(int(round(float(v) * g)), g)


def _at(node, qs, point):
    if isinstance(node, F):
        return float(node)
    iv = ZC._reading(node, qs, {n: (v, v) for n, v in point.items()})
    if iv is None:
        raise Z.LinError("a coefficient has no value at the piece's centre")
    return float((iv[0] + iv[1]) / 2)


def greedy_vertex(A, b, qs, k, up, piece):
    """The search's best guess of the extreme: a VERTEX of the piece reached by coordinate ascent — each quantity
    flipped to its other end while that moves x_k the wanted way (floats; the caller solves the result exactly).
    Where every quantity enters by one layer the extreme IS a vertex (zlin step 6), and this walk found it at once on
    every case measured (2026-10-15: 5 unknowns +-10 %, 10 +-5 %, 30 +-2 %). -> {name: value}."""
    names = [n for n in piece if piece[n][0] != piece[n][1]]
    # ONE QUANTITY MOVES AT A TIME: only the coefficients it enters are read again (Muhanna's benchmark 1, 230 unknowns,
    # 420 moduli: every probe re-read all 53 000 coefficients exactly — hours, MEASURED 2026-10-16)
    deps = {n: [] for n in names}
    for i, row in enumerate(A):
        for j, e in enumerate(row):
            if not isinstance(e, F):
                for n in ZC._names(e):
                    if n in deps:
                        deps[n].append((i, j))
        if not isinstance(b[i], F):
            for n in ZC._names(b[i]):
                if n in deps:
                    deps[n].append((i, None))

    def full(pt):
        return (np.array([[_at(e, qs, pt) for e in row] for row in A]), np.array([_at(e, qs, pt) for e in b]))

    def moved(base, pt, n):
        Am, bm = base[0].copy(), base[1].copy()
        for i, j in deps[n]:
            if j is None:
                bm[i] = _at(b[i], qs, pt)
            else:
                Am[i, j] = _at(A[i][j], qs, pt)
        return Am, bm

    def val(m):
        return float(np.linalg.solve(m[0], m[1])[k])
    mid = {n: (lo + hi) / 2 for n, (lo, hi) in piece.items()}
    at_mid = full(mid)
    cur = dict(mid)
    for n in names:                                 # start: each quantity at the end its centre derivative favours
        lo_pt, hi_pt = dict(mid, **{n: piece[n][0]}), dict(mid, **{n: piece[n][1]})
        try:
            cur[n] = piece[n][1] if (val(moved(at_mid, hi_pt, n)) >= val(moved(at_mid, lo_pt, n))) == up \
                else piece[n][0]
        except np.linalg.LinAlgError:
            cur[n] = piece[n][1]
    at_cur = full(cur)
    best = val(at_cur)
    for _ in range(4 * len(names) + 4):             # flips until none helps (a local optimum over vertices)
        improved = False
        for n in names:
            alt = dict(cur, **{n: piece[n][0] if cur[n] == piece[n][1] else piece[n][1]})
            m = moved(at_cur, alt, n)
            try:
                v = val(m)
            except np.linalg.LinAlgError:
                continue
            if (v > best) if up else (v < best):
                cur, best, at_cur, improved = alt, v, m, True
        if not improved:
            break
    return cur


def search(laws, unknowns, qs, target, op, bound, budget=None):
    """-> {"cert": tree, "pieces": n} | {"witness": {name: value}} | {"gave_up": why}."""
    budget = budget or MAX_PIECES
    unknowns = list(unknowns)
    try:
        A, b = Z.system(laws, unknowns, qs)
    except Z.LinError as e:
        return {"gave_up": f"system: {e}"}
    k = unknowns.index(target)
    names = sorted({n for row in A for e in row for n in ZC._names(e)} | {n for e in b for n in ZC._names(e)})
    bound = F(bound)
    up = op == "<="
    spent = [0]
    wit = [None]

    def leaf_data(piece):
        mid = {n: (lo + hi) / 2 for n, (lo, hi) in piece.items()}
        Am = np.array([[_at(e, qs, mid) for e in row] for row in A])
        bm = np.array([_at(e, qs, mid) for e in b])
        Rm = np.linalg.inv(Am)
        xm = Rm @ bm
        return mid, Am, Rm, xm, [[_q(v) for v in row] for row in Rm], [_q(v) for v in xm]

    def go(piece, depth):
        spent[0] += 1
        if spent[0] > budget:
            raise _Budget()
        mid, Am, Rm, xm, R, xt = leaf_data(piece)
        Rs = [[str(v) for v in row] for row in R]
        xs = [str(v) for v in xt]
        wide = [n for n in names if piece[n][0] != piece[n][1]]
        if not wide:
            # a POINT: the kernel solves it exactly — a proof, or a witness the stand decides exactly
            xk = Z._solve_point(A, b, qs, piece, k)
            if (xk <= bound) if up else (xk >= bound):
                return {"leaf": "exact"}
            wit[0] = {n: v[0] for n, v in piece.items()}
            raise _Witness()
        Ai, bi = Z._imatrix(A, qs, piece), [Z._read(e, qs, piece) for e in b]
        par = Z._param(A, b, qs, piece)
        try:
            _beta, _C, X = Z._enclose(Ai, bi, R, xt, ITERS, par)
            lo, hi = X[k]
            if (hi <= bound) if up else (lo >= bound):
                return {"leaf": "enclose", "R": Rs, "x": xs, "iter": ITERS}
        except Z.LinError:
            pass
        # the signs at the centre: d = -R (dA x - db), per name
        sens = {}
        if par is not None:
            # the derivatives the kernel's parametric form already read over the piece: their centres, at the centre
            Rk = Rm[k]
            for nm, _w, dA, db in par["terms"]:
                if nm not in wide:
                    continue
                r = {}
                for i, iv in db.items():
                    r[i] = r.get(i, 0.0) - float((iv[0] + iv[1]) / 2)
                for (i, j), iv in dA.items():
                    r[i] = r.get(i, 0.0) + float((iv[0] + iv[1]) / 2) * xm[j]
                sens[nm] = -sum(Rk[i] * v for i, v in r.items())
        else:
            for n in wide:
                r = np.zeros(len(A))
                for i in range(len(A)):
                    try:
                        r[i] = -_at(ZC.derivative(b[i], n), qs, mid)
                        for j in range(len(A)):
                            da = ZC.derivative(A[i][j], n)
                            if not ZC._is0(da):
                                r[i] += _at(da, qs, mid) * xm[j]
                    except ZC.NoDerivative:
                        r = None
                        break
                if r is not None:
                    sens[n] = float(-(Rm @ r)[k])
        guess = {n: ("+" if s > 0 else "-") for n, s in sens.items() if s != 0}
        proved = {}
        try:
            reads = Z._dread(A, b, list(guess), k, qs, piece, R, xt, Ai, bi, ITERS, par)   # every name in one pass
        except Z.LinError:
            reads = {}
        for n, d in reads.items():
            if not isinstance(d, str) and (d[0] >= 0 or d[1] <= 0):
                proved[n] = "+" if d[0] >= 0 else "-"
        fcache = {}                     # this piece's two contractions (A's, A^T's), computed once for every name
        for n in guess:
            # zlin step 6: a quantity that enters by one layer — its sign by three factors, each enclosed alone
            if n not in proved and structs.get(n) is not None and par is not None:
                try:
                    sg = Z._factor_sign(A, b, k, qs, piece, R, Ai, bi, par, structs[n], fcache)
                except Z.LinError:
                    sg = None
                if sg is not None:
                    proved[n] = sg
        if proved:
            to = {n: (piece[n][1] if (s == "+") == up else piece[n][0]) for n, s in proved.items()}
            then = go(dict(piece, **{n: (v, v) for n, v in to.items()}), depth + 1)
            return {"leaf": "pin", "signs": proved, "R": Rs, "x": xs, "iter": ITERS, "then": then}
        if depth > 200:
            raise _Stuck("the search went deeper than 200")
        # a VERTEX branch (zlin step 6) on a one-layer quantity: its two faces, not two halves — each removes a whole
        # dimension; needs A nonsingular over the piece (beta < 1) and phi monotone (its derivative of one sign)
        cands = []
        for n in wide:
            st = structs.get(n)
            if st is None:
                continue
            lead = Z._read(st["g"] if st["g"] is not None else st["h"], qs, piece)
            if lead[0] > 0 or lead[1] < 0:
                cands.append(n)
        if cands and par is not None:
            try:
                Z._core(Ai, bi, R, xt, 0, par)
                ok_ns = True
            except Z.LinError:
                ok_ns = False
            if ok_ns:
                nm = max(cands, key=lambda n: abs(sens.get(n, 1.0)) * float(piece[n][1] - piece[n][0]))
                lo_, hi_ = piece[nm]
                first_hi = (sens.get(nm, 0.0) > 0) == up          # the face the centre's sign points to, first
                faces = [(hi_, "hi"), (lo_, "lo")] if first_hi else [(lo_, "lo"), (hi_, "hi")]
                sub = {}
                for v, side in faces:
                    sub[side] = go(dict(piece, **{nm: (v, v)}), depth + 1)
                return {"vertex": nm, "R": Rs, "x": xs, "lo": sub["lo"], "hi": sub["hi"]}
        # split the name that moves x_k most over its width
        nm = max(wide, key=lambda n: abs(sens.get(n, 1.0)) * float(piece[n][1] - piece[n][0]))
        lo_, hi_ = piece[nm]
        at = (lo_ + hi_) / 2
        return {"split": nm, "at": str(at), "lo": go(dict(piece, **{nm: (lo_, at)}), depth + 1),
                "hi": go(dict(piece, **{nm: (at, hi_)}), depth + 1)}

    piece0 = {n: (qs[n]["lo"], qs[n]["hi"]) for n in names}
    # FIRST the greedy vertex (2026-10-15, the curator's "да"): when it already passes the bound, a witness at once —
    # no tree is built (it measured 9 descent steps of a whole search each, ~500 s, at 20 unknowns)
    try:
        gv = greedy_vertex(A, b, qs, k, up, piece0)
        xg = Z._solve_point(A, b, qs, {n: (v, v) for n, v in gv.items()}, k)
        if (xg > bound) if up else (xg < bound):
            return {"witness": gv, "greedy": True}
    except (Z.LinError, np.linalg.LinAlgError):
        pass
    structs = {n: Z._structure(A, b, n, qs, piece0) for n in names}      # zlin step 6, once
    # the grid: fine enough for the target's scale and its derivatives' (a long ladder: u ~ 1e-35)
    try:
        xk0 = abs(float(leaf_data(piece0)[3][k]))
    except (Z.LinError, np.linalg.LinAlgError) as e:
        return {"gave_up": str(e)}
    import math
    bits = 64 + (max(0, int(-math.log2(xk0))) if xk0 > 0 else 0) + 64
    bits = min(Z.MAX_BITS, -(-bits // 32) * 32)
    try:
        with Z.grid(bits):
            cert = go(piece0, 0)
    except _Budget:
        return {"gave_up": f"no certificate within {budget} pieces"}
    except _Witness:
        return {"witness": wit[0]}
    except _Stuck as e:
        return {"gave_up": str(e)}
    except (Z.LinError, np.linalg.LinAlgError) as e:
        return {"gave_up": str(e)}
    return {"cert": {"grid": bits, "tree": cert}, "pieces": spent[0]}


class _Budget(Exception):
    pass


class _Witness(Exception):
    pass


class _Stuck(Exception):
    pass
