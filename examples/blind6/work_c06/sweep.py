import json,subprocess,time,sys,os
from gen2 import *
NS={"E2":2,"E3":3,"E4":4,"E3H":3}
rows=[]
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
for e in ("E2","E3","E4","E3H"):
  for s in ("SA","SB","SC"):
    for b in ("G600","G1200","G2000"):
        f="examples/blind6/work_c06/sweep/%s_%s_%s.json"%(e,s,b)
        build(NS[e],[e],[s],[b],f)
        t0=time.time()
        r=subprocess.run("OPENBLAS_NUM_THREADS=1 timeout 900 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand "+f,shell=True,capture_output=True,text=True)
        dt=time.time()-t0
        t=r.stdout
        try: j=json.loads(t[t.index('{'):t.rindex('}')+1])
        except Exception as ex:
            rows.append((e,s,b,"ERR",r.stdout[-300:]+r.stderr[-300:],dt)); print(rows[-1],flush=True); continue
        if j['verdict']=='EARNED':
            rows.append((e,s,b,"EARNED",j['design']['SS']['x'],j['objective']['value'],j['objective']['lower_bound'],j['guaranteed']['y1'][1],dt))
        else: rows.append((e,s,b,j['verdict'],j.get('why'),dt))
        print(rows[-1],flush=True)
json.dump(rows,open("examples/blind6/work_c06/sweep/rows.json","w"),indent=1)
