import json
from model import mmin, aer, seasons
import gen
b=gen.build()
slot={"winter":"MW","spring":"MS","summer":"MU","autumn":"MA"}
cl=[b["where"][0]]
b["quantities"]["Ey"]={"role":"derived","unit":"kWh"}
b["quantities"]["Load"]={"role":"derived","unit":"kW"}
b["laws"].append({"zfl":"Ey == days_winter*hrs_winter*MW.k*AE.P + days_spring*hrs_spring*MS.k*AE.P + days_summer*hrs_summer*MU.k*AE.P + days_autumn*hrs_autumn*MA.k*AE.P","source":"annual aerator energy = sum over seasons of days * night hours * m_s * P"})
b["laws"].append({"zfl":"Load == N.k*AE.P","source":"connected load n * P"})
b["requirements"].append({"quantity":"Ey","op":"<=","value":"Emax","why":"R3: annual aerator energy <= 31000 kWh"})
b["requirements"].append({"quantity":"Load","op":"<=","value":"Pmax","why":"R4: connected load <= 40 kW"})
for s,sl in slot.items():
    for t in aer:
        for lox,ln in ((0,"none"),(1,"LOX")):
            mm=mmin(s,t,lox)
            lo=16 if mm is None else mm
            hi=min(lo+1,16)
            cl.append(f'AE.name != "{t}" or OX.name != "{ln}" or ({sl}.k >= {lo} and {sl}.k <= {hi})')
b["where"]=cl
cat=b["catalog"]
del cat["ncount"]; del cat["mcount"]
rng={"MW":(1,2),"MS":(2,5),"MU":(6,13),"MA":(2,6),"N":(6,13)}
for sl,(lo,hi) in rng.items():
    cat["cnt_"+sl]={"integers":{"field":"k","from":str(lo),"to":str(hi),"unit":""}}
    b["slots"][sl]={"from":["cnt_"+sl]}
json.dump(b,open("../c10.json","w"),indent=1)
print(len(cl))
