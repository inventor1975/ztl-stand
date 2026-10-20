from p10 import *
from scipy.optimize import brentq
def Mfmax(fan):
    f=lambda Mf: ST(Mf,Ts(fan,Tamb[1]))-Mf_stor_days
    return brentq(f,0.10,0.30)
rows=[]
for dr in dryers:
    B,Tmax,_=dryers[dr]
    for fan in fans:
        Mf=Mfmax(fan)
        # min Td for throughput
        g=lambda Td: design_eval(dr,fan,Td,Mf)[0]['thru']
        ok=None
        if g(Tmax)<0: rows.append((dr,fan,'infeasible thru',round(Mf,5))); continue
        Td=brentq(g,40,Tmax) if g(40)<0 else 40
        m,t=design_eval(dr,fan,Td,Mf)
        if min(m['damage'],m['store'])<-1e-9: rows.append((dr,fan,'damage',round(Td,3))); continue
        rows.append((round(cost(dr,fan,Td,Mf),3),dr,fan,round(Td,3),round(Mf,5),round(t,3),{k:round(v,4) for k,v in m.items()}))
for r in sorted(rows,key=lambda r:(isinstance(r[0],str),r[0] if not isinstance(r[0],str) else 0)): print(r)
