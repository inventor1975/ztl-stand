import json,sys
from model import mmin, aer, seasons
import gen
def sub(sname):
    b=gen.build()
    d=seasons[sname]
    b["modes"]=None; del b["modes"]
    b["quantities"]["T"]={"role":"given","range":[str(d["T"][0]),str(d["T"][1])],"unit":"C"}
    b["quantities"]["W"]={"role":"given","range":[str(d["W"][0]),str(d["W"][1])],"unit":"kg"}
    b["slots"]={"AE":b["slots"]["AE"],"OX":b["slots"]["OX"],"M":{"from":["mcount"]}}
    b["define"]["mrun"]="M.k"
    b["computed"]={}
    cl=[]
    for t in aer:
        for lox,ln in ((0,"none"),(1,"LOX")):
            mm=mmin(sname,t,lox)
            if mm is None: mm=17  # none within 16
            lo=max(mm-1,0); hi=min(mm,16)
            cl.append(f'AE.name != "{t}" or OX.name != "{ln}" or (M.k >= {lo} and M.k <= {hi})')
    b["where"]=cl
    b["objective"]={"minimize":"M.k","unit":"","why":"scan"}
    del b["objective"]
    b["report"]="all"
    return b
for s in seasons:
    json.dump(sub(s),open(f"sub_{s}.json","w"),indent=1)
