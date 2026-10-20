import json, sys
def brick(Ta="263.15", find=None, cells=None, bms=None, nps=(1,4), heater_opt=True, report=None):
    cells_all = [("P15","1.5","11","30","2.4"),("H20","2.0","16","22","2.0"),("H25","2.5","17","20","2.9"),
                 ("E25","2.5","24","12","1.7"),("E30","3.0","33","9","1.6")]
    bms_all = [("M30","30","9.0","3.2"),("M40","40","6.0","4.5"),("M60","60","3.5","7.5"),("M80","80","2.5","11.0")]
    cells = [c for c in cells_all if cells is None or c[0] in cells]
    bms = [b for b in bms_all if bms is None or b[0] in bms]
    Q = {
     "Ta":   {"role":"given","value":Ta,"unit":"K","why":"ambient; -10 degC = 263.15 K (K because the exponential needs an absolute temperature)"},
     "Tref": {"role":"given","value":"298.15","unit":"K","why":"25 degC reference"},
     "P":    {"role":"given","range":["540","640"],"unit":"W","why":"controller input power (constant-power load)"},
     "Voc":  {"role":"given","range":["3.46","3.52"],"unit":"V","why":"cell OCV at 20 % charge left"},
     "a":    {"role":"given","range":["1.00","1.10"],"unit":"","why":"ageing factor on cell resistance"},
     "B":    {"role":"given","range":["2000","2400"],"unit":"K","why":"temperature constant, one value for all cells"},
     "cf":   {"role":"given","range":["0.97","1.03"],"unit":"","why":"actual / nominal capacity"},
     "kb":   {"role":"given","range":["1.0","1.2"],"unit":"","why":"BMS resistance / nominal"},
     "Rw":   {"role":"given","value":"4","unit":"mohm","why":"wiring and connector resistance, fixed"},
     "kc":   {"role":"given","value":"0.007","unit":"1/K","why":"cold capacity slope"},
     "ki":   {"role":"given","value":"0.012","unit":"1/K","why":"cell current-limit slope"},
     "kfl":  {"role":"given","value":"0.5","unit":"","why":"cold capacity factor floor"},
     "Vn":   {"role":"given","value":"3.6","unit":"V","why":"nominal cell voltage used for energy"},
     "dod":  {"role":"given","value":"0.8","unit":"","why":"usable fraction of the charge"},
     "Rtot": {"role":"derived","unit":"mohm"},
     "Rcell":{"role":"derived","unit":"mohm"},
     "Vt":   {"role":"derived","unit":"V"},
     "I":    {"role":"derived","unit":"A"},
     "Icell":{"role":"derived","unit":"A"},
     "Vcell":{"role":"derived","unit":"V"},
     "E":    {"role":"derived","unit":"Wh"},
     "Runtime":{"role":"derived","unit":"min"},
     "Imarg":{"role":"derived","unit":"A"},
    }
    d = {
     "stand":"ztl-stand/1",
     "why":"blind6 problem 3: cordless saw, cell + Np + BMS + optional heater, cold end",
     "quantities":Q,
     "slots":{"CELL":{"from":["cells"]},"NP":{"from":["np"]},"BMS":{"from":["bms"]},
              "HT":{"from":["heater"],"optional":heater_opt}},
     "define":{
       "Tc":"Ta + HT.dTh",
       "V0":"5*Voc",
       "kT":"max(kfl, 1 - kc*(Tref - Tc))",
       "Imaxc":"CELL.Imax25*(1 - ki*(Tref - Tc))"},
     "laws":[
      {"zfl":"Rcell == a*CELL.R25*exp(B*(1/Tc - 1/Tref))","source":"Arrhenius cell resistance (problem statement)"},
      {"zfl":"Rtot == 5*Rcell/NP.N + BMS.R*kb + Rw","source":"5 series groups of Np parallel cells + BMS + wiring"},
      {"zfl":"Vt == (V0 + sqrt(max(0, V0*V0 - 4*Rtot*P)))/2","source":"constant-power load on a source V0 with series R: larger root of Vt*(V0-Vt)/R = P","valid":"V0*V0 > 4*Rtot*P"},
      {"zfl":"I == P/Vt","source":"constant power load"},
      {"zfl":"Icell == I/NP.N","source":"Np parallel cells share the pack current"},
      {"zfl":"Vcell == Voc - Icell*Rcell","source":"cell terminal voltage under load"},
      {"zfl":"E == 5*NP.N*CELL.Cap*cf*Vn*dod*kT - HT.Eh","source":"usable energy, cold-capacity factor, heater draw"},
      {"zfl":"Runtime == E/P","source":"runtime = energy / power"},
      {"zfl":"Imarg == Imaxc - Icell","source":"cell current limit at temperature minus cell current"},
     ],
     "requirements":[
      {"quantity":"Vt","op":">=","value":"14.2","why":"R1 controller shut-down threshold"},
      {"quantity":"Runtime","op":">=","value":"9","why":"R2"},
      {"quantity":"I","op":"<=","value":"BMS.Irat","why":"R3 BMS rating"},
      {"quantity":"Imarg","op":">=","value":"0","why":"R4 cell current <= Imax(Tc)"},
      {"quantity":"Vcell","op":">=","value":"2.9","why":"R5 cell cut-off"},
     ],
     "objective":{"minimize":"5*NP.N*CELL.price + BMS.price + HT.price","why":"pack price"},
     "catalog":{
      "cells":{"items":[{"Cap":{"value":c[1]},"R25":{"value":c[2]},"Imax25":{"value":c[3]},"price":c[4],"name":c[0]} for c in cells],
               "fields":{"Cap":{"unit":"Ah"},"R25":{"unit":"mohm"},"Imax25":{"unit":"A"},"price":{"unit":"EUR"}}},
      "np":{"integers":{"field":"N","from":str(nps[0]),"to":str(nps[1]),"unit":""}},
      "bms":{"items":[{"Irat":{"value":b[1]},"R":{"value":b[2]},"price":b[3],"name":b[0]} for b in bms],
             "fields":{"Irat":{"unit":"A"},"R":{"unit":"mohm"},"price":{"unit":"EUR"}}},
      "heater":{"items":[{"dTh":{"range":["9","13"]},"Eh":{"value":"3.5"},"price":"4.5","name":"film"}],
                "fields":{"dTh":{"unit":"K"},"Eh":{"unit":"Wh"},"price":{"unit":"EUR"}}},
     }}
    if report: d["report"]=report
    if find: d["find"]=find
    return d
if __name__=="__main__":
    name=sys.argv[1]
    kw=eval(sys.argv[2]) if len(sys.argv)>2 else {}
    json.dump(brick(**kw), open(name,"w"), indent=1)
