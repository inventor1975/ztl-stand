import math, numpy as np
meth={'TS':((0.20,0.30),(0.2,0.3),0.35),'TL':((0.80,0.88),(0.6,0.9),1.6),'TF':((0.92,0.97),(1.6,2.0),4.2)}
reg={'winter':(0.33,(5,12),(40,60)),'summer':(0.25,(24,32),(25,40)),'shoulder':(0.42,(12,20),(15,25))}  # fraction, room T, run hours
lam0=(1.8e-6,2.4e-6); Bk=3000.0; Tov=2190.0
cm={0:(1.0,0.0),1:(0.92,2.2)}   # worst lambda factor, price kEUR/yr
Utarget=2.25e-3
def lam_bar(cmflag):
    # worst case: lam0 high, room T high, run hours high
    s=0
    for r,(f,(Tl,Th),(Hl,Hh)) in reg.items():
        s+=f*lam0[1]*math.exp(Bk*(1/293.15-1/(Th+273.15)))*(Hh/50)**0.35
    return s*cm[cmflag][0]
def U(m,cmflag,tau_h):
    c=meth[m][0][0]; td=meth[m][1][1]
    lb=lam_bar(cmflag)
    return c*lb*tau_h/2+(1-c)*lb*Tov/2+td/tau_h
def feasible_range(m,cmflag):
    taus=np.arange(24,2190.01,1.0)
    ok=[t for t in taus if U(m,cmflag,t)<=Utarget]
    return (min(ok),max(ok)) if ok else None
def annual_cost(m,cmflag,tau_h):
    return 8760/tau_h*meth[m][2]+cm[cmflag][1]
if __name__=='__main__':
    print('lam_bar',lam_bar(0),lam_bar(1))
    for m in meth:
        for f in (0,1):
            r=feasible_range(m,f)
            print(m,f,r, None if r is None else round(annual_cost(m,f,r[1]),3))
