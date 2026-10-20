import json,sys,itertools
PTS=sys.argv[2].split(",") if len(sys.argv)>2 else None
STRIKES=sys.argv[3].split(",") if len(sys.argv)>3 else None
Q=[1,2,3,4]
F={1:"1.085",2:"1.090",3:"1.095",4:"1.100"}
q={}
q["U"]={"role":"given","value":"4","unit":"MUSD","why":"nominal USD revenue per quarter"}
q["Cost"]={"role":"given","value":"3","unit":"MEUR","why":"EUR costs per quarter"}
q["bank"]={"role":"given","value":"0.0012","unit":"","why":"bank charge 0.12 % of EUR notional"}
q["v"]={"role":"given","range":["0.85","1.10"],"unit":"","why":"volume factor, ONE value shared by all four quarters"}
for i in Q:
    q[f"S{i}"]={"role":"given","range":["1.02","1.22"],"unit":"USD/EUR","why":f"spot at end of quarter {i}, independent"}
    q[f"F{i}"]={"role":"given","value":F[i],"unit":"USD/EUR","why":f"forward rate quarter {i}"}
    q[f"P{i}"]={"role":"derived","unit":"MEUR"}
    q[f"G{i}"]={"role":"derived","unit":"","why":"h+o effective in quarter"}
for n in ["A","HS","FW","PR","BK","COST"]:
    pass
q["A"]={"role":"derived","unit":"MEUR"}
q["HS"]={"role":"derived","unit":""}
q["FW"]={"role":"derived","unit":"MUSD"}
q["PR"]={"role":"derived","unit":"MEUR"}
q["BK"]={"role":"derived","unit":"MEUR"}
q["COST"]={"role":"derived","unit":"MEUR"}
slots={"SK":{"from":["strikes"]}}
cat={"strikes":{"items":[
  {"K":"1.06","pi":"0.0210","on":"1","label":"K=1.06"},
  {"K":"1.10","pi":"0.0120","on":"1","label":"K=1.10"},
  {"K":"1.14","pi":"0.0058","on":"1","label":"K=1.14"},
  {"K":"1.10","pi":"0","on":"0","label":"no options"}],
  "fields":{"K":{"unit":"USD/EUR"},"pi":{"unit":"EUR/USD"},"on":{"unit":""}}}}
for i in Q:
    slots[f"H{i}"]={"from":[f"hf{i}"]}
    slots[f"O{i}"]={"from":[f"of{i}"]}
    cat[f"hf{i}"]={"continuous":{"field":"x","from":"0","to":"1","unit":""}}
    cat[f"of{i}"]={"continuous":{"field":"x","from":"0","to":"1","unit":""}}
define={}
for i in Q:
    define[f"iS{i}"]=f"1/S{i}"
    define[f"iM{i}"]=f"1/min(S{i}, SK.K)"
laws=[]
for i in Q:
    laws.append({"zfl":f"P{i} == U*(v*iS{i} + H{i}.x*(1/F{i} - iS{i}) + SK.on*O{i}.x*(iM{i} - iS{i})) - SK.pi*SK.on*O{i}.x*U - bank*H{i}.x*U/F{i} - Cost",
                 "source":"problem statement: quarter profit = revenue - EUR cost"})
    laws.append({"zfl":f"G{i} == H{i}.x + SK.on*O{i}.x","source":"effective hedge fraction in quarter (option fraction forced to 0 when no options)"})
laws+= [
 {"zfl":"A == P1 + P2 + P3 + P4","source":"annual profit"},
 {"zfl":"HS == G1 + G2 + G3 + G4","source":"sum of hedge fractions"},
 {"zfl":"FW == (H1.x + H2.x + H3.x + H4.x)*U","source":"forward notional"},
 {"zfl":"PR == SK.pi*SK.on*(O1.x + O2.x + O3.x + O4.x)*U","source":"total option premium"},
 {"zfl":"BK == bank*U*(H1.x/F1 + H2.x/F2 + H3.x/F3 + H4.x/F4)","source":"total bank charge"},
 {"zfl":"COST == PR + BK","source":"hedging cost"},
]
reqs=[]
for i in Q:
    reqs.append({"quantity":f"P{i}","op":">=","value":"-0.10","why":f"R1 quarter {i} profit >= -0.10 MEUR"})
reqs+=[
 {"quantity":"A","op":">=","value":"0.30","why":"R2 annual profit >= 0.30 MEUR"},
 {"quantity":"HS","op":"within","value":["1.6","3.2"],"why":"R3 |avg(h+o)-0.6|<=0.2 i.e. sum in [1.6,3.2]"}]
for i in Q:
    reqs.append({"quantity":f"G{i}","op":"<=","value":"1","why":f"R4 h+o<=1 quarter {i}"})
reqs+=[
 {"quantity":"FW","op":"<=","value":"9","why":"R5 forward notional <= 9 MUSD"},
 {"quantity":"PR","op":"<=","value":"0.10","why":"R6 premium <= 0.10 MEUR"}]
if STRIKES:
    cat["strikes"]["items"]=[it for it in cat["strikes"]["items"] if it["label"] in STRIKES]
b={"stand":"universal-stand/1","quantities":q,"slots":slots,"catalog":cat,"define":define,"laws":laws,"requirements":reqs,
 "objective":{"minimize":"COST","unit":"kEUR","why":"total premium + bank charge"}}
if PTS:
    modes={}
    r2=[r for r in reqs if r["quantity"] in ("P1","P2","P3","P4","A")]
    common=[r for r in reqs if r not in r2]
    b["requirements"]=common
    for combo in itertools.product(PTS,repeat=4):
        nm="m_"+"_".join(p.replace(".","") for p in combo)
        modes[nm]={"quantities":{f"S{i+1}":{"value":combo[i]} for i in range(4)},"requirements":r2}
    b["modes"]=modes
json.dump(b,open(sys.argv[1],"w"),indent=1)
