import sys
k = int(sys.argv[1])
L = ["/PREP7", "ET, 1, LINK1"]
for f in range(k + 1):
    L += [f"N, {2*f+1}, 0, {f*0.75}", f"N, {2*f+2}, 1, {f*0.75}"]
L += ["MP, EX, 1, 1", "R, 1, 1", "MAT  1", "REAL 1"]
for f in range(k):
    a, b, c, d = 2*f+1, 2*f+2, 2*f+3, 2*f+4
    L += [f"E, {a}, {c}", f"E, {b}, {d}", f"E, {c}, {d}", f"E, {a}, {d}", f"E, {b}, {c}"]
L += ["E, 1, 2"]
L += [f"F, {2*f+1}, FX, 1" for f in range(1, k + 1)]
L += ["D, 1, UX, 0", "D, 1, UY, 0", "D, 2, UY, 0"]
print("\n".join(L))
