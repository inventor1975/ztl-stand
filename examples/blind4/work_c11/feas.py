from ref import *
import sys
def lr_right(th,Tset,tau_s,N,dT=-0.5,T0=45):
    Tch=Tset+dT; tau=tau_s/60.0; h=th/N
    return h/mpf(1.5)*sum(mpf(10)**((Tch-(Tch-T0)*exp(-k*h/tau)-121.1)/10) for k in range(1,N+1))
def tmin(F,req):
    lo,hi=0.01,300.0
    for _ in range(40):
        m=(lo+hi)/2
        if F(m)>=req: hi=m
        else: lo=m
    return hi
mode=sys.argv[1]; N=int(sys.argv[2]); Wlim=float(sys.argv[3])
for Ts in DRY:
    dmg=40/10**((Ts+1.5-121)/25)   # L4 budget; L1,L2 120, L3 150 looser
    wk=Wlim*60/50-15-DRY[Ts]
    need={}
    ok=True
    for (L,tau,req,al,pk,cy,bud) in LOADS:
        best=None
        for p in al:
            if Ts+1.5>PK[p][1]: continue
            F=(lambda t:LR(t,Ts,tau*PK[p][0])) if mode=='true' else ((lambda t:lr_riem(t,Ts,tau*PK[p][0],N)) if mode=='left' else (lambda t:lr_right(t,Ts,tau*PK[p][0],N)))
            t=float(tmin(F,req)); 
            if best is None or t<best[0]: best=(t,p)
        need[L]=best
    thneed=max(v[0] for v in need.values() if v)
    cap=min(dmg,wk)
    print(Ts,"need",{k:(round(v[0],2),v[1]) if v else None for k,v in need.items()},"cap damage %.2f wk %.2f"%(dmg,wk),"FEAS" if all(need.values()) and thneed<=cap else "infeasible")
