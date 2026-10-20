import math
models = {"U1":(5,1.25,90,60,.22,2100,60),"U2":(5,1.25,150,110,.4,2600,110),"U3":(7.5,1.25,150,110,.4,3100,110),
"U4":(7.5,1.5,150,180,.62,3900,160),"U5":(10,1.5,150,180,.62,4300,160),"U6":(10,1.5,200,260,.88,5200,220),
"U7":(6,1.25,200,200,.7,4600,190),"U8":(12.5,2,200,330,1.1,6100,280)}
regs={"p":(40,.68,.80,8,14,.10),"a":(24,.76,.86,12,24,.60),"l":(8,.82,.90,22,30,.30)}
pts=[(8,.88),(14,.96),(20,1.0),(26,.97),(30,.93)]
def fT(T):
    for (a,fa),(b,fb) in zip(pts,pts[1:]):
        if a<=T<=b: return fa+(fb-fa)*(T-a)/(b-a)
def Dfull(m,n,r,uvt,T):   # D at dim=1
    R,rq,L,P,kw,pr,lp=models[m]; Q,*_=regs[r]
    alpha=-math.log(uvt)
    I=P*1*0.7*0.9*fT(T)/(2*math.pi*R*L)*math.exp(-alpha*(R-rq))*1000  # mW/cm2
    V=math.pi*(R*R-rq*rq)*L; t=V/((Q*1e6/3600)/n)
    return 0.7*I*t
def worstD1(m,n,r):
    Q,u0,u1,t0,t1,fr=regs[r]
    Ts=[t0,t1]+[x for x,_ in pts if t0<x<t1]
    return min(Dfull(m,n,r,u0,T) for T in Ts)
Dreq=4*math.log(10)/0.23
best=None; res=[]
for m in models:
    R,rq,L,P,kw,pr,lp=models[m]
    for n in range(1,61):
        dims={}
        ok=True
        for r in regs:
            d=max(0.4,Dreq/worstD1(m,n,r)); 
            if d>1: ok=False
            dims[r]=d
        if not ok: continue
        if n*(kw*dims['p']+.03)>10: continue
        el=sum(regs[r][5]*n*(kw*dims[r]+.03) for r in regs)
        cost=n*pr+10*(0.14*8760*el+n*lp*8760/12000)
        res.append((cost,m,n,dims))
res.sort(key=lambda x:x[0])
for x in res[:8]: print(x)
print(len(res))
