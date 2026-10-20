import json, os
D = os.path.dirname(os.path.abspath(__file__))
comp = [("K32",32,"6.8","8.0",6900),("K40",40,"6.8","8.0",8200),("K40M",40,"7.3","8.4",8900),("K50",50,"7.3","8.4",10600),("K50H",50,"8.0","9.0",11800)]
dry = [("D30",30,"0.40",1100),("D40",40,"0.35",1450),("D50",50,"0.30",1900),("D60",60,"0.30",2500)]
pipe = [(25,"6.0"),(32,"9.0"),(40,"14.0"),(50,"21.0"),(63,"33.0")]
G = lambda v,u,tol=None,rng=None: ({"role":"given","value":v,"unit":u} if rng is None else {"role":"given","range":rng,"unit":u})
def w(name, brick): json.dump(brick, open(os.path.join(D,name),"w"), indent=1)
def der(u): return {"role":"derived","unit":u}
def law(z,s): return {"zfl":z,"source":s}
# flow sum
w("flowsum.json",{"stand":"universal-stand/1","why":"S3: total flow = tool flows + leakage",
 "interface":{"inputs":{"QA":{"assume":["14","18"]},"QB":{"assume":["8.5","10.5"]},"leak":{"assume":["1.5","2.5"]}},"outputs":["Qt"]},
 "quantities":{"QA":G("16","L/s"),"QB":G("9","L/s"),"leak":G("2","L/s"),"Qt":der("L/s")},
 "laws":[law("Qt == QA + QB + leak","total flow")],"requirements":[]})
# compressors
for n,fad,ci,co,p in comp:
    w("cmp_%s.json"%n,{"stand":"universal-stand/1","why":"compressor "+n,
     "interface":{"inputs":{"Qt":{"assume":["0",str(round(0.94*fad,2))],"bands":"arriving"}},"outputs":["Pc","Pabs"]},
     "quantities":{"Qt":G("30","L/s"),"FAD":G(str(fad),"L/s"),"facfad":G("0",""," ",["0.94","1.0"]),
        "cutin":G(ci,"bar"),"cutout":G(co,"bar"),"dtol":G("0.15","bar"),"poff":G("0.5","bar"),"patm":G("1.013","bar"),
        "Pc":der("bar"),"Pabs":der("bar"),"Pnf":der("bar"),"Qcap":der("L/s")},
     "laws":[law("Pc == cutin - dtol","outlet pressure = lowest cut-in"),
             law("Pabs == cutin - dtol - poff + patm","p_abs of the pipe law"),
             law("Pnf == cutout + dtol","no-flow pressure"),
             law("Qcap == Qt","load on the compressor")],
     "requirements":[{"quantity":"Qcap","op":"<=","value":"facfad*FAD","why":"R2 0.94 FAD >= total flow"},
                     {"quantity":"Pnf","op":"<=","value":"8.5","why":"R3 vs tool A max"},
                     {"quantity":"Pnf","op":"<=","value":"9.0","why":"R3 vs tool B max"}]})
for n,qr,dpr,p in dry:
    w("dry_%s.json"%n,{"stand":"universal-stand/1","why":"dryer "+n,
     "interface":{"inputs":{"Qt":{"assume":["0",str(qr)],"bands":"arriving"}},"outputs":["dp"]},
     "quantities":{"Qt":G("30","L/s"),"Qr":G(str(qr),"L/s"),"dpr":G(dpr,"bar"),"f":{"role":"given","range":["1.0","1.7"],"unit":""},
        "dp":der("bar"),"Qload":der("L/s")},
     "laws":[law("dp == dpr*Qt*Qt*f/(Qr*Qr)","dryer law"),law("Qload == Qt","load")],
     "requirements":[{"quantity":"Qload","op":"<=","value":"Qr","why":"R4 rated flow >= largest Qt"}]})
def pipelaw(name,why,d,L,qrange,tag):
    return {"stand":"universal-stand/1","why":why,
     "interface":{"inputs":{"Q":{"assume":qrange,"bands":"arriving"},"Pabs":{"assume":["6.5","9.0"],"bands":"arriving"}},"outputs":["dp"]},
     "quantities":{"Q":G("20","L/s"),"Pabs":G("7","bar"),"KP":G("1600","bar^2"),"Qu":G("1","L/s"),"du":G("1","mm"),"Lu":G("1","m"),
        "d":G(str(d),"mm"),"L":G(str(L),"m"),"dp":der("bar")},
     "laws":[law("dp == KP*(L/Lu)/((d/du)*(d/du)*(d/du)*(d/du)*(d/du)*Pabs)*pow(Q/Qu, 1.85)","empirical pipe law")],
     "requirements":[]}
for d,p in pipe:
    w("pipe_d%d.json"%d, pipelaw("pipe","main pipe d=%d"%d,d,180,["5","60"],None))
w("hose_A.json",pipelaw("hoseA","hose A 19 mm 12 m",19,12,["5","25"],None))
w("hose_B.json",pipelaw("hoseB","hose B 16 mm 8 m",16,8,["5","25"],None))
sysb = {"stand":"universal-stand/1","why":"c05 as components, situation S3 only",
 "components":{
  "FS":{"file":"flowsum.json"},
  "CP":{"choose":[{"label":n,"file":"cmp_%s.json"%n,"fields":{"price":{"value":str(p),"unit":"EUR"}}} for n,fad,ci,co,p in comp]},
  "DR":{"choose":[{"label":n,"file":"dry_%s.json"%n,"fields":{"price":{"value":str(p),"unit":"EUR"}}} for n,qr,dpr,p in dry]},
  "PI":{"choose":[{"label":"d%d"%d,"file":"pipe_d%d.json"%d,"fields":{"price":{"value":str(float(p)*180).rstrip('0').rstrip('.'),"unit":"EUR"}}} for d,p in pipe]},
  "HA":{"file":"hose_A.json"},"HB":{"file":"hose_B.json"}},
 "connect":{"FS.QA":"QA","FS.QB":"QB","FS.leak":"leak","CP.Qt":"FS.Qt","DR.Qt":"FS.Qt","PI.Q":"FS.Qt","PI.Pabs":"CP.Pabs",
   "HA.Q":"QA","HA.Pabs":"CP.Pabs","HB.Q":"QB","HB.Pabs":"CP.Pabs"},
 "quantities":{"QA":{"role":"given","range":["14","18"],"unit":"L/s"},"QB":{"role":"given","range":["8.5","10.5"],"unit":"L/s"},
   "leak":{"role":"given","range":["1.5","2.5"],"unit":"L/s"},
   "PinA":der("bar"),"PinB":der("bar")},
 "laws":[law("PinA == CP.Pc - DR.dp - PI.dp - HA.dp","tool A inlet"),law("PinB == CP.Pc - DR.dp - PI.dp - HB.dp","tool B inlet")],
 "requirements":[{"quantity":"PinA","op":">=","value":"6.0","why":"R1 A"},{"quantity":"PinB","op":">=","value":"6.2","why":"R1 B"}],
 "objective":{"minimize":"CP.price + DR.price + PI.price","unit":"EUR"}}
if os.environ.get("ARR"): sysb["bands"]="arriving"
json.dump(sysb,open(os.path.join(D,"c05_components.json"),"w"),indent=1)
