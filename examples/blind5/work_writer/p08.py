import math, itertools
G=9.81; RHO=1.20
PACK=[("B40",40,285,6.4),("B52",52,365,8.1),("B64",64,440,9.8),("B77",77,530,11.9),("B90",90,610,13.8),("B110",110,745,17.0)]
TYRE=[("std",0.0105,0.0),("low",0.0082,0.35),("ultra",0.0072,0.70)]
AERO=[("none",1.00,0.0),("deflector",0.92,0.5),("full",0.86,1.4)]
HEAT=[("resistive",2.6,0.0),("heatpump",1.1,0.85)]   # aux power kW (cabin) in cold regime, common 0.4 kW electronics
SOLAR=[("none",0.0,0,0.0),("roof",0.9,18,1.1)]        # kWp, kg, kEUR
CURB=2050.0; GVW=3500.0
ROUTES=[("urban",140,26,45,2.4,0.50),("suburban",170,52,70,0.6,0.35),("motorway",158,95,110,0.05,0.15)]  # km, avg v km/h, cruise v km/h, stops per km, day share
CDA0=(1.05,1.15)          # m2 baseline (CdA), tolerance
PAY=(500,850); TF=(0.82,0.92); CRR_TOL=0.10
ETA_D=0.88; ETA_R=0.55; SOH=math.exp(-0.028*8)
RES=0.92   # usable fraction (reserve)
def cons(pack,tyre,aero,heat,solar,cda,pay,crr_f,cold=True):
    m=CURB+pack[2]+pay+solar[2]
    out={}
    for nm,dist,vavg,vc,stops,share in ROUTES:
        v=vc/3.6
        F=tyre[1]*crr_f*m*G+0.5*RHO*cda*aero[1]*v*v
        Ekin=stops*0.5*m*v*v*(1-ETA_R)         # J per km  (stops per km)
        Wh_km=(F*1000+Ekin)/ETA_D/3600
        aux=(0.4+(heat[1] if cold else 0.0))*1000/vavg   # Wh/km
        out[nm]=Wh_km+aux
    return out,m
def worst(pack,tyre,aero,heat,solar):
    res={}
    cdaH=CDA0[1]; payH=PAY[1]; crrH=1+CRR_TOL
    out,m=cons(pack,tyre,aero,heat,solar,cdaH,payH,crrH,True)
    # range at end of life, cold battery (TF low): energy available
    Eav=pack[1]*SOH*TF[0]*RES   # kWh
    # solar adds only for winter-case: ignore for worst (assumed 0.0) ... solar gives energy credit 
    esol=0.35*solar[1]   # kWh/day credit, winter-low
    rngs={k:(Eav+esol)/(v/1000) for k,v in out.items()}
    # average consumption over mix, kWh/100km, worst-case params but WARM (annual average -> heat only half the year handled via cold flag blend)
    avg=0
    outc,_=cons(pack,tyre,aero,heat,solar,cdaH,payH,crrH,True)
    outw,_=cons(pack,tyre,aero,heat,solar,cdaH,payH,crrH,False)
    for nm,dist,vavg,vc,stops,share in ROUTES:
        avg+=share*(0.5*outc[nm]+0.5*outw[nm])/10.0   # kWh/100km
    return rngs,avg,m
if __name__=="__main__":
    rows=[]
    for pk,ty,ae,he,so in itertools.product(PACK,TYRE,AERO,HEAT,SOLAR):
        rngs,avg,m=worst(pk,ty,ae,he,so)
        cost=pk[3]+ty[2]+ae[2]+he[2]+so[3]
        rows.append((cost,pk[0],ty[0],ae[0],he[0],so[0],{k:round(v/ [r for r in ROUTES if r[0]==k][0][1],3) for k,v in rngs.items()},round(avg,2),m))
    print(len(rows))
    AV=24.8
    ok=[r for r in rows if all(v>=1.0 for v in r[6].values()) and r[7]<=AV and r[8]<=GVW]
    ok.sort(key=lambda r:r[0])
    for r in ok[:6]: print(r)
    print("without GVW:")
    ok2=[r for r in rows if all(v>=1.0 for v in r[6].values()) and r[7]<=AV]
    ok2.sort(key=lambda r:r[0])
    for r in ok2[:4]: print(r)
