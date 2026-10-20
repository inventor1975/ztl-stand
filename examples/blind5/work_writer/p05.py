import math, itertools
from scipy.optimize import brentq
# source: Ca, Alk, Cl, SiO2, SO4, TDS  (lo,hi) mg/L ; price EUR/m3
SRC={"Town":dict(Ca=(60,80),Alk=(70,90),Cl=(20,30),Si=(8,12),SO4=(25,35),TDS=(220,280),price=1.90),
     "Well":dict(Ca=(180,230),Alk=(200,240),Cl=(60,90),Si=(22,30),SO4=(80,110),TDS=(650,780),price=0.65),
     "SoftWell":dict(Ca=(10,25),Alk=(200,240),Cl=(60,90),Si=(22,30),SO4=(80,110),TDS=(700,820),price=1.45)}
INH={"none":(0.5,0.0),"P1":(1.3,0.12),"P2":(1.9,0.22),"P3":(2.5,0.38)}   # LSImax, EUR per m3 makeup
ACID={"0":0.0,"40":0.4,"70":0.7}
SEAS=[("winter",2000,0.9,1.2,28,32),("midseason",3200,1.5,2.0,30,34),("summer",2200,2.2,2.8,34,38)]
FCIRC=1150.0; DRIFT=2e-5*FCIRC     # m3/h
HF=2430.0
LIM=dict(Si=150,Cl=400,SO4=1000)
DISCH=0.90   # EUR/m3 blowdown
ACIDC=0.12   # EUR per kg H2SO4 ; 0.98 kg per kg CaCO3 neutralised
CAP=26000.0
def E_of(Q): return Q*1000*3600/HF/1000   # m3/h
def lsi(Ca,Alk,TDS,T):
    A=(math.log10(TDS)-1)/10; B=-13.12*math.log10(T+273)+34.55
    pHs=9.3+A+B-(math.log10(Ca)-0.4+math.log10(Alk))
    pH=5.9+0.95*math.log10(Alk)
    return pH-pHs
def conc_ok(src,inh,r,N,Tb):
    s=SRC[src]
    Si=N*s["Si"][1]; Cl=N*s["Cl"][1]
    SO4=N*(s["SO4"][1]+0.96*r*s["Alk"][1])
    if Si>LIM["Si"] or Cl>LIM["Cl"] or SO4>LIM["SO4"]: return False
    Ca=N*s["Ca"][1]; Alk=N*s["Alk"][1]*(1-r)
    TDS=N*(s["TDS"][0]-0.26*r*s["Alk"][1])
    return lsi(Ca,Alk,TDS,Tb)<=INH[inh][0]
def Nmax(src,inh,r,Tb):
    if not conc_ok(src,inh,r,1.0,Tb): return 0.0
    lo,hi=1.0,200.0
    for _ in range(80):
        mid=(lo+hi)/2
        if conc_ok(src,inh,r,mid,Tb): lo=mid
        else: hi=mid
    return lo
def design(src,inh,rk):
    r=ACID[rk]; s=SRC[src]
    tot_M=0; cost=0; Bs=[]
    for nm,h,Ql,Qh,Tl,Th in SEAS:
        N=Nmax(src,inh,r,Th)
        if N<=1.0: return None
        E=E_of(Qh)
        B=max(0.0,E/(N-1)-DRIFT)
        M=E+B+DRIFT
        tot_M+=h*M; Bs.append(B)
        cost+=h*(M*s["price"]+B*DISCH+M*INH[inh][1]+M*r*s["Alk"][1]/1000*0.98*ACIDC)
    return dict(M=tot_M,cost=cost/1000,B=Bs,N=None)
if __name__=="__main__":
    rows=[]
    for src in SRC:
      for inh in INH:
        for rk in ACID:
            d=design(src,inh,rk)
            if d: rows.append((d["cost"],src,inh,rk,round(d["M"]),[round(b,3) for b in d["B"]]))
            else: rows.append((None,src,inh,rk,None,None))
    for r in sorted(rows,key=lambda r:(r[0] is None,r[0])): print(r)
