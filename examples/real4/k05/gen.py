import json, copy
base=json.load(open("brick.json"))

def cont(b, lo, hi, finds, name):
    # continuous ratio: i is a given searched by find; no catalog
    b=copy.deepcopy(b)
    b["slots"]={}; b["catalog"]={}
    b["quantities"]["ig"]={"role":"given","value":str(lo),"unit":""}
    b.pop("objective",None); b.pop("report",None)
    for l in b["laws"]:
        l["zfl"]=l["zfl"].replace("G.i","ig")
    b["requirements"]=[r for r in b["requirements"] if r["quantity"]!="TL"]
    b["find"]=finds
    json.dump(b,open(name,"w"),indent=1)
    return b

def motor_given(b, rng, why):
    b=copy.deepcopy(b)
    for q in ("phi",): b["quantities"].pop(q)
    b["quantities"]["NM"]={"role":"given","range":rng,"unit":"rpm"}
    b["laws"]=[l for l in b["laws"] if not l["zfl"].startswith(("phi","NM"))]
    for k in ("N0","Nr","Tr"): b["quantities"].pop(k)
    b["why"]=why
    return b

def fl(frm):
    return [{"largest":"ig","from":str(frm),"to":"80","precision":"0.01"},
            {"smallest":"ig","from":"20","to":str(frm),"precision":"0.01"}]

# A: linear speed-torque (the main brick) -> continuous ratio finds
cont(base,50,50,[{"largest":"ig","from":"50","to":"80","precision":"0.01"},{"smallest":"ig","from":"20","to":"50","precision":"0.01"}],"vA_linear_find.json")

# B: envelope [1450,1740]
B=motor_given(base,["1450","1740"],"motor speed anywhere between the stated rated low (1450) and no-load (1740)")
json.dump(B,open("vB_envelope.json","w"),indent=1)
cont(B,48,48,fl(48),"vB_envelope_find.json")

# C: the tech-ref's own rated range only [1450,1550]
C=motor_given(base,["1450","1550"],"motor speed anywhere in the tech-ref rated range 1450-1550")
json.dump(C,open("vC_rated.json","w"),indent=1)
cont(C,45,45,fl(45),"vC_rated_find.json")

# D: the catalog's 2..20 % slip of synchronous 1800
D=copy.deepcopy(base)
D["quantities"].pop("phi")
for k in ("N0","Nr","Tr"): D["quantities"].pop(k)
D["quantities"]["Ns"]={"role":"given","value":"1800","unit":"rpm"}
D["quantities"]["s"]={"role":"given","range":["0.02","0.2"],"unit":""}
D["laws"]=[l for l in D["laws"] if not l["zfl"].startswith(("phi","NM"))]
D["laws"].append({"zfl":"NM == Ns*(1 - s)","source":"catalog: actual speed 2-20 % below synchronous 1800 rpm"})
D["why"]="catalog statement: speed 2..20 % below synchronous 1800 rpm, whatever the load"
json.dump(D,open("vD_catalog_slip.json","w"),indent=1)
cont(D,48,48,fl(48),"vD_catalog_slip_find.json")

# E: the single point the tech-ref finally checks: no-load 1740
E=motor_given(base,["1740","1740"],"the tech-ref's final check: no-load 1740 rpm, a point")
E["quantities"]["NM"]={"role":"given","value":"1740","unit":"rpm"}
json.dump(E,open("vE_point1740.json","w"),indent=1)
