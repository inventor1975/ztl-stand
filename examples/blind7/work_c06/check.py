import itertools, math
from fractions import Fraction as F
G={'A':((0.2375,0.2625),(240,260),2.5,1.0,60,180),
   'B':((0.285,0.315),(300,330),4.0,1.0,80,220),
   'C':((0.38,0.42),(430,470),7.0,1.5,100,260)}
Cm=1.2;Tl=1.5
def cost(V,n,C,Ct,Tc):
    Tm=math.pi*60*200/(1000*0.2*V); T=(C/V)**(1/n)
    return Cm*(Tl+Tm)+(Cm*Tc+Ct)*Tm/T
def worst(g,V):
    (n,C,Ct,Tc,lo,hi)=G[g]
    # scan corners and a fine grid inside (cost monotone expected; verify)
    w=0
    for k in range(21):
        for m in range(21):
            nn=n[0]+(n[1]-n[0])*k/20; CC=C[0]+(C[1]-C[0])*m/20
            w=max(w,cost(V,nn,CC,Ct,Tc))
    return w
for g in G:
    (n,C,Ct,Tc,lo,hi)=G[g]
    res=[]
    for i in range(int(lo*10),int(hi*10)+1):
        V=i/10
        if Cm*0+Tl+math.pi*60*200/(1000*0.2*V)>3.0: continue
        res.append((worst(g,V),V))
    if not res: print(g,'no V meets cycle'); continue
    b=min(res); print(g,'best worst cost',b, 'meets 4.04:',b[0]<=4.04, 'Vrange feasible cycle', min(r[1] for r in res), 'cost<=4.04 V set:',[min(r[1] for r in res if r[0]<=4.04), max(r[1] for r in res if r[0]<=4.04)] if b[0]<=4.04 else None)
