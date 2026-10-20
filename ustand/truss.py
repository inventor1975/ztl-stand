"""A PLANE TRUSS (an ANSYS input deck, LINK1/LINK180 bars) -> a stand brick (2026-10-15, the curator's "подтянем
стенд" for the classic interval-FEM benchmarks of Muhanna & Mullen, Georgia Tech REC: 101 and 420 uncertain moduli).

Each bar's stiffness enters the equilibrium as E_i * (A/L) * c c^T — a RANK-ONE term in its own parameter, exactly
as a resistor's conductance does in a circuit; so the stand judges it with the same certificates (ZTL's zlin).

    python3 -m ustand.truss deck.txt --tol 0.5% --range "U(42,X)"           the PROVED range of a displacement
    python3 -m ustand.truss deck.txt --tol 0.5% --req "U(42,X) <= 18300"    a requirement
            [--dev] [--emit brick.json]

THE DECK (the subset ANSYS's own input files of the benchmarks use; anything else is REFUSED aloud):
    N, id, x, y                  a node
    E, i, j                      a bar between nodes i and j (one material, one real constant: MP EX and R)
    MP, EX, 1, value             Young's modulus (nominal)
    R, 1, area                   the cross-section area
    F, node, FX|FY, value        a nodal force
    D, node, UX|UY, 0            a support (zero displacement)
    /PREP7, ET, MAT, REAL, comments (!) — read and skipped.
--tol t: every bar's modulus anywhere in E*(1 +- t), independently ("1 % uncertainty" of the benchmarks is
E in [0.995, 1.005]E, i.e. --tol 0.5%). Displacements: U(node,X|Y). Lengths must be rational (a bar whose length is
irrational is refused: its stiffness would not be exact).
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction as F
from math import isqrt

from . import bricks as B
from .spice import range_by, _run, SpiceError, tolerance, _progress


class TrussError(B.BrickError):
    pass


def _num(t, what):
    try:
        return F(t.strip())
    except (ValueError, ZeroDivisionError):
        raise TrussError(f"{what}: not a number: {t!r}")


def _sqrt(q):
    """The exact square root of a rational, or None."""
    n, d = q.numerator, q.denominator
    rn, rd = isqrt(n), isqrt(d)
    return F(rn, rd) if rn * rn == n and rd * rd == d else None


def read_deck(text):
    nodes, bars, forces, supports = {}, [], {}, set()
    ex, area = None, None
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.split("!")[0].strip()
        if not line or line.startswith("/"):
            continue
        f = [x.strip() for x in (line.split(",") if "," in line else line.split())]   # "MAT  1" too
        cmd = f[0].upper()
        where = f"line {ln}"
        if cmd == "N":
            nodes[int(f[1])] = (_num(f[2], where), _num(f[3], where) if len(f) > 3 and f[3] else F(0))
            if len(f) > 4 and f[4] and _num(f[4], where) != 0:
                raise TrussError(f"{where}: a z coordinate — only a plane truss")
        elif cmd == "E":
            bars.append((int(f[1]), int(f[2])))
        elif cmd == "MP":
            if f[1].upper() != "EX":
                raise TrussError(f"{where}: MP {f[1]} — only EX is read")
            if ex is not None and _num(f[3], where) != ex:
                raise TrussError(f"{where}: a second material — one EX only (version 1)")
            ex = _num(f[3], where)
        elif cmd == "R":
            if area is not None and _num(f[2], where) != area:
                raise TrussError(f"{where}: a second real constant — one area only (version 1)")
            area = _num(f[2], where)
        elif cmd == "F":
            d = f[2].upper()
            if d not in ("FX", "FY"):
                raise TrussError(f"{where}: force {f[2]} — FX or FY only")
            k = (int(f[1]), d[1])
            forces[k] = forces.get(k, F(0)) + _num(f[3], where)
        elif cmd == "D":
            d = f[2].upper()
            if d not in ("UX", "UY"):
                raise TrussError(f"{where}: support {f[2]} — UX or UY only")
            if _num(f[3], where) != 0:
                raise TrussError(f"{where}: a prescribed nonzero displacement — not read (version 1)")
            supports.add((int(f[1]), d[1]))
        elif cmd == "ET":
            if f[2].upper() not in ("LINK1", "LINK180", "1", "180"):
                raise TrussError(f"{where}: element type {f[2]} — only LINK1/LINK180 bars")
        elif cmd in ("MAT", "REAL", "TYPE"):
            if len(f) > 1 and f[1] not in ("1", ""):
                raise TrussError(f"{where}: {cmd},{f[1]} — one material and one real constant only")
        else:
            raise TrussError(f"{where}: {f[0]} — not read (only N E MP R F D ET MAT REAL)")
    if not nodes or not bars:
        raise TrussError("no nodes or no bars")
    if ex is None or area is None:
        raise TrussError("no MP,EX or no R (the modulus and the area are needed)")
    for i, j in bars:
        for n in (i, j):
            if n not in nodes:
                raise TrussError(f"bar {i}-{j}: node {n} does not exist")
    return nodes, bars, forces, supports, ex, area


def _u(n, d):
    return f"U_{n}_{d}"


def to_brick(text, tol, requirements=()):
    """Quantities: each bar's modulus E<k> (toleranced), each free displacement U_<node>_<X|Y> (derived).
    Laws: equilibrium at every free degree of freedom. Requirements: [(node, dir, op, value)]."""
    nodes, bars, forces, supports, ex, area = read_deck(text)
    t = F(0) if tol in (None, "0", 0) else tolerance(tol) if isinstance(tol, str) else F(tol)
    qs, terms = {}, {}
    free = [(n, d) for n in sorted(nodes) for d in "XY" if (n, d) not in supports]
    fset = set(free)
    for k, (a, b) in enumerate(bars, 1):
        dx, dy = nodes[b][0] - nodes[a][0], nodes[b][1] - nodes[a][1]
        L = _sqrt(dx * dx + dy * dy)
        if not L:
            raise TrussError(f"bar {k} ({a}-{b}): its length is irrational or zero — not exact (version 1)")
        q = f"E{k}"
        qq = {"role": "given", "value": str(ex), "unit": ""}
        if t:
            qq["tolerance"] = str(t)
        qs[q] = qq
        c = {"X": dx / L, "Y": dy / L}
        # elongation = c . (u_b - u_a); force on a = +N c, on b = -N c; N = E A/L * elongation
        el = " + ".join(f"({c[d] * sg})*{_u(n, d)}" for n, sg in ((b, 1), (a, -1)) for d in "XY"
                        if c[d] != 0 and (n, d) in fset) or "0"
        s = area / L
        # (the element-force form — each bar's force an unknown — was tried 2026-10-16: the same contraction, more
        # unknowns, 3x slower; what the tall cantilever needed was units for the unknowns: certify._scaling)
        for n, sg in ((a, 1), (b, -1)):
            for d in "XY":
                if (n, d) in fset and c[d] != 0:
                    terms.setdefault((n, d), []).append(f"({s * c[d] * sg})*{q}*({el})")
    laws = []
    for n, d in free:
        qs[_u(n, d)] = {"role": "derived", "unit": ""}
        lhs = " + ".join(terms.get((n, d), [])) or "0"
        laws.append({"zfl": f"{lhs} + ({forces.get((n, d), F(0))}) == 0",
                     "source": f"equilibrium at node {n}, {d}"})
    for (n, d) in forces:
        if (n, d) not in fset:
            if n not in nodes:
                raise TrussError(f"a force at node {n}, which does not exist")
    reqs = []
    for i, (n, d, op, v) in enumerate(requirements):
        if (n, d) not in fset:
            raise TrussError(f"U({n},{d}): not a free displacement of this truss")
        reqs.append({"quantity": _u(n, d), "op": op, "value": str(v), "why": f"U({n},{d}) {op} {v}"})
    return {"stand": "ztl-stand/1", "why": "imported from an ANSYS truss deck (ustand/truss.py)", "quantities": qs,
            "laws": laws, "requirements": reqs}


def _target(text):
    import re
    m = re.match(r"^\s*U\(\s*(\d+)\s*,\s*([XYxy])\s*\)\s*$", text)
    if not m:
        raise TrussError(f"{text!r}: a target is U(node,X) or U(node,Y)")
    return int(m.group(1)), m.group(2).upper()


def _req(text):
    import re
    m = re.match(r"^\s*(U\([^)]*\))\s*(<=|>=)\s*(\S+)\s*$", text)
    if not m:
        raise TrussError(f"{text!r}: a requirement is U(node,X|Y) <= value or >= value")
    n, d = _target(m.group(1))
    return n, d, m.group(2), _num(m.group(3), text)


def judge(text, tol, requirements):
    bk = to_brick(text, tol, requirements)
    return _run(bk, bk["requirements"])


def range_of(text, tol, target, steps=40, progress=None):
    n, d = _target(target)
    return range_by(lambda op, bound: judge(text, tol, [(n, d, op, bound)]), steps, progress)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    from . import mode as MODE
    MODE.DEV[0] = "--dev" in argv
    try:
        text = open(argv[0], encoding="utf-8").read()
        tol = argv[argv.index("--tol") + 1] if "--tol" in argv else "0"
        reqs = [_req(argv[i + 1]) for i, a in enumerate(argv) if a == "--req"]
        ranges = [argv[i + 1] for i, a in enumerate(argv) if a == "--range"]
        if "--emit" in argv:
            json.dump(to_brick(text, tol, reqs), open(argv[argv.index("--emit") + 1], "w"), indent=1)
        if ranges:
            out = {t: range_of(text, tol, t, progress=_progress) for t in ranges}   # each end to stderr at once
        else:
            out = judge(text, tol, reqs)
    except (B.BrickError, SpiceError, OSError, ValueError, IndexError) as e:
        out = {"verdict": "BRICK ERROR", "why": f"{e}"}
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
