import json,sys
dr=sys.argv[1].split(',') ; fn=sys.argv[2].split(','); out=sys.argv[3]
b=json.load(open('../c10.json'))
b['catalog']['dryers']['items']=[i for i in b['catalog']['dryers']['items'] if i['name'] in dr]
b['catalog']['fans']['items']=[i for i in b['catalog']['fans']['items'] if i['name'] in fn]
json.dump(b,open(out,'w'),indent=1)
