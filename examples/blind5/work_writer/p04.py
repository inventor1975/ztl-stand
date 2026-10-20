import math, itertools, numpy as np
from scipy.optimize import brentq
DS=[200,250,300,400,500]            # mm
SL=[0.0,0.002,0.0035,0.005,0.008,0.012,0.02]
MAT={"PVC":(0.0095,0.0115,62.0),"CONC":(0.012,0.016,48.0),"PE":(0.013,0.017,55.0)}
REACH={"A":dict(L=420,Qmin=0.0065,Qpk=0.022),"B":dict(L=380,Qmin=0.012,Qpk=0.041)}
VMAXMAT={"PVC":3.0,"PE":2.5,"CONC":1.5}
D0=1.5
def geom(D,th):
    A=D*D/8*(th-math.sin(th)); R=D/4*(1-math.sin(th)/th); return A,R
def solve(D,n,S,Q):
    if S<=0: return None
    def f(th):
        A,R=geom(D,th); return A*R**(2/3)*math.sqrt(S)/n-Q
    thmax=2*math.acos(1-2*0.938)  # y/D=.938 : th=2*acos(1-2y/D)
    thmax=2*math.acos(1-2*0.938)
    if f(thmax)<0: return None
    th=brentq(f,1e-6,thmax)
    A,R=geom(D,th); y=D*(1-math.cos(th/2))/2
    return y/D,Q/A
def check_reach(D_mm,S,mat,r):
    D=D_mm/1000; nlo,nhi,_=MAT[mat]
    out=dict(ok=True,why=[])
    vmin=9;yq=0;vmax=0
    for n in np.linspace(nlo,nhi,5):
        a=solve(D,n,S,r["Qmin"]); b=solve(D,n,S,r["Qpk"])
        if a is None or b is None: return dict(ok=False,why=["capacity"],vmin=0,y=9,vmax=0)
        vmin=min(vmin,a[1]); yq=max(yq,b[0]); vmax=max(vmax,b[1])
    return dict(ok=True,vmin=vmin,y=yq,vmax=vmax)
def cost(Dsel,Ssel,mat):
    tot=0; d_up=D0
    for key,D,S in zip("AB",Dsel,Ssel):
        L=REACH[key]["L"]; d_dn=d_up+S*L
        pipe=MAT[mat][2]*(D/200)**1.3
        trench=(20+28*(d_up+d_dn)/2)*(1+D/1000)
        tot+=L*(pipe+trench)/1000.0   # kEUR
        d_up=d_dn
    return tot,d_dn
VMIN,YMAX,DEND=0.60,0.70,5.0
if __name__=="__main__":
    cache={}
    for mat in MAT:
      for key in "AB":
        for D in DS:
          for S in SL:
            cache[(mat,key,D,S)]=check_reach(D,S,mat,REACH[key]) if S>0 else dict(ok=False,vmin=0,y=9,vmax=0)
    def good(c,mat): return c["ok"] and c["vmin"]>=VMIN and c["y"]<=YMAX and c["vmax"]<=VMAXMAT[mat]
    res=[]
    for mat in MAT:
      for DA,SA,DB,SB in itertools.product(DS,SL,DS,SL):
        if DB<DA: continue
        ca=cache[(mat,"A",DA,SA)]; cb=cache[(mat,"B",DB,SB)]
        if not(good(ca,mat) and good(cb,mat)): continue
        c,dend=cost((DA,DB),(SA,SB),mat)
        if dend>DEND: continue
        res.append((c,mat,DA,SA,DB,SB,dend,ca,cb))
    res.sort(key=lambda r:r[0])
    print(len(res))
    for r in res[:6]:
        print(round(r[0],2),r[1:7],{k:round(v,3) for k,v in r[7].items() if k!='ok'},{k:round(v,3) for k,v in r[8].items() if k!='ok'})
