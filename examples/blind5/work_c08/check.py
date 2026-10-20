import itertools, math
packs=[(40,285,6.4),(52,365,8.1),(64,440,9.8),(77,530,11.9),(90,610,13.8),(110,745,17.0)]
tyres=[(0.0105,0),(0.0082,0.35),(0.0072,0.70)]
aeros=[(1.0,0),(0.92,0.5),(0.86,1.4)]
heat=[(2.6,0),(1.1,0.85)]
sol=[(0,0,0),(0.9,18,1.1)]
routes=[(140,26,45,2.4,.5),(170,52,70,.6,.35),(158,95,110,.05,.15)]
RET=math.exp(-0.028*8)
def ev(p,t,a,h,s,cda,pay,kr,ft):
    E,mp,_=p; m=2050+mp+pay+s[1]
    U=E*RET*ft*0.92+0.35*s[0]
    rng=[];cons=0
    for D,va,vc,st,sh in routes:
        v=vc/3.6
        F=t[0]*kr*m*9.81+0.5*1.2*cda*a[0]*v*v
        K=st/1000*0.5*m*v*v*0.45
        Et=(F+K)*1000/(0.88*3600)  # Wh/km
        Ec=Et+(0.4+h[0])*1000/va
        Ew=Et+0.4*1000/va
        rng.append(U*1000/Ec)
        cons+=sh*(0.5*Ec+0.5*Ew)
    return rng,cons
res=[]
for p,t,a,h,s in itertools.product(packs,tyres,aeros,heat,sol):
    cost=p[2]+t[1]+a[1]+h[1]+s[2]
    mg=2050+p[1]+s[1]+850
    # worst case: range worst = cdaMax,payMax,krMax,ftMin; cons worst = max all (ft irrelevant)
    rng,_=ev(p,t,a,h,s,1.15,850,1.10,0.82)
    _,cons=ev(p,t,a,h,s,1.15,850,1.10,0.82)
    ok = all(r>=r_[0] for r,r_ in zip(rng,routes)) and cons/10<=24.8 and mg<=3500
    res.append((cost,ok,p[0],t[0],a[0],h[0],s[0],[round(x,3) for x in rng],round(cons,3),mg))
res.sort()
print([r for r in res if r[1]][:5])
# the stand's design
print(ev(packs[3],tyres[2],aeros[2],heat[1],sol[0],1.15,850,1.10,0.82))
print(ev(packs[3],tyres[2],aeros[2],heat[1],sol[0],1.05,500,0.90,0.92))
# near misses
for r in res[:12]: print(r)
