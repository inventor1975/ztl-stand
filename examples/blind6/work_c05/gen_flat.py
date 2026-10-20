import json
comp = [("K32",32,"6.8","8.0",6900),("K40",40,"6.8","8.0",8200),("K40M",40,"7.3","8.4",8900),("K50",50,"7.3","8.4",10600),("K50H",50,"8.0","9.0",11800)]
dry = [("D30",30,"0.40",1100),("D40",40,"0.35",1450),("D50",50,"0.30",1900),("D60",60,"0.30",2500)]
pipe = [(25,"6.0"),(32,"9.0"),(40,"14.0"),(50,"21.0"),(63,"33.0")]
G = lambda v,u,why: {"role":"given","value":v,"unit":u,"why":why}
q = {
 "QA": {"role":"given","range":["14","18"],"unit":"L/s","why":"tool A free-air flow, any value 14..18"},
 "QB": {"role":"given","range":["8.5","10.5"],"unit":"L/s","why":"tool B free-air flow, any value 8.5..10.5"},
 "leak": {"role":"given","range":["1.5","2.5"],"unit":"L/s","why":"system leakage, ONE value for the whole system"},
 "f": {"role":"given","range":["1.0","1.7"],"unit":"","why":"dryer filter fouling factor, one value"},
 "facfad": {"role":"given","range":["0.94","1.0"],"unit":"","why":"actual FAD = 0.94..1.00 of nominal (R2 uses the lower end)"},
 "dtol": G("0.15","bar","cut-in / cut-out tolerance"),
 "poff": G("0.5","bar","gauge-to-absolute pressure offset used by the pipe law (as stated: -0.5)"),
 "patm": G("1.013","bar","atmosphere"),
 "KP": G("1600","bar^2","empirical constant 1.6e3 of the pipe law, carries the units so that dp comes out in bar"),
 "Qu": G("1","L/s","unit flow for the law's Q^1.85"),
 "du": G("1","mm","unit diameter for the law's d^5"),
 "Lu": G("1","m","unit length for the law's Lm"),
 "Lmain": G("180","m","main pipe length"),
 "dA": G("19","mm","hose A inside diameter"), "LA": G("12","m","hose A length"),
 "dB": G("16","mm","hose B inside diameter"), "LB": G("8","m","hose B length"),
 "Qt": {"role":"derived","unit":"L/s"},
 "dpdry": {"role":"derived","unit":"bar"},
 "dpmain": {"role":"derived","unit":"bar"},
 "Pnf": {"role":"derived","unit":"bar"},
 "dphA": {"role":"derived","unit":"bar"},
 "PinA": {"role":"derived","unit":"bar"},
 "dphB": {"role":"derived","unit":"bar"},
 "PinB": {"role":"derived","unit":"bar"},
}
pw = "pow({x}/Qu, 1.85)"
laws = [
 {"zfl":"dpdry == D.dpr*Qt*Qt*f/(D.Qr*D.Qr)","source":"dryer: dp = dp_rated (Qt/Qr)^2 f"},
 {"zfl":"dpmain == CMAIN*pow(Qt/Qu, 1.85)","source":"empirical pipe law, CMAIN = 1.6e3*Lm/(d^5*pabs) per design"},
 {"zfl":"Pnf == C.pout + dtol","source":"no-flow pressure = cut-out + 0.15"},
]
def mode(tools, req):
    ls=[]; 
    qt = {"A":"QA + leak","B":"QB + leak","AB":"QA + QB + leak"}[tools]
    ls.append({"zfl":"Qt == "+qt,"source":"total flow = running tools + leakage"})
    if "A" in tools:
        ls.append({"zfl":"dphA == CHA*pow(QA/Qu, 1.85)","source":"hose A, own flow only"})
        ls.append({"zfl":"PinA == PCMIN - dpdry - dpmain - dphA","source":"tool inlet pressure"})
        req.append({"quantity":"PinA","op":">=","value":"6.0","why":"R1 tool A minimum inlet pressure"})
    if "A" not in tools:
        ls.append({"zfl":"dphA == 0*dpdry","source":"tool A idle: no flow, no hose drop (keeps the system determined)"})
        ls.append({"zfl":"PinA == PCMIN - dpdry - dpmain - dphA","source":"tool inlet pressure (idle tool: not required)"})
    if "B" not in tools:
        ls.append({"zfl":"dphB == 0*dpdry","source":"tool B idle: no flow, no hose drop (keeps the system determined)"})
        ls.append({"zfl":"PinB == PCMIN - dpdry - dpmain - dphB","source":"tool inlet pressure (idle tool: not required)"})
    if "B" in tools:
        ls.append({"zfl":"dphB == CHB*pow(QB/Qu, 1.85)","source":"hose B, own flow only"})
        ls.append({"zfl":"PinB == PCMIN - dpdry - dpmain - dphB","source":"tool inlet pressure"})
        req.append({"quantity":"PinB","op":">=","value":"6.2","why":"R1 tool B minimum inlet pressure"})
    return {"laws":ls,"requirements":req,"quantities":{},"define":{}}
