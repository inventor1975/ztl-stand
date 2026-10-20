import math, itertools
INS={'MW-30':(30,.040,.30,7.5),'MW-50':(50,.040,.30,11.0),'PIR-30':(30,.026,.08,13.0),'PIR-40':(40,.026,.08,16.0),'PIR-50':(50,.026,.08,19.5)}
CAB={'T10':(10,4.8),'T15':(15,6.2),'T20':(20,8.0),'T30':(30,11.5)}
r1=0.045
def q(t,k10,w,ho,Ta,Tp=3):
    Tm=(Tp+Ta)/2; k=k10*(1+0.0018*(Tm-10))*(1+w); r2=r1+t/1000
    return 1.3*(Tp-Ta)/(math.log(r2/r1)/(2*math.pi*k)+1/(2*math.pi*r2*ho))
def P(P10,V,Tp=3): return P10*(1+0.012*(10-Tp))*(V/230)**1.6
def ok(i,c,Ta,verbose=False):
    t,k10,w,pr=INS[i]; P10,cp=CAB[c]
    qmax=q(t,k10,w,25,Ta)  # worst: w max, ho max (higher ho = more loss)
    r1_=P(P10,207)-qmax; r2_=P(P10,253); r3=2*(r1+t/1000)
    if verbose: print(i,c,'qmax %.3f Pmin %.3f Pmax %.3f D %.0f'%(qmax,P(P10,207),r2_,r3*1000))
    return r1_>=0 and r2_<=24 and r3<=0.18
def best(Ta):
    res=[((INS[i][3]+CAB[c][1])*140,i,c) for i in INS for c in CAB if ok(i,c,Ta)]
    return sorted(res)
if __name__=='__main__':
    for i in INS:
        for c in CAB: ok(i,c,-40,True)
    print(best(-40))
    lo,hi=-200,-40
    for _ in range(60):
        m=(lo+hi)/2
        if best(m): hi=m
        else: lo=m
    print(hi,best(hi))
    # per-design limit
    for i in INS:
        for c in CAB:
            lo,hi=-300,-40
            if not ok(i,c,-40): continue
            for _ in range(60):
                m=(lo+hi)/2
                if ok(i,c,m): hi=m
                else: lo=m
            print(i,c,hi)
