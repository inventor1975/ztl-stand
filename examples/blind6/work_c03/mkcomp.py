import json,sys
sys.path.insert(0,'.')
from gen import brick
b=brick()
# --- PACK component: cell + Np + heater, input Ta, outputs
pk={"stand":"ztl-stand/1","why":"cell pack with optional heater: resistance, OCV, usable energy, cell current limit at the given ambient",
 "interface":{"inputs":{"Ta":{"assume":["233.15","313.15"],"bands":"arriving"}},
              "outputs":["Rpk","V0","Rc","E","Imaxc"]}}
q=b["quantities"]
keep=["Ta","Tref","Voc","a","B","cf","kc","ki","kfl","Vn","dod"]
pk["quantities"]={k:q[k] for k in keep}
pk["quantities"]["Ta"]={"role":"given","value":"263.15","unit":"K"}
pk["quantities"]["V0"]={"role":"derived","unit":"V"}
pk["quantities"]["Rc"]={"role":"derived","unit":"mohm"}
pk["quantities"]["Rpk"]={"role":"derived","unit":"mohm"}
pk["quantities"]["E"]={"role":"derived","unit":"Wh"}
pk["quantities"]["Imaxc"]={"role":"derived","unit":"A"}
pk["slots"]={"CELL":{"from":["cells"]},"NP":{"from":["np"]},"HT":{"from":["heater"]}}
pk["define"]={"Tc":"Ta + HT.dTh","kT":"max(kfl, 1 - kc*(Tref - Tc))"}
pk["laws"]=[
 {"zfl":"Rc == a*CELL.R25*exp(B*(1/Tc - 1/Tref))","source":"Arrhenius cell resistance"},
 {"zfl":"Rpk == 5*Rc/NP.N","source":"5 series groups of Np parallel cells"},
 {"zfl":"V0 == 5*Voc","source":"5 series groups"},
 {"zfl":"E == 5*NP.N*CELL.Cap*cf*Vn*dod*kT - HT.Eh","source":"usable energy"},
 {"zfl":"Imaxc == CELL.Imax25*(1 - ki*(Tref - Tc))","source":"cell current limit at temperature"}]
pk["requirements"]=[]
pk["objective"]={"minimize":"5*NP.N*CELL.price + HT.price","unit":"EUR"}
pk["catalog"]={k:b["catalog"][k] for k in("cells","np","heater")}
h=pk["catalog"]["heater"]; h=json.loads(json.dumps(h)); h["items"].insert(0,{"dTh":{"value":"0"},"Eh":{"value":"0"},"price":"0","name":"none"}); pk["catalog"]["heater"]=h
json.dump(pk,open("pack.json","w"),indent=1)
# --- system
sysb={"stand":"ztl-stand/1","why":"saw chain: PACK component -> BMS + constant-power controller in the system laws",
 "components":{"PK":{"file":"pack.json"}},
 "connect":{"PK.Ta":"Ta"},
 "quantities":{k:q[k] for k in("Ta","P","kb","Rw")},
 "slots":{"BMS":b["slots"]["BMS"]},
 "laws":[
  {"zfl":"Rtot == PK.Rpk + BMS.R*kb + Rw","source":"series resistances"},
  {"zfl":"Vt == (PK.V0 + sqrt(max(0, PK.V0*PK.V0 - 4*Rtot*P)))/2","source":"constant power load"},
  {"zfl":"I == P/Vt","source":"constant power"},
  {"zfl":"Icell == I/PK.NP.N","source":"parallel cells share current"},
  {"zfl":"Vcell == PK.V0/5 - Icell*PK.Rc","source":"cell terminal voltage"},
  {"zfl":"Runtime == PK.E/P","source":"energy/power"},
  {"zfl":"Imarg == PK.Imaxc - Icell","source":"cell current limit margin"}],
 "requirements":b["requirements"],
 "objective":{"minimize":"PK.cost + BMS.price","unit":"EUR"},
 "catalog":{"bms":b["catalog"]["bms"]}}
for k in("Rtot","Vt","I","Icell","Vcell","Runtime","Imarg"):
    sysb["quantities"][k]=q[k] if k in q else {"role":"derived"}
sysb["quantities"]["Ta"]=dict(q["Ta"])
json.dump(sysb,open("system.json","w"),indent=1)
