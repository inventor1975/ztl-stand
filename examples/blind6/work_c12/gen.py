import json
def G(v=None,unit="",rng=None,why="",ground=None):
    d={"role":"given","unit":unit,"why":why}
    if rng: d["range"]=rng
    else: d["value"]=v
    if ground: d["ground"]=ground
    return d
Q={}
Q["lam0"]=G(rng=["0.0000018","0.0000024"],unit="1/h",why="base failure rate at 20 degC, ONE value for all regimes")
Q["B"]=G("3000","K",why="thermal constant",ground="problem statement")
Q["Tref"]=G("293.15","K",why="20 degC reference",ground="problem statement")
Q["Tov"]=G("2190","h",why="quarterly overhaul interval",ground="problem statement")
Q["Hn"]=G("50","h",why="normalising hours in (H/50)^0.35",ground="problem statement")
Q["Hyr"]=G("8760","h",why="hours per year for the test count",ground="problem statement")
Q["Ulim"]=G("0.00225","",why="R1 limit",ground="problem statement")
regs=[("1","winter","0.33",["278.15","285.15"],["40","60"]),
      ("2","summer","0.25",["297.15","305.15"],["25","40"]),
      ("3","shoulder","0.42",["285.15","293.15"],["15","25"])]
laws=[]
for i,n,f,T,H in regs:
    Q["f"+i]=G(f,"",why=n+" share of year",ground="problem statement")
    Q["T"+i]=G(rng=T,unit="K",why=n+" room temperature (degC range + 273.15, written in K)")
    Q["H"+i]=G(rng=H,unit="h",why=n+" annual running hours")
    Q["lam"+i]={"role":"derived","unit":"1/h","why":n+" failure rate"}
    Q["U"+i]={"role":"derived","unit":"","why":n+" hidden-state unavailability"}
    laws.append({"zfl":f"lam{i} == lam0*exp(B*(1/Tref - 1/T{i}))*pow(H{i}/Hn, 7/20)*CM.k","source":"Arrhenius-type temperature factor x (H/50)^0.35 x monitoring factor"})
    laws.append({"zfl":f"U{i} == TM.c*lam{i}*TAU.x/2 + (1 - TM.c)*lam{i}*Tov/2 + TM.td/TAU.x","source":"hidden-state unavailability: undetected-failure term + overhaul term + test downtime share"})
Q["U"]={"role":"derived","unit":"","why":"weighted unavailability"}
Q["tauq"]={"role":"derived","unit":"h","why":"the chosen interval, for R2"}
laws.append({"zfl":"U == f1*U1 + f2*U2 + f3*U3","source":"weighted unavailability"})
laws.append({"zfl":"tauq == TAU.x","source":"the chosen test interval"})
brick={"stand":"ztl-stand/1","quantities":Q,
 "slots":{"TM":{"from":["tests"]},"CM":{"from":["mon"]},"TAU":{"from":["tauc"]}},
 "laws":laws,
 "requirements":[{"quantity":"U","op":"<=","value":"Ulim","why":"R1: U <= 2.25e-3"},
                 {"quantity":"tauq","op":"<=","value":"Tov","why":"R2: tau <= Tov"}],
 "objective":{"minimize":"Hyr*TM.ct/TAU.x + CM.cm","unit":"kEUR","why":"annual cost = 8760/tau * cost per test + monitoring"},
 "catalog":{
  "tests":{"ground":"problem statement","items":[
    {"name":"TS start-up only","c":{"range":["0.20","0.30"]},"td":{"range":["0.2","0.3"]},"ct":"0.35"},
    {"name":"TL load-bank run","c":{"range":["0.80","0.88"]},"td":{"range":["0.6","0.9"]},"ct":"1.6"},
    {"name":"TF full transfer test","c":{"range":["0.92","0.97"]},"td":{"range":["1.6","2.0"]},"ct":"4.2"}],
    "fields":{"c":{"unit":""},"td":{"unit":"h"},"ct":{"unit":"kEUR"}}},
  "mon":{"ground":"problem statement","items":[
    {"name":"none","k":"1","cm":"0"},
    {"name":"condition monitoring","k":{"range":["0.85","0.92"]},"cm":"2.2"}],
    "fields":{"k":{"unit":""},"cm":{"unit":"kEUR"}}},
  "tauc":{"continuous":{"field":"x","from":"24","to":"2190","unit":"h"}}}}
json.dump(brick,open("../c12.json","w"),indent=1)
