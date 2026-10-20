import math, itertools, numpy as np
V=24000.0
CSX=[5,10,15,20,25,30,35]; CSY=[12.8,11.3,10.1,9.1,8.3,7.6,7.0]
def Cs(T): return float(np.interp(T,CSX,CSY))
BETA=0.95; ALPHA=0.90; THETA=1.024
KD=0.015   # 1/h at 20C, times 1.024^(T-20)
# seasons: name, days, night hours, biomass lo,hi, T lo,hi
SEAS=[("winter",90,12,4000,5000,8,11),("spring",92,10,9000,11000,16,19),("summer",92,8,16000,19000,26,30),("autumn",91,11,14000,16500,14,18)]
AER={"PW2":(2.0,2.2,3.6),"PW37":(3.7,2.0,5.2),"PROP":(1.5,1.7,2.3),"DIFF":(5.5,1.4,6.8)}  # kW, SAE kgO2/kWh, kEUR installed
LOX=(6000.0,2.0,6.5)   # g/h, hours, kEUR
NMAX=16
PRICE=0.16
def resp(T,Wb):
    return (0.30*Wb*1.08**(T-20))/V + 0.15*1.065**(T-20)    # g/m3/h
def Css(T,Wb,m,a):
    P,SAE,_=AER[a]; cs=Cs(T); r=resp(T,Wb)
    kd=KD*1.024**(T-20)
    Ka=m*P*SAE*1000*ALPHA*THETA**(T-20)/9.09/V   # 1/h per (mg/L)/(Cs20) scaled per volume  (g/h per mg/L)/V
    # r = kd (cs-C) + Ka (beta cs - C)
    C=(kd*cs+Ka*BETA*cs-r)/(kd+Ka)
    return C
def after_fail(T,Wb,C0,lox,hrs=2.0):
    cs=Cs(T); r=resp(T,Wb); kd=KD*1.024**(T-20)
    ox=LOX[0]/V if lox else 0.0
    Cinf=cs-(r-ox)/kd
    t=hrs
    return max(0.0,Cinf+(C0-Cinf)*math.exp(-kd*t))
def worst(a,n_run,lox):   # n_run list of running counts per season
    cmin=1e9; fmin=1e9
    for (nm,d,h,wl,wh,tl,th),m in zip(SEAS,n_run):
        for T in np.linspace(tl,th,9):
            for Wb in (wl,wh):
                C=Css(T,Wb,m,a); cmin=min(cmin,C)
                fmin=min(fmin,after_fail(T,Wb,C,lox))
    return cmin,fmin
def energy(a,n_run): return sum(d*h*m*AER[a][0] for (nm,d,h,*_),m in zip(SEAS,n_run))  # kWh
def table():
    tab={}
    for a in AER:
        for si,s in enumerate(SEAS):
            for m in range(0,NMAX+1):
                cmin=1e9; f0=1e9; f1=1e9
                for T in np.linspace(s[5],s[6],9):
                    for Wb in (s[3],s[4]):
                        C=Css(T,Wb,m,a); cmin=min(cmin,C)
                        f0=min(f0,after_fail(T,Wb,C,False)); f1=min(f1,after_fail(T,Wb,C,True))
                tab[(a,si,m)]=(cmin,f0,f1)
    return tab
def search(CMIN,FMIN,LOADMAX,ECAP):
    tab=table(); best=[]
    for a in AER:
        P=AER[a][0]
        for lox in (False,True):
            for ms in itertools.product(range(NMAX+1),repeat=4):
                n=max(ms)
                if n==0 or n*P>LOADMAX: continue
                ok=True
                for si,m in enumerate(ms):
                    c,f0,f1=tab[(a,si,m)]
                    if c<CMIN or (f1 if lox else f0)<FMIN: ok=False;break
                if not ok: continue
                E=energy(a,ms)
                if E>ECAP: continue
                capex=n*AER[a][2]+(LOX[2] if lox else 0)
                tot=capex+10*E*PRICE/1000
                best.append((tot,a,lox,ms,n,E,capex))
    best.sort(key=lambda r:r[0]); return best
if __name__=="__main__":
    b=search(4.0,2.5,40.0,150000)
    print(len(b))
    for r in b[:6]: print(r)
    print("no-lox best:",[r for r in b if not r[2]][:2])
