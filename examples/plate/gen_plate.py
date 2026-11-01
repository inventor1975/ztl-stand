"""A plane-stress plate: a rectangle (NX h) x (NY h) meshed in NX x NY squares of side h, each square split into two
triangles (CST, ustand/plate.py), all coordinates rational. The left edge (x = 0) is supported, the right edge
(x = NX h) loaded by a uniform edge traction p distributed CONSISTENTLY: each edge segment of length h carries
p th h, half to each of its two end nodes (so the two corner nodes get half of an interior node's share).
(2026-11-01, ztl-stand: plates after frames.)

    python3 examples/plate/gen_plate.py NX NY [--load tension|shear] [--support clamped|roller]
            [--h 1/10] [--E 200e9] [--nu 3/10] [--th 1/100] [--p 1e6]  > deck.txt
  --load tension   p in +X on the right edge (default)
  --load shear     p in -Y on the right edge (a tip shear)
  --support clamped   UX = UY = 0 at every node of x = 0 (default)
  --support roller    UX = 0 at every node of x = 0, UY = 0 only at the bottom-left node: rigid motion removed and
                      the lateral contraction free (the patch test)
Defaults: steel-like E 200 GPa, nu 0.3, 10 mm thick, h = 0.1 m, p = 1 MPa. Nodes: id = j (NX + 1) + i + 1 at
(i h, j h); the tip corners are NX + 1 (bottom right) and (NX + 1)(NY + 1) (top right)."""
import sys
from fractions import Fraction as F


def _opt(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv else default


def _dec(q):
    """A rational as an exact decimal when it has one, else as a fraction (the stand reads both exactly)."""
    q = F(q)
    d = q.denominator
    k = 0
    while d % 2 == 0 or d % 5 == 0:
        d //= 2 if d % 2 == 0 else 5
        k += 1
    if d != 1:
        return str(q)
    if q.denominator == 1:
        return str(q.numerator)
    s = q.numerator * 10 ** k // q.denominator
    sign = "-" if s < 0 else ""
    s = str(abs(s)).rjust(k + 1, "0")
    return f"{sign}{s[:-k]}.{s[-k:]}".rstrip("0").rstrip(".")


def deck(nx, ny, load="tension", support="clamped", h="1/10", E="200e9", nu="3/10", th="1/100", p="1e6"):
    h, p, th = F(h), F(p), F(th)
    nid = lambda i, j: j * (nx + 1) + i + 1
    L = ["/PREP7", "ET, 1, PLANE182", f"MP, EX, 1, {E}", f"MP, PRXY, 1, {nu}", f"R, 1, {_dec(th)}"]
    for j in range(ny + 1):
        for i in range(nx + 1):
            L.append(f"N, {nid(i, j)}, {_dec(i * h)}, {_dec(j * h)}")
    for j in range(ny):
        for i in range(nx):
            a, b, c, d = nid(i, j), nid(i + 1, j), nid(i + 1, j + 1), nid(i, j + 1)
            L.append(f"E, {a}, {b}, {c}")
            L.append(f"E, {a}, {c}, {d}")
    for j in range(ny + 1):
        L.append(f"D, {nid(0, j)}, UX, 0")
        if support == "clamped" or j == 0:
            L.append(f"D, {nid(0, j)}, UY, 0")
    share = p * th * h / 2
    for j in range(ny + 1):
        fj = share * (1 if j in (0, ny) else 2)
        if load == "tension":
            L.append(f"F, {nid(nx, j)}, FX, {_dec(fj)}")
        else:
            L.append(f"F, {nid(nx, j)}, FY, {_dec(-fj)}")
    # the continuum's load (ustand/hypercircle.py): the same uniform traction, segment by segment (resultants)
    seg = p * th * h
    for j in range(ny):
        fx, fy = (seg, 0) if load == "tension" else (0, -seg)
        L.append(f"TRAC, {nid(nx, j)}, {nid(nx, j + 1)}, {_dec(fx)}, {_dec(fy)}")
    return "\n".join(L)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2 or a[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(2)
    load, sup = _opt(a, "--load", "tension"), _opt(a, "--support", "clamped")
    if load not in ("tension", "shear") or sup not in ("clamped", "roller"):
        print(__doc__)
        sys.exit(2)
    print(deck(int(a[0]), int(a[1]), load, sup, _opt(a, "--h", "1/10"), _opt(a, "--E", "200e9"),
               _opt(a, "--nu", "3/10"), _opt(a, "--th", "1/100"), _opt(a, "--p", "1e6")))
