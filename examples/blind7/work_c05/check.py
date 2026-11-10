from fractions import Fraction as F
import itertools
reg=[-16000,2000,4000,5000,5000,5000,5000]; hv=[-25000,2000,4000,8000,9000,9000,9000]
def npv(cf,r,low=True):
    s=F(cf[0])
    for k in range(1,7):
        s+=F(cf[k])*(F(97,100) if low else F(103,100))/(1+r)**k
    return s
# inflows all positive -> worst = all at 97%; NPV decreasing... in r? flows after 0 positive -> NPV decreasing in r -> worst r=11%
for n,cf in (("reg",reg),("heavy",hv)):
    w=min(npv(cf,F(r,100)) for r in range(9,12)) # corners
    # fine scan over r
    ws=min(npv(cf,F(9)/100+F(i,1000)*F(2,100)) for i in range(0,1001))
    print(n,"worst",float(npv(cf,F(11,100))),float(ws),"best",float(npv(cf,F(9,100),False)))
# crossover
d=[h-r for h,r in zip(hv,reg)]
f=lambda r: sum(F(d[k])/(1+r)**k for k in range(7))
lo,hi=F(0),F(3,10)
for _ in range(200):
    m=(lo+hi)/2
    if f(m)>0: lo=m
    else: hi=m
print("crossover %",float(lo*100), "f(.11926)",float(f(F(11926,100000))),float(f(F(11927,100000))))
