import math, itertools
import numpy as np
knots=[(5,12.8),(10,11.3),(15,10.1),(20,9.1),(25,8.3),(30,7.6),(35,7.0)]
def Cs(T): return float(np.interp(T,[k[0] for k in knots],[k[1] for k in knots]))
seasons={"winter":dict(days=90,hrs=12,W=(4000,5000),T=(8,11)),
 "spring":dict(days=92,hrs=10,W=(9000,11000),T=(16,19)),
 "summer":dict(days=92,hrs=8,W=(16000,19000),T=(26,30)),
 "autumn":dict(days=91,hrs=11,W=(14000,16500),T=(14,18))}
aer={"PW2":(2.0,2.2,3.6),"PW37":(3.7,2.0,5.2),"PROP":(1.5,1.7,2.3),"DIFF":(5.5,1.4,6.8)}
def season(T,W,m,P,SAE,lox):
    cs=Cs(T); kd=0.015*1.024**(T-20); r=0.30*W*1.08**(T-20)/24000+0.15*1.065**(T-20)
    a=m*P*SAE*1000*0.90*1.024**(T-20)/(9.09*24000)
    css=((kd+0.95*a)*cs-r)/(kd+a)
    ox=0.25 if lox else 0.0
    cinf=cs-(r-ox)/kd
    c2=max(cinf+(css-cinf)*math.exp(-kd*2),0)
    return css,c2
def worst(sname,m,typ,lox,ng=61):
    s=seasons[sname];P,SAE,_=aer[typ]
    wc=1e9;w2=1e9
    for T in np.linspace(*s["T"],ng):
        for W in s["W"]:
            c,c2=season(T,W,m,P,SAE,lox); wc=min(wc,c); w2=min(w2,c2)
    return wc,w2
def mmin(sname,typ,lox):
    for m in range(0,17):
        c,c2=worst(sname,m,typ,lox)
        if c>=4.0 and c2>=3.0: return m
    return None
if __name__=="__main__":
    for typ in aer:
        for lox in (0,1):
            print(typ,lox,{s:mmin(s,typ,lox) for s in seasons})
