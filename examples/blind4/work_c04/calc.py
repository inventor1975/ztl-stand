import numpy as np
from math import pi
rho=1025.;kn=0.5144;w=.12;t=.10;eg=.97
props={'P1':(1.30,.28,.62,.030,5200),'P2':(1.30,.33,.78,.036,5400),'P3':(1.30,.38,.92,.042,5600),
'P4':(1.45,.27,.64,.030,6900),'P5':(1.45,.32,.80,.036,7100),'P6':(1.45,.37,.94,.042,7400),
'P7':(1.60,.26,.66,.030,9100),'P8':(1.60,.31,.82,.036,9500)}
gears={'G1':(3.0,4800),'G2':(3.5,5200),'G3':(4.0,5900),'G4':(4.5,6700),'G5':(5.0,7500)}
Tn=[(0,1000),(800,1000),(1000,1250),(1400,1500),(1800,1450),(2000,1430),(2150,0),(1e9,0)]
Rt=[(0,0),(4,3),(6,7),(8,13.5),(9,18.5),(10,25),(11,34),(12,47),(13,64)]
def Te(N): return np.interp(N,[a for a,b in Tn],[b for a,b in Tn])
def R(vk): 
    xs=[a for a,b in Rt];ys=[b for a,b in Rt]
    if vk<=13: return np.interp(vk,xs,ys)*1000
    return (64+17*(vk-13))*1000
def op(p,i,fkt,fkq,fe,fres,bol=False):
    D,KT0,J0,KQ0,_=p
    out=[]
    for N in np.arange(200,2400,0.25):
        n=N/(60*i)
        Teng=fe*Te(N)
        kqn=Teng*i*eg/(rho*n*n*D**5)
        J=0 if bol else J0/.75*(1-kqn/(KQ0*fkq))
        T=(1-t)*fkt*KT0*(1-J/J0)*rho*n*n*D**4
        if bol: res=KQ0*fkq*rho*n*n*D**5-Teng*i*eg   # torque
        else:
            V=J*n*D/(1-w); res=T-fres*R(V/kn)
        out.append((N,res,J,T))
    roots=[]
    for a,b in zip(out,out[1:]):
        if a[1]*b[1]<0: roots.append((a[0],a[2],a[3]))
    return roots
if __name__=="__main__":
    for pn,p in props.items():
        for gn,(i,_) in gears.items():
            rb=op(p,i,.97,1.03,.96,1,True)
            rh=op(p,i,.97,1.03,.96,1.365)
            rl=op(p,i,1.03,.97,1.0,.76)
            print(pn,gn,'B',[(round(r[0]),round(r[2])) for r in rb],'H',[(round(r[0]),round(r[1],3)) for r in rh],'L',[(round(r[0]),round(r[1],3)) for r in rl])
