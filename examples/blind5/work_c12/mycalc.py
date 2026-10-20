import math, itertools
from math import exp, ceil
LAM=[(180,220),(230,280),(170,210),(90,120)]
COST=[33,36,38,45]
IVR={'none':(0,0,0),'basic':(0.06,0.10,14),'advanced':(0.12,0.18,31)}
def SL(lam,d,aht,n):
    A=lam*(1-d)*aht/60
    if n<=A: return 0.0,A
    # erlang B recursion
    B=1.0
    for k in range(1,n+1): B=A*B/(k+A*B)
    C=n*B/(n-A*(1-B))
    Pw=C
    return 1-Pw*exp(-(n-A)*20/(60*aht)),A
def worst(ivr,n):
    dlo=IVR[ivr][0]
    # R1,R3 worst corner
    out=[]
    for s in range(4):
        sl,A=SL(LAM[s][1],dlo,5.6,n[s])
        out.append((sl,A/n[s]))
    # R2 worst: aht hi, d lo, lam scan
    M=0
    for s in range(4):
        lo,hi=LAM[s]
        best=1e9
        for i in range(0,201):
            lam=lo+(hi-lo)*i/200
            sl,_=SL(lam,dlo,5.6,n[s])
            best=min(best,lam*(sl-0.87))
        M+=best
    return out,M
def feasible(ivr,n):
    out,M=worst(ivr,n)
    return all(sl>=0.70 and occ<=0.92 for sl,occ in out) and M>=0
def cost(ivr,n):
    return sum(n[s]*COST[s]*0.9 for s in range(4))+IVR[ivr][2]
if __name__=="__main__":
    for ivr in IVR:
        dlo=IVR[ivr][0]
        # per-part min n for R1,R3
        mins=[]
        for s in range(4):
            n=1
            while True:
                sl,A=SL(LAM[s][1],dlo,5.6,n)
                if sl>=0.7 and A/n<=0.92: break
                n+=1
            mins.append(n)
        print(ivr,'min n R1/R3',mins,'A max',[round(LAM[s][1]*(1-dlo)*5.6/60,2) for s in range(4)])
