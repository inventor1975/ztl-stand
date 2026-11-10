from fractions import Fraction as F
import math
Q=1.12
S=[("A36",36,60),("A441",50,53),("A572",50,100),("A514",100,60)]
def ac(sy,k): return (k/(Q*0.6*sy))**2/math.pi
for n,sy,k in S:
    print(n,"worst",ac(sy,.9*k),"best",ac(sy,1.1*k),"ok2.5",ac(sy,.9*k)>=2.5)
print("max over steels of worst:",max(ac(sy,.9*k) for n,sy,k in S))
# scan K over range for monotonic check
for n,sy,k in S:
    m=min(ac(sy,k*(0.9+0.2*i/1000)) for i in range(1001)); print(n,"scan min",m)
