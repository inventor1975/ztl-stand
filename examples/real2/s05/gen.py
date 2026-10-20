import json
def brick(find, req, vth, tfrom, tto, title, rp=True, extra=None):
    b={
 "stand":"ztl-stand/1",
 "quantities":{
  "T":{"role":"given","value":"300","unit":"K","ground":"battery pack NTC temperature"},
  "T25":{"role":"given","value":"298.15","unit":"K","ground":"25 C in kelvin"},
  "beta":{"role":"given","value":"3435","unit":"K","ground":"NTC 10k beta(25/85C), TI SPVA059 ex.1"},
  "R25":{"role":"given","value":"10000","unit":"ohm","ground":"NTC 10k at 25C, TI SPVA059 ex.1"},
  "Ib":{"role":"given","range":["76.8","83.2"],"unit":"uA","ground":"BQ25190 TS bias current min/max (SPVA059 sec 4.2)"},
  "Vth":{"role":"given","range":vth,"unit":"V","ground":"BQ25190 TS threshold min/max (SPVA059 sec 4.2)"},
  "Rn":{"role":"derived","unit":"ohm"},
  "Vts":{"role":"derived","unit":"V"}},
 "slots":{"RP":{"from":["rp_12k_1pct"]}},
 "laws":[
  {"zfl":"Rn == R25*exp(beta*(1/T - 1/T25))","source":"beta equation (SPVA059 eq.1)"},
  {"zfl":"Vts == Ib*RP.R*Rn/(RP.R + Rn)","source":"TS pin: bias current into RP parallel (RS=0 + NTC) (SPVA059 eq.4)"}],
 "requirements":[{"quantity":"Vts","op":req,"value":"Vth","why":title}],
 "find":find,
 "catalog":{"rp_12k_1pct":{"items":[{"R":{"value":"12000","tolerance":"0.01"}}],"fields":{"R":{"unit":"ohm"}},"ground":"SPVA059 ex.1: RP = 12k E96 1%, RS = 0 ohm (short)"}}}
    return b
cfgs={
 "brick.json":(dict(largest=None),),
}
def mk(name, kind, req, vth, frm, to, title):
    b=brick({kind:"T","from":frm,"to":to,"precision":"1/100"},req,vth,frm,to,title)
    json.dump(b,open(name,"w"),indent=1)
# hot, highest entry temp: T guaranteed tripped (Vts <= Vth_min) on [a, 330 K]; smallest a
mk("brick.json","smallest","<=",["272/1000","280/1000"],"305","333.15","HOT trip is guaranteed for every NTC temperature from a up to 60 C: Vts below the lowest HOT threshold")
# hot, lowest entry temp: no trip (Vts >= Vth_max) on [from a], largest
mk("brick_hot_low.json","largest",">=",["272/1000","280/1000"],"298.15","325","no HOT trip for any NTC temperature from 25 C up to a: Vts above the highest HOT threshold")
# cold, highest entry: Vts >= Vth_max guaranteed tripped on [from, a], largest
mk("brick_cold_high.json","largest",">=",["576/1000","584/1000"],"263.15","298.15","COLD trip is guaranteed for every NTC temperature from -10 C up to a")
# cold, lowest entry: no trip, Vts <= Vth_min on [a, 25..] smallest
mk("brick_cold_low.json","smallest","<=",["576/1000","584/1000"],"263.15","298.15","no COLD trip for any NTC temperature from a up to 25 C")
