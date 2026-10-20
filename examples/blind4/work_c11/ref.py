import itertools, math
from mpmath import mp, mpf, quad, exp
mp.dps=20
PK={"PK1":(1.0,137,0.10),"PK2":(1.4,137,0.35),"PK3":(1.8,135,1.20),"PK4":(2.2,132,1.90),"PK5":(1.2,126,0.80)}
LOADS=[("L1",30,9,["PK1","PK2","PK5"],12,20,120),("L2",60,12,["PK2","PK3","PK4","PK5"],6,15,120),
       ("L3",110,12,["PK2","PK3","PK4"],8,10,150),("L4",150,15,["PK3","PK4","PK5"],4,5,40)]
DRY={121:25,124:23,126:22,130:20,134:18}
def LR(th_min,Tset,tau_s,dT=-0.5,T0=45):
    Tch=Tset+dT; tau=tau_s/60.0
    f=lambda t: mpf(10)**((Tch-(Tch-T0)*exp(-t/tau)-121.1)/10)
    pts=[0]+[tau*k for k in (0.5,1,2,4,8) if tau*k<th_min]+[th_min]
    return quad(f,pts)/mpf(1.5)
def lr_riem(th_min,Tset,tau_s,N,dT=-0.5,T0=45):
    Tch=Tset+dT; tau=tau_s/60.0; h=th_min/N
    return h/mpf(1.5)*sum(mpf(10)**((Tch-(Tch-T0)*exp(-k*h/tau)-121.1)/10) for k in range(N))
def thmin(Tset,tau_s,req,N=None):
    lo,hi=0.01,300.0
    F=(lambda t:LR(t,Tset,tau_s)) if N is None else (lambda t:lr_riem(t,Tset,tau_s,N))
    for _ in range(45):
        m=(lo+hi)/2
        if F(m)>=req: hi=m
        else: lo=m
    return hi
if __name__=="__main__":
    import sys
    N=int(sys.argv[1]) if len(sys.argv)>1 else None
    for Ts in DRY:
        for (L,tau,req,al,pk,cy,bud) in LOADS:
            r={p:round(float(thmin(Ts,tau*PK[p][0],req,N)),3) for p in al}
            print(Ts,L,r)
        print(Ts,"damage max th (L4 40):",round(40/10**((Ts+1.5-121)/25),2))
