import numpy as np, itertools
from scipy.optimize import milp, LinearConstraint, Bounds
src=open('ref.py').read().split("budget=None")[0]
src=src.replace("rows.append(0.3*cost-bbb*cost); lo.append(0); hi.append(np.inf)","R2=(0.3*cost-bbb*cost)")
exec(src)
groups={"Rbase":list(range(0,6)),"Rstress":list(range(6,12)),"Rfall":list(range(12,18)),"R3":[18,19]}
def solve(names,integ=0):
    A=[];l=[];h=[]
    for g in names:
        if g in groups:
            for i in groups[g]: A.append(rows[i]);l.append(lo[i]);h.append(hi[i])
    if "R2" in names: A.append(R2);l.append(0);h.append(np.inf)
    if "R4" in names: A.append(cost);l.append(-np.inf);h.append(2300)
    return milp(cost,constraints=LinearConstraint(np.array(A),l,h),integrality=np.ones(14)*integ,bounds=Bounds(0,100))
allg=["Rbase","Rstress","Rfall","R2","R3","R4"]
for k in range(1,6):
    for S in itertools.combinations(allg,k):
        if "R4" not in S: continue
        r=solve(S); r2=solve(S,1)
        print(S, "LP",("INFEAS" if r.status else round(r.fun,3)),"INT",("INFEAS" if r2.status else round(r2.fun,3)))
