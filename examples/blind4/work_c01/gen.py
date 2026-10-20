import json,sys
# usage: gen.py out step nlo nhi form(faithful|alg)
out=sys.argv[1]; step=sys.argv[2]; nlo=sys.argv[3]; nhi=sys.argv[4]; form=sys.argv[5]
g=lambda **k: dict(role="given",**k)
Q={
 "Lx":g(value="0.5",unit="m",ground="airline",why="outer length"),
 "Ly":g(value="0.4",unit="m",ground="airline",why="outer width"),
 "Lz":g(value="0.4",unit="m",ground="airline",why="outer height"),
 "tend":g(value="48",unit="h",ground="problem",why="transit duration"),
 "Tm":g(value="5",unit="C",ground="problem",why="PCM melt point (difference-only C)"),
 "Ta":g(value="36",unit="C",why="ambient, hot lane (mode overrides)"),
 "sg":g(value="1",unit="",why="+1 hot lane, -1 cold lane (mode overrides)"),
 "f":g(range=["0.85","1"],unit="",why="available latent fraction (mode overrides)"),
 "Llat":g(range=["185","215"],unit="kJ/kg",why="PCM latent heat"),
 "Cp":g(range=["30","34"],unit="kJ/K",why="payload thermal capacity"),
 "cpcm":g(value="3.2",unit="kJ/(kg*K)",ground="problem",why="PCM sensible heat"),
 "rpcm":g(value="0.92",unit="kg/L",ground="problem",why="pack density"),
 "ppcm":g(value="6.5",unit="EUR/kg",ground="problem",why="PCM price"),
 "Vpay":g(value="8",unit="L",ground="problem",why="payload volume"),
 "Mpay":g(value="8",unit="kg",ground="problem"),
 "Mshell":g(value="0.6",unit="kg",ground="problem"),
 "Mmax":g(value="22",unit="kg",ground="carrier"),
 "mstep":g(value=step,unit="kg",ground="discretisation of PCM mass (my approximation)"),
 "moff":g(value=nlo and "0",unit="kg"),
}
for n,u in [("t1","s"),("tau","s"),("Tend","C"),("Vmargin","L"),("Mtot","kg")]:
    Q[n]=dict(role="derived",unit=u)
if form=="alg":
    del Q["t1"]; del Q["tau"]
D={
 "Vin":"(Lx-2*INS.t)*(Ly-2*INS.t)*(Lz-2*INS.t)",
 "Aout":"2*(Lx*Ly+Lx*Lz+Ly*Lz)",
 "Ain":"2*((Lx-2*INS.t)*(Ly-2*INS.t)+(Lx-2*INS.t)*(Lz-2*INS.t)+(Ly-2*INS.t)*(Lz-2*INS.t))",
 "Am":"sqrt(Aout*Ain)",
 "UA":"INS.k*Am/INS.t",
 "dT":"sg*(Ta-Tm)",
}
laws=[]
if form=="faithful":
    laws+=[{"zfl":"t1 == f*m*Llat/(UA*dT)","source":"phase 1 duration t1 = f m L/(UA |Ta-5|)"},
           {"zfl":"tau == (Cp + m*cpcm)/UA","source":"time constant"},
           {"zfl":"Tend == Tm + sg*dT*(1 - exp(-max(0, tend - t1)/tau))","source":"phase 2 exponential approach (T=5 if t1>=48h)"}]
else:
    laws+=[{"zfl":"Tend == Tm + sg*dT*(1 - exp(-max(0, tend*UA - f*m*Llat/dT)/(Cp + m*cpcm)))","source":"same as faithful, UA/tau algebra: (tend-t1)/tau = (tend*UA - f m L/dT)/(Cp+m c)"}]
laws+=[{"zfl":"Vmargin == Vin - Vpay - m/rpcm","source":"R3: interior volume contains payload and PCM"},
       {"zfl":"Mtot == Mpay + Mshell + INS.rho*(Lx*Ly*Lz - Vin) + m","source":"mass formula"}]
mode_h={"quantities":{"Ta":{"value":"36"},"sg":{"value":"1"},"f":{"range":["0.85","1"]}},
 "requirements":[{"quantity":"Tend","op":"<=","value":"8","why":"R1 hot lane T(48h) <= 8 C"}]}
mode_c={"quantities":{"Ta":{"value":"-20"},"sg":{"value":"-1"},"f":{"range":["0.70","1"]}},
 "requirements":[{"quantity":"Tend","op":">=","value":"2","why":"R2 cold lane T(48h) >= 2 C"}]}
names=[("EPS-30",30,"0.038","0.003",4.0,20),("EPS-40",40,"0.038","0.003",5.5,20),("EPS-50",50,"0.038","0.003",7.0,20),("EPS-60",60,"0.038","0.003",8.5,20),("EPS-80",80,"0.038","0.003",16.0,20),
("PU-25",25,"0.025","0.002",7.0,40),("PU-35",35,"0.025","0.002",9.5,40),("PU-45",45,"0.025","0.002",12.0,40),("PU-55",55,"0.025","0.002",14.5,40),
("VIP-20",20,"0.0075","0.0020",38.0,180),("VIP-30",30,"0.0075","0.0020",52.0,180),("VIP-40",40,"0.0075","0.0020",68.0,180)]
from fractions import Fraction as F
items=[]
for nm,t,k,dk,p,r in names:
    k=F(k);dk=F(dk)
    items.append({"name":nm,"t":str(t),"k":{"range":[str(k-dk),str(k+dk)]},"price":str(p),"rho":str(r)})
cat={"insulation":{"ground":"problem statement table","items":items,
   "fields":{"t":{"unit":"mm"},"k":{"unit":"W/(m*K)"},"price":{"unit":"EUR"},"rho":{"unit":"kg/m^3"}}},
   "pcm":{"ground":"discretised continuous PCM mass","integers":{"field":"N","from":nlo,"to":nhi,"unit":""}}}
brick={"stand":"universal-stand/1","quantities":Q,"slots":{"INS":{"from":["insulation"]},"PCM":{"from":["pcm"]}},
 "define":D,"computed":{"m":{"value":"moff + PCM.N*mstep","unit":"kg"}},
 "laws":laws,
 "requirements":[{"quantity":"Vmargin","op":">=","value":"0","why":"R3 PCM volume fits"},
                 {"quantity":"Mtot","op":"<=","value":"Mmax","why":"R4 shipping mass <= 22 kg"}],
 "modes":{"hot lane":mode_h,"cold lane":mode_c},
 "objective":{"minimize":"INS.price + ppcm*m","why":"panel price + 6.5 EUR/kg PCM"},
 "catalog":cat}
json.dump(brick,open(out,"w"),indent=1)
