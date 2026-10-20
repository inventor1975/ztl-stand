import json,sys
def base(tol=False):
    q={
     "P1":{"role":"given","value":"101325","unit":"Pa","why":"1 atm, slide 12"},
     "P2":{"role":"given","value":"607950","unit":"Pa","why":"6 atm, slide 12"},
     "dz":{"role":"given","value":"10","unit":"m","why":"Z2-Z1 = 10 m, slide 12"},
     "L":{"role":"given","value":"200","unit":"m","why":"pipe length, slide 12"},
     "D":{"role":"given","value":"0.1","unit":"m","why":"pipe diameter, slide 12"},
     "eps":{"role":"given","value":"0.045","unit":"mm","why":"roughness, slide 12"},
     "RHO":{"role":"given","value":"1000","unit":"kg/m^3","why":"handwritten on slide 12"},
     "mu":{"role":"given","value":"0.000798","unit":"Pa*s","why":"handwritten on slide 12 (0.798e-3 kg/(m s))"},
     "Q":{"role":"derived","unit":"m^3/s","search":["0.005","0.1"],"why":"operating flow: pump curve meets system curve"},
     "Vel":{"role":"derived","unit":"m/s","why":"mean velocity in the 0.1 m pipe"},
     "H":{"role":"derived","unit":"m","why":"pump head at the operating point"},
     "Pw":{"role":"derived","unit":"kW","why":"brake power rho g H Q / eta"},
    }
    return q
brick={
 "stand":"ztl-stand/1",
 "quantities":base(),
 "slots":{"PUMP":{"from":["pumps"]}},
 "define":{
   "AR":"pi*D*D/4",
   "V":"Q/AR",
   "RE":"RHO*V*D/mu",
   "FH":"1/pow(1.8*log10(pow(eps/(3.7*D),1.11) + 6.9/RE),2)"},
 "laws":[
  {"zfl":"PUMP.H0 - PUMP.c*V*V == dz + (P2 - P1)/(RHO*g0) + FH*L/D*V*V/(2*g0)",
   "source":"BYU ChEn 374 lecture 30 slide 12: Hp = Hreq = dP/(rho g) + dZ + (f L/D) v^2/2g; f by Haaland (inferred, reproduces the slide's Hreq(10 m/s) = 232.223)"},
  {"zfl":"Vel == V","source":"mean velocity = Q/A"},
  {"zfl":"H == PUMP.H0 - PUMP.c*Vel*Vel","source":"slide 12 pump curve Hp = 200 m - v^2 s^2/m"},
  {"zfl":"Pw == RHO*g0*Q*H/PUMP.eta","source":"slide 12 bhp = rho g H Q / eta"}],
 "requirements":[
  {"quantity":"Vel","op":"within","value":["7.1305","7.1315"],"why":"published v_op = 7.131 m/s (4 digits, +-half of last digit)"},
  {"quantity":"H","op":"within","value":["149.1485","149.1495"],"why":"published H_op = 149.149 m (+-half of last digit)"},
  {"quantity":"Q","op":"within","value":["0.0545","0.0555"],"why":"published flow 0.055 m3/s (2 digits, +-half of last digit)"},
  {"quantity":"Pw","op":"within","value":["89.345","89.355"],"why":"published bhp = 89.35 kW (+-half of last digit)"}],
 "catalog":{"pumps":{"ground":"slide 12 pump curve","items":[
   {"H0":{"value":"200"},"c":{"value":"1"},"eta":{"value":"0.9"},"grade":"BYU slide pump"}],
   "fields":{"H0":{"unit":"m"},"c":{"unit":"s^2/m"},"eta":{"unit":""}}}},
 "report":"all"}
json.dump(brick,open("brick.json","w"),indent=1)
# variant: only the two numbers the slide reproduces
b2=json.loads(json.dumps(brick)); b2["requirements"]=[brick["requirements"][0],brick["requirements"][1]]
json.dump(b2,open("brick_vH.json","w"),indent=1)
# variant: honest uncertainty the slide leaves out, windows +-3% of published
b3=json.loads(json.dumps(brick))
b3["quantities"]["mu"]={"role":"given","range":["0.000653","0.001002"],"unit":"Pa*s","why":"water 20..40 C (ASSUMED: slide fixes 30 C)"}
b3["quantities"]["D"]={"role":"given","value":"0.1","tolerance":"0.01","unit":"m","why":"ASSUMED +-1% on the inner diameter"}
b3["quantities"]["eps"]={"role":"given","range":["0.03","0.06"],"unit":"mm","why":"ASSUMED roughness spread around 0.045"}
b3["requirements"]=[
  {"quantity":"Vel","op":"within","value":["6.917","7.345"],"why":"published 7.131 m/s +-3%"},
  {"quantity":"H","op":"within","value":["144.67","153.62"],"why":"published 149.149 m +-3%"},
  {"quantity":"Pw","op":"<=","value":"92","why":"brake power at most ~3% above the printed 89.35 kW"}]
json.dump(b3,open("brick_tol.json","w"),indent=1)
