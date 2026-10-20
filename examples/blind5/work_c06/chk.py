import math, itertools
gw=9.81
def ev(B,Df,phid,c,gam,N,M,zw,E):
    phi=math.radians(phid)
    Dbf=max(Df-0.45,0)
    W=24*0.45*B+gam*B*Dbf
    Nt=N+W; e=M/Nt; Bp=B-2*e; q=Nt/Bp
    Nq=math.exp(math.pi*math.tan(phi))*math.tan(math.pi/4+phi/2)**2
    Nc=(Nq-1)/math.tan(phi); Ng=(Nq-1)*math.tan(1.4*phi)
    q0=gam*Df if zw>=Df else gam*zw+(gam-gw)*(Df-zw)
    if zw<=Df: gb=gam-gw
    elif zw<Df+Bp: gb=(gam-gw)+gw*(zw-Df)/Bp
    else: gb=gam
    qu=c*Nc+q0*Nq+0.5*gb*Bp*Ng
    s=q*Bp*(1-0.09)*1.12/(E*1000)*1000
    return dict(FS=qu/q,s=s,e=e,Bp=Bp,Nq=Nq,qu=qu,q=q,gb=gb,q0=q0)
rng=dict(phid=(25,29),c=(0,4),gam=(17.5,19.5),N=(100,115),M=(8,18),zw=(0.8,2.2),E=(10,16))
import sys
Bs=[0.6,0.8,1.0,1.2,1.5,1.8,2.0,2.4]; Ds=[0.5,0.8,1.0,1.2,1.5]
# corners + zw grid
zws=[0.8+0.05*i for i in range(29)]
def worst(B,Df):
    fs=1e9;s=0;e=0;ar=None
    for ph in rng['phid']:
      for c in rng['c']:
        for g in rng['gam']:
          for N in rng['N']:
            for M in rng['M']:
              for zw in zws+[Df,Df+0.001,Df-0.001]:
                if not .8<=zw<=2.2: continue
                for E in rng['E']:
                    r=ev(B,Df,ph,c,g,N,M,zw,E)
                    if r['FS']<fs: fs=r['FS'];ar=(ph,c,g,N,M,zw,E)
                    s=max(s,r['s']);e=max(e,r['e'])
    return fs,s,e,ar
if __name__=="__main__":
    for B in Bs:
      for Df in Ds:
        fs,s,e,ar=worst(B,Df)
        cost=72*B+28*(B+.6)*Df+32
        ok= fs>=3 and s<=25 and e<=B/6 and B<=2
        print(B,Df,round(cost,2),round(fs,3),round(s,2),round(e,4),round(B/6,4),ok,ar)
