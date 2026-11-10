from fractions import Fraction as F
import itertools
def eaa(price,n,infl,r):
    npv=-price+sum(infl/(1+r)**k for k in range(1,n+1))   # explicit sum
    return npv*r/(1-(1+r)**(-n))
for name,n,lo,hi in (("older",3,38000,42000),("newer",6,28500,31500)):
    best=None
    N=2000
    for i in range(N+1):
        r=F(9,100)+F(2,100)*i/N
        for infl in (F(lo),F(hi)):
            v=eaa(50000,n,infl,r)
            if best is None or v<best[0]: best=(v,r,infl)
    print(name,float(best[0]),float(best[1]),float(best[2]), "corner r=.11,lo:",float(eaa(50000,n,F(lo),F(11,100))),"r=.09,lo:",float(eaa(50000,n,F(lo),F(9,100))))
    print(" best-case",float(eaa(50000,n,F(hi),F(9,100))))
