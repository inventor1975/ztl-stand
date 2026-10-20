import itertools
ded={5:128,10:104,20:82,40:63,80:48}      # deductible kEUR -> premium kEUR/yr (nominal)
sl={'none':(None,0,0),'SL60':(60,200,16),'SL100':(100,200,10),'SL160':(160,200,6)}  # attach, limit, price kEUR/yr
prem_f=(1.00,1.08)
sev={'small':(2.0,8.0),'large':(60.0,120.0),'cat':(800.0,1200.0)}
scen={'normal':{'small':(20,26),'large':(0,1),'cat':(0,0)},
      'bad':{'small':(28,36),'large':(2,3),'cat':(0,0)},
      'cat':{'small':(24,30),'large':(1,2),'cat':(1,1)}}
carry=0.05; credit=40.0
limits={'normal':210.0,'bad':300.0}; stab=62.0; total3=680.0
def retained(D,slname,sc,high=True):
    idx=1 if high else 0
    r=0
    for k in ('small','large','cat'):
        n=scen[sc][k][idx]; s=sev[k][idx]
        r+=n*min(s,D)
    a,lim,_=sl[slname]
    if a is not None and r>a: r=r-min(r-a,lim)
    return r
def totals(D,slname,R,high=True):
    out={}
    for sc in scen:
        P=ded[D]*(prem_f[1] if high else prem_f[0])+sl[slname][2]
        out[sc]=P+retained(D,slname,sc,high)+carry*R
    return out
def check(D,slname,R):
    hi=totals(D,slname,R,True); lo=totals(D,slname,R,False)
    m={}
    m['R1']=limits['normal']/hi['normal']-1
    m['R2']=limits['bad']/hi['bad']-1
    m['R3']=(R+credit)/retained(D,slname,'cat',True)-1 if retained(D,slname,'cat',True)>0 else 1
    diff=max(retained(D,slname,'bad',True)-retained(D,slname,'normal',False),retained(D,slname,'normal',True)-retained(D,slname,'bad',False),1e-9)
    m['R4']=stab/diff-1
    m['R5']=total3/sum(hi.values())-1
    return m
def best():
    res=[]
    for D in ded:
        for s in sl:
            r=max(0,retained(D,s,'cat',True)-credit)
            m=check(D,s,r)
            res.append((min(m.values()),D,s,round(r,1),{k:round(v,3) for k,v in m.items()},{k:round(v,1) for k,v in totals(D,s,r).items()}))
    return sorted(res,key=lambda x:-x[0])
if __name__=='__main__':
    for r in best()[:8]: print(r)
