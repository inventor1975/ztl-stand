import numpy as np, itertools, math
T0=298.15
NTC={'N1':(10e3,.01,3435,.0075,2.0,.45),'N2':(10e3,.01,3950,.01,2.0,.30),'N3':(10e3,.05,3380,.02,2.0,.10),
 'N4':(10e3,.002,3977,.003,2.0,1.80),'N5':(4.7e3,.01,3480,.01,2.0,.40),'N6':(47e3,.03,4050,.01,1.5,.35),'N7':(100e3,.01,4250,.01,1.5,.55)}
ADC={'A10':(10,3,.20),'A12':(12,4,.50),'A16':(16,12,2.40)}
E24=[1.0,1.1,1.2,1.3,1.5,1.6,1.8,2.0,2.2,2.4,2.7,3.0,3.3,3.6,3.9,4.3,4.7,5.1,5.6,6.2,6.8,7.5,8.2,9.1]
RV=[m*d for d in (1e3,1e4,1e5) for m in E24]
CLS={'1':(.01,.01),'0.5':(.005,.03),'0.1':(.001,.08)}
Tg=np.linspace(253.15,333.15,321)
def par(a,b): return a*b/(a+b) if b is not None else a
def Rn(T,R25,B): return R25*np.exp(B*(1/T-1/T0))
def xr(Rn_,Rp,Rpar):
    Rx=Rn_ if Rpar is None else Rn_*Rpar/(Rn_+Rpar)
    return Rx/(Rx+Rp)
def Tinf(x,R25,B,Rp,Rpar):
    Rx=x*Rp/(1-x)
    Rn_=Rx if Rpar is None else Rx*Rpar/(Rpar-Rx)
    return 1/(1/T0+np.log(Rn_/R25)/B)
def err(n,a,Rp,Rpar,cls,T=Tg):
    R25,tR,B,tB,dl,_=NTC[n]; bits,tue,_=ADC[a]; tr=CLS[cls][0]
    x=xr(Rn(T,R25,B),Rp,Rpar)
    def item(R25t=R25,Bt=B,Rpt=Rp,Rpart=Rpar,dx=0):
        xx=xr(Rn(T,R25t,Bt),Rpt,Rpart)+dx
        return Tinf(xx,R25,B,Rp,Rpar)-T
    tot=0
    tot=tot+np.maximum(abs(item(R25t=R25*(1+tR))),abs(item(R25t=R25*(1-tR))))
    tot=tot+np.maximum(abs(item(Bt=B*(1+tB))),abs(item(Bt=B*(1-tB))))
    tot=tot+np.maximum(abs(item(Rpt=Rp*(1+tr))),abs(item(Rpt=Rp*(1-tr))))
    if Rpar is not None:
        tot=tot+np.maximum(abs(item(Rpart=Rpar*(1+tr))),abs(item(Rpart=Rpar*(1-tr))))
    dx=(tue+.5)/2**bits
    tot=tot+np.maximum(abs(item(dx=dx)),abs(item(dx=-dx)))
    Rnn=Rn(T,R25,B); Rx=Rnn if Rpar is None else Rnn*Rpar/(Rnn+Rpar)
    Vn=3.6*x  # V across NTC||Rpar ; P_NTC = Vn^2/Rntc
    P=Vn**2/Rnn
    tot=tot+P/(dl*1e-3)
    return x,tot
def ok(n,a,Rp,Rpar,cls):
    x,e=err(n,a,Rp,Rpar,cls)
    r2=(x.min()>=.03) and (x.max()<=.97)
    m=(Tg>=273.15-1e-9)&(Tg<=313.15+1e-9)
    r1=(e[m].max()<=.4) and (e.max()<=1.0)
    return r2,r1,e[m].max(),e.max()
def bom(n,a,cls,haspar): return NTC[n][5]+ADC[a][2]+CLS[cls][1]*(1+haspar)

# ---- check of the hand-derived delta formulas against the direct chain (used by check_algebra.py)
def err_alg(n,a,Rp,Rpar,cls,T=Tg):
    R25,tR,B,tB,dl,_=NTC[n]; bits,tue,_=ADC[a]; tr=CLS[cls][0]
    Rpar_=1e12 if Rpar is None else Rpar
    Rnn=Rn(T,R25,B); Du=1/T-1/T0
    g=Rnn/Rpar_; q=g/(1+g); Rxn=Rnn*Rpar_/(Rnn+Rpar_)
    FD=lambda d: -T*T*d/(B+T*d)
    two=lambda x,y: np.maximum(np.maximum(FD(x),-FD(x)),np.maximum(FD(y),-FD(y)))
    e=two(np.log(1+tR),np.log(1-tR))+two(B*tB*Du,-B*tB*Du)
    e=e+two(-np.log(1+tr*(1+g)),-np.log(1-tr*(1+g)))
    e=e+two(-np.log(1-tr*g/(1+tr)),-np.log(1+tr*g/(1-tr)))
    dx=(tue+.5)/2**bits
    def dad(sg):
        rho=(1+sg*dx*(Rxn+Rp)/Rxn)/(1-sg*dx*(Rxn+Rp)/Rp)
        return np.log(rho)+np.log((1-q)/(1-q*rho))
    e=e+two(dad(1),dad(-1))
    x=Rxn/(Rxn+Rp)
    P=(3.6*x)**2/Rnn
    return e+P/(dl*1e-3)
