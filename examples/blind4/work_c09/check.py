import math, itertools, numpy as np
from gen import discs, pads, rets, modes_d
g=9.81
Tb=[20,100,300,450,550,650]
def hf(v): return np.interp(v,[0,5,10,15],[12,28,45,62])  # constant beyond 15
def sim(f,r,pad,ret,mode,fh,fmu,fK):
    m,s,vk,L,ta=modes_d[mode]; s=float(s); v=vk/3.6
    Pg=m*g*s*v; Pr=0.012*m*g*v; Pa=0.5*1.2*5.0*v**3; Pret=ret[1]*1000*vk/40
    Pf=max(0,Pg-Pr-Pa-Pret)
    t=L*1000/v
    out=[]
    for d,share in ((f,0.65),(r,0.35)):
        Pd=0.92*Pf*share/2; hA=fh*hf(v)*float(d[2]); C=d[1]*460
        Tss=ta+Pd/hA; tau=C/hA
        out.append(Tss-(Tss-(ta+30))*math.exp(-t/tau))
    Tf,Tr=out
    mus=[float(x) for x in pads[pad][0]]
    muf=np.interp(Tf,Tb,mus); mur=np.interp(Tr,Tb,mus)
    F=0.9*1000*fK*fmu*(muf*f[3]+mur*r[4])
    Freq=m*(4.0+g*s-0.012*g)
    return Tf,Tr,F-Freq
fhs=np.linspace(0.8,1,21)
res={}
for f in discs:
  for r in discs:
    for pad in pads:
      for ret in rets:
        price=2*f[5]+2*r[5]+4*pads[pad][1]+ret[2]
        worst=[1e18,1e18]  # min (600-T), min margin
        for mode in modes_d:
          for fh in fhs:
            for fmu in (0.92,1):
              Tf,Tr,M=sim(f,r,pad,ret,mode,fh,fmu,0.95)
              worst[0]=min(worst[0],600-Tf,600-Tr); worst[1]=min(worst[1],M)
        res[(f[0],r[0],pad,ret[0])]=(price,worst)
ok=[(p,k,w) for k,(p,w) in res.items() if w[0]>=0 and w[1]>=0]
ok.sort()
print(len(ok)); 
for x in ok[:8]: print(x)
# near misses
nm=sorted([(p,k,w) for k,(p,w) in res.items() if p<=5040 and (w[0]>=0 or w[1]>=0)])
print(len(nm))
for x in nm[-12:]: print(x)
