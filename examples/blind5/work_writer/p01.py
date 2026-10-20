import itertools, math, numpy as np
# bearings: name, C, C0, OD, price kEUR
B=[("R-60A",95,100,110,0.38),("R-60B",118,128,110,0.52),("R-60C",135,150,130,0.61),
   ("R-60D",160,180,130,0.80),("R-60E",190,215,150,1.05),("R-60F",235,270,150,1.45),("R-60G",290,345,180,2.10)]
LUB=[("VG68",68,0.20),("VG150",150,0.25),("VG320",320,0.35),("VG680",680,0.50)]
KIT=[("none",0.60,0.0),("kit",1.00,0.9)]
cyc=[# f, n, Frlo,Frhi, Tlo,Thi
 (0.25,1450,4,5,58,66),(0.45,1450,11,13,66,74),(0.25,900,20,23.1,70,80),(0.05,300,36,40,60,70)]
KT=0.040; Y=0.45; ax=0.30
akap=[(0.4,0.40),(0.7,0.75),(1.0,1.0),(2.0,1.7),(4.0,2.3)]
def aL(k):
    return float(np.interp(k,[a for a,b in akap],[b for a,b in akap]))
def life(b,l,k, worst=True):
    name,C,C0,OD,pr=b; dm=(60+OD)/2
    d=0
    for f,n,lo,hi,tlo,thi in cyc:
        Fr=hi; T=thi
        P=Fr+Y*ax*Fr
        nu=l[1]*math.exp(-KT*(T-40))
        nu1=45000*n**-0.83*dm**-0.5 if n<1000 else 4500*n**-0.5*dm**-0.5
        kap=nu/nu1
        L=aL(kap)*k[1]*(C/P)**(10/3)
        d+=f*n*60/(1e6*L)
    return 1/d
REQ=56000
res=[]
for b in B:
  for l in LUB:
    for k in KIT:
      if b[3]>150: continue
      # static: P0 = Fr+0.6*Fa at shock peak
      P0=40*(1+0.6*ax)
      if b[2]/P0<2.5: continue
      Lh=life(b,l,k)
      res.append((b[4]+l[2]+k[2],b[0],l[0],k[0],Lh,Lh/REQ-1))
res.sort()
for r in res[:14]: print(r)
print([r for r in res if r[5]>=0][:3])
