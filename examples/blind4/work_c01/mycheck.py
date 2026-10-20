import math
from itertools import product
opts=[("EPS-30",30,.038,.003,4,20),("EPS-40",40,.038,.003,5.5,20),("EPS-50",50,.038,.003,7,20),("EPS-60",60,.038,.003,8.5,20),("EPS-80",80,.038,.003,16,20),
("PU-25",25,.025,.002,7,40),("PU-35",35,.025,.002,9.5,40),("PU-45",45,.025,.002,12,40),("PU-55",55,.025,.002,14.5,40),
("VIP-20",20,.0075,.002,38,180),("VIP-30",30,.0075,.002,52,180),("VIP-40",40,.0075,.002,68,180)]
def geom(t):
    t/=1000; a,b,c=.5-2*t,.4-2*t,.4-2*t
    Ain=2*(a*b+a*c+b*c); Aout=2*(.5*.4+.5*.4+.4*.4)
    return math.sqrt(Aout*Ain), a*b*c*1000
def Tend(m,t,k,Ta,f,L,Cp):
    Am,_=geom(t); UA=k*Am/(t/1000)
    dT=abs(Ta-5); t1=f*m*L*1000/(UA*dT); tau=(Cp*1000+m*3200)/UA
    T48=48*3600
    if t1>=T48: return 5.0
    e=math.exp(-(T48-t1)/tau)
    return Ta-(Ta-5)*e if Ta>5 else Ta+(5-Ta)*e
def ok(m,o):
    nm,t,k0,dk,p,r=o
    Vin=geom(t)[1]
    if Vin-8<m/0.92 or 8.6+r*(0.08-Vin/1000)+m>22: return False
    # worst case: hot: T max -> k high, f low, L low, Cp high ; cold: T min -> k high, f low, L low, Cp high (check all corners)
    for k in (k0-dk,k0+dk):
      for L in (185,215):
        for Cp in (30,34):
          for f in (.85,1):
            if Tend(m,t,k,36,f,L,Cp)>8: return False
          for f in (.7,1):
            if Tend(m,t,k,-20,f,L,Cp)<2: return False
    return True
best=[]
for o in opts:
    # smallest m feasible: scan fine, feasibility may be non-monotone (mass/vol upper bounds) -> scan
    ms=[i*0.001 for i in range(0,20000)]
    feas=[m for m in ms if ok(m,o)]
    if feas:
        print(o[0],"m range",feas[0],feas[-1],"cost",o[4]+6.5*feas[0])
    else: print(o[0],"infeasible")
