import itertools, json
from fractions import Fraction as F
Z=lambda p:1-4.8e-4*p+1.3e-6*p*p
cyl={'CY5':(5,200,7.5,95),'CY7':(7,200,10.4,120),'CY10':(10,200,14.0,165),'CY5H':(5,300,4.2,480),'CY7H':(7,300,5.6,640)}
reg={'RA':(.10,.30,10,60),'RB':(.05,.15,10,140),'RC':(.02,.05,10,320)}
cv={'none':(0,0,0,0),'conserver':(.30,25,450)}
ph=[(20,8.5,10),(35,9,8),(40,5,6)]   # max flows
def run(c,n,r1,r2,k,worst=True):
    Vw,Pn,m,pr=cyl[c]
    a1,l1,p1,c1=reg[r1]; a2,l2,p2,c2=reg[r2]
    kap,pc,cp=(0,0,0) if k=='none' else (.30,25,450)
    pmin=max(p1,p2,pc)
    pf=Pn*0.97
    N=n*Vw*(pf/Z(pf)*273.15/288.15-pmin/Z(pmin)*273.15/263.15)/1.013
    C=sum(t*(q1*(1+a1)*(1-kap)+q2*(1+a2)+l1+l2) for t,q1,q2 in ph)
    price=n*pr+(40 if n==2 else 0)+c1+c2+cp
    return N,C,N-1.2*C,n*m,price
res=[]
for c,n,r1,r2,k in itertools.product(cyl,[1,2],reg,reg,cv):
    N,C,mg,M,pr=run(c,n,r1,r2,k)
    ok=mg>=0 and M<=16
    res.append((pr,ok,c,n,r1,r2,k,mg))
print(sum(1 for r in res if r[1]),"earned of",len(res))
best=min(r for r in res if r[1]); print(best)
for r in sorted(r for r in res if r[1])[:6]: print(r)
print(run('CY10',1,'RB','RC','none'))
# near-miss: cheaper designs and their margins
for r in sorted(res)[:12]: print(r)
# (see report: cross-check of all 180 designs vs the stand's verdicts done with run1.out)
