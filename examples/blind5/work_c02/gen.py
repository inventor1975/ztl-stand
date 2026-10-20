import json, sys
Sn=[400,630,800,1000,1250,1600]; uk=[4,4,6,6,6,6]
cls={
 "S":dict(P0=[650,860,1000,1150,1350,1650],Pk=[4600,6500,7600,9500,11000,14000],pr=[5.8,7.4,8.8,10.2,12.4,15.5],m=[1150,1650,2000,2350,2900,3600]),
 "L":dict(P0=[430,600,700,770,950,1150],Pk=[4600,6000,7000,9000,10500,13500],pr=[6.9,8.8,10.5,12.0,14.6,18.0],m=[1240,1780,2160,2540,3130,3890]),
 "A":dict(P0=[190,260,300,340,400,480],Pk=[4800,6700,7900,9800,11500,14500],pr=[8.4,10.8,12.8,14.6,17.5,22.0],m=[1380,1980,2400,2820,3480,4320]),
}
def s(x): return str(x)
catalog={}
names={"S":"cls_S_standard","L":"cls_L_lowloss","A":"cls_A_amorphous"}
for c,d in cls.items():
    items=[]
    for i in range(6):
        items.append({"Sn":s(Sn[i]),"uk":s(uk[i]),"P0":s(d["P0"][i]),"Pk":s(d["Pk"][i]),"price":s(d["pr"][i]),"mass":s(d["m"][i]),"cls":c})
    catalog[names[c]]={"items":items,"ground":"fictional catalog of problem 2",
      "fields":{"Sn":{"unit":"kW"},"uk":{"unit":"%"},"P0":{"unit":"W"},"Pk":{"unit":"W"},"price":{"unit":"kEUR"},"mass":{"unit":"kg"}}}
catalog["banks"]={"items":[{"Qc":"0","price":"0","name":"none"},{"Qc":"100","price":"1.2","name":"C100"},{"Qc":"150","price":"1.7","name":"C150"},{"Qc":"200","price":"2.2","name":"C200"}],
  "fields":{"Qc":{"unit":"kW"},"price":{"unit":"kEUR"}}}
seas={"w":("winter","2184","520","600","0.80","0.86"),"sp":("spring","2208","400","470","0.82","0.88"),
      "su":("summer","2208","330","400","0.82","0.88"),"au":("autumn","2160","430","500","0.80","0.86")}
q={}
define={}
laws=[];reqs=[]
for k,(n,h,p0,p1,f0,f1) in seas.items():
    q["h"+k]={"role":"given","value":h,"unit":"h","why":n+" hours per year"}
    q["P"+k]={"role":"given","range":[p0,p1],"unit":"kW","why":n+" active load, year 1"}
    q["pf"+k]={"role":"given","range":[f0,f1],"unit":"","why":n+" uncorrected power factor"}
    define["Q"+k]=f"P{k}*sqrt(1 - pf{k}^2)/pf{k}"
