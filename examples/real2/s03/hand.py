from fractions import Fraction as F
import itertools
def off(voff=F(1,10),adctc=F(4,100)):
    dT=30;Rs=500;Kn=5;R2=40000;V=F(5,4095)
    amp=voff*F(1,1000)+10e-6*dT
    ib=(5e-9+1e-9*dT)*abs(Rs*Kn-R2)/Kn
    io=(5e-9+1e-9*dT)*(Rs*Kn+R2)/2/Kn
    adc=(3+adctc*dT+F(1,2)+1)*V/Kn
    return float(amp+ib+io+adc)*1e3
print("offset mV (voff .1, tc .04):",off(), " voff 1mV:",off(F(1)), " tc .05:",off(F(1,10),F(5,100)))
# gain: exact corner max (monotone in each factor)
def gain(vt=0.005):
    best=0
    for s in itertools.product([-1,1],repeat=8):
        t1,t2,c1,c2,ga,gc,vtt,vc=s
        R1=10e3*(1+t1*0.001)*(1+c1*100e-6*30); R2=40e3*(1+t2*0.001)*(1+c2*100e-6*30)
        e=(1+R2/R1)/5*(1+ga*0.0005)*(1+gc*20e-6*30)/((1+vtt*vt)*(1+vc*50e-6*30))-1
        best=max(best,abs(e))
    return best
print("gain max |e| %:",gain()*100," linear sum:",(0.16+0.48+0.05+0.06+0.5+0.15))
print("vref .1%:",gain(0.001)*100)
# linear sum for vref .1
