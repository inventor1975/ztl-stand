import itertools, math
import numpy as np
banks={100:4100,150:5850,175:6725,200:7000,225:7875,250:8750,300:10500}
def ev(P,pf,dl,C):
    Q=P*math.tan(math.acos(pf)); k0=math.hypot(P,Q); k1=math.hypot(P,Q-dl*C)
    return P/k1, 3*(k0-k1)
for C,cost in banks.items():
    # grid scan incl. corners
    Ps=np.linspace(380,420,41); pfs=np.linspace(.75,.79,41); dls=np.linspace(.95,1.05,41)
    minpf=9; maxpb=0; wpf=None; wpb=None
    for P in Ps:
        for pf in pfs:
            for dl in dls:
                a,s=ev(P,pf,dl,C)
                if a<minpf: minpf=a; wpf=(P,pf,dl)
                pb=cost/s if s>0 else 1e18
                if pb>maxpb: maxpb=pb; wpb=(P,pf,dl)
    print(C,"min pfc %.5f at %s | worst payback %.4f at %s | ok=%s"%(minpf,wpf,maxpb,wpb,minpf>=.95 and maxpb<=32))
