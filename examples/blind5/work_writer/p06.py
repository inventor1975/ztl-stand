import math, itertools
BS=[0.6,0.8,1.0,1.2,1.5,1.8,2.0,2.4]
DFS=[0.5,0.8,1.0,1.2,1.5]
PH=(25.0,29.0); CC=(0.0,4.0); GM=(17.5,19.5); NL=(100.0,115.0); MM=(8.0,18.0); EM=(10.0,16.0); ZW=(0.8,2.2)
GW=9.81
def Nfac(phi):
    p=math.radians(phi)
    Nq=math.exp(math.pi*math.tan(p))*math.tan(math.pi/4+p/2)**2
    Nc=(Nq-1)/math.tan(p); Ng=(Nq-1)*math.tan(1.4*p)
    return Nc,Nq,Ng
def FSset(B,Df,phi,c,g,N,M,zw):
    W=24*0.45*B+g*B*max(Df-0.45,0)
    Nt=N+W
    e=abs(M)/Nt; Be=B-2*e
    if Be<=0: return 0.0,0.0,e
    q=Nt/Be
    Nc,Nq,Ng=Nfac(phi)
    if zw<=Df: q0=g*zw+(g-GW)*(Df-zw)
    else: q0=g*Df
    gp=g-GW
    if zw<=Df: gb=gp
    elif zw<Df+Be: gb=gp+(zw-Df)/Be*(g-gp)
    else: gb=g
    qu=c*Nc+q0*Nq+0.5*gb*Be*Ng
    return qu/q,q,e
def worst(B,Df):
    best=(1e9,None)
    fs=1e9; smax=0; emax=0
    for phi,c,g,N,M,zw in itertools.product(PH,CC,GM,NL,MM,ZW):
        f,q,e=FSset(B,Df,phi,c,g,N,M,zw)
        fs=min(fs,f); emax=max(emax,e)
        for E in EM:
            s=q*(B-2*e)*(1-0.3**2)*1.12/(E*1000)*1000  # mm : q kPa*B m/(E MPa*1000 kPa) -> m -> *1000 mm
            smax=max(smax,s)
    return fs,smax,emax
if __name__=="__main__":
    print("B Df FSmin smax_mm emax/B")
    for Df in DFS:
        print(Df,[ (B,round(worst(B,Df)[0],2)) for B in BS])
    for B in (1.5,1.8,2.4):
        print(B,[(Df,round(worst(B,Df)[1],1),round(worst(B,Df)[2]/B,3)) for Df in DFS])
