import math, itertools
Sn=[400,630,800,1000,1250,1600]
uk=[4,4,6,6,6,6]
cls={"S":dict(P0=[650,860,1000,1150,1350,1650],Pk=[4600,6500,7600,9500,11000,14000],pr=[5.8,7.4,8.8,10.2,12.4,15.5]),
     "L":dict(P0=[430,600,700,770,950,1150],Pk=[4600,6000,7000,9000,10500,13500],pr=[6.9,8.8,10.5,12.0,14.6,18.0]),
     "A":dict(P0=[190,260,300,340,400,480],Pk=[4800,6700,7900,9800,11500,14500],pr=[8.4,10.8,12.8,14.6,17.5,22.0])}
caps=[("none",0,0.0),("C100",100,1.2),("C150",150,1.7),("C200",200,2.2)]
# seasons: hours, P kW lo,hi, pf lo,hi
seas=[("winter",2184,520,600,0.80,0.86),("spring",2208,400,470,0.82,0.88),("summer",2208,330,400,0.82,0.88),("autumn",2160,430,500,0.80,0.86)]
night=(60,80,0.80,0.86)   # summer night light-load, for voltage rise
G=0.012; Y=30; DISC=0.03
def S_of(P,pf,Qc):
    Q=P*math.tan(math.acos(pf)); return math.sqrt(P*P+(Q-Qc)**2), Q-Qc
def evaluate(i,c,cp,detail=False):
    Sr=Sn[i]; d=cls[c]; P0=d["P0"][i]; Pk=d["Pk"][i]; u=uk[i]
    r=Pk/(Sr*1000); x=math.sqrt((u/100)**2-r*r)
    # worst-case loss energy: monotone in P and pf? S depends on Q-Qc : evaluate corners
    def seasonloss(s,gf,corner):
        name,h,plo,phi,flo,fhi=s
        best=None
        out=[]
        for P in (plo,phi):
            for pf in (flo,fhi):
                Sx,_=S_of(P*gf,pf,cp[1])
                L=h*(P0+Pk*(Sx/Sr)**2+2.5*cp[1])/1000.  # kWh ; cap loss 2.5 W/kvar
                out.append(L)
        return max(out),min(out)
    # year-1 annual loss (worst= max)
    y1=sum(seasonloss(s,1.0,0)[0] for s in seas)
    # lifetime PV, tariff worst 0.14
    pv=0
    for y in range(1,Y+1):
        gf=(1+G)**(y-1)
        E=sum(seasonloss(s,gf,0)[0] for s in seas)
        pv+=E*0.14/1000/(1+DISC)**y   # kEUR
    cost=d["pr"][i]+cp[2]+pv
    # R1 peak S at year 30 winter (corner max)
    S30=max(S_of(P*(1+G)**(Y-1),pf,cp[1])[0] for P in (520,600) for pf in (0.80,0.86))
    # wait: also over-compensation at summer where Qc>Q irrelevant for peak; check all seasons
    S30=max(S_of(P*(1+G)**(Y-1),pf,cp[1])[0] for s in seas for P in s[2:4] for pf in s[4:6])
    # R2 regulation peak at year 30 (max over corners) and rise at night year 1..(min)
    def dU(P,pf):
        Sx,qn=S_of(P,pf,cp[1]); p=P/Sr; q=qn/Sr; return 100*(p*r+q*x)
    dUpk=max(dU(P*(1+G)**(Y-1),pf) for s in seas for P in s[2:4] for pf in s[4:6])
    dUnight=min(dU(P,pf) for P in night[:2] for pf in night[2:])
    return dict(cost=cost,y1=y1,S30=S30/Sr,dUpk=dUpk,dUnight=dUnight,capex=d["pr"][i]+cp[2])
rows=[]
for i in range(6):
  for c in cls:
    for cp in caps:
      e=evaluate(i,c,cp); e.update(Sn=Sn[i],c=c,cap=cp[0]); rows.append(e)
if __name__=="__main__":
    mass={"S":[1150,1650,2000,2350,2900,3600]}
    mass["L"]=[round(m*1.08,-1) for m in mass["S"]]; mass["A"]=[round(m*1.20,-1) for m in mass["S"]]
    print(mass)
    L1,SMAX,DUPK,DUN,MM=32000,1.05,3.8,-0.8,3000
    ok=[]
    for e in rows:
        e["mass"]=mass[e["c"]][Sn.index(e["Sn"])]
        if e["y1"]<=L1 and e["S30"]<=SMAX and e["dUpk"]<=DUPK and e["dUnight"]>=DUN and e["mass"]<=MM: ok.append(e)
    ok.sort(key=lambda e:e["cost"])
    print(len(rows),len(ok))
    for e in ok[:5]: print({k:(round(v,3) if isinstance(v,float) else v) for k,v in e.items()})
