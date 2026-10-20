import json, sys
variant = sys.argv[1] if len(sys.argv)>1 else "main"
out = sys.argv[2] if len(sys.argv)>2 else "../c04.json"
T_HI = "3.8896"   # y/D = 0.938 -> t = sqrt(0.938/0.062) = 3.8896
T_LO = "0.01"
q = {}
def given(name, value, unit, why, **kw):
    d = {"role":"given","value":value,"unit":unit,"why":why}; d.update(kw); q[name]=d
given("H0","1.5","m","head of reach A: invert depth below ground")
given("LA","420","m","reach A length"); given("LB","380","m","reach B length")
given("Dref","200","mm","reference diameter of the pipe price law (D/200)")
given("Dm","1000","mm","trench diameter factor (1 + D/1000)")
given("c0","20","EUR/m","trench price constant")
given("c1","28","EUR/m^2","trench price per metre of mean depth")
given("Dmax","5","m","outfall depth limit")
given("hmax","0.70","", "storm depth ratio limit")
given("vmin","0.60","m/s","self-cleansing velocity")
for r,(qd,qp) in {"A":("6.5","22"),"B":("12","41")}.items():
    given("Q%sd"%r,qd,"L/s","dry-weather daily peak, reach "+r)
    given("Q%sp"%r,qp,"L/s","storm peak, reach "+r)
import os
CLAMP = bool(os.environ.get("CLAMP"))
defs = {}; laws = []; reqs = []
if CLAMP:
    given("Tc",T_HI,"","t at y/D = 0.938 (surcharge limit)")
    for r in "AB":
        D = ("DA.D" if r=="A" else "DB.D"); S = ("SA.S" if r=="A" else "SB.S")
        defs["th0"+r]="4*atan(Tc)"; defs["sn0"+r]="4*Tc*(1 - Tc*Tc)/((1 + Tc*Tc)*(1 + Tc*Tc))"
        defs["Af0"+r]="%s*%s/8*(th0%s - sn0%s)"%(D,D,r,r)
        defs["Rh0"+r]="%s/4*(1 - sn0%s/th0%s)"%(D,r,r)
        defs["K6"+r]="pow(Af0%s, 6)*pow(Rh0%s, 4)*pow(%s, 3)"%(r,r,S)
for r in "AB":
    for f,desc in (("d","dry"),("p","storm")):
        t = "t%s%s"%(r,f)
        q[t] = {"role":"derived","unit":"","search":[T_LO,T_HI],
                "why":"tan(theta/4) of the wetted segment, reach %s %s peak (theta = 4 atan t, y/D = t^2/(1+t^2), sin theta = 4t(1-t^2)/(1+t^2)^2)"%(r,desc)}
        th = "th%s%s"%(r,f); sn="sn%s%s"%(r,f); af="Af%s%s"%(r,f); rh="Rh%s%s"%(r,f)
        D = "D%s.D"%r; D = ("DA.D" if r=="A" else "DB.D"); S = ("SA.S" if r=="A" else "SB.S")
        defs[th] = "4*atan(%s)"%t
        defs[sn] = "4*%s*(1 - %s*%s)/((1 + %s*%s)*(1 + %s*%s))"%(t,t,t,t,t,t,t)
        defs[af] = "%s*%s/8*(%s - %s)"%(D,D,th,sn)
        defs[rh] = "%s/4*(1 - %s/%s)"%(D,sn,th)
        lhs = "pow(Q%s%s*M.n, 6)"%(r,f)
        if CLAMP:
            lhs = "min(%s, 99/100*K6%s)"%(lhs,r)
        laws.append({"zfl":"%s == pow(%s, 6)*pow(%s, 4)*pow(%s, 3)"%(lhs,af,rh,S),
                     "source":"Manning (SI) Q = (1/n) A_f R^(2/3) S^(1/2), raised to the 6th power (all sides positive, same root): (Q n)^6 = A_f^6 R^4 S^3; partly full circular pipe, reach %s %s peak; operating depth = root t"%(r,desc)})
        if CLAMP:
            g = "g%s%s"%(r,f)
            q[g] = {"role":"derived","unit":"","why":"flow / capacity at y/D = 0.938, sixth powers (<= 1: not surcharged), reach %s %s"%(r,desc)}
            laws.append({"zfl":"%s == pow(Q%s%s*M.n, 6)/K6%s"%(g,r,f,r),"source":"Manning capacity at y/D = 0.938: (Q n)^6 / (A^6 R^4 S^3 at y/D=0.938)"})
            reqs.append({"quantity":g,"op":"<=","value":"1","why":"not surcharged: Q <= flow at y/D = 0.938, reach %s %s"%(r,desc)})
        v = "v%s%s"%(r,f)
        q[v] = {"role":"derived","unit":"m/s","why":"velocity Q/A_f, reach %s %s"%(r,desc)}
        laws.append({"zfl":"%s == Q%s%s/%s"%(v,r,f,af),"source":"continuity v = Q/A_f"})
        if f=="p":
            y = "y%s"%r
            q[y] = {"role":"derived","unit":"","why":"depth ratio y/D at storm peak, reach "+r}
            laws.append({"zfl":"%s == %s*%s/(1 + %s*%s)"%(y,t,t,t,t),"source":"y/D = (1 - cos(theta/2))/2 = t^2/(1+t^2) with t = tan(theta/4)"})
            reqs.append({"quantity":y,"op":"<=","value":"hmax","why":"R2 storm depth ratio <= 0.70 reach "+r})
            reqs.append({"quantity":v,"op":"<=","value":"M.vmax","why":"R3 storm velocity <= material maximum, reach "+r})
        else:
            reqs.append({"quantity":v,"op":">=","value":"vmin","why":"R1 dry-weather velocity >= 0.60 m/s reach "+r})
