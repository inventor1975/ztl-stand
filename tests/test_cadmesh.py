# -*- coding: utf-8 -*-
"""ustand.cadmesh: what a mesh proves, and that each failure is named. Run: python3 -m tests.test_cadmesh"""
import os
import struct
import sys
import tempfile
from fractions import Fraction as Fr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import cadmesh as CM          # noqa: E402

CHECKS, FAILS = 0, []


def check(cond, what):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(what)
        print(f"FAIL: {what}")


def cube(o=(0, 0, 0), s=10):
    """A closed outward-oriented cube: 8 vertices, 12 triangles."""
    x, y, z = o
    V = [(x + a * s, y + b * s, z + c * s) for a in (0, 1) for b in (0, 1) for c in (0, 1)]
    q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    F = []
    for a, b, c, d in q:
        F += [(a, b, c), (a, c, d)]
    return V, F


def write_stl_ascii(path, V, F):
    with open(path, "w") as f:
        f.write("solid t\n")
        for a, b, c in F:
            f.write("facet normal 0 0 0\nouter loop\n")
            for i in (a, b, c):
                f.write("vertex %s %s %s\n" % V[i])
            f.write("endloop\nendfacet\n")
        f.write("endsolid t\n")


def write_stl_binary(path, V, F):
    with open(path, "wb") as f:
        f.write(b"\0" * 80 + struct.pack("<I", len(F)))
        for a, b, c in F:
            f.write(struct.pack("<12fH", 0, 0, 0, *V[a], *V[b], *V[c], 0))


def run(V, F):
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, "m.stl")
    write_stl_ascii(p, V, F)
    v, f, u = CM.read(p)
    return CM.analyse(v, f, u)


# 1. a cube: closed, oriented, genus 0, volume exactly 1000, no self-intersection, box 10 x 10 x 10
V, F = cube()
rep, vol = run(V, F)
t = rep["topology"]
check(t["closed"] and t["oriented"] and t["genus"] == 0 and t["components"] == 1, f"cube topology {t}")
check(vol == 1000 and rep["volume"]["proved"], f"cube volume exactly 1000 ({vol})")
check(rep["self_intersection"]["pairs_found"] == 0, "cube: no self-intersection")
check(rep["bounding_box"]["size"] == [10.0, 10.0, 10.0], "cube box")
check(rep["surface_area"]["lo"] <= 600 <= rep["surface_area"]["hi"], f"cube area bracket holds 600 {rep['surface_area']}")

# 2. binary STL: the same cube, binary32 coordinates read exactly
tmp = tempfile.mkdtemp()
pb = os.path.join(tmp, "b.stl")
write_stl_binary(pb, [(x + 0.5, y, z) for x, y, z in V], F)   # 0.5 is exact in binary32
v, f, u = CM.read(pb)
rb, volb = CM.analyse(v, f, u)
check(volb == 1000 and rb["topology"]["vertices"] == 8, f"binary STL: welded to 8 vertices, volume 1000 ({volb})")

# 3. an open mesh: one face removed -> not closed, volume NOT proved, the open edges named
rep, _ = run(V, F[:-1])
check(not rep["topology"]["closed"] and rep["topology"]["open_edges"] == 3 and not rep["volume"]["proved"],
      f"open mesh: 3 open edges, volume not proved ({rep['topology']['open_edges']})")

# 4. one face flipped -> closed but not oriented, volume NOT proved
F2 = list(F)
a, b, c = F2[0]
F2[0] = (a, c, b)
rep, _ = run(V, F2)
check(rep["topology"]["closed"] and not rep["topology"]["oriented"] and not rep["volume"]["proved"],
      "a flipped face: closed, not oriented, volume not proved")

# 5. two cubes that OVERLAP: each closed and oriented, together the surface intersects itself -> volume NOT proved
V2, F2 = cube((5, 5, 5))
VV = V + V2
FF = F + [(a + 8, b + 8, c + 8) for a, b, c in F2]
rep, vol = run(VV, FF)
check(rep["topology"]["oriented"] and rep["topology"]["components"] == 2, "two cubes: oriented, two components")
check(rep["self_intersection"]["pairs_found"] > 0 and not rep["volume"]["proved"],
      f"overlapping cubes: self-intersection found ({rep['self_intersection']['pairs_found']}), volume not proved")
check(vol == 2000, "the formula alone would say 2000 (the union is 1875) — which is why the check exists")

# 6. two cubes APART: genus 0 each, volume 2000 proved
V3, F3 = cube((20, 0, 0))
rep, vol = run(V + V3, F + [(a + 8, b + 8, c + 8) for a, b, c in F3])
check(rep["volume"]["proved"] and vol == 2000 and rep["topology"]["genus"] == 0, "two separate cubes: 2000, proved")

# 7. two cubes TOUCHING at a face (coplanar contact, no shared vertices) -> caught
V4, F4 = cube((10, 2, 2), s=4)
rep, _ = run(V + V4, F + [(a + 8, b + 8, c + 8) for a, b, c in F4])
check(rep["self_intersection"]["pairs_found"] > 0, "a cube touching another's face (coplanar): caught")

# 8. mass through ZTL's judge: V = 1000 exactly, density [0.9, 1.1] on credit
m = CM.judge_mass(Fr(1000), (0.9, 1.1), mass_max=800)
check(m["mass_max"]["disposition"] == "ON CREDIT" and m["mass_max"]["polarity"] == "toward F"
      and m["mass_max"]["next_check"] == ["document rho"],
      f"mass <= 800 with V*rho >= 900: ON CREDIT toward F, check the density ({m['mass_max']})")
m = CM.judge_mass(Fr(1000), (0.9, 1.1), mass_max=1200)
check(m["mass_max"]["disposition"] == "ON CREDIT" and m["mass_max"]["polarity"] == "toward T",
      f"mass <= 1200: toward T on the density's word ({m})")

# 9. the SimJEB bracket 148, if the data is here: equal to the dataset's own numbers
p148 = "/media/vitaly/SSD_1000GB/Projects/ext-data/simjeb/sample/148.obj"
if os.path.exists(p148):
    v, f, u = CM.read(p148)
    rep, vol = CM.analyse(v, f, u)
    check(rep["topology"]["genus"] == 12 and abs(float(vol) - 130190.585221618) < 1e-6 and rep["volume"]["proved"],
          "SimJEB 148: genus 12, volume = the dataset's 130190.585221618, proved")
else:
    print("  (SimJEB 148 not present: skipped)")

if FAILS:
    print(f"CADMESH RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"CADMESH GREEN ({CHECKS} checks)")
