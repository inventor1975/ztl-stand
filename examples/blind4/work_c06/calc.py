from fractions import Fraction as Fr
import itertools, numpy as np
q=[500,1200,300,800,2000]; r=[Fr(60,100),Fr(45,100),Fr(85,100),Fr(70,100),Fr(30,100)]
cost=[9000,13000,14000,15500,16000]
FA,FB,x,FH=3000,2000,800,4200
def solve(p,Rcap,gA,gB,cm):
    # unknowns cT,cAo,cBi,cBo,cH
    A=np.zeros((5,5));b=np.zeros(5)
    A[0]=[-1,1,0,0,0];b[0]=gA/FA
    A[1]=[-(FB-x),-x,FB,0,0];b[1]=0
    A[2]=[0,0,-1,1,0];b[2]=gB/FB
    A[3]=[0,-(FA-x),0,-FB,FH];b[3]=0
    A[4]=[FH,0,0,0,-((1-p)*FH-Rcap)];b[4]=p*FH*cm
    return np.linalg.solve(A,b)
def worst(n,p):
    Rcap=sum(n[i]*0.85*q[i]*(float(r[i])-0.05) for i in range(5))
    Q=sum(n[i]*0.85*q[i] for i in range(5))
    if Q>0.6*FH+1e-9 or sum(n)>8: return None
    try:
        s1=solve(p,Rcap,10,6,0.0006); s2=solve(p,0,0.18,0,0.0001)
    except np.linalg.LinAlgError: return 'sing'
    # impurity2 g_B=0
    return s1,s2,Rcap,Q
best=[]
for n in itertools.product(range(5),repeat=5):
    for N in range(0,41):
        p=N/1000
        w=worst(n,p)
        if w is None or w=='sing': continue
        s1,s2,_,_=w
        if s1[0]<=0.008 and s1[2]<=0.011 and s1[3]<=0.015 and s2[0]<=0.004:
            c=sum(n[i]*cost[i] for i in range(5))+p*8.4e6
            best.append((c,n,N))
best.sort()
print(len(best)); print(best[:10])
# impurity 2 only
for N in (0,10,20,30,40):
    print(N, solve(N/1000,0,0.18,0,0.0001))
