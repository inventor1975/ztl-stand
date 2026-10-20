from model import *
# lower bound on total error for ANY Rp,Rpar: E_R25+E_B+ADC_lb at T in control band (273.15..313.15) and wide
for n in NTC:
  for a in ADC:
    R25,tR,B,tB,dl,_=NTC[n]; bits,tue,_=ADC[a]
    T=np.linspace(253.15,333.15,161)
    u=1/T-1/T0
    def inf(Tx): return Tx
    e25=np.maximum(abs(1/(1/T+np.log(1+tR)/B)-T),abs(1/(1/T+np.log(1-tR)/B)-T))
    eB=np.maximum(abs(1/(1/T0+(1+tB)*u)-T),abs(1/(1/T0+(1-tB)*u)-T))
    dx=(tue+.5)/2**bits
    # slope bound B/(4T^2); use T-0.5 to be safe about the finite difference
    ea=dx/(B/(4*(T-1.0)**2))
    tot=e25+eB+ea
    m=(T>=273.15)&(T<=313.15)
    print(n,a,'control lb %.3f  wide lb %.3f'%(tot[m].max(),tot.max()),'  -> ' + ('REFUTED' if tot[m].max()>.4 or tot.max()>1 else 'survives'))
