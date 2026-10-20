from calc import *
from scipy.optimize import brentq
f=lambda p: solve(p,0,0.18,0,0.0001)[0]-0.004
p2=brentq(f,0.005,0.04); print("p2min",p2, p2*8.4e6)
# at p2, cheapest module set feasible?
res=[]
for n in itertools.product(range(5),repeat=5):
    w=worst(n,p2)
    if w is None: continue
    s1=w[0]
    if s1[0]<=0.008 and s1[2]<=0.011 and s1[3]<=0.015:
        res.append((sum(n[i]*cost[i] for i in range(5)),n,s1))
res.sort(); print(res[:3])
# smallest p feasible for imp1 for the best set, ignoring imp2
n=res[0][1]
for p in [0.0105,0.0108,0.011]:
    print(p,worst(n,p)[0])
