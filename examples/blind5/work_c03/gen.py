import json, sys
from decimal import Decimal, getcontext
from mpmath import mp, mpf
mp.dps = 40
def fmt(x, d=8):
    return format(Decimal(str(x)).quantize(Decimal(1).scaleb(-d)), 'f')
cols = [("F1",2.0,"0.76","4.2","0.016","0.42"),("F2",2.3,"0.80","3.4","0.014","0.55"),
        ("F3",2.5,"0.81","3.0","0.012","0.68"),("T1",2.2,"0.74","1.4","0.005","0.85"),
        ("T2",3.0,"0.76","1.3","0.004","1.15"),("T3",2.6,"0.78","1.2","0.0035","1.05")]
items=[]
for n,A,e,a1,a2,p in cols:
    items.append({"A":str(A),"eta0":e,"a1":a1,"a2":a2,"price":p,"model":n})
tanks=[]
for V in (300,500,750,1000,1500):
    r=mpf(V)/300
    tanks.append({"V":str(V),"UA":fmt(mpf('1.8')*r**mpf('0.6'),8),"price":fmt(mpf('0.9')*r**mpf('0.8'),6)})
seasons={"winter":(90,"1.4","2.0",6,"3","7","6","9"),
 "spring":(92,"3.6","4.6",8,"10","14","9","12"),
 "summer":(92,"5.6","6.8",10,"20","26","15","18"),
 "autumn":(91,"2.6","3.4",7,"11","15","11","14")}
modes={}
for s,(d,h0,h1,hs,t0,t1,c0,c1) in seasons.items():
    modes[s]={"weight":f"{d}*dd",
      "quantities":{"H":{"range":[h0,h1]},"hs":{"value":str(hs)},"Ta":{"range":[t0,t1]},"Tc":{"range":[c0,c1]}},
      "requirements":[{"quantity":"T","op":"<=","value":"Tmax","why":"R2: tank <= 80 C in "+s}]}
brick={
 "stand":"universal-stand/1",
 "quantities":{
  "H":{"role":"given","range":["1","7"],"unit":"kWh/m^2/day","why":"overridden per season"},
  "hs":{"role":"given","value":"8","unit":"h","why":"sun hours, overridden per season"},
  "Ta":{"role":"given","range":["0","30"],"unit":"C","why":"day ambient, overridden per season"},
  "Tc":{"role":"given","range":["5","20"],"unit":"C","why":"cold inlet, overridden per season"},
  "D":{"role":"given","range":["540","660"],"unit":"L/day","why":"daily draw, ONE shared value for all seasons (not overridden in any mode)"},
  "cw":{"role":"given","value":"0.0011628","unit":"kWh/(L*K)","why":"c_w of water"},
  "Tt":{"role":"given","value":"45","unit":"C","why":"hot-water set point"},
  "dTo":{"role":"given","value":"6","unit":"C","why":"mean collector T = T + 6"},
  "dTr":{"role":"given","value":"8","unit":"C","why":"room = Ta + 8"},
  "dd":{"role":"given","value":"1","unit":"day","why":"unit of a day for season weights"},
  "Tmax":{"role":"given","value":"80","unit":"C","why":"R2 limit"},
  "Emax":{"role":"given","value":"3700","unit":"kWh","why":"R1 limit (annual)"},
  "Rmin":{"role":"given","value":"50","unit":"L/m^2","why":"R3"},
  "Rmax":{"role":"given","value":"100","unit":"L/m^2","why":"R3"},
  "T":{"role":"derived","unit":"C","search":["0","150"],"why":"tank temperature: collector heat = load + losses"},
  "Bk":{"role":"derived","unit":"kWh/day","why":"daily back-up boiler energy"}
 },
 "slots":{"COL":{"from":["collectors"]},"N":{"from":["modules"]},"TANK":{"from":["tanks"]},"INS":{"from":["insulation"]}},
 "where":["TANK.V/(N.n*COL.A) >= Rmin","TANK.V/(N.n*COL.A) <= Rmax"],
 "define":{
  "G":"H*dd/hs",
  "UAe":"TANK.UA*INS.f",
  "Tr":"Ta + dTr"
 },
 "laws":[
  {"zfl":"N.n*COL.A*H*if(COL.eta0 - COL.a1*(T + dTo - Ta)/G - COL.a2*(T + dTo - Ta)*(T + dTo - Ta)/G > 0, COL.eta0 - COL.a1*(T + dTo - Ta)/G - COL.a2*(T + dTo - Ta)*(T + dTo - Ta)/G, 0) == cw*D*(T - Tc) + UAe*(T - Tr)","source":"daily heat balance: collector useful heat = load + tank loss (0.024 = 24 h/day is carried by the units)"},
  {"zfl":"Bk == cw*D*if(T > Tt, 0, Tt - T)","source":"back-up boiler tops water up to 45 C"}
 ],
 "modes":modes,
 "totals":{"Eyear":{"sum":"Bk","unit":"kWh"}},
 "requirements":[{"quantity":"Eyear","op":"<=","value":"Emax","why":"R1 annual back-up <= 3700 kWh"}],
 "objective":{"minimize":"N.n*COL.price + TANK.price + INS.price","unit":"kEUR","why":"minimum price"},
 "catalog":{
  "collectors":{"ground":"datasheet","items":items,"fields":{"A":{"unit":"m^2"},"eta0":{"unit":""},"a1":{"unit":"W/(m^2*K)"},"a2":{"unit":"W/(m^2*K^2)"},"price":{"unit":"kEUR"}}},
  "modules":{"integers":{"field":"n","from":"1","to":"16","unit":""}},
  "tanks":{"ground":"tank price/loss formulas (rounded to 8 / 6 digits)","items":tanks,"fields":{"V":{"unit":"L"},"UA":{"unit":"W/K"},"price":{"unit":"kEUR"}}},
  "insulation":{"ground":"problem statement","items":[{"f":"1","price":"0","kind":"none"},{"f":"0.6","price":"0.25","kind":"upgrade"}],"fields":{"f":{"unit":""},"price":{"unit":"kEUR"}}}
 }
}
if len(sys.argv)>2:
    brick["where"].append("N.n*COL.price + TANK.price + INS.price >= Pmin")
    brick["quantities"]["Pmin"]={"role":"given","value":sys.argv[2],"unit":"kEUR","why":"PRE-FILTER (run-time cut, my own): designs cheaper than this were refuted outside the stand"}
json.dump(brick,open(sys.argv[1],"w"),indent=1)
