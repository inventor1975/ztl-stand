from calc import *
import itertools
def speed_tip(p,i,N,J):
    D=p[0];n=N/(60*i);return J*n*D/(1-w)/kn, pi*n*D
res=[]
for pn,p in props.items():
  for gn,(i,gp) in gears.items():
    D,KT0,J0,KQ0,pp=p
    b=op(p,i,.97,1.03,.96,1,True)
    h=op(p,i,.97,1.03,.96,1.365)
    # R3 box: enumerate corners of tolerance box for N min
    Nmin=min(op(p,i,a,b2,c,1.365)[0][0] for a in(.97,1.03) for b2 in(.97,1.03) for c in(.96,1.0))
    l=op(p,i,1.03,.97,1.0,.76)
    Tb=b[0][2]/1000 if b else None
    vh=speed_tip(p,i,h[0][0],h[0][1])[0]
    Nl=l[0][0]; tip=speed_tip(p,i,Nl,l[0][1])[1]
    r1=Tb>=30; r2=vh>=9; r3=Nmin>=1900; r4=Nl<=2060 and tip<=32
    res.append((pp+gp,pn,gn,round(Tb,1),round(vh,2),round(Nmin),round(Nl),round(tip,1),r1,r2,r3,r4))
for r in sorted(res):
    print(r, 'PASS' if all(r[-4:]) else '')
