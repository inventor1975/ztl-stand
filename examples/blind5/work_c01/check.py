import math, itertools
cyc=[(0.25,1450,(4,5),(58,66)),(0.45,1450,(11,13),(66,74)),(0.25,900,(20,23.1),(70,80)),(0.05,300,(36,40),(60,70))]
B={"A":(95,100,110,.38),"B":(118,128,110,.52),"C":(135,150,130,.61),"D":(160,180,130,.8),"E":(190,215,150,1.05),"F":(235,270,150,1.45),"G":(290,345,180,2.1)}
O={"VG68":(68,.2),"VG150":(150,.25),"VG320":(320,.35),"VG680":(680,.5)}
K={"none":(.6,0),"kit":(1.0,.9)}
kn=[.4,.7,1,2,4]; an=[.4,.75,1,1.7,2.3]
def aL(k):
    if k<=kn[0]: return an[0]
    if k>=kn[-1]: return an[-1]
    for i in range(4):
        if kn[i]<=k<=kn[i+1]: return an[i]+(an[i+1]-an[i])*(k-kn[i])/(kn[i+1]-kn[i])
def life(C,od,nu40,fc,Frs,Ts):
    dm=(60+od)/2; d=0
    for (f,n,_,_),Fr,T in zip(cyc,Frs,Ts):
        P=Fr*(1+.45*.3)
        nu=nu40*math.exp(-.04*(T-40))
        nu1=(45000*n**-.83 if n<1000 else 4500*n**-.5)*dm**-.5
        L=aL(nu/nu1)*fc*(C/P)**(10/3)
        d+=f*60*n/(1e6*L)
    return 1/d
res=[]
for b,(C,C0,od,pb) in B.items():
  for o,(nu,po) in O.items():
    for k,(fc,pk) in K.items():
      Lw=life(C,od,nu,fc,[c[2][1] for c in cyc],[c[3][1] for c in cyc])
      # brute worst over all 2^8 corners (also check monotonic)
      Lmin=min(life(C,od,nu,fc,Fs,Ts) for Fs in itertools.product(*[c[2] for c in cyc]) for Ts in itertools.product(*[c[3] for c in cyc]))
      ok=Lmin>=56000 and C0>=2.5*1.18*40 and od<=150
      res.append((round(pb+po+pk,2),b,o,k,round(Lw),round(Lmin),ok))
for r in sorted(res):
    print(r)
print("----")
mid=lambda r:(r[0]+r[1])/2
print(life(95,110,68,.6,[mid(c[2]) for c in cyc],[mid(c[3]) for c in cyc]), "nominal A/VG68/none; stand by=53991.7 => value", 56000-53991.7257)
print(life(235,150,150,.6,[c[2][1] for c in cyc],[c[3][1] for c in cyc]))
# EARNED but loosest: also min over interior? monotone check on random sample
import random
C,od,nu,fc=235,150,150,.6
m=1e9
for _ in range(20000):
    m=min(m,life(C,od,nu,fc,[random.uniform(*c[2]) for c in cyc],[random.uniform(*c[3]) for c in cyc]))
print("random min",m)
