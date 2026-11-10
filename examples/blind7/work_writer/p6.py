# P6 turning: cost/part = Cm(Tl+Tm)+(Cm*Tc+Ct)*Tm/T, T=(C/V)^(1/n), Tm=pi D L/(1000 f V)
import numpy as np
D=60;L=200;f=0.2;Cm=1.2;Tl=1.5
Tm=lambda V: np.pi*D*L/(1000*f*V)
G={'A':dict(n=0.25,C=(240,260),Ct=2.5,Tc=1.0,vr=(60,180)),
   'B':dict(n=0.30,C=(300,330),Ct=4.0,Tc=1.0,vr=(80,220)),
   'C':dict(n=0.40,C=(430,470),Ct=7.0,Tc=1.5,vr=(100,260))}
def cost(V,n,C,g):
    T=(C/V)**(1/n); tm=Tm(V); return Cm*(Tl+tm)+(Cm*g['Tc']+g['Ct'])*tm/T
Vmin_time=np.pi*D*L/(1000*f*(3.0-Tl))
print("cycle time <=3.0 min needs V >=",round(Vmin_time,3))
for k,g in G.items():
    best=(1e9,0)
    for V in np.arange(max(g['vr'][0],Vmin_time),g['vr'][1]+1e-9,0.01):
        w=max(cost(V,n,C,g) for C in g['C'] for n in (g['n']*.95,g['n']*1.05))
        if w<best[0]: best=(w,V)
    print(k,"min worst-case cost %.4f at V=%.2f"%best,"PASS(<=4.04)" if best[0]<=4.04 else "fail", "margin %.3f%%"%((4.04-best[0])/4.04*100))
# source-style check: min-cost tool life T=(1/n-1)(Tc+Ct/Cm) at nominal A
g=G['A'];n=g['n'];C=250.0;T=(1/n-1)*(g['Tc']+g['Ct']/Cm);V=C/T**n
print("nominal A: T_opt=%.2f min, V_opt=%.2f, cost=%.4f"%(T,V,cost(V,n,C,g)))
