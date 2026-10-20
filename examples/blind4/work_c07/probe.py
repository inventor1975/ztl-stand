import json,subprocess,time,sys
def runf(path):
    t=time.time()
    r=subprocess.run(['./run.sh',path],capture_output=True,text=True)
    try: j=json.loads(r.stdout)
    except Exception: j={'verdict':'NOJSON','raw':r.stdout[-300:]+r.stderr[-300:]}
    return j,round(time.time()-t,1)
