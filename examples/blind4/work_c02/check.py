import math, itertools
from scipy.optimize import brentq
T=[("Mg-S-8",8,1.55,1100,0.60,0.15,45),("Mg-S-17",17,1.55,1100,1.0,0.20,78),("Mg-S-32",32,1.55,1100,1.4,0.25,130),
("Mg-H-8",8,1.75,1150,0.6,0.15,52),("Mg-H-17",17,1.75,1150,1.0,0.2,90),("Zn-12",12,1.10,780,0.8,0.12,60),("Zn-25",25,1.10,780,1.2,0.16,110)]
def Rg(rho,L,d,n):
    R1=rho/(2*math.pi*L)*(math.log(4*L/d)-1)
    return R1/n*(1+0.15*math.log(n))+0.2
def op(Ea,rho,L,d,n,beta,Ip):
    Rt=Rg(rho,L,d,n)
    f=lambda I: I*Rt-(Ea-0.85-beta*math.log10(I/Ip))
    I=brentq(f,1e-7,50,xtol=1e-14); return I,Ea-I*Rt
res=[]
for name,m,ea,cap,L,d,pr in T:
  for n in range(1,61):
    ok1=True; worst=None; lo=9;hi=0
    for Ea in (ea-.05,ea,ea+.05):
      for beta in (.12,.15,.18):
        for Ip in (.012,.02,.03,.045,.06):
          for rho in (12,140):
            I,Es=op(Ea,rho,L,d,n,beta,Ip); lo=min(lo,Es);hi=max(hi,Es)
    ok1 = lo>=0.85 and hi<=1.18
    # life
    lifeworst=1e99
    for Ea in (ea-.05,ea,ea+.05):
      for beta in (.12,.15,.18):
        Iw,_=op(Ea,12,L,d,n,beta,.03); Id,_=op(Ea,140,L,d,n,beta,.03)
        Iav=.5*Iw+.5*Id
        lifeworst=min(lifeworst,n*m*cap*.92*.9/Iav)
    res.append((n*(pr+40),name,n,ok1,lo,hi,lifeworst/8760))
res.sort()
for r in res[:400]:
    if r[3] and r[6]>=30: print("first full pass",r);break
print("cheapest protection-only passes:",[r for r in res if r[3]][:3])
print("cheapest life-only passes:",[r for r in res if r[6]>=30][:3])
print("n for each type: protection pass n-range")
for name in [t[0] for t in T]:
    ns=[r[2] for r in res if r[1]==name and r[3]]; ls=[r[2] for r in res if r[1]==name and r[6]>=30]
    print(name,"prot",(min(ns),max(ns)) if ns else None,"life",(min(ls),max(ls)) if ls else None)
