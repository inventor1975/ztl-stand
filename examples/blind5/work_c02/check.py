import math, numpy as np, itertools, json
exec(open('gen.py').read().split("def s(x)")[0])  # Sn, uk, cls
seas={"w":(2184,520,600,.80,.86),"sp":(2208,400,470,.82,.88),"su":(2208,330,400,.82,.88),"au":(2160,430,500,.80,.86)}
banks={"none":(0,0),"C100":(100,1.2),"C150":(150,1.7),"C200":(200,2.2)}
def grid(p0,p1,f0,f1,n=41):
    P,F=np.meshgrid(np.linspace(p0,p1,n),np.linspace(f0,f1,n)); return P,F
def Qf(P,F): return P*np.sqrt(1-F**2)/F
res=[]
for c,d in cls.items():
  for i in range(6):
    sn=Sn[i];u=uk[i]/100;P0=d["P0"][i];Pk=d["Pk"][i];pr=d["pr"][i];m=d["m"][i]
    r=Pk/(1000*sn); x=math.sqrt(u*u-r*r)
    for bn,(qc,bp) in banks.items():
      fails=[]
      # R5
      if m>3000: fails.append(("R5",m-3000))
      E1=0;S30=[];dU=[];PVs=0
      for k,(h,p0,p1,f0,f1) in seas.items():
        P,F=grid(p0,p1,f0,f1);Q=Qf(P,F)
        S2=P**2+(Q-qc)**2
        L1=P0+Pk*S2/sn**2+2.5*qc
        E1+=h*L1.max()/1000
        # year-wise weighted energy
        Ew=0
        for y in range(1,31):
            g=1.012**(y-1)
            Sy2=(g*P)**2+(g*Q-qc)**2
            Ew=Ew+h*(P0+Pk*Sy2/sn**2+2.5*qc)/1000/1.03**y
        PVs+=Ew.max()   # kWh worst per season (separable, tariff max)
        g=1.012**29
        S30.append(np.sqrt((g*P)**2+(g*Q-qc)**2).max()/ (1.05*sn))
        dU.append((100*((g*P)/sn*r+(g*Q-qc)/sn*x)).max())
      if E1>32000: fails.append(("R1",E1-32000))
      for k,v in zip(seas,S30):
        if v>1: fails.append(("R2"+k,v))
      for k,v in zip(seas,dU):
        if v>3.8: fails.append(("R3"+k,v-3.8))
      P,F=grid(60,80,.80,.86);Q=Qf(P,F)
      dun=(100*(P/sn*r+(Q-qc)/sn*x)).min()
      if dun<-0.8: fails.append(("R4",-0.8-dun))
      cost=pr+bp+0.14*PVs/1000
      res.append((cost,c,sn,bn,fails,E1,dun,max(S30),max(dU)))
res.sort()
for t in res:
    if not t[4]: print("PASS",t[:4],"E1max %.0f dUn %.3f S30ratio %.3f dU30 %.3f"%t[5:])
print("n pass",sum(1 for t in res if not t[4]))
for t in res:
    if t[4] and all(f[0]!="R5" for f in t[4]) and t[1]!="" : pass
import collections
for t in res[:30]: print(round(t[0],2),t[1],t[2],t[3],[(a,round(b,3)) for a,b in t[4]])
