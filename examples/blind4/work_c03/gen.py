import json, sys
variant = sys.argv[1] if len(sys.argv)>1 else "main"
out = sys.argv[2] if len(sys.argv)>2 else "../c03.json"
models = [
 ("U1","5.0","1.25","90","60","0.22","2100","60"),
 ("U2","5.0","1.25","150","110","0.40","2600","110"),
 ("U3","7.5","1.25","150","110","0.40","3100","110"),
 ("U4","7.5","1.50","150","180","0.62","3900","160"),
 ("U5","10.0","1.50","150","180","0.62","4300","160"),
 ("U6","10.0","1.50","200","260","0.88","5200","220"),
 ("U7","6.0","1.25","200","200","0.70","4600","190"),
 ("U8","12.5","2.00","200","330","1.10","6100","280"),
]
nmax = 60
if variant=="small": models=models[:3]; nmax=12
regs = {"p":("40","0.68","0.80","8","14","0.10"),
        "a":("24","0.76","0.86","12","24","0.60"),
        "l":("8","0.82","0.90","22","30","0.30")}
names={"p":"Peak","a":"Average","l":"Low"}
q={}
def g(name,unit,**kw):
    d={"role":"given","unit":unit}; d.update(kw); q[name]=d
g("ONECM","cm",value="1",why="unit length for alpha per 1 cm path")
g("AGE","",value="0.70",why="end-of-life lamp output factor")
g("FOUL","",value="0.90",why="sleeve fouling factor before wiping")
g("VAL","",value="0.7",why="reactor validation factor")
g("KK","cm^2/mJ",value="0.23",why="inactivation rate constant k")
g("Pb","kW",value="0.03",why="ballast loss per chamber")
g("Ce","EUR/kWh",value="0.14",why="electricity price")
g("Hyr","h",value="8760",why="hours per year")
g("Llife","h",value="12000",why="lamp life")
for r,(Qf,u0,u1,t0,t1,fr) in regs.items():
    g("Q"+r,"m^3/h",value=Qf,why=names[r]+" flow")
    g("UVT"+r,"",range=[u0,u1],why=names[r]+" UVT per 1 cm (fraction)")
    g("Tw"+r,"",range=[t0,t1],why=names[r]+" water temperature, degC as a plain number (f_T needs dimensionless T)")
    g("fr"+r,"",value=fr,why=names[r]+" fraction of year")
    for n,u in [("alpha","1/cm"),("att",""),("fT",""),("t","s"),("D","mJ/cm^2"),("LR","")]:
        q[n+r]={"role":"derived","unit":u}
q["Pel"]={"role":"derived","unit":"kW"}
laws=[]
def fT(T):
    return (f"min(min(0.88 + (0.08/6)*({T} - 8), 0.96 + (0.04/6)*({T} - 14)),"
            f" min(1 - (0.03/6)*({T} - 20), 0.97 - 0.01*({T} - 26)))")
sl={"p":"DP","a":"DA","l":"DL"}
for r in regs:
    laws += [
     {"zfl":f"alpha{r} == -ln(UVT{r})/ONECM","source":"Beer-Lambert: alpha = -ln(UVT/100) per cm"},
     {"zfl":f"att{r} == exp(-alpha{r}*(CH.R - CH.rq))","source":"attenuation from sleeve to wall"},
     {"zfl":f"fT{r} == "+fT("Tw"+r),"source":"lamp output factor vs water temperature (concave piecewise-linear = min of its 4 segment lines, exact on 8..30 degC)"},
     {"zfl":f"t{r} == pi*(CH.R*CH.R - CH.rq*CH.rq)*CH.L/(Q{r}/NN.N)","source":"residence time t = V/(Q/n), V = pi (R^2 - rq^2) L"},
     {"zfl":f"D{r} == VAL*(CH.Puv*{sl[r]}.x*AGE*FOUL*fT{r}/(2*pi*CH.R*CH.L))*att{r}*t{r}","source":"fluence = 0.7 * I_wall * t, I_wall = Puv dim a f_foul f_T/(2 pi R L) exp(-alpha (R-rq))"},
     {"zfl":f"LR{r} == KK*D{r}/ln(10)","source":"first-order inactivation: log-reduction = k D / ln10"},
    ]
laws.append({"zfl":"Pel == NN.N*(CH.kW*DP.x + Pb)","source":"electric power at the Peak dimming: n (kW100 dim + 0.03 kW)"})
reqs=[]
for r in regs:
    reqs.append({"quantity":"LR"+r,"op":">=","value":"4","why":f"R1: 4-log in {names[r]} regime, all UVT and T in the box"})
reqs.append({"quantity":"Pel","op":"<=","value":"10","why":"R2: electrical connection <= 10 kW at the Peak dimming"})
elec = "+".join(f"fr{r}*(NN.N*(CH.kW*{sl[r]}.x + Pb))" for r in regs)
obj = f"NN.N*CH.price + 10*(Ce*Hyr*({elec}) + NN.N*CH.lamp*Hyr/Llife)"
cat={}
cat["chambers"]={"items":[{"R":{"value":m[1]},"rq":{"value":m[2]},"L":{"value":m[3]},"Puv":{"value":m[4]},
   "kW":{"value":m[5]},"price":m[6],"lamp":m[7],"model":m[0]} for m in models],
   "ground":"problem statement chamber table",
   "fields":{"R":{"unit":"cm"},"rq":{"unit":"cm"},"L":{"unit":"cm"},"Puv":{"unit":"W"},"kW":{"unit":"kW"},
             "price":{"unit":"EUR"},"lamp":{"unit":"EUR"}}}
cat["counts"]={"integers":{"field":"N","from":"1","to":str(nmax),"unit":""}}
for s in "pal":
    cat["dim"+s]={"continuous":{"field":"x","from":"0.4","to":"1","unit":""}}
brick={"stand":"universal-stand/1","quantities":q,
 "slots":{"CH":{"from":["chambers"]},"NN":{"from":["counts"]},
          "DP":{"from":["dimp"]},"DA":{"from":["dima"]},"DL":{"from":["dimal" if False else "diml"]}},
 "laws":laws,"requirements":reqs,
 "objective":{"minimize":obj,"unit":"EUR","why":"10-year cost: chambers + 10 x (electricity + lamp replacement)"},
 "catalog":cat}
json.dump(brick,open(out,"w"),indent=1)
print("wrote",out)
