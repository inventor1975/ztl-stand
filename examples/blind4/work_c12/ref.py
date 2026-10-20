import numpy as np, sys
from scipy.optimize import milp, LinearConstraint, Bounds
from fractions import Fraction as F
B=[("B1",2.0,1,100.9,"AA",None),("B2",3.0,2,100.4,"AA",None),("B3",2.5,3,99.0,"AAA",None),("B4",3.5,3,101.2,"A",None),
("B5",3.0,4,98.2,"AAA",None),("B6",6.0,4,100.5,"BBB",None),("B7",4.0,5,100.3,"A",None),("B8",6.5,5,104.0,"BBB",3),
("B9",3.5,6,98.7,"AA",None),("B10",5.0,6,103.0,"A",None),("B11",7.0,6,108.0,"BBB",3),("B12",0,2,95.8,"AA",None),
("B13",0,4,89.6,"A",None),("B14",0,6,82.3,"AAA",None)]
L=[400,350,450,300,500,650]
def cf(i,sc):
    n,c,m,p,r,cy=B[i]; end=m
    if sc=="fall" and cy: end=cy
    w=0.5 if (sc=="stress" and r=="BBB") else 1
    return np.array([w*10*(c/100*(t<=end)+(1 if t==end else 0)) for t in range(1,7)])
cost=np.array([b[3]/10 for b in B]); bbb=np.array([b[4]=="BBB" for b in B])
y=1.04
def Dl():
    pv=[L[t-1]/y**t for t in range(1,7)]; return sum((t+1)*pv[t] for t in range(6))/sum(pv)
D=Dl(); print("Dliab",D)
rows=[];lo=[];hi=[]
for sc in ["base","stress","fall"]:
    M=np.array([cf(i,sc) for i in range(14)]).T  # 6x14
    for t in range(6):
        rows.append(M[:t+1].sum(0)); lo.append(sum(L[:t+1])); hi.append(np.inf)
Mb=np.array([cf(i,"base") for i in range(14)]).T
pvt=np.array([[Mb[t,i]/y**(t+1) for i in range(14)] for t in range(6)])
tt=np.arange(1,7)[:,None]
rows.append(((tt-D)*pvt).sum(0)); lo.append(-np.inf); hi.append(0.25*pvt.sum()*0) # placeholder
# duration: |sum (t-D) pv| <= .25 sum pv
S=pvt.sum(0); T=((tt-D)*pvt).sum(0)
rows.pop(); lo.pop(); hi.pop()
rows.append(T-0.25*S); lo.append(-np.inf); hi.append(0)
rows.append(T+0.25*S); lo.append(0); hi.append(np.inf)
rows.append(0.3*cost-bbb*cost); lo.append(0); hi.append(np.inf)
budget=None if len(sys.argv)>1 and sys.argv[1]=="nob" else 2300
for integ in [0,1]:
    rr=list(rows);l=list(lo);h=list(hi)
    if budget: rr.append(cost); l.append(-np.inf); h.append(budget)
    r=milp(cost,constraints=LinearConstraint(np.array(rr),l,h),integrality=np.ones(14)*integ,bounds=Bounds(0,100))
    print("integer" if integ else "LP", r.status, r.message, r.fun, None if r.x is None else np.round(r.x,4))
