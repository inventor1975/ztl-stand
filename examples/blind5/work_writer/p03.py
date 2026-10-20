import math, itertools, numpy as np
from scipy.optimize import brentq
COL={"F1":(2.0,0.76,4.2,0.016,0.42),"F2":(2.3,0.80,3.4,0.014,0.55),"F3":(2.5,0.81,3.0,0.012,0.68),
     "T1":(2.2,0.74,1.4,0.005,0.85),"T2":(3.0,0.76,1.3,0.004,1.15),"T3":(2.6,0.78,1.2,0.0035,1.05)}
TANKS=[300,500,750,1000,1500]
SEAS=[# name, days, H lo,hi (kWh/m2/d), sun h, Ta lo,hi, Tc lo,hi
 ("winter",90,1.4,2.0,6,3,7,6,9),("spring",92,3.6,4.6,8,10,14,9,12),
 ("summer",92,5.6,6.8,10,20,26,15,18),("autumn",91,2.6,3.4,7,11,15,11,14)]
CW=4.186/3600  # kWh/(kg K)
def tank_T(A,col,UA,H,h,Ta,Tc,draw):
    A0,e0,a1,a2,_=COL[col]
    G=H/h*1000
    Tr=Ta+8
    def f(T):
        dT=T+6-Ta
        eta=max(0.0,e0-a1*dT/G-a2*dT*dT/G)
        return A*H*eta-draw*CW*(T-Tc)-UA*24/1000*(T-Tr)
    return brentq(f,Tc-1,800)   # f(Tc-1)>0? check
def grid(lo,hi): return [lo,(lo+hi)/2,hi]
def evaluate(col,n,V,ins,grd=grid):
    A=COL[col][0]*n
    UA=1.8*(V/300)**0.6*(0.6 if ins else 1.0)
    Tmax=0; auxw=0
    for draw in (540,600,660):
        tot=0
        for (nm,d,Hl,Hh,h,Tal,Tah,Tcl,Tch) in SEAS:
            worst=0
            for H in grd(Hl,Hh):
              for Ta in grd(Tal,Tah):
                for Tc in grd(Tcl,Tch):
                    T=tank_T(A,col,UA,H,h,Ta,Tc,draw)
                    Tmax=max(Tmax,T)
                    aux=max(0.0,draw*CW*(45-T))
                    worst=max(worst,aux)
            tot+=d*worst
        auxw=max(auxw,tot)
    return dict(aux=auxw,Tmax=Tmax,ratio=V/A,cost=n*COL[col][4]+0.90*(V/300)**0.8+(0.25 if ins else 0.0))
if __name__=="__main__":
    rows=[]
    for col in COL:
      for n in range(1,17):
        for V in TANKS:
          for ins in (0,1):
            e=evaluate(col,n,V,ins); e.update(col=col,n=n,V=V,ins=ins); rows.append(e)
    import pickle; pickle.dump(rows,open('p03rows.pkl','wb'))
    print(len(rows))
    for FMIN,TM in ((3300,75),):
        ok=[e for e in rows if e["aux"]<=FMIN and e["Tmax"]<=TM and 50<=e["ratio"]<=100]
        ok.sort(key=lambda e:e["cost"])
        print(len(ok))
        for e in ok[:8]: print({k:(round(v,3) if isinstance(v,float) else v) for k,v in e.items()})
