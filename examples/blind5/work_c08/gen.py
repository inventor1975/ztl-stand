import json,sys
cons_unit = sys.argv[1] if len(sys.argv)>1 else "kWh/100km"
Q={}
def g(n,v=None,unit="",why="",rng=None,ground="problem statement"):
    d={"role":"given","unit":unit,"why":why}
    if rng: d["range"]=rng
    else: d["value"]=v; d["ground"]=ground
    Q[n]=d
def dv(n,unit,why=""): Q[n]={"role":"derived","unit":unit,"why":why}
g("CURB","2050","kg","curb mass with driver")
g("RHO","1.20","kg/m^3","air density")
g("GR","9.81","m/s^2","gravity (problem value, not g0)")
g("CDA0",unit="m^2",why="baseline CdA, common to all routes",rng=["1.05","1.15"])
g("PAY",unit="kg",why="payload, the same on all routes",rng=["500","850"])
g("KR",unit="",why="rolling-resistance multiplier on catalog Crr",rng=["0.90","1.10"])
g("FT",unit="",why="cold-day usable-capacity factor",rng=["0.82","0.92"])
g("PAYMAX","850","kg","highest payload (R3)")
g("PAUX","0.4","kW","auxiliary base power")
g("RGEN","0.55","","regeneration recovery")
g("ETA","0.88","","drivetrain efficiency")
g("RES","0.92","","reserve factor")
g("SOLC","0.35","h","solar credit on a cold day, 0.35 kWh per kWp (kWh/kW = h)")
g("HALF","0.5","","half of the days cold, half warm")
routes={"u":("urban","140","26","45","2.4","0.50"),
        "s":("suburban","170","52","70","0.6","0.35"),
        "m":("motorway","158","95","110","0.05","0.15")}
laws=[];reqs=[]
for k,(nm,D,va,vc,st,sh) in routes.items():
    g("D"+k,D,"km",nm+" daily distance")
    g("va"+k,va,"km/h",nm+" average speed")
    g("vc"+k,vc,"km/h",nm+" cruise speed")
    g("st"+k,st,"1/km",nm+" stops per km")
    g("sh"+k,sh,"",nm+" share of days")
    dv("F"+k,"N","road load force, "+nm)
    dv("K"+k,"J/m","kinetic loss per distance, "+nm)
    dv("Et"+k,"Wh/km","traction energy, "+nm)
    dv("Ec"+k,"Wh/km","total energy cold day, "+nm)
    dv("Ew"+k,"Wh/km","total energy warm day, "+nm)
    dv("Rg"+k,"km","cold-day range, "+nm)
    laws += [
     {"zfl":f"F{k} == TYR.Crr*KR*M*GR + 0.5*RHO*CDA0*AERO.k*vc{k}*vc{k}","source":"road load: rolling + aero"},
     {"zfl":f"K{k} == st{k}*0.5*M*vc{k}*vc{k}*(1 - RGEN)","source":"kinetic loss net of regeneration"},
     {"zfl":f"Et{k} == (F{k} + K{k})/ETA","source":"traction energy at battery"},
     {"zfl":f"Ec{k} == Et{k} + (PAUX + HEAT.P)/va{k}","source":"aux energy incl. cabin heating (cold)"},
     {"zfl":f"Ew{k} == Et{k} + PAUX/va{k}","source":"aux energy, no heating (warm)"},
     {"zfl":f"Rg{k} == U/Ec{k}","source":"range = usable energy / consumption"},
    ]
    reqs.append({"quantity":"Rg"+k,"op":">=","value":"D"+k,"why":"R1: cold-day range covers daily distance, "+nm})
dv("U","kWh","cold-day usable energy after 8 years")
dv("Cons",cons_unit,"average consumption")
dv("Mg","kg","gross mass at highest payload")
laws += [
 {"zfl":"U == PACK.E*RET*FT*RES + SOLC*SOL.kWp","source":"retention, cold factor, reserve, solar credit"},
 {"zfl":"Cons == shu*(HALF*Ecu + HALF*Ewu) + shs*(HALF*Ecs + HALF*Ews) + shm*(HALF*Ecm + HALF*Ewm)","source":"share-weighted half cold/half warm; solar not counted"},
 {"zfl":"Mg == CURB + PACK.mass + SOL.mass + PAYMAX","source":"gross mass limit"},
]
reqs += [{"quantity":"Cons","op":"<=","value":"248","why":"R2: 24.8 kWh/100km written as 248 Wh/km (x10 by hand: 1 kWh/100km = 10 Wh/km)"},
         {"quantity":"Mg","op":"<=","value":"3500","why":"R3: legal gross mass"}]
out={"stand":"universal-stand/1","quantities":Q,
 "slots":{"PACK":{"from":["packs"]},"TYR":{"from":["tyres"]},"AERO":{"from":["aeros"]},"HEAT":{"from":["heaters"]},"SOL":{"from":["solar"],"optional":True}},
 "define":{"M":"CURB + PACK.mass + PAY + SOL.mass","RET":"exp(-0.028*8)"},
 "laws":laws,"requirements":reqs,
 "objective":{"minimize":"PACK.price + TYR.price + AERO.price + HEAT.price + SOL.price","why":"minimum total price"},
 "catalog":{
  "packs":{"items":[{"E":str(e),"mass":str(m),"price":str(p)} for e,m,p in [(40,285,6.4),(52,365,8.1),(64,440,9.8),(77,530,11.9),(90,610,13.8),(110,745,17.0)]],
           "fields":{"E":{"unit":"kWh"},"mass":{"unit":"kg"},"price":{"unit":"kEUR"}}},
  "tyres":{"items":[{"Crr":c,"price":p} for c,p in [("0.0105","0"),("0.0082","0.35"),("0.0072","0.70")]],
           "fields":{"Crr":{"unit":""},"price":{"unit":"kEUR"}}},
  "aeros":{"items":[{"k":c,"price":p} for c,p in [("1.00","0"),("0.92","0.5"),("0.86","1.4")]],
           "fields":{"k":{"unit":""},"price":{"unit":"kEUR"}}},
  "heaters":{"items":[{"P":c,"price":p} for c,p in [("2.6","0"),("1.1","0.85")]],
           "fields":{"P":{"unit":"kW"},"price":{"unit":"kEUR"}}},
  "solar":{"items":[{"kWp":"0.9","mass":"18","price":"1.1"}],
           "fields":{"kWp":{"unit":"kW"},"mass":{"unit":"kg"},"price":{"unit":"kEUR"}}}}}
json.dump(out,open("c08.json","w"),indent=1)
