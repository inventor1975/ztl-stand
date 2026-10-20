import numpy as np, itertools, math
F=1.5
cF=(6.0,7.5); T=(15.0,30.0); rho=(0.02,0.04)
ext={'E2':(2,0.85,12.0),'E3':(3,0.80,17.0),'E4':(4,0.75,22.0),'E3H':(3,0.92,20.0)}
sol={'SA':(4.0,0.021,1.2),'SB':(7.5,0.035,2.6),'SC':(12.0,0.045,4.5)}
bed={'G600':(600,1.8),'G1200':(1200,3.2),'G2000':(2000,5.0)}
qmin=0.10; emin=0.90; H=700.0
def solve(N,Keff,S,c0,r):
    # unknowns x1..xN
    A=np.zeros((N,N)); b=np.zeros(N)
    a=S*Keff/F  # extraction factor
    for i in range(N):
        # F(x_{i-1}-x_i) = S(Keff x_i - y_{i+1})  -> divide by F
        # x_{i-1} - x_i - a x_i + (S/F) y_{i+1} = 0
        A[i,i]+= -1-a
        if i>0: A[i,i-1]+=1
        else: b[i]-=c0
        if i<N-1: A[i,i+1]+= a   # S/F*Keff x_{i+1}
        else: A[i,0]+= (S/F)*r*Keff   # y_in = r*Keff*x1
    x=np.linalg.solve(A,b)
    return x
def margins(e,s,bd,S,detail=False):
    N,eta,_=ext[e]; K25,a,_=sol[s]; m,_=bed[bd]
    worst={'R1':1e9,'R3':1e9,'R5':1e9}
    xN_max=0; y1_max=0
    for c0 in cF:
      for r in rho:
        for Tt in np.linspace(T[0],T[1],7):
            Keff=eta*K25*math.exp(-a*(Tt-25))
            x=solve(N,Keff,S,c0,r)
            xN_max=max(xN_max,x[-1]); y1_max=max(y1_max,Keff*x[0])
    R1=0.12/xN_max-1
    R2=0.006/((1-emin)*xN_max)-1
    life=qmin*m/(F*xN_max)/H   # F m3/h * x kg/m3 ; x g/L = kg/m3 -> kg/h
    # life months = q*m / (F*x) hours / H
    R3=life/2-1
    R4=1.2*F/S-1
    R5=8.5/y1_max-1
    return dict(R1=R1,R2=R2,R3=R3,R4=R4,R5=R5,xN=xN_max,life=life,y1=y1_max)
def best_S(e,s,bd):
    best=None
    for S in np.arange(0.5,1.2*F+1e-9,0.002):
        mm=margins(e,s,bd,S)
        if min(mm[k] for k in('R1','R2','R3','R4','R5'))>=0:
            c=cost(e,s,bd,S,mm)
            if best is None or c<best[0]: best=(c,round(S,3),mm)
    return best
def cost(e,s,bd,S,mm):
    cap=ext[e][2]+bed[bd][1]
    op=5*8000*S*sol[s][2]/1000
    rep=0
    return cap+op+rep
if __name__=='__main__':
    rows=[]
    for e in ext:
      for s_ in sol:
        for bd in bed:
            r=best_S(e,s_,bd)
            if r: rows.append((round(r[0],2),e,s_,bd,r[1],round(r[2]['xN'],4),round(r[2]['life'],2),round(r[2]['y1'],2)))
    for r in sorted(rows)[:12]: print(r)
    print(len(rows))
