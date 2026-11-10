import itertools, math
from fractions import Fraction as F
P=[(2.5,97,101),(3.0,91,94),(2.0,84,87),(0.5,74,79)]
def dose(red,pick):
    D=0
    for (c,lo,hi),s in zip(P,pick):
        L=(lo,hi)[s]-red
        if L>=80: D+=c/8*2**((L-90)/5)
    return 100*D
def rng(nrr):
    red=nrr-7
    v=[dose(red,p) for p in itertools.product((0,1),repeat=4)]
    return min(v),max(v)
lo,hi=rng(7); print("none",lo,hi,[16.61*math.log10(x/100)+90 for x in(lo,hi)])
# fine scan to confirm monotone (corners)
import random
for n in(15,19,22,24,27,30):
    lo,hi=rng(n)
    mx=max(dose(n-7,[0]*4) if False else 0 for _ in[0])
    # random scan
    m=0
    for _ in range(200000):
        D=0
        for c,l,h in P:
            L=random.uniform(l,h)-(n-7)
            if L>=80: D+=c/8*2**((L-90)/5)
        m=max(m,100*D)
    print(n,lo,hi,"scan max",m)
