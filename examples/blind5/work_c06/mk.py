import json,sys
b=json.load(open('../c06.json'))
name=sys.argv[1]; Bs=sys.argv[2].split(','); Ds=sys.argv[3].split(',')
v=b
v['catalog']['widths']['items']=[{"B":x} for x in Bs]
v['catalog']['depths']['items']=[{"Df":x} for x in Ds]
json.dump(v,open(name,'w'),indent=1)
