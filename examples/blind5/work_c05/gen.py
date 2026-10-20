import json, sys
# generator for c05.json (scratch). mode: "lp" (continuous B, hand-algebra margins) or "pin" (direct laws, B pinned)
mode = sys.argv[1] if len(sys.argv) > 1 else "lp"
pinB = [x for x in sys.argv[2:5]] if mode == "pin" else None
S = {"w": dict(h="2000", Q=("0.9","1.2"), T=("28","32")),
     "m": dict(h="3200", Q=("1.5","2.0"), T=("30","34")),
     "s": dict(h="2200", Q=("2.2","2.8"), T=("34","38"))}
q = {}
def given(name, value, unit, why, **kw):
    d = {"role":"given","value":value,"unit":unit,"why":why}; d.update(kw); q[name]=d
given("kE","1.4815","m^3/(h*MW)","evaporation per MW of heat load (problem statement)",ground="problem")
given("Dr","0.023","m^3/h","drift (problem statement)",ground="problem")
given("cu","1","mg/L","unit quantity to make concentrations dimensionless inside log10")
given("Tu","1","C","unit quantity to make temperature dimensionless inside log10")
given("Si_lim","150","mg/L","R1")
given("Cl_lim","400","mg/L","R2")
given("SO_lim","1000","mg/L","R3")

given("disch","0.90","EUR/m^3","discharge cost")
given("cacid","0.12","EUR/kg","acid price")
given("kacid","0.98","","kg H2SO4 per kg alkalinity-as-CaCO3 neutralised")
for s,d in S.items():
    given("h_"+s, d["h"], "h", "season hours")
    given("Qtop_"+s, d["Q"][1], "MW", "top of Q range: the cost is evaluated at the worst case")
    q["Q_"+s] = {"role":"given","range":list(d["Q"]),"unit":"MW","why":"heat load, season "+s}
    q["T_"+s] = {"role":"given","range":list(d["T"]),"unit":"C","why":"basin temperature, season "+s}
define = {}
laws = []
reqs = []
derived = {}
def der(name, unit, why): derived[name] = {"role":"derived","unit":unit,"why":why}
slotname = {"w":"BW","m":"BM","s":"BS"}
for s in S:
    B = slotname[s]+".x"
    define["E_"+s] = "kE*Q_"+s
    if mode == "lp":
        define["Kc_"+s] = ("(-3.4 + 1.95*log10(SRC.Alk/cu*(1-ACID.r)) - (log10((SRC.TDS - 0.26*ACID.r*SRC.Alk)/cu) - 1)/10"
                           " + 13.12*log10(T_%s/Tu + 273) - 34.55 + log10(SRC.Ca/cu) - 0.4)" % s)
        define["Ncap_"+s] = "pow(10, (PROG.Lmax - Kc_%s)/2.85)" % s
        der("gSi_"+s,"mg/L*m^3/h","R1 margin, season "+s); der("gCl_"+s,"mg/L*m^3/h","R2 margin"); der("gSO_"+s,"mg/L*m^3/h","R3 margin"); der("gLSI_"+s,"m^3/h","R4 margin")
        laws += [
         {"zfl":"gSi_%s == Si_lim*(%s + Dr) - SRC.Si*(E_%s + %s + Dr)"%(s,B,s,B),"source":"N*SiO2_m <= 150 with N=M/(B+D), multiplied by (B+D)>0"},
         {"zfl":"gCl_%s == Cl_lim*(%s + Dr) - SRC.Cl*(E_%s + %s + Dr)"%(s,B,s,B),"source":"N*Cl_m <= 400 times (B+D)"},
         {"zfl":"gSO_%s == SO_lim*(%s + Dr) - (SRC.SO4 + 0.96*ACID.r*SRC.Alk)*(E_%s + %s + Dr)"%(s,B,s,B),"source":"N*(SO4_m+0.96 r Alk_m) <= 1000 times (B+D)"},
         {"zfl":"gLSI_%s == Ncap_%s*(%s + Dr) - (E_%s + %s + Dr)"%(s,s,B,s,B),"source":"LSI = 2.85*log10(N)+K <= Lmax  <=>  N <= 10^((Lmax-K)/2.85) (hand algebra), times (B+D)"},
        ]
        for n,t in (("gSi","R1 SiO2 <= 150"),("gCl","R2 chloride <= 400"),("gSO","R3 sulphate <= 1000"),("gLSI","R4 LSI <= programme max")):
            reqs.append({"quantity":n+"_"+s,"op":">=","value":"0","why":t+", season "+s})
    else:
        der("M_"+s,"m^3/h","make-up"); der("N_"+s,"","cycles")
        der("Si_"+s,"mg/L","basin SiO2"); der("Cl_"+s,"mg/L","basin chloride"); der("SO_"+s,"mg/L","basin sulphate")
        der("Alk_"+s,"mg/L","basin alkalinity"); der("TDS_"+s,"mg/L","TDS_lsi"); der("Ca_"+s,"mg/L","basin Ca")
        der("pH_"+s,"","pH"); der("LSI_"+s,"","LSI")
        laws += [
         {"zfl":"M_%s == E_%s + %s + Dr"%(s,s,B),"source":"M = E+B+D"},
         {"zfl":"N_%s == M_%s/(%s + Dr)"%(s,s,B),"source":"N = M/(B+D)"},
         {"zfl":"Si_%s == N_%s*SRC.Si"%(s,s),"source":"concentration"},
         {"zfl":"Cl_%s == N_%s*SRC.Cl"%(s,s),"source":"concentration"},
         {"zfl":"SO_%s == N_%s*(SRC.SO4 + 0.96*ACID.r*SRC.Alk)"%(s,s),"source":"concentration"},
         {"zfl":"Alk_%s == N_%s*SRC.Alk*(1-ACID.r)"%(s,s),"source":"concentration"},
         {"zfl":"TDS_%s == N_%s*(SRC.TDS - 0.26*ACID.r*SRC.Alk)"%(s,s),"source":"concentration"},
         {"zfl":"Ca_%s == N_%s*SRC.Ca"%(s,s),"source":"concentration"},
         {"zfl":"pH_%s == 5.9 + 0.95*log10(Alk_%s/cu)"%(s,s),"source":"empirical pH"},
         {"zfl":"LSI_%s == pH_%s - (9.3 + (log10(TDS_%s/cu) - 1)/10 + (-13.12*log10(T_%s/Tu + 273) + 34.55) - (log10(Ca_%s/cu) - 0.4 + log10(Alk_%s/cu)))"%(s,s,s,s,s,s),"source":"LSI = pH - pHs"},
        ]
        for n,lim,t in (("Si","Si_lim","R1"),("Cl","Cl_lim","R2"),("SO","SO_lim","R3")):
            reqs.append({"quantity":n+"_"+s,"op":"<=","value":lim,"why":t+", season "+s})
        reqs.append({"quantity":"LSI_"+s,"op":"<=","value":"PROG.Lmax","why":"R4, season "+s})
