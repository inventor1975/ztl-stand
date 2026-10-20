import json,sys
from fractions import Fraction as Fr
def build(budget="355", step=100, extra=True, tiers_only=None, report=None):
    I={1:("2000","2370"),2:("1750","2110"),3:("2300","2730"),4:("3150","3780")}
    Sc={1:"800",2:"800",3:"800",4:"300"}
    q={}
    for k,(lo,hi) in I.items():
        q[f"I{k}"]={"role":"given","range":[lo,hi],"unit":"","why":f"average inventory Q{k}, pallets"}
        q[f"Sc{k}"]={"role":"given","value":Sc[k],"unit":"","why":f"spot availability Q{k}, positions","ground":"spot pool contract"}
    q["u"]={"role":"given","range":["0.88","0.94"],"unit":"","why":"space utilisation, ONE value for the year"}
    q["Ps"]={"role":"given","range":["18","24"],"unit":"EUR","why":"spot price EUR per position-month"}
    q["Cown"]={"role":"given","value":"118","unit":"EUR","why":"own block EUR per position per year","ground":"lease"}
    q["Bmax"]={"role":"given","value":"3200","unit":"","why":"building limit, positions","ground":"building"}
    for k in I:
        for n in ("F","S","M"):
            q[f"{n}{k}"]={"role":"derived","unit":""}
    q["Bchk"]={"role":"derived","unit":""}
    q["Cost"]={"role":"derived","unit":"kEUR"}
    define={f"N{k}":f"I{k}/u" for k in I}
    laws=[]
    for k in I:
        laws.append({"zfl":f"F{k} == min(T.cap, max(0, N{k} - OWN.B))","source":f"Q{k}: 3PL takes the shortfall first, up to the tier cap"})
        laws.append({"zfl":f"S{k} == min(Sc{k}, max(0, N{k} - OWN.B - T.cap))","source":f"Q{k}: spot takes what remains after the 3PL cap, up to its availability (hand algebra of min(Sc, max(0, N-B-F)))"})
        laws.append({"zfl":f"M{k} == max(0, N{k} - OWN.B - T.cap - Sc{k})","source":f"Q{k}: need left uncovered after own block, 3PL cap and spot availability"})
    laws.append({"zfl":"Bchk == OWN.B","source":"own block size"})
    bill=" + ".join(f"max(F{k}, T.commit)" for k in I)
    sp=" + ".join(f"S{k}" for k in I)
    laws.append({"zfl":f"Cost == Cown*OWN.B + 3*T.price*({bill}) + 3*Ps*({sp})","source":"own lease + 3PL billing max(F,commit)*price*3 months per quarter + spot at its price"})
    q["Mmin"]={"role":"derived","unit":""}
    laws.append({"zfl":"Mmin == max(max(M1, M2), max(M3, M4))","source":"worst quarter of the uncovered need"})
    reqs=[{"quantity":"Mmin","op":"<=","value":"0","why":"R1 every quarter: B+F+S >= needed with F<=cap, S<=spot availability: uncovered need must be 0"}]
    reqs.append({"quantity":"Cost","op":"<=","value":budget,"why":"R2 worst-case annual cost <= 355 kEUR (spot range top, inventory top, u bottom)"})
    reqs.append({"quantity":"Bchk","op":"<=","value":"Bmax","why":"R3 building limit"})
    Bs=set(Fr(b) for b in range(0,3201,step))
    if extra:
        need=[Fr(i[1])/Fr("0.88") for i in I.values()]
        for n in need:
            Bs.add(n)
            for cap in (0,800,1500,2200):
                for sc in (0,300,800):
                    v=n-cap-sc
                    if 0<=v<=3200: Bs.add(v)
    Bs=sorted(Bs)
    def s(x): return str(x.numerator) if x.denominator==1 else f"{x.numerator}/{x.denominator}"
    tiers=[("T0","0","0","0"),("T1","11.8","0","800"),("T2","9.6","400","1500"),("T3","8.4","900","2200")]
    if tiers_only: tiers=[t for t in tiers if t[0] in tiers_only]
    brick={"stand":"universal-stand/1","quantities":q,"slots":{"OWN":{"from":["own_block"]},"T":{"from":["tiers"]}},
      "define":define,"laws":laws,"requirements":reqs,
      "objective":{"minimize":"Cost","case":"worst","why":"minimum worst-case annual cost"},
      "catalog":{"own_block":{"ground":"lease","items":[{"B":s(b)} for b in Bs],"fields":{"B":{"unit":""}}},
        "tiers":{"ground":"3PL tariff","items":[{"name":n,"price":p,"commit":c,"cap":cap} for n,p,c,cap in tiers],
                 "fields":{"price":{"unit":"EUR"},"commit":{"unit":""},"cap":{"unit":""}}}}}
    if report: brick["report"]=report
    return brick,len(Bs)
if __name__=="__main__":
    out=sys.argv[1]; kw=eval(sys.argv[2]) if len(sys.argv)>2 else {}
    b,n=build(**kw); json.dump(b,open(out,"w"),indent=1); print(out,n,"B values")
