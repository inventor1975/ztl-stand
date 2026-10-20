import json,sys
sys.path.insert(0,'.')
from gen import brick
d=brick(cells=["H25"],bms=["M60"],nps=(4,4))
keep=sys.argv[1].split(",")
d["requirements"]=[r for r in d["requirements"] if r["quantity"] in keep]
d.pop("objective",None)
json.dump(d,open(sys.argv[2],"w"),indent=1)
