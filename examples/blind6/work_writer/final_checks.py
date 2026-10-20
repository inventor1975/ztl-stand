import math, numpy as np
from scipy.optimize import brentq
print('=== P1')
import p1
for d in (10,12,14):
    lo,hi=0.15,0.45
    f=lambda D: 1.0-p1.life_ok(d,D)*10
    if f(hi)<0: print(d,'infeasible'); continue
    Dm=max(brentq(f,0.05,0.45), d*18/1000)
    print(d,'Dmin',round(Dm,5),'cost',round(p1.ropes[d][2]*p1.L/1000+0.5+16*Dm**2,4), 'SF_C', round(p1.worst_tension(d,'C')[1]/p1.worst_tension(d,'C')[0],3))
print('=== P2'); import p2
c=p2.cheapest(160,85,38); print(c)
m=p2.check(50,16,63,40,160,85,38); print({k:round(v,4) for k,v in m.items()})
