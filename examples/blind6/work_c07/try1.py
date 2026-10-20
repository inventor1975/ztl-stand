import json,sys,copy
b=json.load(open('../c07.json'))
mode=sys.argv[1]
keep=lambda n: n.endswith('a') or n in('Ac','C','Cd','g','cp','fb')
b['quantities']={k:v for k,v in b['quantities'].items() if keep(k) or k in ('Ac','C','Cd','g','cp','fb')}
b['quantities']={k:v for k,v in b['quantities'].items() if k not in ('Mb',)}
b['define']={k:v for k,v in b['define'].items() if k=='Ao' or k=='Qina'}
b['laws']=b['laws'][:2]
b['requirements']=[r for r in b['requirements'] if r['quantity'] in('Qpa','PL.d')]
if mode=='givenA':
    b['quantities']['AA']={"role":"given","value":"300","unit":"m^2"}
    b['laws'][0]['zfl']=b['laws'][0]['zfl'].replace('PA.A','AA')
    b['slots'].pop('PA');b['catalog'].pop('pondA')
    b['objective']['minimize']="cp*300*PH.H+PL.price" if False else "PL.price"
    b['objective']['unit']='kEUR'
if mode=='givenA_noQin':
    pass
json.dump(b,open('try_%s.json'%mode,'w'),indent=1)
