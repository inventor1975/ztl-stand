import json, sys
def s(x): return str(x)
cables=[("C16","16","1.150","100","5.5"),("C25","25","0.727","130","8.0"),("C35","35","0.524","160","10.5"),
        ("C50","50","0.387","190","14.0"),("C70","70","0.268","240","19.0"),("C95","95","0.193","290","26.0")]
breakers=[("B40","40","48"),("B50","50","58"),("B63","63","70"),("B80","80","95"),("B100","100","120"),("B125","125","160"),("B160","160","230")]
def build(cab=cables, brk=breakers, L1="160", find=None, conflicts=True):
    q={}
    def g(n,unit,why,**kw):
        d={"role":"given","unit":unit,"why":why}; d.update(kw); q[n]=d
    def dv(n,unit,why=None):
        q[n]={"role":"derived","unit":unit}
        if why: q[n]["why"]=why
    g("V0","V","no-load busbar voltage (tap tolerance)",range=["395","415"])
    g("ks","V/A","transformer load regulation, ONE shared value",range=["0.060","0.085"])
    g("L1","m","feeder 1 length",value=L1)
    g("L2","m","feeder 2 length",value="85")
    g("Tamb","C","ambient for conductor temperature and rating (worst case of 5..38)",value="38")
    g("Tins","C","XLPE insulation limit",value="90")
    g("Tcal","C","rating reference ambient",value="30")
    g("dTr","C","conductor rise at rated current",value="60")
    g("alpha","1/C","copper temperature coefficient",value="0.00393")
    g("Tref","C","resistance reference temperature",value="20")
    g("Xp","mohm/m","cable reactance, every cable",value="0.08")
    # motors: highest running current appears through the range itself (any value in range; worst case = top)
    g("Irun1","A","M1 running current (theta, R4)",range=["50","56"])
    g("Irun2","A","M2 running current (theta, R4)",range=["30","35"])
    g("kls1","","M1 locked-rotor ratio",range=["5.8","6.4"])
    g("kls2","","M2 locked-rotor ratio",range=["5.8","6.4"])
    g("Iref1","A","M1 starting-current base",value="53")
    g("Iref2","A","M2 starting-current base",value="32")
    # situation data: base current x multiplier, power factor (the three modes override them)
    g("Ib1","A","feeder-1 base current in the situation (mode overrides)",range=["50","56"])
    g("Ib2","A","feeder-2 base current in the situation (mode overrides)",range=["30","35"])
    g("k1","","feeder-1 multiplier in the situation (mode overrides)",value="1")
    g("k2","","feeder-2 multiplier in the situation (mode overrides)",value="1")
    g("c1","","cos phi on feeder 1 in the situation (mode overrides)",value="0.85")
    g("c2","","cos phi on feeder 2 in the situation (mode overrides)",value="0.85")
    for n,u in [("Vbus","V"),("dV1","V"),("dV2","V"),("Vt1","V"),("Vt2","V"),("Iz1","A"),("Iz2","A"),
                ("m4_1","A"),("m4_2","A"),("m5_1","A"),("m5_2","A"),("m6_1","A"),("m6_2","A")]:
        dv(n,u)
    d={}
    for i in ("1","2"):
        d["th"+i]=f"Tamb + dTr*(Irun{i}/C{i}.Iz30)*(Irun{i}/C{i}.Iz30)"
        d["Rp"+i]=f"C{i}.R20*(1 + alpha*(th{i} - Tref))"
        d["I"+i]=f"Ib{i}*k{i}"
        d["s"+i]=f"sqrt(1 - c{i}*c{i})"
    laws=[{"zfl":"Vbus == V0 - ks*(I1 + I2)","source":"transformer: V_bus = V0 - ks (I_a + I_b)"}]
    for i in ("1","2"):
        laws.append({"zfl":f"dV{i} == sqrt(3)*I{i}*L{i}*(Rp{i}*c{i} + Xp*s{i})","source":"3-phase cable drop, R'(theta) from the conductor temperature"})
        laws.append({"zfl":f"Vt{i} == Vbus - dV{i}","source":"terminal voltage = V_bus - dV of its feeder"})
        laws.append({"zfl":f"Iz{i} == C{i}.Iz30*sqrt((Tins - Tamb)/(Tins - Tcal))","source":"Iz(T) = Iz30 sqrt((90-T)/60)"})
        laws.append({"zfl":f"m4_{i} == B{i}.In - 1.1*Irun{i}","source":"R4 margin"})
        laws.append({"zfl":f"m5_{i} == 8*B{i}.In - 1.25*kls{i}*Iref{i}","source":"R5 margin"})
        laws.append({"zfl":f"m6_{i} == Iz{i} - B{i}.In","source":"R6 margin"})
    reqs=[]
    for i in ("1","2"):
        reqs.append({"quantity":f"m4_{i}","op":">=","value":"0","why":f"R4 feeder {i}: In >= 1.1 x highest running current"})
        reqs.append({"quantity":f"m5_{i}","op":">=","value":"0","why":f"R5 feeder {i}: 8 In >= 1.25 x highest starting current"})
        reqs.append({"quantity":f"m6_{i}","op":">=","value":"0","why":f"R6 feeder {i}: In <= Iz(38) of its cable"})
    modes={
     "S1":{"quantities":{"Ib1":{"range":["50","56"]},"k1":{"value":"1"},"Ib2":{"range":["30","35"]},"k2":{"value":"1"},
                         "c1":{"value":"0.85"},"c2":{"value":"0.85"}},
           "requirements":[{"quantity":"Vt1","op":">=","value":"380","why":"R1 M1 running"},
                           {"quantity":"Vt2","op":">=","value":"380","why":"R1 M2 running"}]},
     "S2":{"quantities":{"Ib1":{"value":"53"},"k1":{"range":["5.8","6.4"]},"Ib2":{"range":["30","35"]},"k2":{"value":"1"},
                         "c1":{"value":"0.40"},"c2":{"value":"0.85"}},
           "requirements":[{"quantity":"Vt1","op":">=","value":"340","why":"R2 M1 starting, M2 running"},
                           {"quantity":"Vbus","op":">=","value":"352","why":"R3 busbar in S2"}]},
     "S3":{"quantities":{"Ib1":{"range":["50","56"]},"k1":{"value":"1"},"Ib2":{"value":"32"},"k2":{"range":["5.8","6.4"]},
                         "c1":{"value":"0.85"},"c2":{"value":"0.40"}},
           "requirements":[{"quantity":"Vt2","op":">=","value":"340","why":"R2 M2 starting, M1 running"},
                           {"quantity":"Vbus","op":">=","value":"352","why":"R3 busbar in S3"}]}}
    cat={"cables":{"items":[{"R20":{"value":r},"Iz30":{"value":iz},"price":p,"type":n,"S":{"value":S}} for n,S,r,iz,p in cab],
                   "fields":{"R20":{"unit":"mohm/m"},"Iz30":{"unit":"A"},"price":{"unit":"EUR/m"},"S":{"unit":"mm^2"}}},
         "breakers":{"items":[{"In":{"value":i},"price":p,"type":n} for n,i,p in brk],
                     "fields":{"In":{"unit":"A"},"price":{"unit":"EUR"}}}}
    b={"stand":"ztl-stand/1",
       "why":"blind6 c02: two pump motors on one transformer; cables and breakers (problem 2). All data fictional.",
       "quantities":q,
       "slots":{"C1":{"from":["cables"]},"C2":{"from":["cables"]},"B1":{"from":["breakers"]},"B2":{"from":["breakers"]}},
       "define":d,"laws":laws,"requirements":reqs,"modes":modes,
       "objective":{"minimize":"C1.price*L1 + C2.price*L2 + B1.price + B2.price","unit":"EUR","why":"cables over their lengths + breakers"},
       "catalog":cat}
    if find: b["find"]=find
    if not conflicts: b["conflicts"]=False
    return b
if __name__=="__main__":
    out=sys.argv[1]
    kw={}
    if len(sys.argv)>2 and sys.argv[2]=="small":
        kw=dict(cab=cables[2:5],brk=breakers[1:5])
    json.dump(build(**kw),open(out,"w"),indent=1)
