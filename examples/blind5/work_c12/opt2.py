from mycalc import *
import itertools
mins={'none':[24,30,23,14],'basic':[23,29,22,14],'advanced':[22,27,21,13]}
for ivr in IVR:
    m=mins[ivr]; best=None
    L=[]
    for ex in itertools.product(range(0,9),repeat=4):
        n=[m[i]+ex[i] for i in range(4)]
        L.append((cost(ivr,n),n))
    L.sort()
    k=0
    for c,n in L:
        f=feasible(ivr,n)
        if k<4 or f:
            out,M=worst(ivr,n)
            print(ivr,round(c,1),n,f,'M',round(M,2),'minSL',[round(o[0],3) for o in out]); k+=1
        if f: break
