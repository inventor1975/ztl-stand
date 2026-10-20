from fractions import Fraction as Fr
I=[2370,2110,2730,3780]; u=Fr(88,100)
need=[Fr(i)/u for i in I]
scap=[800,800,800,300]
tiers={'T0':(0,0,0),'T1':(Fr('11.8'),0,800),'T2':(Fr('9.6'),400,1500),'T3':(Fr('8.4'),900,2200)}
print([float(n) for n in need])
def cost(B,t,ps=24,need=need):
    pr,cm,cap=tiers[t]; tot=118*B; ok=True
    for n,s in zip(need,scap):
        F=min(cap,max(0,n-B)); S=max(0,n-B-F)
        if S>s: ok=False
        tot+=3*pr*max(F,cm)+3*ps*min(S,s)
    return tot,ok
import numpy as np
best=None
for t in tiers:
    # piecewise linear in B: scan fine + breakpoints
    cands=set(range(0,3201,1))
    res=[(cost(B,t),B) for B in cands]
    ok=[(float(c),B) for (c,o),B in res if o]
    if ok:
        m=min(ok); print(t,m, 'min over feasible', 'cost<=355k' if m[0]<=355000 else 'over')
    else: print(t,'infeasible')
for t in tiers:
    feas=[B for B in range(3201) if cost(B,t)[1]]
    print(t, (min(feas),max(feas)) if feas else None)
print('----')
bp=set()
for n in need:
    for cap in (0,800,1500,2200):
        for sc in (0,300,800):
            bp.add(n-cap-sc); bp.add(n-cap)
    bp.add(n)
bp|={Fr(0),Fr(3200)}
for t in tiers:
    r=[(cost(B,t)[0],B) for B in bp if 0<=B<=3200 and cost(B,t)[1]]
    if r: c,B=min(r); print(t,float(c),float(B))
