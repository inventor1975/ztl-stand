import json,sys,re
t=open(sys.argv[1]).read()
try: j=json.loads(t[t.index('\n{'):] if '\n{' in t else t)
except Exception as e: print(t[:1500]); sys.exit()
print(j['verdict'],j.get('designs_count'),j.get('excluded_by_where'),j.get('checked_by'))
def val(s):
    m=re.search(r'R=([0-9/]+)',s); a=m.group(1)
    return eval(a.replace('/','/')) if '/' in a else float(a)
ds=j['designs']
for v in ('EARNED','REFUTED','OPEN'):
    xs=sorted(val(d['design']) for d in ds if d['verdict']==v)
    if xs: print(v,len(xs),'min',xs[0],'max',xs[-1])
print([ (val(d['design']),d.get('fails'),d.get('by_at_witness')) for d in ds if d['verdict']=='REFUTED'][:0])
