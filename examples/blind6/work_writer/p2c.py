from p2 import *
# largest L1 with any design (L2=85,T=38): use best cables 95/95 and breakers choose ok
def exists(L1,L2,T):
    return cheapest(L1,L2,T) is not None
lo,hi=100,600
while hi-lo>0.01:
    mid=(lo+hi)/2
    if exists(mid,85,38): lo=mid
    else: hi=mid
print('Lmax1',lo)
lo,hi=20,80
while hi-lo>0.001:
    mid=(lo+hi)/2
    if exists(160,85,mid): lo=mid
    else: hi=mid
print('Tmax at L1=160',lo)
print(cheapest(160,85,38))
for L in (200,230,260):
    print(L,cheapest(L,85,38))
