import json
from gen import cables, breakers
def cat():
    return {"cables":{"items":[{"R20":{"value":r},"Iz30":{"value":iz},"price":p,"type":n} for n,S,r,iz,p in cables],
                      "fields":{"R20":{"unit":"mohm/m"},"Iz30":{"unit":"A"},"price":{"unit":"EUR/m"}}},
            "breakers":{"items":[{"In":{"value":i},"price":p,"type":n} for n,i,p in breakers],
                        "fields":{"In":{"unit":"A"},"price":{"unit":"EUR"}}}}
def motor(name, irun, kls, iref):
    return {"stand":"ztl-stand/1","why":f"{name} datasheet: running current, starting current = kls x {iref} A",
     "interface":{"inputs":{},"outputs":["Irun","Istart"]},
     "quantities":{"Ir":{"role":"given","range":irun,"unit":"A"},"kls":{"role":"given","range":kls,"unit":""},
                   "Iref":{"role":"given","value":iref,"unit":"A"},
                   "Irun":{"role":"derived","unit":"A"},"Istart":{"role":"derived","unit":"A"}},
     "slots":{},"catalog":{},
     "laws":[{"zfl":"Irun == Ir","source":"datasheet"},{"zfl":"Istart == kls*Iref","source":"datasheet: I_s = k_ls x base"}],
     "requirements":[]}
def tr():
    return {"stand":"ztl-stand/1","why":"workshop transformer: V_bus = V0 - ks (Ia + Ib)",
     "interface":{"inputs":{"Ia":{"assume":["0","400"],"bands":"arriving"},"Ib":{"assume":["0","400"],"bands":"arriving"}},"outputs":["Vbus"]},
     "quantities":{"V0":{"role":"given","range":["395","415"],"unit":"V"},"ks":{"role":"given","range":["0.060","0.085"],"unit":"V/A"},
                   "Ia":{"role":"given","value":"50","unit":"A"},"Ib":{"role":"given","value":"30","unit":"A"},
                   "Vbus":{"role":"derived","unit":"V"}},
     "slots":{},"catalog":{},
     "laws":[{"zfl":"Vbus == V0 - ks*(Ia + Ib)","source":"transformer datasheet"}],"requirements":[]}
def feeder(starts):  # starts = 2 : starting motor in S2 (feeder 1); 3 : in S3 (feeder 2)
    q={"L":("m","given","100"),"Ir":("A","given","50"),"Is":("A","given","300"),
       "Vb1":("V","given","400"),"Vb2":("V","given","400"),"Vb3":("V","given","400")}
    Q={k:{"role":"given","value":v[2],"unit":v[0]} for k,v in q.items()}
    g=lambda n,u,v:Q.__setitem__(n,{"role":"given","unit":u,"value":v})
    g("Tamb","C","38");g("Tins","C","90");g("Tcal","C","30");g("dTr","C","60");g("alpha","1/C","0.00393");g("Tref","C","20");g("Xp","mohm/m","0.08")
    for n,u in [("Vt1","V"),("Vt2","V"),("Vt3","V"),("dV1","V"),("dV2","V"),("dV3","V"),("Iz","A"),("m4","A"),("m5","A"),("m6","A")]:
        Q[n]={"role":"derived","unit":u}
    cur={1:"Ir",2:"Is" if starts==2 else "Ir",3:"Is" if starts==3 else "Ir"}
    cos={1:"0.85",2:"0.40" if starts==2 else "0.85",3:"0.40" if starts==3 else "0.85"}
    d={"th":"Tamb + dTr*(Ir/C.Iz30)*(Ir/C.Iz30)","Rp":"C.R20*(1 + alpha*(th - Tref))"}
    laws=[]
    for s in (1,2,3):
        c=cos[s]
        laws.append({"zfl":f"dV{s} == sqrt(3)*{cur[s]}*L*(Rp*{c} + Xp*sqrt(1 - {c}*{c}))","source":"3-phase cable drop, R'(theta)"})
        laws.append({"zfl":f"Vt{s} == Vb{s} - dV{s}","source":"terminal voltage = V_bus - dV"})
    laws+= [{"zfl":"Iz == C.Iz30*sqrt((Tins - Tamb)/(Tins - Tcal))","source":"Iz(T) = Iz30 sqrt((90-T)/60)"},
            {"zfl":"m4 == B.In - 1.1*Ir","source":"R4 margin"},
            {"zfl":"m5 == 8*B.In - 1.25*Is","source":"R5 margin"},
            {"zfl":"m6 == Iz - B.In","source":"R6 margin"}]
    inp={"L":{"assume":["0","600"]},"Ir":{"assume":["0","100"]},"Is":{"assume":["0","400"]}}
    for s in (1,2,3): inp[f"Vb{s}"]={"assume":["300","420"],"bands":"arriving"}
    for k in ("L","Ir","Is"): inp[k]["bands"]="arriving"
    return {"stand":"ztl-stand/1","why":"one feeder: cable C + breaker B, three situations; ratings R4-R6 are its own requirements",
      "interface":{"inputs":inp,"outputs":["Vt1","Vt2","Vt3"]},
      "quantities":Q,"slots":{"C":{"from":["cables"]},"B":{"from":["breakers"]}},"define":d,"laws":laws,
      "requirements":[{"quantity":"m4","op":">=","value":"0","why":"R4"},{"quantity":"m5","op":">=","value":"0","why":"R5"},{"quantity":"m6","op":">=","value":"0","why":"R6"}],
      "objective":{"minimize":"C.price*L + B.price","unit":"EUR","why":"cable over its length + breaker"},
      "catalog":cat()}
