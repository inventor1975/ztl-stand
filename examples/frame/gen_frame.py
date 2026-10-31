"""A plane multi-storey frame: `storeys` x `bays`, storey 3 m, bay 5 m, fixed bases; columns and beams one BEAM3
section (E 210 GPa, A 0.01 m2, I 8e-5 m4); a lateral load of 10 kN at every floor's left node and 20 kN down at
every beam-column joint. (2026-11-01, ztl-stand stage 1: frames.)
    python3 examples/frame/gen_frame.py STOREYS BAYS > deck.txt"""
import sys
ns, nb = int(sys.argv[1]), int(sys.argv[2])
nid = lambda f, c: f * (nb + 1) + c + 1
L = ["/PREP7", "ET, 1, BEAM3", "MP, EX, 1, 210e9", "R, 1, 0.01, 8e-5"]
for f in range(ns + 1):
    for c in range(nb + 1):
        L.append(f"N, {nid(f, c)}, {5 * c}, {3 * f}")
for f in range(ns):
    for c in range(nb + 1):
        L.append(f"E, {nid(f, c)}, {nid(f + 1, c)}")          # columns
for f in range(1, ns + 1):
    for c in range(nb):
        L.append(f"E, {nid(f, c)}, {nid(f, c + 1)}")          # beams
for c in range(nb + 1):
    L += [f"D, {nid(0, c)}, UX, 0", f"D, {nid(0, c)}, UY, 0", f"D, {nid(0, c)}, ROTZ, 0"]
for f in range(1, ns + 1):
    L.append(f"F, {nid(f, 0)}, FX, 10000")
    for c in range(nb + 1):
        L.append(f"F, {nid(f, c)}, FY, -20000")
print("\n".join(L))
