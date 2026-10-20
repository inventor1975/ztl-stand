import math
cells={'P15':(1.5,11,30,2.4),'H20':(2.0,16,22,2.0),'H25':(2.5,17,20,2.9),'E25':(2.5,24,12,1.7),'E30':(3.0,33,9,1.6)}
bms={'M30':(30,9,3.2),'M40':(40,6,4.5),'M60':(60,3.5,7.5),'M80':(80,2.5,11.0)}
Rconn=4.0
Voc=(3.46,3.52); P=(540,640); agef=(1.0,1.10); B=(2000,2400); Rb=(1.0,1.2)
capt=(0.97,1.03)
heater_price=4.5; heater_dT=(9,13); heater_Wh=3.5
def evaluate(cell,Np,bm,heat,Tamb):
    cap,R25,Imax,_=cells[cell]; Ibms,Rbm,_=bms[bm]
    Tc=Tamb+(heater_dT[0] if heat else 0)
    TK=Tc+273.15
    Rc=R25*agef[1]*math.exp(B[1]*(1/TK-1/298.15))
    Rtot=(5*Rc/Np+Rbm*Rb[1]+Rconn)*1e-3
    V0=5*Voc[0]; p=P[1]
    disc=V0*V0-4*Rtot*p
    if disc<0: return {'R1':-1,'R2':-1,'R3':-1,'R4':-1,'R5':-1}
    I=(V0-math.sqrt(disc))/(2*Rtot)
    Vt=V0-I*Rtot
    kT=max(0.5,1-0.007*(25-Tc))
    E=5*Np*cap*capt[0]*3.6*0.8*kT-(heater_Wh if heat else 0)
    run=E/p*60
    Icmax=Imax*(1-0.012*(25-Tc))
    Vcell=Voc[0]-(I/Np)*Rc*1e-3
    return {'R1':Vt/14.2-1,'R2':run/9-1,'R3':Ibms/I-1,'R4':Icmax/(I/Np)-1,'R5':Vcell/2.9-1,'I':I,'Vt':Vt,'run':run}
def cheapest(Tamb,verbose=False):
    best=None
    for c in cells:
        for Np in (1,2,3,4):
            for b in bms:
                for h in (0,1):
                    m=evaluate(c,Np,b,h,Tamb)
                    if min(m[k] for k in ('R1','R2','R3','R4','R5'))>=0:
                        price=5*Np*cells[c][3]+bms[b][2]+(heater_price if h else 0)
                        if best is None or price<best[0]-1e-9: best=(round(price,3),c,Np,b,h,{k:round(v,4) for k,v in m.items()})
    return best
if __name__=='__main__':
    for T in (-20,-15,-10,-5,0,5,25):
        print(T,cheapest(T))
