import json,sys
pipes=[('H200-10','0.176',140,100,18),('H225-10','0.198',140,100,23),('H250-10','0.220',140,100,29),('H315-10','0.277',140,100,45),('H355-10','0.312',140,100,57),
('H200-16','0.163',140,160,24),('H225-16','0.184',140,160,30),('H250-16','0.204',140,160,37),('H315-16','0.257',140,160,58),('H355-16','0.290',140,160,73),('H400-16','0.327',140,160,92),
('S250','0.250',120,300,70),('S300','0.300',120,300,95),('S350','0.350',120,300,128)]
tur=[('T1','0.0225',[.70,.78,.82,.85,.86,.85],'0.2',58000),('T2','0.03',[.66,.75,.80,.84,.86,.86],'0.2',74000),('T3','0.03',[.55,.65,.72,.78,.80,.79],'0.2',42000),
('T4','0.042',[.55,.65,.72,.78,.80,.79],'0.2',56000),('T5','0.036',[.62,.62,.62,.82,.89,.90],'0.4',96000)]
frs=['0.05','0.15','0.25','0.25','0.20','0.10']; qrs=['0.28','0.20','0.14','0.10','0.07','0.04']
from fractions import Fraction as F
q={}
def g(v,u,why=None,**k):
    d={"role":"given","value":v,"unit":u}; d.update(k)
    if why: d["why"]=why
    return d
q["HG"]=g("85","m","gross head")
q["LU"]=g("240","m"); q["LL"]=g("180","m")
q["HSU"]=g("40","m","max static head upper section"); q["HSL"]=g("85","m","max static head lower section")
q["SURGE"]=g("1.3","","surge allowance on pressure head")
q["Q0"]=g("1","m^3/s","unit flow, makes HW powers dimensionless"); q["D0"]=g("1","m","unit diameter")
q["ETAG"]=g("0.93","","drive and generator efficiency"); q["G"]=g("9.81","m*s^-2"); q["RHO"]=g("1000","kg/m^3")
q["HY"]=g("8760","h","hours per year")
q["f"]=g("1","","common river-flow factor; set per mode")
for i in range(6):
    q[f"FR{i+1}"]=g(frs[i],"","fraction of the year"); q[f"QR{i+1}"]=g(qrs[i],"m^3/s","river flow, nominal (flow-duration)")
q["QF"]={"role":"derived","unit":"m^3/s","search":["0.005","0.45"],"why":"turbine full flow: QF = K sqrt(Hnet(QF)), written squared (QF*QF = K2*Hnet)"}
for i in range(1,7):
    for n,u in [("Q","m^3/s"),("PH",""),("ET",""),("HN","m"),("P","kW")]:
        q[f"{n}{i}"]={"role":"derived","unit":u}
for n,u in [("E","MWh"),("PPK","kW"),("VU","m/s"),("VL","m/s"),("MU","m"),("ML","m")]:
    q[n]={"role":"derived","unit":u}
define={"AU":"pi*UP.D*UP.D/4","AL":"pi*LO.D*LO.D/4",
 "KU":"10.67*LU/(pow(UP.C,1.852)*pow(UP.D/D0,4.87))","KL":"10.67*LL/(pow(LO.C,1.852)*pow(LO.D/D0,4.87))"}
for k,(a,b) in enumerate([("e03","e02"),("e04","e03"),("e06","e04"),("e08","e06"),("e10","e08")]):
    d=["0.1","0.1","0.2","0.2","0.2"][k]
    define[f"SL{k+1}"]=f"(TB.{a}-TB.{b})/{d}"
