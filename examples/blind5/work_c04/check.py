import math, itertools
from scipy.optimize import brentq
mats={"PVC":((0.0095,0.0115),62,3.0),"CONC":((0.012,0.016),48,1.5),"PE":((0.013,0.017),55,2.5)}
Ds=[200,250,300,400,500]; Ss=[0,0.002,0.0035,0.005,0.008,0.012,0.02]
reach={"A":(420,6.5,22),"B":(380,12,41)}
def geom(D,th):
    s=math.sin(th); A=D*D*(th-s)/8; R=D/4*(1-s/th); return A,R
def solve(Q,n,S,D):
    # theta in (0, theta938); Q(theta) increasing there
    th938=2*math.acos(1-2*0.938)
    f=lambda th: (lambda A,R: A*R**(2/3)*math.sqrt(S)/n-Q)(*geom(D,th))
    if S==0 or f(th938)<0: return None
    return brentq(f,1e-6,th938)
def ok(mat,r,D,S):
    (n0,n1),k,vmax=mats[mat]; L,Qd,Qp=reach[r]; Dm=D/1000
    worst=[]
    for n in [n0+(n1-n0)*i/20 for i in range(21)]:
        td=solve(Qd/1000,n,S,Dm); tp=solve(Qp/1000,n,S,Dm)
        if td is None or tp is None: return False
        vd=Qd/1000/geom(Dm,td)[0]; vp=Qp/1000/geom(Dm,tp)[0]
        y=(1-math.cos(tp/2))/2
        if vd<0.6 or y>0.7 or vp>vmax: return False
    return True
def cost(mat,DA,SA,DB,SB):
    k=mats[mat][1]; c=0
    dA=1.5+SA*420/2; dB=1.5+SA*420+SB*380/2
    for L,D,d in ((420,DA,dA),(380,DB,dB)):
        c+=L*(k*(D/200)**1.3+(20+28*d)*(1+D/1000))
    return c
res=[]
for m in mats:
    okA={(D,S):ok(m,"A",D,S) for D in Ds for S in Ss}
    okB={(D,S):ok(m,"B",D,S) for D in Ds for S in Ss}
    for DA,SA,DB,SB in itertools.product(Ds,Ss,Ds,Ss):
        if DB<DA or not okA[(DA,SA)] or not okB[(DB,SB)]: continue
        if 1.5+SA*420+SB*380>5.0: continue
        res.append((cost(m,DA,SA,DB,SB),m,DA,SA,DB,SB))
res.sort()
for r in res[:8]: print(r)
print(len(res))
for m in mats:
    print(m,[ (D,S) for D in Ds for S in Ss if ok(m,"A",D,S)][:40])
    print(m,"B",[ (D,S) for D in Ds for S in Ss if ok(m,"B",D,S)][:60])
