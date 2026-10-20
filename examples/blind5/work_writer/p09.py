import numpy as np
INV=[(2000,2370),(1750,2110),(2300,2730),(3150,3780)]; UT=(0.88,0.94)
DEM=[(a/UT[1],b/UT[0]) for a,b in INV]    # Q1..Q4 positions needed
OWN=118.0  # EUR/position/yr
TIER={"T0":(None,0,0),"T1":(11.8,0,800),"T2":(9.6,400,1500),"T3":(8.4,900,2200)}  # price/pos/month, min commit, cap
SPOT=(18.0,24.0); SPOTCAP=[800,800,800,300]
BMAX=3200
def cost_for(B,tier,Dq=None,spot=24.0):
    p,commit,cap=TIER[tier]
    tot=OWN*B
    for q,(lo,hi) in enumerate(DEM):
        D=hi
        need=max(0.0,D-B)
        if tier=="T0": F=0.0
        else: F=min(cap,need)
        S=need-F
        if S>SPOTCAP[q]+1e-9: return None
        tot+=3*(0 if tier=="T0" else p*max(F,commit))+3*spot*S
    return tot
if __name__=="__main__":
    best={}
    for tier in TIER:
        bb=None
        for B in np.arange(0,BMAX+1,5):
            c=cost_for(B,tier)
            if c is not None and (bb is None or c<bb[0]): bb=(c,B)
        best[tier]=bb; print(tier,bb)
    # unrestricted B limit
    for tier in TIER:
        bb=None
        for B in np.arange(0,4301,5):
            c=cost_for(B,tier)
            if c is not None and (bb is None or c<bb[0]): bb=(c,B)
        print("noBmax",tier,bb)
