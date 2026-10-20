import json, sys
step = sys.argv[1] if len(sys.argv)>1 else "1/10"   # h grid step
nmax = int(sys.argv[2]) if len(sys.argv)>2 else 25
out  = sys.argv[3] if len(sys.argv)>3 else "examples/blind4/c05.json"
nlo  = int(sys.argv[4]) if len(sys.argv)>4 else 0
Q={}
def g(n,v,u,why=None,**kw):
    d={"role":"given","unit":u}
    d.update(kw)
    if v is not None: d["value"]=v
    if why: d["why"]=why
    Q[n]=d
g("t","210","day","t_r: surcharge removed at 210 days")
g("Hf","4","m","permanent fill height",ground="problem statement")
g("gam","19","kN/m^3","fill unit weight",ground="problem statement")
g("Hmax","13/2","m","total fill limit for slope stability",ground="problem statement")
g("Sres","3/100","m","residual settlement allowed after removal (30 mm)",ground="problem statement")
g("cs","15/2","EUR/m^3","surcharge cost per m2 of footprint per m of height",ground="problem statement")
g("cinst","4","EUR","installation per drain",ground="problem statement")
g("hstep",step,"m","grid step of the surcharge height (discretisation of a continuous choice)")
Z={1:dict(A="6000",H="8",Cc="0.45",e0="1.4",s0="30",cv=("7/1825","3/365")),
   2:dict(A="9000",H="5",Cc="0.38",e0="1.2",s0="24",cv=("9/1825","9/730"))}
for z,d in Z.items():
    g(f"A{z}",d["A"],"m^2",f"zone {z} area",ground="site data")
    g(f"H{z}",d["H"],"m",f"zone {z} clay thickness = PVD length",ground="site data")
    g(f"Cc{z}",d["Cc"],"",ground="site data")
    g(f"e0{z}",d["e0"],"",ground="site data")
    g(f"sg{z}",d["s0"],"kPa",f"zone {z} effective stress at mid-layer",ground="site data")
    g(f"cv{z}",None,"m^2/day",f"zone {z} c_v, 1.4-3.0 / 1.8-4.5 m2/yr converted to m2/day (/365)",range=list(d["cv"]))
    g(f"rch{z}",None,"",f"zone {z} c_h/c_v in 2..3",range=["2","3"])
    g(f"rk{z}",None,"",f"zone {z} k_h/k_s in 2..4",range=["2","4"])
    g(f"sm{z}",None,"",f"zone {z} smear ratio s=d_s/d_w in 2..3",range=["2","3"])
    for n,u,w in [(f"S0{z}","m","permanent-load settlement"),(f"Ssur{z}","m","settlement under surcharged load"),
                  (f"Uv{z}","","vertical degree of consolidation"),(f"F{z}","","Hansbo drain-resistance factor"),
                  (f"Ur{z}","","radial degree"),(f"U{z}","","combined degree"),(f"M{z}","m","margin: U*S(sur) - (S0 - 30mm)")]:
        Q[n]={"role":"derived","unit":u,"why":f"zone {z}: {w}"}
laws=[]; reqs=[]; define={}
for z in Z:
    define[f"Tv{z}"]=f"cv{z}*t/(H{z}*H{z})"
    define[f"De{z}"]=f"105/100*SP{z}.s"
    define[f"nn{z}"]=f"De{z}/DR.dw"
    define[f"Tr{z}"]=f"cv{z}*rch{z}*t/(De{z}*De{z})"
    laws+= [
     {"zfl":f"S0{z} == Cc{z}*H{z}/(1+e0{z})*log10((sg{z}+Hf*gam)/sg{z})","source":"final settlement, log10 compression law, permanent load"},
     {"zfl":f"Ssur{z} == Cc{z}*H{z}/(1+e0{z})*log10((sg{z}+(Hf+hs)*gam)/sg{z})","source":"final settlement, log10 compression law, load incl. surcharge"},
     {"zfl":f"Uv{z} == if(Tv{z} < 1/5, 2*sqrt(Tv{z}/pi), 1 - 8/(pi*pi)*exp(-pi*pi*Tv{z}/4))","source":"vertical consolidation, Terzaghi (two branches)"},
     {"zfl":f"F{z} == ln(nn{z}/sm{z}) + rk{z}*ln(sm{z}) - 3/4","source":"Hansbo with smear"},
     {"zfl":f"Ur{z} == 1 - exp(-8*Tr{z}/F{z})","source":"Hansbo radial consolidation"},
     {"zfl":f"U{z} == 1 - (1-Uv{z})*(1-Ur{z})","source":"Carrillo combination"},
     {"zfl":f"M{z} == U{z}*Ssur{z} - S0{z} + Sres","source":"requirement margin: achieved settlement minus (permanent minus residual)"}]
    reqs.append({"quantity":f"M{z}","op":">=","value":"0","why":f"zone {z}: U*S(sur) >= S(perm) - 30 mm at t_r, all c_v, c_h/c_v, kh/ks, s"})
sp=[0.9,1.0,1.1,1.2,1.35,1.5,1.7,1.9,2.2,2.5]
spi=[{"s":str(x)} for x in sp]
cat={"spacing":{"ground":"problem statement","items":spi,"fields":{"s":{"unit":"m"}}},
 "drain":{"ground":"problem statement","items":[{"name":"A","dw":"0.0663","pm":"0.55"},{"name":"B","dw":"0.0780","pm":"0.70"},{"name":"C","dw":"0.0900","pm":"0.95"}],
          "fields":{"dw":{"unit":"m"},"pm":{"unit":"EUR/m"}}},
 "hgrid":{"ground":"discretisation by the author","integers":{"field":"N","from":str(nlo),"to":str(nmax),"unit":""}}}
cost="A1/(866/1000*SP1.s*SP1.s)*(H1*DR.pm + cinst) + A2/(866/1000*SP2.s*SP2.s)*(H2*DR.pm + cinst) + cs*(A1+A2)*hs"
brick={"stand":"universal-stand/1","quantities":Q,
 "slots":{"DR":{"from":["drain"]},"SP1":{"from":["spacing"]},"SP2":{"from":["spacing"]},"HS":{"from":["hgrid"]}},
 "computed":{"hs":{"value":"HS.N*hstep","unit":"m"}},
 "where":["Hf + hs <= Hmax"],
 "define":define,"laws":laws,"requirements":reqs,
 "objective":{"minimize":cost,"unit":"EUR","why":"total cost: drains (length*price + installation) + surcharge, both zones"},
 "catalog":cat}
json.dump(brick,open(out,"w"),indent=1)
