"""ADAPTIVE REFINEMENT for the continuum bounds (2026-11-01, the curator's "максимальное устранение ошибок"): the
hypercircle's own exact local error, eta_T^2 = ||tau - sigma(v)||^2 on element T, marks where the mesh is too coarse
(the clamped corners' singular stresses); those elements are bisected on their longest edge (Rivara's LEPP —
conforming, every angle bounded below), and the bounds are proved again on the new mesh. Nothing here is trusted:
every step's bracket is hypercircle.py's, tau checked exactly; refinement only decides WHERE to spend unknowns.

    python3 -m ustand.adapt deck.txt [--tol 0.5%] [--steps 8] [--theta 1/2] [--avg "X: 69-70 70-71"]

The deck: hypercircle.py's (plate + TRAC). Clamped edges split stay clamped (the new node supported in UX, UY);
a TRAC segment split gives each half half the resultant (a uniform traction stays uniform); the nodal F are written
as the TRAC lines' consistent loads.
"""
from __future__ import annotations

import json
import sys
import time
from fractions import Fraction as F

from . import hypercircle as HC


def _len2(nodes, a, b):
    return (nodes[a][0] - nodes[b][0]) ** 2 + (nodes[a][1] - nodes[b][1]) ** 2


class Mesh:
    def __init__(self, S):
        self.nodes = dict(S["nodes"])
        self.tris = {k: tr for k, tr in enumerate(S["tris"])}
        self.next_tri = len(self.tris)
        self.next_node = max(self.nodes) + 1
        self.clamped = set(S["clamped"])
        self.trac = dict(S["trac"])
        self.ex, self.nu, self.th = S["ex"], S["nu"], S["th"]
        self.mid = {}
        self.edge_tris = {}
        for k, tr in self.tris.items():
            self._add(k, tr)

    @staticmethod
    def _keys(tr):
        return [(min(tr[i], tr[(i + 1) % 3]), max(tr[i], tr[(i + 1) % 3])) for i in range(3)]

    def _add(self, k, tr):
        for key in self._keys(tr):
            self.edge_tris.setdefault(key, set()).add(k)

    def _remove(self, k):
        for key in self._keys(self.tris[k]):
            self.edge_tris[key].discard(k)
            if not self.edge_tris[key]:
                del self.edge_tris[key]
        del self.tris[k]

    def longest(self, k):
        """The longest edge; ties broken by the smaller key (deterministic, so LEPP terminates)."""
        return max(self._keys(self.tris[k]), key=lambda e: (_len2(self.nodes, *e), (-e[0], -e[1])))

    def split_edge(self, key):
        a, b = key
        if key not in self.mid:
            m = self.next_node
            self.next_node += 1
            self.nodes[m] = ((self.nodes[a][0] + self.nodes[b][0]) / 2, (self.nodes[a][1] + self.nodes[b][1]) / 2)
            self.mid[key] = m
        m = self.mid[key]
        for k in list(self.edge_tris.get(key, ())):
            tr = self.tris[k]
            i = next(i for i in range(3) if {tr[i], tr[(i + 1) % 3]} == {a, b})
            p, q, r = tr[i], tr[(i + 1) % 3], tr[(i + 2) % 3]          # p -> q is the edge, ccw kept
            self._remove(k)
            for child in ((p, m, r), (m, q, r)):
                self.tris[self.next_tri] = child
                self._add(self.next_tri, child)
                self.next_tri += 1
        if key in self.clamped:
            self.clamped.discard(key)
            self.clamped |= {(min(a, m), max(a, m)), (min(m, b), max(m, b))}
        if key in self.trac:
            fx, fy = self.trac.pop(key)
            self.trac[(min(a, m), max(a, m))] = (fx / 2, fy / 2)
            self.trac[(min(m, b), max(m, b))] = (fx / 2, fy / 2)

    def bisect(self, k):
        """Rivara's LEPP: walk to the terminal edge (the longest edge of both its triangles, or on the boundary),
        split it; repeat until triangle k itself is split."""
        guard = 0
        while k in self.tris:
            cur = k
            while True:
                e = self.longest(cur)
                nb = [j for j in self.edge_tris[e] if j != cur]
                if not nb or self.longest(nb[0]) == e:
                    self.split_edge(e)
                    break
                cur = nb[0]
            guard += 1
            if guard > 10000:
                raise HC.HCError("internal: LEPP did not terminate")

    def deck(self):
        L = ["/PREP7", "ET, 1, PLANE182", f"MP, EX, 1, {self.ex}", f"MP, PRXY, 1, {self.nu}", f"R, 1, {self.th}"]
        for n in sorted(self.nodes):
            L.append(f"N, {n}, {self.nodes[n][0]}, {self.nodes[n][1]}")
        for k in sorted(self.tris):
            L.append("E, %d, %d, %d" % self.tris[k])
        sup = sorted({n for key in self.clamped for n in key})
        for n in sup:
            L.append(f"D, {n}, UX, 0")
            L.append(f"D, {n}, UY, 0")
        cons = {}
        for (a, b), (fx, fy) in self.trac.items():
            for n in (a, b):
                cons[(n, "X")] = cons.get((n, "X"), F(0)) + fx / 2
                cons[(n, "Y")] = cons.get((n, "Y"), F(0)) + fy / 2
        for (n, d), v in sorted(cons.items()):
            if v:
                L.append(f"F, {n}, F{d}, {v}")
        for (a, b), (fx, fy) in sorted(self.trac.items()):
            L.append(f"TRAC, {a}, {b}, {fx}, {fy}")
        return "\n".join(L) + "\n"