q["dend"] = {"role":"derived","unit":"m","why":"invert depth at downstream end of B"}
laws.append({"zfl":"dend == H0 + SA.S*LA + SB.S*LB","source":"constant slope per reach: depth_down = depth_up + S*L; B starts where A ends"})
q["dDia"] = {"role":"derived","unit":"mm","why":"D_B - D_A"}
laws.append({"zfl":"dDia == DB.D - DA.D","source":"definition"})
reqs.append({"quantity":"dend","op":"<=","value":"Dmax","why":"R4 outfall depth <= 5.0 m"})
reqs.append({"quantity":"dDia","op":">=","value":"0","why":"R5 pipe never narrows downstream"})
# cost
for r,L,Dn,Sn,dav in (("A","LA","DA.D","SA.S","(H0 + SA.S*LA/2)"),("B","LB","DB.D","SB.S","(H0 + SA.S*LA + SB.S*LB/2)")):
    defs["cost"+r] = "%s*(M.k*%s + (c0 + c1*%s)*(1 + %s/Dm))"%(L,Dn.replace(".D",".pf"),dav,Dn)
cat = {
 "mats":{"ground":"problem statement material table","items":[
   {"name":"PVC","n":{"range":["0.0095","0.0115"]},"k":"62","vmax":"3.0"},
   {"name":"CONC","n":{"range":["0.012","0.016"]},"k":"48","vmax":"1.5"},
   {"name":"PE","n":{"range":["0.013","0.017"]},"k":"55","vmax":"2.5"}],
  "fields":{"n":{"unit":"s*m^(-1/3)"},"k":{"unit":"EUR/m"},"vmax":{"unit":"m/s"}}},
 "diam":{"ground":"problem statement diameter list; pf = (D/200 mm)^1.3 computed outside, 12 significant digits","items":[{"D":str(d),"pf":"%.12g"%((d/200)**1.3)} for d in (200,250,300,400,500)],"fields":{"D":{"unit":"mm"},"pf":{"unit":""}}},
 "slope":{"ground":"problem statement slope list {0,0.002,0.0035,0.005,0.008,0.012,0.02}; PRUNED BY HAND to 0.002..0.005: S=0 carries no flow (inadmissible by the statement), S>=0.008 breaks R4 (1.5+0.008*420=4.86 m already at the end of A, B needs S>0 -> >5.0 m; S_B>=0.008 -> 1.5+0.002*420+0.008*380=5.38>5.0)","items":[{"S":s} for s in ("0.002","0.0035","0.005")],"fields":{"S":{"unit":""}}}}
brick = {"stand":"universal-stand/1","quantities":q,
  "slots":{"M":{"from":["mats"]},"DA":{"from":["diam"]},"SA":{"from":["slope"]},"DB":{"from":["diam"]},"SB":{"from":["slope"]}},
  "define":defs,"laws":laws,"requirements":reqs,
  "objective":{"minimize":"(costA + costB)","unit":"kEUR","why":"total cost of both reaches (pipe + trench)"},
  "catalog":cat}
if variant=="where":
    brick["where"]=["SA.S > 0 and SB.S > 0","DB.D >= DA.D","H0 + SA.S*LA + SB.S*LB <= Dmax"]
elif variant=="slope":
    brick["where"]=["SA.S > 0 and SB.S > 0"]
import os
sub=os.environ.get("SUB")
if sub:
    m,ds,ss=sub.split("|")
    cat["mats"]["items"]=[i for i in cat["mats"]["items"] if i["name"] in m.split(",")]
    cat["diam"]["items"]=[i for i in cat["diam"]["items"] if i["D"] in ds.split(",")]
    cat["slope"]["items"]=[i for i in cat["slope"]["items"] if i["S"] in ss.split(",")]
if sub:
    cat["diam"]["ground"]="problem statement diameter list {200,250,300,400,500}, REDUCED BY THE AUTHOR to the listed items to fit the 900 s run limit; pf = (D/200 mm)^1.3 computed outside, 12 significant digits"
    cat["slope"]["ground"]="problem statement slope list {0,0.002,0.0035,0.005,0.008,0.012,0.02}, REDUCED BY THE AUTHOR to the listed items to fit the 900 s run limit"
    brick["note"]="c04 REDUCED catalog (author's choice, informed by an outside scan): the optimum below is optimal only inside it. The full-slope-pruned 675-design catalog is work_c04/full675.json (killed at 900 s after 300 designs, no EARNED)."
if os.environ.get("ALL"): brick["report"]="all"
json.dump(brick,open(out,"w"),indent=1)
