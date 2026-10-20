import json
SRC="UCSD CSE140 lec10 timing slides (Harris&Harris style example), tccq/tpcq/tcd/tpd/tsetup/thold/tskew table"
def base(short_gates, skew, find=None, tc="215", check=("setup",), why=""):
    q={}
    q["tcq"]={"role":"given","range":["30","50"],"unit":"ps","ground":SRC,"why":"clock-to-Q: min tccq=30, max tpcq=50"}
    for i in (1,2,3):
        q[f"g{i}"]={"role":"given","range":["25","35"],"unit":"ps","ground":SRC,"why":"gate delay: min tcd=25, max tpd=35 (long path stage %d)"%i}
    for i in range(1,short_gates+1):
        q[f"h{i}"]={"role":"given","range":["25","35"],"unit":"ps","ground":SRC,"why":"gate delay: min tcd=25, max tpd=35 (short path stage %d)"%i}
    q["tsu"]={"role":"given","value":"60","unit":"ps","ground":SRC,"why":"setup time"}
    q["thold"]={"role":"given","value":"70","unit":"ps","ground":SRC,"why":"hold time"}
    laws=[];reqs=[]
    if skew is not None:
        q["sk"]={"role":"given","range":skew,"unit":"ps","ground":SRC,"why":"skew: capture clock lag minus launch clock, |skew|<=50 (slide: tskew=50 worst case, either sign)"}
    skx=" + sk" if skew is not None else ""
    skm=" - sk" if skew is not None else ""
    if "setup" in check:
        q["Tc"]={"role":"given","value":tc,"unit":"ps","why":"clock period"}
        q["ss"]={"role":"derived","unit":"ps"}
        laws.append({"zfl":"ss == Tc"+skx+" - tcq - (g1 + g2 + g3) - tsu","source":"setup: Tc >= tpcq + tpd + tsetup (+ tskew)"})
        reqs.append({"quantity":"ss","op":">=","value":"0","why":"setup slack nonnegative"})
    if "hold" in check:
        q["sh"]={"role":"derived","unit":"ps"}
        sp=" + ".join(f"h{i}" for i in range(1,short_gates+1))
        laws.append({"zfl":"sh == tcq + (%s)"%sp+skm+" - thold","source":"hold: tccq + tcd > thold (+ tskew)"})
        reqs.append({"quantity":"sh","op":">=","value":"0","why":"hold slack nonnegative (the source writes strict >; see report)"})
    b={"stand":"ztl-stand/1","why":why,"quantities":q,"slots":{},"laws":laws,"requirements":reqs,"catalog":{},"conflicts":False}
    if find: b["find"]=find
    return b
def w(name,b): json.dump(b,open(name,"w"),indent=1)
# main: setup, skew +-50, smallest Tc
b=base(1,["-50","50"],check=("setup",),why="s04 main: smallest clock period with +-50 ps skew; source: 265 ps")
b["quantities"]["Tc"]["why"]="clock period searched (find)"
b["find"]={"smallest":"Tc","from":"150","to":"400","precision":"1"}
w("brick.json",b)
b=base(1,None,check=("setup",),why="setup without skew; source: 215 ps")
b["find"]={"smallest":"Tc","from":"150","to":"400","precision":"1"}; w("v1_setup_noskew.json",b)
w("v2_hold_short1_noskew.json",base(1,None,check=("hold",),why="hold, short path one gate, no skew; source: 55 vs 70 violated"))
w("v3_hold_short2_noskew.json",base(2,None,check=("hold",),why="hold, short path two gates (buffer added), no skew; source: 80 > 70 ok"))
w("v4_hold_short2_skew50.json",base(2,["-50","50"],check=("hold",),why="hold, two gates, skew up to 50; source: 80 vs 120 violated"))
b=base(2,["0","0"],check=("hold",),why="largest skew that keeps hold with two-gate short path; source implies <10 ps (80>70+skew)")
b["quantities"]["sk"]["why"]="skew searched (find)"; del b["quantities"]["sk"]["range"]; b["quantities"]["sk"]["value"]="0"
b["find"]={"largest":"sk","from":"0","to":"60","precision":"1"}; w("v5_hold_find_skew.json",b)
# both setup and hold combined, buffered, no skew, Tc=215 -> EARNED expected
w("v6_both_buffered_noskew_215.json",base(2,None,check=("setup","hold"),tc="215",why="whole retimed design, no skew, Tc=215"))
w("v7_both_buffered_noskew_214.json",base(2,None,check=("setup","hold"),tc="214",why="same with Tc=214, expected refuted"))
