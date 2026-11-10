# P10 heat pump. COP=eta*Th/(Th-Tc) (K); eta*0.9 if Tc<-15C; P_el=Q/COP <= 4.0 kW
import numpy as np
cat={'U1':(0.42,4200),'U2':(0.47,5100),'U3':(0.52,6400),'U4':(0.55,7900)}
Q=(8.5,9.5);Th=(40,45);Tc=(-20,-10)
def Pel(eta,q,th,tc):
    e=eta*(0.9 if tc<-15 else 1.0)
    return q/(e*(th+273.15)/(th-tc))
print("source check: COP carnot 45C/-15C = %.2f"%((318.15)/(60)) )
for k,(eta,pr) in cat.items():
    w=max(Pel(eta,q,th,tc) for q in Q for th in Th for tc in Tc)
    # continuity check on Tc scan
    ws=max(Pel(eta,Q[1],Th[1],tc) for tc in np.linspace(-20,-10,1001))
    print(k,"worst P_el %.4f kW"%w,"scan %.4f"%ws,"PASS" if w<=4.0 else "fail",pr)
# min eta for worst case
need=Q[1]/(4.0*0.9*(318.15/65))
print("min eta needed %.4f"%need)
