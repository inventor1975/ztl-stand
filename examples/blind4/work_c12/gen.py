import json, sys
B=[("B1","2.0",1,"100.9","AA",None),("B2","3.0",2,"100.4","AA",None),("B3","2.5",3,"99.0","AAA",None),("B4","3.5",3,"101.2","A",None),
("B5","3.0",4,"98.2","AAA",None),("B6","6.0",4,"100.5","BBB",None),("B7","4.0",5,"100.3","A",None),("B8","6.5",5,"104.0","BBB",3),
("B9","3.5",6,"98.7","AA",None),("B10","5.0",6,"103.0","A",None),("B11","7.0",6,"108.0","BBB",3),("B12","0",2,"95.8","AA",None),
("B13","0",4,"89.6","A",None),("B14","0",6,"82.3","AAA",None)]
L=[400,350,450,300,500,650]
def build(budget=True, fname="../c12.json", extra=None, slotspec=None, integer=None):
    q={}; slots={}; cat={}; define={}; laws=[]
    q["face"]={"role":"given","value":"10000","unit":"EUR","why":"one lot = 10 kEUR face"}
    q["y"]={"role":"given","value":"4/100","unit":"","why":"flat yield 4 % for the duration test"}
    for t,l in enumerate(L,1):
        q[f"L{t}"]={"role":"given","value":str(l*1000),"unit":"EUR","why":f"liability end of year {t}"}
    for n,c,m,p,r,cy in B:
        q[f"c_{n}"]={"role":"given","value":str(float(c)/100).rstrip('0') if False else str(__import__('fractions').Fraction(c)/100),"unit":"","why":f"{n} coupon {c} % of face"}
        q[f"m_{n}"]={"role":"given","value":str(m),"unit":"","why":f"{n} maturity (years)"}
        q[f"e_{n}"]={"role":"given","value":str(m),"unit":"","why":f"{n} last paying year: maturity (Fall mode: call year)"}
        q[f"w_{n}"]={"role":"given","value":"1","unit":"","why":f"{n} share of cash flows paid (Stress mode: 1/2 for BBB)"}
        q[f"p_{n}"]={"role":"given","value":str(__import__('fractions').Fraction(p)/100),"unit":"","why":f"{n} price per 100 face","ground":"bond table"}
        q[f"bbb_{n}"]={"role":"given","value":"1" if r=="BBB" else "0","unit":"","why":f"{n} rated {r}"}
        slots[f"N{n[1:]}"]={"from":[f"cat_{n}"]}
        cat[f"cat_{n}"]={"continuous":{"field":"x","from":"0","to":"100","unit":""}}
    # discount factors
    for t in range(1,7):
        define[f"df{t}"]="1/("+"*".join(["(1+y)"]*t)+")"
    for t in range(1,7):
        define[f"cL{t}"]="+".join(f"L{u}" for u in range(1,t+1))
    # cumulative cash per lot of bond through year t
    for n,c,m,p,r,cy in B:
        for t in range(0,7):
            if t==0: define[f"cum_{n}_0"]="0*face"
            else: define[f"cum_{n}_{t}"]=f"w_{n}*face*(c_{n}*min({t},e_{n}) + if(e_{n} <= {t}, 1, 0))"
        for t in range(1,7):
            define[f"cf_{n}_{t}"]=f"(cum_{n}_{t} - cum_{n}_{t-1})"
    define["Dl"]="("+"+".join(f"{t}*L{t}*df{t}" for t in range(1,7))+")/("+"+".join(f"L{t}*df{t}" for t in range(1,7))+")"
    define["Dlo"]="Dl - 1/4"; define["Dhi"]="Dl + 1/4"
    for t in range(1,7):
        q[f"S{t}"]={"role":"derived","unit":"EUR","why":f"cumulative cash received minus cumulative liabilities, through year {t}"}
        laws.append({"zfl":f"S{t} == "+" + ".join(f"N{n[1:]}.x*cum_{n}_{t}" for n,*_ in B)+f" - cL{t}","source":"surplus carried at 0 %, no borrowing: cumulative receipts minus cumulative liabilities"})
    q["C"]={"role":"derived","unit":"EUR","why":"total purchase cost"}
    q["CB"]={"role":"derived","unit":"EUR","why":"purchase cost of BBB bonds"}
    q["M2"]={"role":"derived","unit":"EUR","why":"30 % of total cost minus BBB cost"}
    laws.append({"zfl":"C == "+" + ".join(f"N{n[1:]}.x*p_{n}*face" for n,*_ in B),"source":"cost of a lot = price/100 x 10 kEUR"})
    laws.append({"zfl":"CB == "+" + ".join(f"N{n[1:]}.x*p_{n}*face*bbb_{n}" for n,*_ in B),"source":"BBB part of the cost"})
    laws.append({"zfl":"M2 == 3/10*C - CB","source":"R2 margin"})
    # duration: sum (t - Dl) PV_t within +-1/4 * sum PV_t  <=>  DA<=0 and DB<=0
    q["DA"]={"role":"derived","unit":"EUR","why":"sum_t (t - Dl - 1/4) PV_t: R3 upper side, must be <= 0"}
    q["DB"]={"role":"derived","unit":"EUR","why":"sum_t (Dl - 1/4 - t) PV_t: R3 lower side, must be <= 0"}
    ta=[];tb=[]
    for n,*_ in B:
        ta.append(f"N{n[1:]}.x*("+" + ".join(f"(({t}) - Dhi)*cf_{n}_{t}*df{t}" for t in range(1,7))+")")
        tb.append(f"N{n[1:]}.x*("+" + ".join(f"(Dlo - ({t}))*cf_{n}_{t}*df{t}" for t in range(1,7))+")")
    laws.append({"zfl":"DA == "+" + ".join(ta),"source":"Macaulay duration of portfolio <= Dl + 1/4  (D - Dl <= 1/4  <=>  sum PV_t (t - Dl - 1/4) <= 0)"})
    laws.append({"zfl":"DB == "+" + ".join(tb),"source":"Macaulay duration of portfolio >= Dl - 1/4"})
    # units: t is dimensionless; ok
    reqs=[{"quantity":f"S{t}","op":">=","value":"0","why":f"R1 cumulative cover through year {t}"} for t in range(1,7)]
    reqs.append({"quantity":"M2","op":">=","value":"0","why":"R2 BBB <= 30 % of purchase cost"})
    if budget: reqs.append({"quantity":"C","op":"<=","value":"2300000","why":"R4 budget 2300 kEUR"})
    modes={
     "Base":{"quantities":{},"requirements":[{"quantity":"DA","op":"<=","value":"0","why":"R3 duration <= liability duration + 0.25"},
                                              {"quantity":"DB","op":"<=","value":"0","why":"R3 duration >= liability duration - 0.25"}]},
     "Stress":{"quantities":{f"w_{n}":{"value":"1/2"} for n,c,m,p,r,cy in B if r=="BBB"},"requirements":[]},
     "Fall":{"quantities":{f"e_{n}":{"value":str(cy)} for n,c,m,p,r,cy in B if cy},"requirements":[]}}
    brick={"stand":"universal-stand/1","quantities":q,"slots":slots,"define":define,"laws":laws,"requirements":reqs,"modes":modes,
     "objective":{"minimize":" + ".join(f"N{n[1:]}.x*p_{n}*face" for n,*_ in B),"unit":"EUR","why":"total purchase cost"},
     "catalog":cat}
    json.dump(brick,open(fname,"w"),indent=1)
if __name__=="__main__":
    build(True,"../c12.json"); build(False,"c12_noR4.json")
