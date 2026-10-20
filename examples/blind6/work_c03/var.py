import json,sys,copy
sys.path.insert(0,'.')
from gen import brick
d=brick()
mode=sys.argv[1]; out=sys.argv[2]
if mode=="novalid":
    for l in d["laws"]: l.pop("valid",None)
if mode=="noI":
    d["laws"]=[l for l in d["laws"] if not l["zfl"].startswith("I ==")]
json.dump(d,open(out,"w"),indent=1)