def hn(i): return f"HG - KU*pow(Q{i}/Q0,1.852) - KL*pow(Q{i}/Q0,1.852)"
laws=[{"zfl":"QF*QF == TB.K2*(HG - KU*pow(QF/Q0,1.852) - KL*pow(QF/Q0,1.852))","source":"turbine full flow QF=K sqrt(Hnet(QF)) squared, Hnet = Hg - HW loss(upper) - HW loss(lower)"}]
for i in range(1,7):
    laws+= [
     {"zfl":f"Q{i} == min(f*QR{i}, QF)","source":"flow used = min(river flow, turbine full flow)"},
     {"zfl":f"PH{i} == Q{i}/QF","source":"flow fraction"},
     {"zfl":f"HN{i} == {hn(i)}","source":"net head at the flow used (Hazen-Williams, both sections)"},
     {"zfl":f"ET{i} == if(PH{i} < TB.phimin, 0, if(PH{i} < 0.3, TB.e02 + SL1*(PH{i}-0.2), if(PH{i} < 0.4, TB.e03 + SL2*(PH{i}-0.3), if(PH{i} < 0.6, TB.e04 + SL3*(PH{i}-0.4), if(PH{i} < 0.8, TB.e06 + SL4*(PH{i}-0.6), TB.e08 + SL5*(PH{i}-0.8))))))","source":"turbine efficiency curve, linear between listed fractions, zero below phimin (shut down)"},
     {"zfl":f"P{i} == ET{i}*ETAG*RHO*G*Q{i}*HN{i}","source":"electric power"}]
laws+=[{"zfl":"E == FR1*HY*P1 + FR2*HY*P2 + FR3*HY*P3 + FR4*HY*P4 + FR5*HY*P5 + FR6*HY*P6","source":"annual energy = sum fraction x 8760 h x P"},
 {"zfl":"PPK == max(max(max(P1,P2),max(P3,P4)),max(P5,P6))","source":"peak electric power over the flow-duration points"},
 {"zfl":"VU == QF/AU","source":"velocity at full turbine flow, upper section"},
 {"zfl":"VL == QF/AL","source":"velocity at full turbine flow, lower section"},
 {"zfl":"MU == UP.hmax - SURGE*HSU","source":"pressure margin upper: allowable head - 1.3 x max static head"},
 {"zfl":"ML == LO.hmax - SURGE*HSL","source":"pressure margin lower"}]
mode_f=lambda v:{"f":{"value":v}}
modes={"low river 0.85":{"quantities":mode_f("0.85"),"requirements":[{"quantity":"E","op":">=","value":"520","why":"R1 annual energy >= 520 MWh at factor 0.85"}]},
 "high river 1.15":{"quantities":mode_f("1.15"),"requirements":[
   {"quantity":"PPK","op":"<=","value":"125","why":"R2 grid connection limit 125 kW at factor 1.15"},
   {"quantity":"VU","op":"<=","value":"3.5","why":"R3 velocity upper section at full turbine flow"},
   {"quantity":"VL","op":"<=","value":"3.5","why":"R3 velocity lower section at full turbine flow"}]}}
reqs=[{"quantity":"MU","op":">=","value":"0","why":"R4 upper pipe allowable head >= 1.3 x 40 m"},{"quantity":"ML","op":">=","value":"0","why":"R4 lower pipe allowable head >= 1.3 x 85 m"}]
cat_p={"ground":"manufacturer pipe list","items":[{"D":{"value":d},"C":str(c),"hmax":str(h),"price":str(p),"grade":n} for n,d,c,h,p in pipes],
  "fields":{"D":{"unit":"m"},"C":{"unit":""},"hmax":{"unit":"m"},"price":{"unit":"EUR/m"}}}
items=[]
for n,K,e,pm,p in tur:
    K2=str(F(K)**2)
    it={"K2":K2,"phimin":pm,"price":str(p),"grade":n}
    for nm,v in zip(["e02","e03","e04","e06","e08","e10"],e): it[nm]=str(F(str(v)))
    items.append(it)
cat_t={"ground":"turbine data sheet","items":items,"fields":{"K2":{"unit":"m^5/s^2"},"phimin":{"unit":""},"price":{"unit":"EUR"},**{k:{"unit":""} for k in ["e02","e03","e04","e06","e08","e10"]}}}
brick={"stand":"universal-stand/1","quantities":q,"slots":{"UP":{"from":["pipes"]},"LO":{"from":["pipes"]},"TB":{"from":["turbines"]}},
 "define":define,"laws":laws,"requirements":reqs,"modes":modes,
 "objective":{"minimize":"UP.price*LU + LO.price*LL + TB.price","why":"capital cost: pipe price x length for both sections + turbine"},
 "catalog":{"pipes":cat_p,"turbines":cat_t}}
if len(sys.argv)>1 and sys.argv[1]=="all": brick["report"]="all"
json.dump(brick,open("../c10.json" if len(sys.argv)<2 else "all.json","w"),indent=1)