S1 = mode("A",[]); S2 = mode("B",[]); 
S3 = mode("AB",[
 {"quantity":"Qt","op":"<=","value":"facfad*C.FAD","why":"R2 compressor capacity: 0.94 FAD >= QA+QB+leak (S3, upper ends)"},
 {"quantity":"Qt","op":"<=","value":"D.Qr","why":"R4 dryer rated flow >= largest Qt (S3, upper ends)"}])
modes = {"S1 tool A alone":S1,"S2 tool B alone":S2,"S3 both tools":S3}
for m in modes.values(): del m["quantities"]; del m["define"]
brick = {
 "stand":"universal-stand/1",
 "why":"c05 compressed-air line, flat brick with three operating situations as modes",
 "quantities":q,
 "slots":{"C":{"from":["compressors"]},"D":{"from":["dryers"]},"P":{"from":["pipes"]}},
 "computed":{
  "PCMIN":{"value":"C.cutin - dtol","unit":"bar"},
  "PABS":{"value":"C.cutin - dtol - poff + patm","unit":"bar"},
  "CMAIN":{"value":"KP*(Lmain/Lu)/((P.d/du)*(P.d/du)*(P.d/du)*(P.d/du)*(P.d/du)*PABS)","unit":"bar"},
  "CHA":{"value":"KP*(LA/Lu)/((dA/du)*(dA/du)*(dA/du)*(dA/du)*(dA/du)*PABS)","unit":"bar"},
  "CHB":{"value":"KP*(LB/Lu)/((dB/du)*(dB/du)*(dB/du)*(dB/du)*(dB/du)*PABS)","unit":"bar"},
 },
 "laws":laws,
 "requirements":[
  {"quantity":"Pnf","op":"<=","value":"8.5","why":"R3 no-flow protection vs tool A maximum inlet pressure"},
  {"quantity":"Pnf","op":"<=","value":"9.0","why":"R3 no-flow protection vs tool B maximum inlet pressure"}],
 "objective":{"minimize":"C.price + D.price + P.price*Lmain","unit":"EUR","why":"total price: compressor + dryer + 180 m of pipe"},
 "modes":modes,
 "catalog":{
  "compressors":{"items":[{"FAD":{"value":str(f)},"cutin":{"value":ci},"pout":{"value":co},"price":str(p),"name":n} for n,f,ci,co,p in comp],
    "ground":"vendor datasheet","fields":{"FAD":{"unit":"L/s"},"cutin":{"unit":"bar"},"pout":{"unit":"bar"},"price":{"unit":"EUR"}}},
  "dryers":{"items":[{"Qr":{"value":str(qr)},"dpr":{"value":dp},"price":str(p),"name":n} for n,qr,dp,p in dry],
    "ground":"vendor datasheet","fields":{"Qr":{"unit":"L/s"},"dpr":{"unit":"bar"},"price":{"unit":"EUR"}}},
  "pipes":{"items":[{"d":{"value":str(d)},"price":p,"name":"d%d"%d} for d,p in pipe],
    "ground":"vendor price list","fields":{"d":{"unit":"mm"},"price":{"unit":"EUR/m"}}}}}
json.dump(brick, open("c05.json","w"), indent=1)
