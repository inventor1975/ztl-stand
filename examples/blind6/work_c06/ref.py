import numpy as np, itertools, math
F=1.5
EX={"E2":(2,.85,12.0),"E3":(3,.80,17.0),"E4":(4,.75,22.0),"E3H":(3,.92,20.0)}
SV={"SA":(4.0,.021,1.2),"SB":(7.5,.035,2.6),"SC":(12.0,.045,4.5)}
BD={"G600":(600,1.8),"G1200":(1200,3.2),"G2000":(2000,5.0)}
def solve(N,eta,K25,a,S,cF,T,rho):
    K=eta*K25*math.exp(-a*(T-25))
    A=np.zeros((N,N)); b=np.zeros(N)
    # x_1..x_N
    for i in range(1,N):
        # F(x_{i-1}-x_i)=S K (x_i-x_{i+1})
        r=i-1
        A[r,i-1]+= -F-S*K; A[r,i]+= S*K
        # F x_{i-1} term
        if i-1>=1: A[r,i-2]+=F
        else: b[r]-=F*cF
        # fix: F(x_{i-1}-x_i) - S K(x_i - x_{i+1})=0 -> F x_{i-1} -(F+SK) x_i + SK x_{i+1}
    # redo cleanly
    A=np.zeros((N,N)); b=np.zeros(N)
    for i in range(1,N+1):
        r=i-1
        # coefficient on x_{i-1}
        if i-1>=1: A[r,i-2]+=F
        else: b[r]-=F*cF
        A[r,i-1]+=-F
        if i<N:
            A[r,i-1]+=-S*K; A[r,i]+=S*K
        else:
            A[r,i-1]+=-S*K; A[r,0]+=S*rho*K   # -S(K xN - rho K x1)
    x=np.linalg.solve(A,b)
    return x,K
def worst(N,eta,K25,a,S,bm):
    res=[]
    for cF,T,rho,q,e in itertools.product((6.0,7.5),(15,30),(.02,.04),(.10,.14),(.90,.96)):
        x,K=solve(N,eta,K25,a,S,cF,T,rho)
        xN=x[-1]; y1=K*x[0]
        res.append((xN,(1-e)*xN,q*bm/(F*xN)/700,y1))
    r=np.array(res)
    return r[:,0].max(),r[:,1].max(),r[:,2].min(),r[:,3].max()
if __name__=="__main__":
    out=[]
    for en,(N,eta,pe) in EX.items():
        for sn,(K25,a,cs) in SV.items():
            for bn,(bm,pb) in BD.items():
                # find smallest feasible S on grid
                best=None
                for S in np.arange(0.5,1.8001,0.0005):
                    w=worst(N,eta,K25,a,S,bm)
                    ok = w[0]<=.12 and w[1]<=.006 and w[2]>=2 and w[3]<=8.5
                    if ok:
                        best=S;break
                if best is None: out.append((en,sn,bn,None)); continue
                cost=pe+pb+5*8000*best*cs/1000
                out.append((en,sn,bn,round(best,4),round(cost,3)))
    for o in sorted(out,key=lambda o:(o[-1] is None, o[-1] if o[-1] else 0)): print(o)
