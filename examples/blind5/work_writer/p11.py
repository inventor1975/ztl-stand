import numpy as np
from scipy.optimize import linprog
U=4.0; C=3.00
F=[1.085,1.090,1.095,1.100]
SLO,SHI=1.02,1.22; VLO,VHI=0.85,1.10
OPT={"none":(None,0.0),"K106":(1.06,0.0210),"K110":(1.10,0.0120),"K114":(1.14,0.0058)}
FCH=0.0012
def solve(strike,qloss=-0.10,annual=0.8,lo_avg=0.4,hi_avg=0.8,credit=9.0,premcap=0.10,K_only=True):
    K,pi=OPT[strike]
    # vars: h0..h3, o0..o3, w[q][v] 8 vars  => 16
    nv=16
    def idx_h(q): return q
    def idx_o(q): return 4+q
    def idx_w(q,vi): return 8+q*2+vi
    c=np.zeros(nv)
    for q in range(4):
        c[idx_h(q)]=FCH*U/F[q]
        c[idx_o(q)]=pi*U
    A=[];b=[]
    def profit_coeffs(q,S,v):
        # profit = U[(v-h-o)/S + h/F + o/min(S,K)] - pi*o*U - FCH*h*U/F - C  -> linear in h,o ; return (ch,co,const)
        mn=S if K is None else min(S,K)
        ch=U*(-1/S+1/F[q])-FCH*U/F[q]
        co=U*(-1/S+(1/mn if K is not None else 1/S))-pi*U
        const=U*v/S-C
        return ch,co,const
    Ss=[SLO,SHI]+([K] if (K is not None and SLO<K<SHI) else [])
    for q in range(4):
        for vi,v in enumerate((VLO,VHI)):
            for S in Ss:
                ch,co,const=profit_coeffs(q,S,v)
                # quarterly loss floor: ch*h+co*o+const >= qloss  ->  -ch*h-co*o <= const-qloss
                row=np.zeros(nv); row[idx_h(q)]=-ch; row[idx_o(q)]=-co; A.append(row); b.append(const-qloss)
                # w_qv <= profit  ->  w - ch h - co o <= const
                row=np.zeros(nv); row[idx_w(q,vi)]=1; row[idx_h(q)]=-ch; row[idx_o(q)]=-co; A.append(row); b.append(const)
    for vi in range(2):
        row=np.zeros(nv)
        for q in range(4): row[idx_w(q,vi)]=-1
        A.append(row); b.append(-annual)
    # average hedge ratio band |avg-0.6|<=0.2
    row=np.zeros(nv)
    for q in range(4): row[idx_h(q)]=0.25; row[idx_o(q)]=0.25
    A.append(row.copy()); b.append(hi_avg); A.append(-row); b.append(-lo_avg)
    # total hedge per quarter <=1
    for q in range(4):
        row=np.zeros(nv); row[idx_h(q)]=1; row[idx_o(q)]=1; A.append(row); b.append(1.0)
    # forward credit line on USD notional
    row=np.zeros(nv)
    for q in range(4): row[idx_h(q)]=U
    A.append(row); b.append(credit)
    # premium cap EUR M
    row=np.zeros(nv)
    for q in range(4): row[idx_o(q)]=pi*U
    A.append(row); b.append(premcap)
    if K is None:
        for q in range(4):
            row=np.zeros(nv); row[idx_o(q)]=1; A.append(row); b.append(0.0)
    bounds=[(0,1)]*8+[(-50,50)]*8
    r=linprog(c,A_ub=np.array(A),b_ub=np.array(b),bounds=bounds,method="highs")
    return r
if __name__=="__main__":
    for st in OPT:
        r=solve(st)
        print(st,r.status, None if r.status else (round(r.fun,5),np.round(r.x[:8],3)))
