from scipy.optimize import brentq
from calc import *
import itertools
def solve(p,i,fkt,fkq,fe,fres,bol=False):
    D,KT0,J0,KQ0,_=p
    def f(N):
        n=N/(60*i);Teng=fe*Te(N);kqn=Teng*i*eg/(rho*n*n*D**5)
        if bol: return KQ0*fkq*rho*n*n*D**5-Teng*i*eg
        J=J0/.75*(1-kqn/(KQ0*fkq));V=J*n*D/(1-w)
        return (1-t)*fkt*KT0*(1-J/J0)*rho*n*n*D**4-fres*R(V/kn)
    N=brentq(f,300,2149.9,xtol=1e-10)
    n=N/(60*i);Teng=fe*Te(N);kqn=Teng*i*eg/(rho*n*n*D**5)
    J=0 if bol else J0/.75*(1-kqn/(KQ0*fkq))
    T=(1-t)*fkt*KT0*(1-J/J0)*rho*n*n*D**4
    return N,J,T/1000,J*n*D/(1-w)/kn,pi*n*D
p=props['P3'];i=4.5
print('bollard',solve(p,i,.97,1.03,.96,1,True))
print('heavyR2',solve(p,i,.97,1.03,.96,1.365))
Ns=[solve(p,i,a,b,c,1.365)[0] for a in(.97,1.03) for b in(.97,1.03) for c in(.96,1.0)]
print('heavyR3 N range over corners',min(Ns),max(Ns))
print('light',solve(p,i,1.03,.97,1.0,.76))
