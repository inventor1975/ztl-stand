import json, sys
N = int(sys.argv[1]); nlo=int(sys.argv[2]); nhi=int(sys.argv[3]); out=sys.argv[4]
MODE = sys.argv[5] if len(sys.argv)>5 else 'A'
WLIM = sys.argv[6] if len(sys.argv)>6 else '48'
PK = {"PK1":("1.0","137","0.10"),"PK2":("1.4","137","0.35"),"PK3":("1.8","135","1.20"),
      "PK4":("2.2","132","1.90"),"PK5":("1.2","126","0.80")}
LOADS = [  # name, tau, req, allowed, packs, cycles, budget
 ("L1","30","9",["PK1","PK2","PK5"],"12","20","120"),
 ("L2","60","12",["PK2","PK3","PK4","PK5"],"6","15","120"),
 ("L3","110","12",["PK2","PK3","PK4"],"8","10","150"),
 ("L4","150","15",["PK3","PK4","PK5"],"4","5","40")]
DRY = {"121":"25","124":"23","126":"22","130":"20","134":"18"}
q={}; laws=[]; reqs=[]; define={}
def g(n,v,u,why,**k): q[n]=dict(role="given",value=v,unit=u,why=why,**k)
q["dT"]=dict(role="given",range=["-0.5","1.5"],unit="C",why="T_ch - T_set, chamber temperature during hold")
q["T0"]=dict(role="given",range=["45","80"],unit="C",why="initial pack temperature")
g("D121","1.5","min","spore D value at 121.1 C","ground" if False else "ground") if False else None
q["D121"]=dict(role="given",value="1.5",unit="min",why="spore D at reference",ground="problem statement")
q["zs"]=dict(role="given",value="10",unit="C",why="spore z-value",ground="problem statement")
q["Tref"]=dict(role="given",value="121.1",unit="C",why="spore reference temperature",ground="problem statement")
q["zm"]=dict(role="given",value="25",unit="C",why="material z-value",ground="problem statement")
q["Tm0"]=dict(role="given",value="121",unit="C",why="material reference temperature",ground="problem statement")
q["step"]=dict(role="given",value="0.5",unit="min",why="grid of the hold time (real t_h approximated by a 0.5 min grid)",ground="modelling choice")
q["ovh"]=dict(role="given",value="15",unit="min",why="vacuum and heat-up",ground="problem statement")
q["Wlim"]=dict(role="given",value=WLIM,unit="h",why="weekly autoclave time limit",ground="problem statement")
q["rate"]=dict(role="given",value="0.9",unit="EUR/min",why="cost per cycle minute",ground="problem statement")
q["dhi"]=dict(role="given",value="1.5",unit="C",why="chamber overshoot max (T_set+1.5)",ground="problem statement")
define["th"]="H.n*step"
define["thhi"]="(H.n+1)*step"
define["Tch"]="TS.Tset + dT"
slots={"TS":{"from":["setpoints"]},"H":{"from":["hold"]}}
cat={"setpoints":{"items":[{"Tset":t,"dry":d,"lbl":"T"+t} for t,d in DRY.items()],
        "fields":{"Tset":{"unit":"C"},"dry":{"unit":"min"}}},
     "hold":{"integers":{"field":"n","from":str(nlo),"to":str(nhi),"unit":""}}}
cyc=[];
for (L,tau,req,allow,packs,cy,bud) in LOADS:
    g("tau0"+L,tau,"s","base tau "+L,ground="problem statement")
    g("req"+L,req,"","required log-reduction "+L,ground="problem statement")
    g("pk"+L,packs,"","packs per cycle "+L,ground="problem statement")
    g("cy"+L,cy,"","cycles per week "+L,ground="problem statement")
    g("bud"+L,bud,"min","damage budget "+L,ground="problem statement")
    slots["P"+L]={"from":["pack"+L]}
    cat["pack"+L]={"items":[{"mult":PK[p][0],"Tmax":PK[p][1],"price":PK[p][2],"name":p} for p in allow],
                   "fields":{"mult":{"unit":""},"Tmax":{"unit":"C"},"price":{"unit":"EUR"}}}
    define["tau"+L]="tau0%s*P%s.mult"%(L,L)
    terms=[]
    for k in (range(N) if MODE=='A' else range(1,N+1)):
        tk=("(%d*th/%d)"%(k,N)) if MODE=='A' else ("(%d*thhi/%d)"%(k,N))
        terms.append("pow(10, (Tch - (Tch - T0)*exp(-%s/tau%s) - Tref)/zs)"%(tk,L))
    for v,u in (("LR"+L,""),("Dm"+L,"min"),("Pm"+L,"C")): q[v]=dict(role="derived",unit=u)
    q["LR"+L]["why"]="log-reduction of %s (left Riemann sum, %d panels, lower bound of the integral)"%(L,N)
    laws.append({"zfl":("LR%s == "+('th' if MODE=='A' else 'thhi')+"/(%d*D121)*(%s)")%(L,N," + ".join(terms)),
        "source":"LR = (1/D)*integral 10^((Tcs-Tref)/z) dt; integrand increasing in t so the "+("left Riemann sum is a lower bound" if MODE=='A' else "right Riemann sum at the upper cell end is an upper bound")})
    laws.append({"zfl":"Dm%s == th*pow(10, (TS.Tset + dhi - Tm0)/zm)"%L,"source":"thermal damage index, z_m = 25"})
    laws.append({"zfl":"Pm%s == P%s.Tmax - (TS.Tset + dhi)"%(L,L),"source":"packaging temperature limit margin"})
    reqs.append({"quantity":"LR"+L,"op":">=","value":"req"+L,"why":"R1 log-reduction "+L})
    reqs.append({"quantity":"Dm"+L,"op":"<=","value":"bud"+L,"why":"R2 damage budget "+L})
    reqs.append({"quantity":"Pm"+L,"op":">=","value":"0","why":"R3 packaging limit "+L})
    cyc.append("cy%s*(ovh + th + TS.dry)"%L)
q["Wk"]=dict(role="derived",unit="h",why="weekly autoclave time")
laws.append({"zfl":"Wk == "+" + ".join(cyc),"source":"sum of cycles x cycle time"})
reqs.append({"quantity":"Wk","op":"<=","value":"Wlim","why":"R4 weekly time"})
cost="rate*("+" + ".join(cyc)+") + "+" + ".join("cy%s*pk%s*P%s.price"%(L[0],L[0],L[0]) for L in LOADS)
brick={"stand":"universal-stand/1","quantities":q,"slots":slots,"define":define,"laws":laws,
 "requirements":reqs,"objective":{"minimize":cost,"unit":"EUR","why":"weekly cost"},"catalog":cat}
json.dump(brick,open(out,"w"),indent=1)
