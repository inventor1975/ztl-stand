import json,sys
sys.path.insert(0,'.')
from gen import brick
d=brick()
reqs=d["requirements"]
pins=[{"quantity":"CELL.Imax25","op":"within","value":["20","20"],"why":"pin cell H25"},
      {"quantity":"NP.N","op":"within","value":["4","4"],"why":"pin Np=4"},
      {"quantity":"BMS.Irat","op":"within","value":["60","60"],"why":"pin BMS M60"},
      {"quantity":"HT.Eh","op":"within","value":["3.5","3.5"],"why":"pin heater fitted"}]
d["find"]=[
 {"smallest":"Ta","from":"233.15","to":"263.15","precision":"0.01","why":"lowest ambient with ANY admissible design"},
 {"smallest":"Ta","from":"233.15","to":"263.15","precision":"0.01","requirements":reqs+pins,"why":"lowest ambient for the chosen design H25/4/M60/heater"}]
json.dump(d,open(sys.argv[1],"w"),indent=1)
