from mycalc import *
import itertools
res=[]
mins={'none':[24,30,23,14],'basic':[23,29,22,14],'advanced':[22,27,21,13]}
for ivr in IVR:
    m=mins[ivr]
    for ex in itertools.product(range(0,6),repeat=4):
        n=[m[i]+ex[i] for i in range(4)]
        c=cost(ivr,n)
        res.append((c,ivr,n))
res.sort()
found=0
for c,ivr,n in res:
    if feasible(ivr,n):
        print(round(c,2),ivr,n,worst(ivr,n)); found+=1
        if found>=6: break
