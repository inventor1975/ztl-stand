import math
g=9.81
straps={'S1':(1500,350,12),'S2':(2500,450,19),'S3':(5000,650,38)}   # LC daN, STF daN, EUR
mats={'M0':(0.30,0.40,0),'M1':(0.55,0.65,140),'M2':(0.70,0.75,260)} # mu range, EUR
c={'fwd':0.8,'rear':0.5,'side':0.5}; cz=0.8
stf_tol=(0.85,1.15); alpha=(62,75); kf_lo=0.85; nmax=10
def need_n(m,S,M):
    LC,STF,_=straps[S]; mu=mats[M][0]
    Fv=STF*10/1000*stf_tol[0]*math.sin(math.radians(alpha[0]))*(1+kf_lo)  # kN
    worst=max(m*g/1000*(cc/mu-cz) for cc in c.values())
    return worst/Fv, Fv
def best(m):
    out=[]
    for S in straps:
        for M in mats:
            nn,Fv=need_n(m,S,M)
            n=max(0,math.ceil(nn-1e-12))
            if n<=nmax:
                out.append((n*straps[S][2]+mats[M][2],S,M,n,round(nn,3)))
    return sorted(out)
if __name__=='__main__':
    print(best(8400)[:6])
    lo,hi=8400,40000
    while hi-lo>0.01:
        mid=(lo+hi)/2
        if best(mid): lo=mid
        else: hi=mid
    print(lo)
