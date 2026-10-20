from chk import *
import math
dr={'DR4':(4,85,26),'DR6':(6,85,33),'DR8':(8,80,40),'DR10':(10,75,46)}
fans={'none':(0,0),'F8':(8,2.4),'F15':(15,4.1),'F25':(25,7.5)}
def best(dn,fn):
    B,Tmax,pr=dr[dn]; qa,fp=fans[fn]
    out=None
    N=3500
    for i in range(N+1):
        Td=50+35*i/N
        if Td>Tmax: break
        def okST(Mf): return worst(Td,Mf,qa)[0]['ST']>=360
        if not okST(0.14): continue
        if okST(0.20): Mm=0.20
        else:
            a,b=0.14,0.20
            for _ in range(45):
                m=(a+b)/2
                if okST(m): a=m
                else: b=m
            Mm=a
        r=worst(Td,Mm,qa)[0]
        if not (B/(r['t']+1)>=0.8 and r['DI']<=0.6): continue
        W=1000*(0.36-Mm)/1.36
        c=pr+fp+900*W*0.09*(1+0.012*(Td-60))/1000
        if out is None or c<out[0]: out=(c,Td,Mm)
    return out
for dn in dr:
    for fn in ['none','F25']:
        print(dn,fn,best(dn,fn))
