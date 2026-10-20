import json, sys
discs = [("D1",14,"0.42",70,52,260),("D2",18,"0.50",78,58,320),("D3",22,"0.62",90,68,400),
         ("D4",27,"0.75",100,76,520),("D5",33,"0.88",112,86,690),("D6",40,"1.05",125,96,900)]
pads = {"PA":(["0.36","0.42","0.46","0.40","0.30","0.20"],60),
        "PB":(["0.30","0.38","0.44","0.44","0.38","0.28"],95),
        "PC":(["0.28","0.34","0.40","0.42","0.41","0.36"],150),
        "PD":(["0.22","0.30","0.38","0.40","0.39","0.37"],110),
        "PE":(["0.40","0.40","0.40","0.33","0.25","0.18"],45)}
rets = [("R0",0,0),("R1",45,1200),("R2",70,2600),("R3",90,4100),("R4",115,5600)]
modes_d = {"a loaded slow": (16000,"0.07",40,7,35),
           "b loaded fast": (16000,"0.07",55,4,20),
           "c empty cold": (9500,"0.08",55,7,0)}

def build(shared=True):
    Q = {}
    def g(n,unit,value=None,tol=None,rng=None,why=None):
        d={"role":"given","unit":unit}
        if value is not None: d["value"]=str(value)
        if tol: d["tolerance"]=tol
        if rng: d["range"]=rng
        if why: d["why"]=why
        Q[n]=d
    g("m","kg",16000); g("sl","",  "0.07"); g("vk","km/h",40); g("Lk","km",7); g("Ta","C",35)
    g("g","m*s^-2",981/100,why="g = 9.81 per problem (not g0)")
    g("rho","kg*m^-3","1.2"); g("CdA","m^2","5.0"); g("cp","J/(kg*K)",460)
    g("dT0","K",30,why="T0 = Tamb + 30 K"); g("Tu","C",1,why="unit temperature for dimensionless ratios")
    g("vu","m/s",1); g("hu","W/(m^2*K)",1); g("vref","km/h",40,why="retarder P40 reference speed")
    g("fh","",rng=["0.8","1"],why="convective h x 0.80 (worst case: h anywhere in 0.8..1.0 of table)")
    g("fmu","",rng=["0.92","1"],why="mu x 0.92")
    g("fK","",rng=["0.95","1"],why="K x 0.95")
    for n,u in [("Tf","C"),("Tr","C"),("muf","" ),("mur",""),("Fav","N")]:
        Q[n]={"role":"derived","unit":u}
    define = {
     "h0": "hu*if(vk <= 5*vu, 12 + 16*vk/(5*vu), if(vk <= 10*vu, 28 + 17*(vk-5*vu)/(5*vu), if(vk <= 15*vu, 45 + 17*(vk-10*vu)/(5*vu), 62)))",
     "Pgrav": "m*g*sl*vk", "Proll": "0.012*m*g*vk", "Pair": "0.5*rho*CdA*vk**3",
     "Pret": "RET.P40*vk/vref",
     "Pf": "max(0, Pgrav - Proll - Pair - Pret)",
     "Pdf": "0.92*Pf*0.65/2", "Pdr": "0.92*Pf*0.35/2",
     "hAf": "fh*h0*F.A", "hAr": "fh*h0*RR.A",
     "tf": "F.mass*cp/hAf", "tr": "RR.mass*cp/hAr",
     "tt": "Lk/vk",
     "Tssf": "Ta + Pdf/hAf", "Tssr": "Ta + Pdr/hAr",
    }
    def mu(T,P):
        f=lambda k: P+"."+k
        return (f"if({T} <= 100*Tu, {f('m20')} + ({f('m100')}-{f('m20')})*(max({T},20*Tu)-20*Tu)/(80*Tu), "
                f"if({T} <= 300*Tu, {f('m100')} + ({f('m300')}-{f('m100')})*({T}-100*Tu)/(200*Tu), "
                f"if({T} <= 450*Tu, {f('m300')} + ({f('m450')}-{f('m300')})*({T}-300*Tu)/(150*Tu), "
                f"if({T} <= 550*Tu, {f('m450')} + ({f('m550')}-{f('m450')})*({T}-450*Tu)/(100*Tu), "
                f"if({T} <= 650*Tu, {f('m550')} + ({f('m650')}-{f('m550')})*({T}-550*Tu)/(100*Tu), {f('m650')})))))")
    laws = [
     {"zfl":"Tf == Tssf - (Tssf - Ta - dT0)*exp(-tt/tf)","source":"disc Newton cooling T(t)=Tss-(Tss-T0)exp(-t/tau), front disc"},
     {"zfl":"Tr == Tssr - (Tssr - Ta - dT0)*exp(-tt/tr)","source":"same, rear disc"},
     {"zfl":"muf == "+mu("Tf","PAD"),"source":"pad mu(T) piecewise linear, front disc temperature"},
     {"zfl":"mur == "+mu("Tr","PAD"),"source":"pad mu(T) piecewise linear, rear disc temperature"},
     {"zfl":"Fav == 0.9*1000*fK*fmu*(muf*F.Kf + mur*RR.Kr)","source":"available stop force; K in kN so x1000 N"},
    ]
    # K in kN: with unit kN the SI value already N, so the factor 1000 must NOT be repeated
    laws[4]["zfl"]="Fav == 0.9*fK*fmu*(muf*F.Kf + mur*RR.Kr)"
    reqs = [
     {"quantity":"Tf","op":"<=","value":"600","why":"R1 front disc end temperature <= 600 C"},
     {"quantity":"Tr","op":"<=","value":"600","why":"R1 rear disc end temperature <= 600 C"},
     {"quantity":"Fav","op":">=","value":"m*(4.0 + g*sl - 0.012*g)","why":"R2 emergency stop F >= F_req (decel 4.0 m/s2 on the grade)"},
    ]
    modes = {}
    for k,(m,s,v,L,ta) in modes_d.items():
        modes[k]={"quantities":{"m":{"value":str(m)},"sl":{"value":s},"vk":{"value":str(v)},
                                "Lk":{"value":str(L)},"Ta":{"value":str(ta)}}}
    cat = {}
    cat["discs"]={"ground":"problem statement table","items":[
        {"mass":str(m),"A":A,"Kf":str(kf),"Kr":str(kr),"price":str(p),"name":n} for n,m,A,kf,kr,p in discs],
        "fields":{"mass":{"unit":"kg"},"A":{"unit":"m^2"},"Kf":{"unit":"kN"},"Kr":{"unit":"kN"},"price":{"unit":"EUR"}}}
    items=[]
    for n,(mus,p) in pads.items():
        d={"m%d"%T:x for T,x in zip([20,100,300,450,550,650],mus)}
        d["price"]=str(p); d["name"]=n; items.append(d)
    cat["pads"]={"ground":"problem statement table","items":items,
        "fields":{**{"m%d"%T:{"unit":""} for T in [20,100,300,450,550,650]},"price":{"unit":"EUR"}}}
    cat["retarders"]={"ground":"problem statement table","items":[
        {"P40":str(p),"price":str(c),"name":n} for n,p,c in rets],
        "fields":{"P40":{"unit":"kW"},"price":{"unit":"EUR"}}}
    return {"stand":"universal-stand/1","quantities":Q,
      "slots":{"F":{"from":["discs"]},"RR":{"from":["discs"]},"PAD":{"from":["pads"]},"RET":{"from":["retarders"]}},
      "define":define,"laws":laws,"requirements":reqs,"modes":modes,
      "objective":{"minimize":"2*F.price + 2*RR.price + 4*PAD.price + RET.price","why":"total price EUR"},
      "catalog":cat}
if __name__=="__main__":
    json.dump(build(),open(sys.argv[1],"w"),indent=1)