q["Pn"]={"role":"given","range":["60","80"],"unit":"kW","why":"summer night light load"}
q["pfn"]={"role":"given","range":["0.80","0.86"],"unit":"","why":"summer night pf"}
define["Qn"]="Pn*sqrt(1 - pfn^2)/pfn"
q["Tar"]={"role":"given","range":["0.09","0.14"],"unit":"EUR/kWh","why":"loss energy tariff, constant over 30 years"}
q["kb"]={"role":"given","value":"2.5","unit":"W/kW","why":"bank dissipation 2.5 W per kvar (kvar written as kW)"}
q["Mmax"]={"role":"given","value":"3000","unit":"kg","why":"floor loading"}
# discount/growth sums
define["A0"]="(1 - pow(1/1.03, 30))/(1 - 1/1.03)/1.03"
define["A1"]="(1 - pow(1.012/1.03, 30))/(1 - 1.012/1.03)/1.03"
define["A2"]="(1 - pow(1.012*1.012/1.03, 30))/(1 - 1.012*1.012/1.03)/1.03"
define["g30"]="pow(1.012, 29)"
define["rr"]="T.Pk/T.Sn"
define["xx"]="sqrt(T.uk^2 - rr^2)"
for k in seas:
    q["L"+k]={"role":"derived","unit":"W"}
    q["LY"+k]={"role":"derived","unit":"W"}
    q["S30"+k]={"role":"derived","unit":"kW"}
    q["dU30"+k]={"role":"derived","unit":"%"}
    laws.append({"zfl":f"L{k} == T.P0 + T.Pk*(P{k}^2 + (Q{k} - B.Qc)^2)/T.Sn^2 + kb*B.Qc","source":"seasonal loss P0+Pk(S/Sn)^2+2.5Qc, year 1"})
    laws.append({"zfl":f"LY{k} == A0*(T.P0 + kb*B.Qc) + T.Pk/T.Sn^2*(A2*(P{k}^2 + Q{k}^2) - 2*A1*Q{k}*B.Qc + A0*B.Qc^2)","source":"sum over y of (loss_y/1.03^y); S_y^2 = g^2(P^2+Q^2) - 2 g Q Qc + Qc^2, g=1.012^(y-1) (hand algebra)"})
    laws.append({"zfl":f"S30{k} == sqrt((g30*P{k})^2 + (g30*Q{k} - B.Qc)^2)","source":"S = sqrt(P^2+(Q-Qc)^2), year 30"})
    laws.append({"zfl":f"dU30{k} == g30*P{k}/T.Sn*rr + (g30*Q{k} - B.Qc)/T.Sn*xx","source":"delta_U = p r + q x, year 30"})
    reqs.append({"quantity":"S30"+k,"op":"<=","value":"1.05*T.Sn","why":"R2 year-30 S <= 1.05 Sn, "+seas[k][0]})
    reqs.append({"quantity":"dU30"+k,"op":"<=","value":"3.8","why":"R3 year-30 voltage drop <= 3.8 %, "+seas[k][0]})
for n in ["E1","Ewt","PV","Tot","Mass"]: pass
q["E1"]={"role":"derived","unit":"kWh"}
q["Ewt"]={"role":"derived","unit":"kWh"}
q["PV"]={"role":"derived","unit":"kEUR"}
q["Tot"]={"role":"derived","unit":"kEUR"}
q["Mass"]={"role":"derived","unit":"kg"}
q["dUn"]={"role":"derived","unit":"%"}
laws.append({"zfl":"E1 == "+" + ".join(f"h{k}*L{k}" for k in seas),"source":"annual loss energy year 1 = sum hours*W"})
laws.append({"zfl":"Ewt == "+" + ".join(f"h{k}*LY{k}" for k in seas),"source":"discounted loss energy sum_y E_y/1.03^y"})
laws.append({"zfl":"PV == Tar*Ewt","source":"present value of losses = tariff * discounted energy"})
laws.append({"zfl":"Tot == T.price + B.price + PV","source":"lifetime cost"})
laws.append({"zfl":"Mass == T.mass","source":"catalog mass"})
laws.append({"zfl":"dUn == Pn/T.Sn*rr + (Qn - B.Qc)/T.Sn*xx","source":"delta_U = p r + q x, summer night, year 1"})
reqs=[{"quantity":"E1","op":"<=","value":"32000","why":"R1 year-1 annual loss energy"}]+reqs+[
 {"quantity":"dUn","op":">=","value":"-0.8","why":"R4 summer-night voltage rise"},
 {"quantity":"Mass","op":"<=","value":"Mmax","why":"R5 mass"}]
brick={"stand":"universal-stand/1","quantities":q,
 "slots":{"T":{"from":list(names.values())},"B":{"from":["banks"]}},
 "define":define,"laws":laws,"requirements":reqs,
 "objective":{"minimize":"Tot","case":"worst","unit":"kEUR","why":"minimum worst-case lifetime cost"},
 "catalog":catalog}
json.dump(brick,open(sys.argv[1],"w"),indent=1)
