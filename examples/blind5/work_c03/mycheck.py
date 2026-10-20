import itertools, sys
from mpmath import mp, mpf, findroot
from scipy.optimize import brentq
cols = {"F1":(2.0,.76,4.2,.016,.42),"F2":(2.3,.80,3.4,.014,.55),"F3":(2.5,.81,3.0,.012,.68),
        "T1":(2.2,.74,1.4,.005,.85),"T2":(3.0,.76,1.3,.004,1.15),"T3":(2.6,.78,1.2,.0035,1.05)}
seas={"winter":(90,(1.4,2.0),6,(3,7),(6,9)),"spring":(92,(3.6,4.6),8,(10,14),(9,12)),
      "summer":(92,(5.6,6.8),10,(20,26),(15,18)),"autumn":(91,(2.6,3.4),7,(11,15),(11,14))}
cw=1.1628e-3
def Tsol(col,n,V,ins,H,hs,Ta,Tc,D):
    A,e0,a1,a2,_=cols[col]; UA=1.8*(V/300)**0.6*(0.6 if ins else 1); G=1000*H/hs; Tr=Ta+8
    def f(T):
        dT=T+6-Ta; eta=max(0,e0-a1*dT/G-a2*dT*dT/G)
        return n*A*H*eta-(cw*D*(T-Tc)+UA*0.024*(T-Tr))
    return brentq(f,-50,400,xtol=1e-12)
def annual(col,n,V,ins,corner):  # corner: (Hsel,Tasel,Tcsel,D) sel 0=lo 1=hi
    hsel,tsel,csel,D=corner; tot=0; Ts=[]
    for s,(d,Hr,hs,Tar,Tcr) in seas.items():
        T=Tsol(col,n,V,ins,Hr[hsel],hs,Tar[tsel],Tcr[csel],D); Ts.append(T)
        tot+=d*cw*D*max(0,45-T)
    return tot,Ts
def price(col,n,V,ins): return n*cols[col][4]+0.9*(V/300)**0.8+(0.25 if ins else 0)
if __name__=="__main__":
    res=[]
    for col in cols:
        for n in range(1,17):
            for V in (300,500,750,1000,1500):
                r=V/(n*cols[col][0])
                if not(50<=r<=100): continue
                for ins in (0,1):
                    E,_=annual(col,n,V,ins,(0,0,0,660))
                    # R2 worst
                    Tm=max(annual(col,n,V,ins,(1,1,1,540))[1])
                    res.append((price(col,n,V,ins),col,n,V,ins,E,Tm))
    res.sort()
    print(len(res))
    for r in res[:40]: print(r, "OK" if r[5]<=3700 and r[6]<=80 else "")
    ok=[r for r in res if r[5]<=3700 and r[6]<=80]
    print("first ok",ok[:3])