def system(L1="160", find=None):
    comps={"M1":{"file":"motor1.json"},"M2":{"file":"motor2.json"},"F1":{"file":"feeder1.json"},"F2":{"file":"feeder2.json"},
           "T1":{"file":"tr.json"},"T2":{"file":"tr.json"},"T3":{"file":"tr.json"}}
    conn={"T1.Ia":"M1.Irun","T1.Ib":"M2.Irun","T2.Ia":"M1.Istart","T2.Ib":"M2.Irun","T3.Ia":"M1.Irun","T3.Ib":"M2.Istart"}
    for f,m,l in (("F1","M1","L1"),("F2","M2","L2")):
        conn.update({f"{f}.L":l,f"{f}.Ir":f"{m}.Irun",f"{f}.Is":f"{m}.Istart",f"{f}.Vb1":"T1.Vbus",f"{f}.Vb2":"T2.Vbus",f"{f}.Vb3":"T3.Vbus"})
    b={"stand":"ztl-stand/1","why":"c02 as a system of devices: 3 transformer instances (one per situation), 2 motors, 2 feeders (cable+breaker chosen inside)",
       "components":comps,"connect":conn,
       "quantities":{"L1":{"role":"given","value":L1,"unit":"m"},"L2":{"role":"given","value":"85","unit":"m"},
                     "Vb_S1":{"role":"derived","unit":"V"}},
       "laws":[{"zfl":"Vb_S1 == T1.Vbus","source":"busbar in S1 (placeholder, unused)"}],
       "requirements":[]}
    return b

def system2(L1="160", find=None):
    b=system(L1)
    for n in ("Vb_S1",): del b["quantities"][n]
    names=[("R1_1","F1.Vt1","380"),("R1_2","F2.Vt1","380"),("R2_1","F1.Vt2","340"),("R2_2","F2.Vt3","340"),("R3_S2","T2.Vbus","352"),("R3_S3","T3.Vbus","352")]
    b["laws"]=[]
    b["requirements"]=[]
    for n,src,lim in names:
        b["quantities"][n]={"role":"derived","unit":"V"}
        b["laws"].append({"zfl":f"{n} == {src}","source":"contract output"})
        b["requirements"].append({"quantity":n,"op":">=","value":lim,"why":n})
    b["objective"]={"minimize":"F1.cost + F2.cost","unit":"EUR","why":"cable over its length + breaker, both feeders"}
    if find: b["find"]=find
    return b
if __name__=="__main__":
    w=lambda n,o: json.dump(o,open(n,"w"),indent=1)
    w("motor1.json",motor("M1",["50","56"],["5.8","6.4"],"53"))
    w("motor2.json",motor("M2",["30","35"],["5.8","6.4"],"32"))
    w("tr.json",tr()); w("feeder1.json",feeder(2)); w("feeder2.json",feeder(3))
    w("c02_sys.json",system2())
    w("c02_sys_find.json",system2(find={"largest":"L1","from":"0","to":"400","precision":"0.1"}))
