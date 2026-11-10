import json,subprocess,sys
b=json.load(open('c08.json'))
banks=b['catalog']['banks']['items']
res={}
for it in banks:
    for kind in ('pf','pb'):
        c=json.loads(json.dumps(b)); c['catalog']['banks']['items']=[it]; c.pop('objective'); c.pop('report'); c['laws']=[l for l in c['laws'] if not l['zfl'].startswith('payback')]; del c['quantities']['payback']
        if kind=='pf':
            c['quantities']['T']={"role":"given","value":"0","unit":""}
            c['requirements']=[{"quantity":"pfc","op":">=","value":"T","why":"pf floor"}]
            c['find']={"largest":"T","from":"0","to":"1","precision":"0.0001"}
        else:
            c['quantities']['L']={"role":"given","value":"40","unit":""}
            c['requirements']=[{"quantity":"save","op":">=","value":"C.cost/L","why":"payback cost/save <= L"}]
            c['find']={"smallest":"L","from":"20","to":"40","precision":"0.001"}
        fn='work_c08/f_%s_%s.json'%(it['name'],kind); json.dump(c,open(fn,'w'))
        r=subprocess.run("cd .. && cd .. && bash -c 'ulimit -v 3145728; timeout 900 python3 -m ustand.stand examples/blind7/%s'"%fn,shell=True,capture_output=True,text=True,cwd='.')
        out=r.stdout
        try:
            j=json.loads(out[out.index('{'):]); f={k:j.get(k) for k in ('proved','beyond','beyond_is','why')}
            print(it['name'],kind,j['verdict'],json.dumps(f)[:300])
        except Exception as e: print(it['name'],kind,'ERR',out[-400:],r.stderr[-300:])