def indicators(S, tmap):
    """eta_T^2 = ||tau - sigma(v)||^2_{C^-1} on every element T (exact), for the load tmap; with the bracket."""
    fields, br, _ = HC._fields(S, tmap)
    eta = {}
    for idx, (tu, vu, ar) in enumerate(fields):
        k = idx // 3
        du = [[a - b for a, b in zip(tu[i], vu[i])] for i in range(3)]
        ms = [[(a + b) / 2 for a, b in zip(du[i], du[j])] for i, j in ((0, 1), (1, 2), (2, 0))]
        eta[k] = eta.get(k, F(0)) + ar / 3 * sum(HC._cinner(S, y, y) for y in ms)
    return eta, br


def dorfler(eta, theta):
    """The fewest elements whose eta^2 sum to at least theta of the total."""
    tot = sum(eta.values())
    out, acc = [], F(0)
    for k, v in sorted(eta.items(), key=lambda kv: -kv[1]):
        if acc >= theta * tot:
            break
        out.append(k)
        acc += v
    return out


def adapt(text, tol="0", steps=8, theta=F(1, 2), avg=None, log=print):
    """Refine where eta is large; report each mesh's proved bracket (compliance, or the AVG output)."""
    rows = []
    for step in range(steps + 1):
        S = HC.setup(text, tol)
        t0 = time.time()
        if avg is None:
            r = HC.compliance_bounds(text, tol)
            lo, hi = r["lower"], r["upper"]
            eta, _ = indicators(S, S["trac"])
        else:
            comp, segs = avg
            r = HC.output_bounds_box(text, tol, segs, comp)
            lo, hi = r["lower"], r["upper"]
            eu, _ = indicators(S, S["trac"])
            nodes = S["nodes"]
            from .truss import _sqrt
            lens = [((min(a, b), max(a, b)), _sqrt(_len2(nodes, a, b))) for a, b in segs]
            Lt = sum(L for _, L in lens)
            J = {key: ((L / Lt, F(0)) if comp == "X" else (F(0), L / Lt)) for key, L in lens}
            ez, _ = indicators(S, J)
            su, sz = sum(eu.values()), sum(ez.values())
            eta = {k: eu[k] / su + ez.get(k, F(0)) / sz for k in eu}      # both problems, each normalised
        width = (hi - lo) / max(abs(hi), abs(lo))
        row = {"step": step, "elements": len(S["tris"]), "nodes": len(S["nodes"]), "lower": float(lo),
               "upper": float(hi), "width_pct": float(width) * 100, "seconds": round(time.time() - t0, 1)}
        rows.append(row)
        log(json.dumps(row))
        if step == steps:
            break
        M = Mesh(S)
        for k in dorfler(eta, theta):
            if k in M.tris:
                M.bisect(k)
        if avg is not None:                                # the output's segments, split with the mesh
            comp, segs = avg
            new = []
            def leaves(a, b):
                key = (min(a, b), max(a, b))
                if key in M.mid:
                    m = M.mid[key]
                    return leaves(a, m) + leaves(m, b)
                return [(a, b)]
            for a, b in segs:
                new += leaves(a, b)
            avg = (comp, new)
        text = M.deck()
    return rows, text


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    import re
    text = open(argv[0], encoding="utf-8").read()
    tol = argv[argv.index("--tol") + 1] if "--tol" in argv else "0"
    steps = int(argv[argv.index("--steps") + 1]) if "--steps" in argv else 8
    theta = F(argv[argv.index("--theta") + 1]) if "--theta" in argv else F(1, 2)
    avg = None
    if "--avg" in argv:
        m = re.match(r"^\s*([XY])\s*:\s*([0-9\- ,]+)$", argv[argv.index("--avg") + 1])
        avg = (m.group(1), [tuple(int(x) for x in s.split("-")) for s in re.split(r"[ ,]+", m.group(2).strip())])
    adapt(text, tol, steps, theta, avg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
