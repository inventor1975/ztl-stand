import itertools, numpy as np
from scipy.optimize import linprog
print("=== P06 ===")
import p06
# fine grid sanity: FS min at B=2.0,Df=1.5 and B=2.4 using 5-level grids
def fine(B,Df,k=5):
    grid=lambda lo,hi:np.linspace(lo,hi,k)
    fs=1e9; smax=0; emax=0
    for phi in grid(*p06.PH):
      for c in grid(*p06.CC):
        for g in grid(*p06.GM):
          for N in grid(*p06.NL):
            for M in grid(*p06.MM):
              for zw in grid(*p06.ZW):
                f,q,e=p06.FSset(B,Df,phi,c,g,N,M,zw)
                fs=min(fs,f); emax=max(emax,e)
                for E in (10,16):
                    smax=max(smax,q*(B-2*e)*0.91*1.12/(E*1000)*1000)
    return fs,smax,emax/B
for B,Df in [(2.0,1.5),(2.0,1.2),(1.8,1.5),(2.4,1.5),(2.4,1.2),(2.4,1.0)]:
    print(B,Df,[round(x,3) for x in fine(B,Df,4)])
print("max FS over catalog with B<=2.0:",max(p06.worst(B,Df)[0] for B in p06.BS if B<=2.0 for Df in p06.DFS))
print("feasible (FS>=3,s<=25,e<=B/6) without width limit:",[(B,Df,round(p06.worst(B,Df)[0],2)) for B in p06.BS for Df in p06.DFS if p06.worst(B,Df)[0]>=3 and p06.worst(B,Df)[1]<=25 and p06.worst(B,Df)[2]<=B/6])
print("=== P07 ===")
import p07
p07.PLIM=0.005
rows=[(p07.dose(*x),p07.mass(*x),p07.thick(*x),)+x for x in itertools.product(p07.LEAD,p07.BAR,p07.CON)]
print("min dose among mass<=55 & thick<=60:",min(r for r in rows if r[1]<=55 and r[2]<=60)[0:1], sorted([r for r in rows if r[1]<=55 and r[2]<=60])[0])
feas=[r for r in rows if r[0]<=0.005]
print("dose-feasible, lightest 3:",[tuple(round(x,4) for x in r) for r in sorted(feas,key=lambda r:r[1])[:3]])
print("dose-feasible thinnest 3:",[tuple(round(x,4) for x in r) for r in sorted(feas,key=lambda r:r[2])[:3]])
print("dose-feasible with mass<=55 count:",len([r for r in feas if r[1]<=55]), " with thick<=60 count:",len([r for r in feas if r[2]<=60]))
print("=== P09 ===")
import p09
def lp(tier):
    p,commit,cap=p09.TIER[tier]
    # vars: B, F0..3, S0..3, y0..3 (billed = max(F,commit))
    nv=1+4+4+4
    c=np.zeros(nv); c[0]=p09.OWN
    for q in range(4):
        c[9+q]=3*(p if p else 0); c[5+q]=3*24.0
    A=[];b=[]
    for q in range(4):
        D=p09.DEM[q][1]
        row=np.zeros(nv); row[0]=-1; row[1+q]=-1; row[5+q]=-1; A.append(row); b.append(-D)
        row=np.zeros(nv); row[1+q]=-1; row[9+q]=1; A.append(row); b.append(0)  # y>=F  -> F-y<=0 (fix sign)
    A=[];b=[]
    for q in range(4):
        D=p09.DEM[q][1]
        row=np.zeros(nv); row[0]=-1; row[1+q]=-1; row[5+q]=-1; A.append(row); b.append(-D)
        row=np.zeros(nv); row[1+q]=1; row[9+q]=-1; A.append(row); b.append(0)
    bnds=[(0,p09.BMAX)]+[(0,cap)]*4+[(0,p09.SPOTCAP[q]) for q in range(4)]+[(commit,None)]*4
    if tier=="T0": bnds=[(0,p09.BMAX)]+[(0,0)]*4+[(0,p09.SPOTCAP[q]) for q in range(4)]+[(0,0)]*4
    r=linprog(c,A_ub=np.array(A),b_ub=np.array(b),bounds=bnds,method="highs")
    return r
for t in p09.TIER:
    r=lp(t); print(t, r.status, None if r.status else (round(r.fun,1), round(r.x[0],1)))
print("D_hi per quarter:",[round(d[1],1) for d in p09.DEM])
