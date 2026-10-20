import json
b=json.load(open("../c12.json"))
b["quantities"]["tau"]={"role":"given","unit":"h","value":"1300","why":"test interval: searched by find"}
b["slots"]={"TM":{"from":["TL"]},"CM":{"from":["mon2"]}}
for l in b["laws"]:
    l["zfl"]=l["zfl"].replace("TAU.x","tau")
b["objective"]=None; del b["objective"]
b["catalog"]={"TL":{"ground":"problem statement","items":[b["catalog"]["tests"]["items"][1]],"fields":b["catalog"]["tests"]["fields"]},
 "mon2":{"ground":"problem statement","items":[b["catalog"]["mon"]["items"][1]],"fields":b["catalog"]["mon"]["fields"]}}
b["requirements"][1]={"quantity":"tauq","op":"<=","value":"Tov","why":"R2: tau <= Tov"}
b["find"]=[{"smallest":"tau","from":"24","to":"1300","precision":"0.1"},{"largest":"tau","from":"1300","to":"2190","precision":"0.1"}]
json.dump(b,open("../work_c12/c12_interval.json","w"),indent=1)
