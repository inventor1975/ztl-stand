# my own brute check: all quantities monotone -> extremes at box corners (exact fractions)
from fractions import Fraction as F
import itertools
ded={5:128,10:104,20:82,40:63,80:48}
sl={'none':(0,0,0),'SL60':(60,200,16),'SL100':(100,200,10),'SL160':(160,200,6)}
sev={'S':(2,8),'L':(60,120),'C':(800,1200)}
cnt={'n':{'S':(20,26),'L':(0,1),'C':(0,0)},'b':{'S':(28,36),'L':(2,3),'C':(0,0)},'c':{'S':(24,30),'L':(1,2),'C':(1,1)}}
def rr(D,s,hi):
    i=1 if hi else 0
    return sum(cnt[s][k][i]*min(sev[k][i],D) for k in 'SLC')
def rp(r,A,lim): return r-min(max(r-A,0),lim)
res=[]
for D,p in ded.items():
  for name,(A,lim,price) in sl.items():
    rpmax={s:rp(rr(D,s,1),A,lim) for s in 'nbc'}
    rpmin={s:rp(rr(D,s,0),A,lim) for s in 'nbc'}
    R=max(0,rpmax['c']-40)
    cost={s:F(108,100)*p+price+rpmax[s]+F(R,20) for s in 'nbc'}
    ok=[cost['n']<=210,cost['b']<=300, rpmax['b']-rpmin['n']<=62 and rpmax['n']-rpmin['b']<=62, sum(cost.values())<=680]
    res.append((float(sum(cost.values())),D,name,R,[float(c) for c in cost.values()],rpmax,rpmin,ok))
for x in sorted(res,key=lambda t:t[0]): print(x)

print('--- minimal conflicts (my corner model)')
import itertools
def feas(sub):
    best=None
    for D,p in ded.items():
      for name,(A,lim,price) in sl.items():
        rpmax={s:rp(rr(D,s,1),A,lim) for s in 'nbc'}
        rpmin={s:rp(rr(D,s,0),A,lim) for s in 'nbc'}
        R=max(0,rpmax['c']-40) if 3 in sub else 0
        cost={s:F(108,100)*p+price+rpmax[s]+F(R,20) for s in 'nbc'}
        ok={1:cost['n']<=210,2:cost['b']<=300,3:True,
            4:rpmax['b']-rpmin['n']<=62 and rpmax['n']-rpmin['b']<=62,5:sum(cost.values())<=680}
        if all(ok[i] for i in sub):
            v=sum(cost.values())
            if best is None or v<best[0]: best=(float(v),D,name,R)
    return best
infeas=[]
for k in range(1,6):
    for sub in itertools.combinations(range(1,6),k):
        if feas(sub) is None and not any(set(s)<=set(sub) for s in infeas): infeas.append(sub)
print('minimal infeasible sets',infeas)
for drop in range(1,6): print('drop R%d ->'%drop, feas(tuple(i for i in range(1,6) if i!=drop)))
