import math, itertools
PER=[("P1 08-11",180,220),("P2 11-14",230,280),("P3 14-17",170,210),("P4 17-20",90,120)]   # calls/h
AHT=(4.8,5.6)      # min incl. wrap-up (shared)
IVR={"none":((0,0),0.0),"basic":((0.06,0.10),14.0),"adv":((0.12,0.18),31.0)}  # deflection range, kEUR/yr
RATE=[33.0,36.0,38.0,45.0]
COSTP=[r*3*300/1000 for r in RATE]
def erlangc(n,A):
    if n<=A: return 1.0
    # iterative
    term=1.0; s=1.0
    for k in range(1,n):
        term*=A/k; s+=term
    term*=A/n   # A^n/n!
    top=term*n/(n-A)
    return top/(s+top)
def SL(n,lam,aht,t=20.0):
    A=lam*aht/60.0
    if n<=A: return 0.0
    pw=erlangc(n,A)
    return 1-pw*math.exp(-(n-A)*t/(aht*60.0))
def evaluate(ns,ivr):
    (dlo,dhi),_=IVR[ivr]
    worst_each=[1.0]*4; worst_avg=1.0; occmax=0
    # corners: aht lo/hi, deflection lo/hi?? deflection low is worst; lam hi worst for each period; but weighted avg: try all corners of lam
    dd=1-dlo
    for aht in AHT:
        lam_hi=[hi*dd for (_,lo,hi) in PER]
        for i in range(4):
            worst_each[i]=min(worst_each[i],SL(ns[i],lam_hi[i],aht))
            occmax=max(occmax,lam_hi[i]*aht/60/ns[i])
        for corner in itertools.product((0,1),repeat=4):
            lam=[(PER[i][1] if c==0 else PER[i][2])*dd for i,c in enumerate(corner)]
            for dsel in (dlo,dhi):
                lam2=[(PER[i][1] if c==0 else PER[i][2])*(1-dsel) for i,c in enumerate(corner)]
                s=sum(l*SL(n,l,aht) for n,l in zip(ns,lam2))/sum(lam2)
                worst_avg=min(worst_avg,s)
    return worst_each,worst_avg,occmax
if __name__=="__main__":
    R1,R2,OCC,SEAT=0.70,0.87,0.92,60
    out=[]
    # minimal n per period for R1 and occ at worst-case, per ivr
    for ivr in IVR:
        dlo=IVR[ivr][0][0]
        mins=[]
        for i,(_,lo,hi) in enumerate(PER):
            lam=hi*(1-dlo)
            m=1
            while not (all(SL(m,lam,a)>=R1 for a in AHT) and lam*AHT[1]/60/m<=OCC): m+=1
            mins.append(m)
        print(ivr,"min per period",mins)
        rng=[range(m,m+9) for m in mins]
        for ns in itertools.product(*rng):
            if max(ns)>SEAT: continue
            we,wa,om=evaluate(ns,ivr)
            if min(we)>=R1 and wa>=R2 and om<=OCC:
                out.append((sum(n*c for n,c in zip(ns,COSTP))+IVR[ivr][1],ivr,ns,round(wa,4),[round(x,3) for x in we],round(om,3)))
    out.sort()
    for r in out[:6]: print(r)
