import numpy as np, itertools
from scipy.optimize import linprog
U=4.0; c=0.0012; F=[1.085,1.09,1.095,1.10]; lo,hi=1.02,1.22
opts={"1.06":(1.06,.021),"1.10":(1.10,.012),"1.14":(1.14,.0058),"none":(1.10,0.0)}
A2=0.30
def run(name,mode="exact"):
    K,pi=opts[name]; on=0 if name=="none" else 1
    # vars: h1..h4,o1..o4 (8), m_q for v in (lo,hi)  -> m[v][q] 8 more
    n=8+8
    def coefs(q,S,v):
        # P_q = a0 + ah*h + ao*o
        a0=U*v/S-3
        ah=U*(1/F[q]-1/S)-c*U/F[q]
        ao=on*U*(1/min(S,K)-1/S)-pi*on*U
        return a0,ah,ao
    Aub=[];bub=[]
    def row(q,a0,ah,ao):
        r=np.zeros(n); r[q]=ah; r[4+q]=ao; return r
    Ss={q:[lo,K,hi] if lo<K<hi else [lo,hi] for q in range(4)}
    vs=[.85,1.10]
    for q in range(4):
        for S in Ss[q]:
            for v in vs:
                a0,ah,ao=coefs(q,S,v)
                # a0+ah h+ao o >= -0.1 -> -(ah h+ao o) <= a0+0.1
                Aub.append(-row(q,a0,ah,ao)); bub.append(a0+0.1)
    for vi,v in enumerate(vs):
        for q in range(4):
            for S in Ss[q]:
                a0,ah,ao=coefs(q,S,v)
                # m <= f -> m - f <=0  -> m - ah h - ao o <= a0
                r=-row(q,a0,ah,ao); r[8+vi*4+q]=1; Aub.append(r); bub.append(a0)
        r=np.zeros(n); r[8+vi*4:8+vi*4+4]=-1; Aub.append(r); bub.append(-A2)
    # R3
    r=np.zeros(n); r[:4]=1; r[4:8]=on; Aub.append(r); bub.append(3.2)
    Aub.append(-r); bub.append(-1.6)
    for q in range(4):
        r=np.zeros(n); r[q]=1; r[4+q]=on; Aub.append(r); bub.append(1)
    r=np.zeros(n); r[:4]=U; Aub.append(r); bub.append(9)
    r=np.zeros(n); r[4:8]=pi*on*U; Aub.append(r); bub.append(0.10)
    cost=np.zeros(n); 
    for q in range(4): cost[q]=c*U/F[q]; cost[4+q]=pi*on*U
    bounds=[(0,1)]*8+[(None,None)]*8
    if on==0: bounds=[(0,1)]*4+[(0,0)]*4+[(None,None)]*8
    res=linprog(cost,A_ub=np.array(Aub),b_ub=bub,bounds=bounds,method="highs")
    return res
import sys
A2=float(sys.argv[1])
for k in ['1.10']:
    r=run(k)
    print(repr(list(r.x[:8])));print(k,r.status,r.message[:50], None if r.status else (round(r.fun*1000,3), np.round(r.x[:8],4)))
