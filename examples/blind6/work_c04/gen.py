import json, copy
ins=[("MW-30 mineral wool",30,"0.040","0.30","7.5"),("MW-50 mineral wool",50,"0.040","0.30","11.0"),
     ("PIR-30 foam",30,"0.026","0.08","13.0"),("PIR-40 foam",40,"0.026","0.08","16.0"),("PIR-50 foam",50,"0.026","0.08","19.5")]
cab=[("T10","10","4.8"),("T15","15","6.2"),("T20","20","8.0"),("T30","30","11.5")]
base={
 "stand":"ztl-stand/1",
 "why":"blind6 problem 4: frost protection of a 140 m pipe run, insulation + self-regulating heat-trace cable",
 "quantities":{
  "Ta":{"role":"given","value":"-40","unit":"C","why":"design ambient temperature","ground":"problem statement"},
  "Tp":{"role":"given","value":"3","unit":"C","why":"pipe held at 3 C","ground":"problem statement"},
  "r1":{"role":"given","value":"45","unit":"mm","why":"pipe outer radius","ground":"problem statement"},
  "L":{"role":"given","value":"140","unit":"m","why":"run length","ground":"problem statement"},
  "fa":{"role":"given","value":"1.3","unit":"","why":"supports and valves allowance","ground":"problem laws"},
  "alpha":{"role":"given","value":"0.0018","unit":"1/C","why":"conductivity temperature coefficient","ground":"problem laws"},
  "lam":{"role":"given","value":"0.012","unit":"1/C","why":"cable output temperature coefficient","ground":"problem laws"},
  "V230":{"role":"given","value":"230","unit":"V","why":"rating voltage of P10","ground":"problem laws"},
  "Pcap":{"role":"given","value":"24","unit":"W/m","why":"liner cap R2","ground":"problem R2"},
  "Dmax":{"role":"given","value":"180","unit":"mm","why":"rack clearance R3","ground":"problem R3"},
  "V":{"role":"given","range":["207","253"],"unit":"V","why":"supply voltage, one value for the whole run","ground":"problem uncertain data"},
  "ho":{"role":"given","range":["8","25"],"unit":"W/(m^2*K)","why":"wind dependent outer film coefficient","ground":"problem uncertain data"},
  "q":{"role":"derived","unit":"W/m"},
  "Pc":{"role":"derived","unit":"W/m"},
  "margin":{"role":"derived","unit":"W/m"},
  "D2":{"role":"derived","unit":"mm"}
 },
 "slots":{"INS":{"from":["insulation"]},"CAB":{"from":["cable"]}},
 "define":{"r2":"r1 + INS.t","Tm":"(Tp + Ta)/2","kk":"INS.k10*(1 + alpha*(Tm - 10))*(1 + INS.w)"},
 "laws":[
  {"zfl":"q == fa*(Tp - Ta)/(ln(r2/r1)/(2*pi*kk) + 1/(2*pi*r2*ho))","source":"heat loss per metre, cylindrical insulation + outer film, allowance 1.3"},
  {"zfl":"Pc == CAB.P10*(1 + lam*(10 - Tp))*pow(V/V230, 1.6)","source":"self-regulating cable output at Tp and supply V"},
  {"zfl":"margin == Pc - q","source":"R1 as one quantity: cable output minus heat loss"},
  {"zfl":"D2 == 2*r2","source":"outer diameter of the insulated pipe"}
 ],
 "requirements":[
  {"quantity":"margin","op":">=","value":"0","why":"R1 freeze protection: output at the lowest supply voltage >= heat loss (V ranges over the box, so the worst V is covered)"},
  {"quantity":"Pc","op":"<=","value":"Pcap","why":"R2 liner protection: output at the highest supply voltage <= 24 W/m"},
  {"quantity":"D2","op":"<=","value":"Dmax","why":"R3 rack clearance"}
 ],
 "objective":{"minimize":"(INS.price + CAB.price)*L","unit":"EUR","why":"minimum price of insulation + cable over the 140 m run"},
 "catalog":{
  "insulation":{"items":[{"name":n,"t":{"value":str(t)},"k10":{"value":k},"w":{"range":["0",w]},"price":p} for n,t,k,w,p in ins],
     "ground":"problem table","fields":{"t":{"unit":"mm"},"k10":{"unit":"W/(m*K)"},"w":{"unit":""},"price":{"unit":"EUR/m"}}},
  "cable":{"items":[{"name":n,"P10":{"value":p},"price":pr} for n,p,pr in cab],
     "ground":"problem table","fields":{"P10":{"unit":"W/m"},"price":{"unit":"EUR/m"}}}
 }
}
dec=copy.deepcopy(base)
json.dump(dec,open("c04_decide.json","w"),indent=1)
f=copy.deepcopy(base)
f["find"]={"smallest":"Ta","from":"-45","to":"-35","precision":"0.01"}
f["quantities"]["Ta"]["why"]="design ambient temperature; placeholder, searched by find"
json.dump(f,open("../c04.json","w"),indent=1)
