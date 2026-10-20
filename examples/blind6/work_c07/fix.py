import json,sys
plate,A,H,fb,out=sys.argv[1:6]
b=json.load(open('c07_closed.json'))
b['catalog']['plates']['items']=[i for i in b['catalog']['plates']['items'] if i['name']==plate]
b['catalog']['pondA']={"items":[{"A":A}],"fields":{"A":{"unit":"m^2"}}}
b['catalog']['pondH']={"items":[{"H":H}],"fields":{"H":{"unit":"m"}}}
b['quantities']['fb']['value']=fb
b['note']=f"fixed-design check {plate} A={A} H={H} freeboard {fb}"
json.dump(b,open(out,'w'),indent=1)