der("Vyr","m^3","annual make-up")
laws.append({"zfl":"Vyr == h_w*(E_w + BW.x + Dr) + h_m*(E_m + BM.x + Dr) + h_s*(E_s + BS.x + Dr)","source":"sum over seasons of hours*M"})
reqs.append({"quantity":"Vyr","op":"<=","value":"26000","why":"R5 annual make-up volume <= 26000 m3 (worst case: Q at top of range)"})
q.update(derived)
obj = " + ".join("h_%s*((kE*Qtop_%s + %s.x + Dr)*(SRC.price + PROG.cost + ACID.r*SRC.Alkhi*kacid*cacid) + disch*%s.x)"%(s,s,slotname[s],slotname[s]) for s in S)
src = [
 ("Town",("60","80"),("70","90"),("20","30"),("8","12"),("25","35"),("220","280"),"1.90","90"),
 ("Well",("180","230"),("200","240"),("60","90"),("22","30"),("80","110"),("650","780"),"0.65","240"),
 ("SoftWell",("10","25"),("200","240"),("60","90"),("22","30"),("80","110"),("700","820"),"1.45","240")]
items = [{"name":n,"Ca":{"range":list(ca)},"Alk":{"range":list(al)},"Cl":{"range":list(cl)},"Si":{"range":list(si)},
          "SO4":{"range":list(so)},"TDS":{"range":list(td)},"price":p,"Alkhi":ah} for n,ca,al,cl,si,so,td,p,ah in src]
cat = {
 "sources":{"items":items,"fields":{"Ca":{"unit":"mg/L"},"Alk":{"unit":"mg/L"},"Cl":{"unit":"mg/L"},"Si":{"unit":"mg/L"},"SO4":{"unit":"mg/L"},"TDS":{"unit":"mg/L"},"price":{"unit":"EUR/m^3"},"Alkhi":{"unit":"mg/L"}}},
 "programmes":{"items":[{"name":n,"Lmax":l,"cost":c} for n,l,c in (("none","0.5","0"),("P1","1.3","0.12"),("P2","1.9","0.22"),("P3","2.5","0.38"))],
               "fields":{"Lmax":{"unit":""},"cost":{"unit":"EUR/m^3"}}},
 "acids":{"items":[{"name":n,"r":r} for n,r in (("0%","0"),("40%","0.4"),("70%","0.7"))],"fields":{"r":{"unit":""}}},
}
slots = {"SRC":{"from":["sources"]},"PROG":{"from":["programmes"]},"ACID":{"from":["acids"]}}
for s in S:
    if mode == "lp":
        cat["flow_"+s] = {"continuous":{"field":"x","from":"0","to":"20","unit":"m^3/h"}}
    else:
        cat["flow_"+s] = {"items":[{"x":pinB[list(S).index(s)]}],"fields":{"x":{"unit":"m^3/h"}}}
    slots[slotname[s]] = {"from":["flow_"+s]}
brick = {"stand":"universal-stand/1","quantities":q,"slots":slots,"define":define,"laws":laws,"requirements":reqs,
         "objective":{"minimize":obj,"unit":"kEUR","why":"annual cost at the worst case (Q and Alk_m at the top of their ranges)"},
         "catalog":cat}
if mode == "pin": brick["report"]="all"
json.dump(brick, open(sys.argv[0].replace("gen.py","out_%s.json"%mode),"w"), indent=1)
