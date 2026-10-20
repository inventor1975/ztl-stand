import json,sys
variant=sys.argv[1] if len(sys.argv)>1 else 'main'
Q={}
def given(n,lo=None,hi=None,unit='',val=None,why=''):
    d={"role":"given","unit":unit,"why":why}
    if val is not None: d["value"]=val
    else: d["range"]=[lo,hi]
    Q[n]=d
def der(n,unit): Q[n]={"role":"derived","unit":unit}
cnt={'n':{'S':(20,26),'L':(0,1),'C':(0,0)},'b':{'S':(28,36),'L':(2,3),'C':(0,0)},'c':{'S':(24,30),'L':(1,2),'C':(1,1)}}
sev={'S':(2,8),'L':(60,120),'C':(800,1200)}
nm={'n':'normal','b':'bad','c':'catastrophe'}
kn={'S':'small','L':'large','C':'catastrophic'}
given('f','1.00','1.08',why='renewal factor, ONE value for all three years')
laws=[]
for s in 'nbc':
    terms=[]
    for k in 'SLC':
        lo,hi=cnt[s][k]
        if hi==0: continue   # no catastrophic claim in the normal/bad year (count exactly 0)
        if lo==hi: given('n%s_%s'%(k,s),val=str(lo),why='%s claims in %s year (exactly)'%(kn[k],nm[s]))
        else: given('n%s_%s'%(k,s),str(lo),str(hi),why='number of %s claims in %s year, any value'%(kn[k],nm[s]))
        Q['n%s_%s'%(k,s)]["unit"]=""
        given('s%s_%s'%(k,s),str(sev[k][0]),str(sev[k][1]),'kEUR','' if False else None) if False else None
        Q['s%s_%s'%(k,s)]={"role":"given","unit":"kEUR","range":[str(sev[k][0]),str(sev[k][1])],"why":"severity of a %s claim in %s year (independent copy per year)"%(kn[k],nm[s])}
        terms.append('n%s_%s*min(s%s_%s, DED.D)'%(k,s,k,s))
    der('r_'+s,'kEUR'); der('rp_'+s,'kEUR'); der('T_'+s,'kEUR')
    laws.append({"zfl":"r_%s == "%s+" + ".join(terms),"source":"retained loss before stop-loss = sum over claims of min(severity, D) (%s year)"%nm[s]})
    laws.append({"zfl":"rp_%s == r_%s - min(max(r_%s - SL.A, 0), SL.lim)"%(s,s,s),"source":"retained loss after stop-loss (%s year)"%nm[s]})
    laws.append({"zfl":"T_%s == f*DED.prem + SL.price + rp_%s + RES.x/20"%(s,s),"source":"total cost of a year = f*premium + SL price + r' + 5%% of R (%s year)"%nm[s]})
der('M3','kEUR'); der('D4','kEUR'); der('S','kEUR')
laws.append({"zfl":"M3 == rp_c - RES.x","source":"liquidity: r' minus reserve (R3 is M3 <= 40, the overdraft line)"})
laws.append({"zfl":"D4 == rp_b - rp_n","source":"budget stability: r'(bad) - r'(normal)"})
laws.append({"zfl":"S == T_n + T_b + T_c","source":"sum of the three scenario costs"})
req=[
 {"quantity":"T_n","op":"<=","value":"210","why":"R1 normal-year total cost <= 210 kEUR"},
 {"quantity":"T_b","op":"<=","value":"300","why":"R2 bad-year total cost <= 300 kEUR"},
 {"quantity":"M3","op":"<=","value":"40","why":"R3 catastrophe-year r' <= R + 40 (overdraft line 40 kEUR)"},
 {"quantity":"D4","op":"within","value":["-62","62"],"why":"R4 |r'(bad) - r'(normal)| <= 62 kEUR"},
 {"quantity":"S","op":"<=","value":"680","why":"R5 sum of the three scenario costs <= 680 kEUR"},
]
if variant=='noR4': req=[r for r in req if not r['why'].startswith('R4')]
if variant=='noR1': req=[r for r in req if not r['why'].startswith('R1')]
ded=[(5,128),(10,104),(20,82),(40,63),(80,48)]
sl=[("none",0,0,0),("SL60",60,200,16),("SL100",100,200,10),("SL160",160,200,6)]
brick={
 "stand":"ztl-stand/1",
 "quantities":Q,
 "slots":{"DED":{"from":["deductibles"]},"SL":{"from":["stoploss"]},"RES":{"from":["reserve"]}},
 "laws":laws,
 "requirements":req,
 "objective":{"minimize":"S","why":"continuous reserve needs a nominal objective (worst-case objective not available with continuous slots)"},
 "catalog":{
  "deductibles":{"ground":"premium table","fields":{"D":{"unit":"kEUR"},"prem":{"unit":"kEUR"}},
     "items":[{"name":"D%d"%d,"D":str(d),"prem":str(p)} for d,p in ded]},
  "stoploss":{"ground":"stop-loss table (none = limit 0, price 0)","fields":{"A":{"unit":"kEUR"},"lim":{"unit":"kEUR"},"price":{"unit":"kEUR"}},
     "items":[{"name":n,"A":str(a),"lim":str(l),"price":str(p)} for n,a,l,p in sl]},
  "reserve":{"continuous":{"field":"x","from":"0","to":"1000","unit":"kEUR"}},
 }}
out={'main':'../c11.json','noR4':'c11_noR4.json','noR1':'c11_noR1.json'}[variant]
json.dump(brick,open(out,'w'),indent=1)
