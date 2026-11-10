# P12 capital rationing: subsets, budget 200, NPV -5% each (worst), choose max worst-case NPV; req >= 74.0
import itertools
P={'A':(60,150),'B':(25,100),'C':(10,70),'D':(15,50),'E':(11,30),'F':(7,20),'G':(2,10)}
B=200;res=[]
for m in range(1,8):
    for s in itertools.combinations(P,m):
        inv=sum(P[k][1] for k in s)
        if inv<=B: res.append((0.95*sum(P[k][0] for k in s),sum(P[k][0] for k in s),inv,s))
res.sort(reverse=True)
for r in res[:6]: print(r)
w=res[0][0];print("best worst-case NPV",w,"margin over 74.0: %.3f%%"%((w-74)/74*100))
