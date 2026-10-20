# independent check: for each (source, programme, acid): minimal B_s from worst case over the full box, by brute-force corners
import itertools, math
from math import log10
mpf=float
src = {"Town":dict(Ca=(60,80),Alk=(70,90),Cl=(20,30),Si=(8,12),SO4=(25,35),TDS=(220,280),price=1.90),
       "Well":dict(Ca=(180,230),Alk=(200,240),Cl=(60,90),Si=(22,30),SO4=(80,110),TDS=(650,780),price=0.65),
       "SoftWell":dict(Ca=(10,25),Alk=(200,240),Cl=(60,90),Si=(22,30),SO4=(80,110),TDS=(700,820),price=1.45)}
prog = {"none":(0.5,0),"P1":(1.3,.12),"P2":(1.9,.22),"P3":(2.5,.38)}
seas = {"w":(2000,(0.9,1.2),(28,32)),"m":(3200,(1.5,2.0),(30,34)),"s":(2200,(2.2,2.8),(34,38))}
D=0.023; kE=1.4815
def Ncap_hi(sname, r, Lmax, T):
    """max N over composition corners: worst (smallest) N allowed over composition box, T given"""
    s=src[sname]; worst=None
    for Ca,Alk,Cl,Si,SO4,TDS in itertools.product(*[s[k] for k in ("Ca","Alk","Cl","Si","SO4","TDS")]):
        lims=[150/Si, 400/Cl, 1000/(SO4+0.96*r*Alk)]
        # LSI(N) direct
        def LSI(N):
            Acw=N*Alk*(1-r); pH=5.9+0.95*log10(Acw); Tl=N*(TDS-0.26*r*Alk)
            A=(log10(Tl)-1)/10; Bp=-13.12*log10(T+273)+34.55; C=log10(N*Ca)-0.4; Dp=log10(Acw)
            return pH-(9.3+A+Bp-(C+Dp))
        # LSI increasing in N: bisect
        K=LSI(1.0); assert abs(LSI(10.0)-K-2.85)<1e-9
        lims.append(10**((Lmax-K)/2.85))
        n=min(lims)
        worst=n if worst is None else min(worst,n)
    return worst
res=[]
for sn in src:
  for pn,(Lm,pc) in prog.items():
    for r in (0,0.4,0.7):
      Bs={}; ok=True; V=0; cost=0
      for sk,(h,Qr,Tr) in seas.items():
        Nmax=min(Ncap_hi(sn,r,Lm,mpf(T)) for T in Tr)   # T monotone: corners suffice
        # note: N>=1 always; need N<=Nmax -> B+D >= E/(Nmax-1) at E top (E=kE*Qtop)
        E=kE*Qr[1]
        if Nmax<=1: ok=False;break
        B=max(mpf(0),E/(Nmax-1)-D)
        Bs[sk]=B; V+=h*(E+B+D)
        acid=r*(90 if sn=="Town" else 240)*0.98*0.12/1000
        cost+=h*((E+B+D)*(src[sn]["price"]+pc+acid)+0.9*B)
      if ok:
        res.append((cost/1000,sn,pn,r,{k:float(v) for k,v in Bs.items()},float(V),V<=26000))
res.sort(key=lambda t:float(t[0]))
for x in res[:12]: print(x)
print(len(res),"combos with Nmax>1;", sum(1 for x in res if x[-1]),"pass R5")
