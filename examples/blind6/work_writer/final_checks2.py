import math, numpy as np, random
print('=== P6 fine check')
import p6
e,s,bd='E3H','SC','G1200'
S=1.3747444
N,eta,_=p6.ext[e]; K25,a,_=p6.sol[s]
worst=dict(xN=0,y1=0)
for c0 in np.linspace(6.0,7.5,4):
  for r in np.linspace(0.02,0.04,5):
    for T in np.linspace(15,30,61):
        Keff=eta*K25*math.exp(-a*(T-25)); x=p6.solve(N,Keff,S,c0,r)
        worst['xN']=max(worst['xN'],x[-1]); worst['y1']=max(worst['y1'],Keff*x[0])
print(worst)
m=p6.margins(e,s,bd,S); print({k:round(float(v),4) for k,v in m.items()})
# exact Smin by R5 for E3H/SC
from scipy.optimize import brentq
f=lambda S: p6.margins(e,s,bd,S)['R5']
Sm=brentq(f,1.0,1.8); print('Smin',Sm, 'cost',p6.cost(e,s,bd,Sm,p6.margins(e,s,bd,Sm)))
for e2 in ('E4','E3','E2'):
    for bd2 in ('G1200','G2000'):
        r=p6.best_S(e2,s,bd2); print(e2,bd2,None if r is None else (round(r[0],3),r[1]))
print('=== P5'); import p5
for r in p5.sweep()[:4]: print(r)
print({k:round(v,4) for k,v in p5.margins('K40','D50',50).items()})
print('K40M','D50',50,{k:round(v,4) for k,v in p5.margins('K40M','D50',50).items()})
print('=== P4'); import p4
p4.ins['PIR-50']=(50,0.026,0.08,19.5)
def feas4(Ta):
    return [x for x in p4.feasible(Ta) if 2*(p4.r1+p4.ins[x[1]][0]/1000)*1000<=180+1e-9]
print(feas4(-40), feas4(-37.9), feas4(-37.8))
lo,hi=-45,-30
while hi-lo>1e-6:
    mid=(lo+hi)/2
    if feas4(mid): hi=mid
    else: lo=mid
print('limit',hi,feas4(hi))
for i in ('PIR-40','PIR-50'):
    print(i,'loss at -40',p4.loss(i,-40))
for c in p4.cab: print(c, p4.out(c,3,207), p4.out(c,3,253))
