import math, itertools, numpy as np
from scipy.optimize import brentq
g=9.81; Ac=2.2e4
C=(0.70,0.80); Cd=(0.58,0.64)
dur={'15':900,'30':1800,'60':3600}
inten={'10':{'15':(85,92),'30':(62,68),'60':(40,44)},'100':{'15':(125,135),'30':(92,100),'60':(62,66)}}
orif={60:0.30,80:0.45,100:0.60,120:0.80,150:1.10}  # d mm: kEUR
def depth(A,d,Cd_,C_,i,t):
    Ao=math.pi*(d/1000)**2/4
    Qin=C_*i/3.6e6*Ac
    f=lambda h: A*h+Cd_*Ao*math.sqrt(1.2*g*h)*t-Qin*t
    return brentq(f,1e-9,50)
def qpeak(h,d,Cd_):
    Ao=math.pi*(d/1000)**2/4
    return Cd_*Ao*math.sqrt(2*g*h)
def worst(A,d,ret,T,which):
    # which: 'depth' -> max depth, 'q' -> max peak flow ; over duration and corners
    best=0
    for dd,t in dur.items():
        lo,hi=inten[ret][dd]
        for Cd_ in Cd:
            for C_ in C:
                for i in (lo,hi):
                    h=depth(A,d,Cd_,C_,i,t)
                    v=h if which=='depth' else qpeak(h,d,Cd_)
                    best=max(best,v)
    return best
Qcap10=0.025; Qcap100=0.045; Amax=610; Hmax=2.0; fb=0.30
def margins(A,H,d,drop=()):
    m={}
    m['R1']=Qcap10/worst(A,d,'10',None,'q')-1
    m['R2']=Qcap100/worst(A,d,'100',None,'q')-1
    m['R3']=(H-fb)/worst(A,d,'100',None,'depth')-1
    m['R4']=d/80-1
    m['R5']=min(Amax/A-1,Hmax/H-1)
    return {k:v for k,v in m.items() if k not in drop}
def feasible(drop=()):
    best=None
    for d in orif:
        for A in np.arange(100,Amax+0.01,5):
            H=Hmax
            m=margins(A,H,d,drop)
            if min(m.values())>=0: return (A,H,d,m)
    return None
if __name__=='__main__':
    print(feasible())
    for dr in ('R1','R2','R3','R4','R5'):
        print('drop',dr,feasible((dr,)))
    for d in orif:
        print(d,margins(560,2.0,d))
