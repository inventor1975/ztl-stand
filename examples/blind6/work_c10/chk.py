import math, itertools
def model(Td,Mf,M0,k0f,n,RH0,T0,Ta,qa):
    RHd=RH0*math.exp(17.27*T0/(T0+237.3)-17.27*Td/(Td+237.3))
    Me=(-math.log(1-RHd)/(8.6541e-5*(Td+49.81)))**(1/1.8634)/100
    MR=(Mf-Me)/(M0-Me)
    k=k0f*6.5e4*math.exp(-4400/(Td+273.15))
    t=(-math.log(MR)/k)**(1/n)
    DI=0.04*t*math.exp(0.08*(Td-60))
    Ts=max(Ta,Ta+6-0.3*qa)
    Mwb=100*Mf/(1+Mf)
    ST=math.exp(7.4-0.6*(Mwb-14)-0.075*(Ts-10))
    return Me,t,DI,ST
def worst(Td,Mf,qa):
    # corners
    best=None
    res=dict(t=0,DI=0,ST=1e9)
    arg={}
    for M0,k0f,n,RH0,T0 in itertools.product((0.30,0.36),(0.9,1.1),(0.82,0.88),(0.55,0.80),(12,22)):
        Me,t,DI,ST=model(Td,Mf,M0,k0f,n,RH0,T0,13,qa)
        if t>res['t']: res['t']=t; arg['t']=(M0,k0f,n,RH0,T0,Me)
    for Ta in (10,16):
        Me,t,DI,ST=model(Td,Mf,0.3,1,0.85,0.6,15,Ta,qa)
        res['ST']=min(res['ST'],ST)
    res['DI']=0.04*res['t']*math.exp(0.08*(Td-60))
    return res,arg
if __name__=="__main__":
    dr={'DR4':(4,85,26),'DR6':(6,85,33),'DR8':(8,80,40),'DR10':(10,75,46)}
    fans={'none':(0,0),'F8':(8,2.4),'F15':(15,4.1),'F25':(25,7.5)}
    best=[]
    for dn,(B,Tmax,pr) in dr.items():
        for fn,(qa,fp) in fans.items():
            for Td in [50+0.25*i for i in range(0,int((Tmax-50)/0.25)+1)]:
                # Mf largest s.t. ST>=360 -> bisect over Mf in [0.14,0.20], then check t constraints (t decreasing in Mf)
                lo,hi=0.14,0.20
                # ST constraint gives upper bound on Mf
                def ok_ST(Mf): return worst(Td,Mf,qa)[0]['ST']>=360
                def ok_t(Mf):
                    r=worst(Td,Mf,qa)[0]
                    return B/(r['t']+1)>=0.8 and r['DI']<=0.6
                # t decreases with Mf: find min Mf for t; ST: max Mf
                try:
                    if not ok_ST(0.14): continue
                    a,b=0.14,0.20
                    if ok_ST(0.20): Mmax=0.20
                    else:
                        a,b=0.14,0.20
                        for _ in range(50):
                            m=(a+b)/2
                            if ok_ST(m): a=m
                            else: b=m
                        Mmax=a
                    if not ok_t(Mmax): continue
                    # cost decreases in Mf: choose Mmax
                    Mf=Mmax
                    W=1000*(0.36-Mf)/1.36
                    cost=pr+fp+900*W*0.09*(1+0.012*(Td-60))/1000
                    best.append((cost,dn,fn,Td,Mf))
                except Exception as e:
                    pass
    best.sort()
    for b in best[:12]: print(b)
