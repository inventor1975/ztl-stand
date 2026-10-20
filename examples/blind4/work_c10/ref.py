# my own independent float reference for problem 10
import itertools, math
from scipy.optimize import brentq
pipes={'H200-10':(0.176,140,100,18),'H225-10':(0.198,140,100,23),'H250-10':(0.220,140,100,29),'H315-10':(0.277,140,100,45),'H355-10':(0.312,140,100,57),
'H200-16':(0.163,140,160,24),'H225-16':(0.184,140,160,30),'H250-16':(0.204,140,160,37),'H315-16':(0.257,140,160,58),'H355-16':(0.290,140,160,73),'H400-16':(0.327,140,160,92),
'S250':(0.25,120,300,70),'S300':(0.3,120,300,95),'S350':(0.35,120,300,128)}
tur={'T1':(0.0225,[.70,.78,.82,.85,.86,.85],0.2,58000),'T2':(0.03,[.66,.75,.80,.84,.86,.86],0.2,74000),'T3':(0.03,[.55,.65,.72,.78,.80,.79],0.2,42000),
'T4':(0.042,[.55,.65,.72,.78,.80,.79],0.2,56000),'T5':(0.036,[.62,.62,.62,.82,.89,.90],0.4,96000)}
fr=[.05,.15,.25,.25,.2,.1]; qr=[.28,.2,.14,.1,.07,.04]
pts=[.2,.3,.4,.6,.8,1.0]
def hf(L,C,D,Q): return 10.67*L*Q**1.852/(C**1.852*D**4.87)
def eta(t,phi):
    K,e,pm,_=tur[t]
    if phi<pm-1e-12: return 0
    for i in range(5):
        if phi<=pts[i+1]+1e-12: return e[i]+(e[i+1]-e[i])*(phi-pts[i])/(pts[i+1]-pts[i])
    return e[5]
def run(u,l,t,f):
    Du,Cu,hu,pu=pipes[u]; Dl,Cl,hl,pl=pipes[l]; K=tur[t][0]
    HN=lambda Q: 85-hf(240,Cu,Du,Q)-hf(180,Cl,Dl,Q)
    QF=brentq(lambda Q:Q*Q-K*K*HN(Q),1e-6,0.6)
    Ps=[];E=0
    for fi,q in zip(fr,qr):
        Q=min(f*q,QF); phi=Q/QF
        P=eta(t,phi)*0.93*9.81*Q*HN(Q); Ps.append(P); E+=fi*8760*P
    return QF,Ps,E/1000,Du,Dl
res=[]
for u,l,t in itertools.product(pipes,pipes,tur):
    if pipes[u][2]<52 or pipes[l][2]<110.5: continue
    QF,_,Elo,Du,Dl=run(u,l,t,0.85)[0:5]
    QF,Ph,_,_,_=run(u,l,t,1.15)
    vu=QF/(math.pi*Du**2/4); vl=QF/(math.pi*Dl**2/4)
    cost=pipes[u][3]*240+pipes[l][3]*180+tur[t][3]
    ok=Elo>=520 and max(Ph)<=125 and vu<=3.5 and vl<=3.5
    res.append((cost,ok,u,l,t,round(QF,4),round(Elo,1),round(max(Ph),1),round(vu,2),round(vl,2)))
res.sort()
print(len(res),sum(r[1] for r in res))
for r in res[:15]: print(r)
print('--passing')
for r in [r for r in res if r[1]][:10]: print(r)
