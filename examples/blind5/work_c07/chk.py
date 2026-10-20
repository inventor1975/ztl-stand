from itertools import product
ex={"ext":(140,180,1.1,1.3,.10,2.0,10.0),"chest":(90,120,.8,1.0,.28,6.0,21.0),"spine":(40,60,5.0,6.0,.16,3.4,14.0),"pelvis":(20,30,7.5,9.0,.21,4.4,17.0)}
def H(pb,ba,co,mode):
    s=0
    for N0,N1,K0,K1,a,b,c in ex.values():
        if mode=="worst": N,K,f=N1,K1,1.1
        elif mode=="nom": N,K,f=(N0+N1)/2,(K0+K1)/2,1.0
        else: N,K,f=N0,K0,0.9
        s+=N*K*2**(-(pb/(a*f)+ba/(b*f)+co/(c*f)))
    return 1.14*.25*1/2.2**2*s
res=[]
for pb in [0,.5,1,1.5,2,2.5,3]:
  for ba in [0,10,20,30]:
    for co in [0,50,100,150]:
      m=11.34*pb+2.7*ba+2.35*co; t=pb+ba+co
      price=14*(40*pb+1.8*ba+.55*co)
      res.append((price,pb,ba,co,m,t,H(pb,ba,co,"nom"),H(pb,ba,co,"worst")))
res.sort()
for r in res:
    if r[4]<=55 and r[5]<=60 and r[6]<=0.02: print(r)
print("passing worst:",[r for r in res if r[4]<=55 and r[5]<=60 and r[7]<=0.005])
print("--- witness")
from fractions import Fraction as Fr
w={"ext":(154,"9/100","9/5","9"),"chest":(72,"77/250","27/5","189/10"),"spine":(200,"18/125","153/50","63/5"),"pelvis":(150,"189/1000","99/25","153/10")}
s=0
for n,(nk,a,b,c) in w.items():
    x=float(Fr(3)/Fr(a))
    s+=nk*2**(-x)
print(1.14*.25/2.2**2*s)
print("--- R1+R3 only (no mass limit), worst-case")
ok=[r for r in res if r[5]<=60 and r[7]<=0.005]
print(ok[:3])
print("--- R1+R2 only (no thickness limit)")
print([r for r in res if r[4]<=55 and r[7]<=0.005][:3])
print("--- R1 only"); print([r for r in res if r[7]<=0.005][:3])
print("min lead3 mass", 11.34*3)
