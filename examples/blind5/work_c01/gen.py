import json
Q={}
def g(name,unit,why,**kw):
    d={"role":"given","unit":unit,"why":why}; d.update(kw); Q[name]=d
cyc=[("1","Idle","0.25","1450",("4","5"),("58","66")),
     ("2","Normal","0.45","1450",("11","13"),("66","74")),
     ("3","Heavy","0.25","900",("20","23.1"),("70","80")),
     ("4","Shock start","0.05","300",("36","40"),("60","70"))]
for i,nm,f,n,fr,t in cyc:
    g("f"+i,"",f"time fraction of cycle {nm}",value=f,ground="problem statement")
    g("n"+i,"1/min",f"speed of cycle {nm}",value=n,ground="problem statement")
    g("Fr"+i,"kN",f"radial load of cycle {nm}",range=list(fr))
    g("T"+i,"C",f"bearing temperature of cycle {nm}",range=list(t))
g("D0","mm","shaft diameter d",value="60",ground="problem statement")
g("MM1","mm","one mm (to make a ratio dimensionless)",value="1")
g("RPM","1/min","one rpm (dimensionless ratio)",value="1")
g("NLIM","1/min","speed split of the nu1 formula",value="1000",ground="problem statement")
g("NUU","mm^2/s","one mm2/s",value="1")
g("MR","","revolutions per million (L is in million revolutions)",value="1000000")
g("KT","1/C","viscosity-temperature coefficient 0.040",value="0.04",ground="problem statement")
g("T0","C","reference temperature of nu40",value="40",ground="problem statement")
g("FAR","","Fa/Fr",value="0.30",ground="problem statement")
g("XE","","equivalent-load axial factor 0.45",value="0.45",ground="problem statement")
g("XS","","static axial factor 0.6",value="0.6",ground="problem statement")
g("EXPL","","life exponent 10/3 (documentation only)",value="10/3")
g("Lreq","h","required service life 8 y x 7000 h",value="56000",ground="problem statement")
g("SFmin","","required static safety C0/P0",value="2.5",ground="problem statement")
g("ODmax","mm","housing bore limit",value="150",ground="problem statement")
for k in ["P1","P2","P3","P4","L1","L2","L3","L4","kap1","kap2","kap3","kap4","aL1","aL2","aL3","aL4","d","Lh","Ps","m0","ODq"]:
    pass
dq={"role":"derived"}
U={"P":"kN","L":"","kap":"","aL":"","d":"1/h","Lh":"h","Ps":"kN","m0":"kN","ODq":"mm"}
for i in "1234":
    Q["P"+i]={"role":"derived","unit":"kN"}
    Q["L"+i]={"role":"derived","unit":""}
    Q["kap"+i]={"role":"derived","unit":""}
    Q["aL"+i]={"role":"derived","unit":""}
for k in ["d","Lh","Ps","m0","ODq"]:
    Q[k]={"role":"derived","unit":U[k]}
define={"DM":"(D0 + B.OD)/2"}
laws=[]
for i,nm,*_ in cyc:
    define["NU1_"+i]=f"NUU*if(n{i} >= NLIM, 4500*pow(n{i}/RPM, -0.5), 45000*pow(n{i}/RPM, -0.83))*pow(DM/MM1, -0.5)"
    laws.append({"zfl":f"P{i} == Fr{i} + XE*FAR*Fr{i}","source":"equivalent load P = Fr + 0.45 Fa, Fa = 0.30 Fr"})
    laws.append({"zfl":f"kap{i} == O.nu40*exp(0 - KT*(T{i} - T0))/NU1_{i}","source":"nu(T)=nu40 exp(-0.040(T-40)); kappa = nu/nu1; nu1 per speed and mean diameter"})
    laws.append({"zfl":f"aL{i} == table(kap{i}, 0.4, 0.4, 0.7, 0.75, 1, 1, 2, 1.7, 4, 2.3)","source":"a_L(kappa) piecewise linear, constant beyond ends"})
    laws.append({"zfl":f"L{i} == aL{i}*K.fc*pow(B.C/P{i}, EXPL)","source":"modified life L_i = a_L f_c (C/P)^(10/3), million rev"})
laws.append({"zfl":"d == f1*n1/(MR*L1) + f2*n2/(MR*L2) + f3*n3/(MR*L3) + f4*n4/(MR*L4)","source":"Miner damage per operating hour, d = sum f_i 60 n_i/(1e6 L_i)"})
laws.append({"zfl":"Lh == 1/d","source":"service life in hours = 1/d"})
laws.append({"zfl":"Ps == Fr4 + XS*FAR*Fr4","source":"static P0 = Fr + 0.6 Fa at the shock cycle, largest Fr"})
laws.append({"zfl":"m0 == B.C0 - SFmin*Ps","source":"C0/P0 >= 2.5 written as C0 - 2.5 P0 >= 0"})
laws.append({"zfl":"ODq == B.OD","source":"housing bore limit on bearing OD"})
bear=[("R-60A",95,100,110,"0.38"),("R-60B",118,128,110,"0.52"),("R-60C",135,150,130,"0.61"),("R-60D",160,180,130,"0.80"),("R-60E",190,215,150,"1.05"),("R-60F",235,270,150,"1.45"),("R-60G",290,345,180,"2.10")]
brick={"stand":"universal-stand/1","report":"all",
"quantities":Q,
"slots":{"B":{"from":["bearings"]},"O":{"from":["oils"]},"K":{"from":["kits"]}},
"define":define,"laws":laws,
"requirements":[
 {"quantity":"Lh","op":">=","value":"Lreq","why":"R1 service life 1/d >= 56000 h for all loads and temperatures"},
 {"quantity":"m0","op":">=","value":"0","why":"R2 static safety C0/P0 >= 2.5 at the shock cycle, worst Fr"},
 {"quantity":"ODq","op":"<=","value":"ODmax","why":"R3 OD <= 150 mm"}],
"objective":{"minimize":"B.price + O.price + K.price","why":"cheapest bearing + oil + kit"},
"catalog":{
 "bearings":{"items":[{"name":nm,"C":{"value":str(c)},"C0":{"value":str(c0)},"OD":{"value":str(od)},"price":p} for nm,c,c0,od,p in bear],
   "fields":{"C":{"unit":"kN"},"C0":{"unit":"kN"},"OD":{"unit":"mm"},"price":{"unit":"kEUR"}},"ground":"problem statement"},
 "oils":{"items":[{"name":nm,"nu40":v,"price":p} for nm,v,p in [("VG68","68","0.20"),("VG150","150","0.25"),("VG320","320","0.35"),("VG680","680","0.50")]],
   "fields":{"nu40":{"unit":"mm^2/s"},"price":{"unit":"kEUR"}},"ground":"problem statement"},
 "kits":{"items":[{"name":"none","fc":"0.6","price":"0"},{"name":"filter-and-seal kit","fc":"1","price":"0.9"}],
   "fields":{"fc":{"unit":""},"price":{"unit":"kEUR"}},"ground":"problem statement"}}}
json.dump(brick,open("c01.json","w"),indent=1)
