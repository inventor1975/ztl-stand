import json, sys
from fractions import Fraction as F
NTCS=[("N1","10000","0.01","3435","0.0075","2.0","0.45"),("N2","10000","0.01","3950","0.01","2.0","0.30"),
("N3","10000","0.05","3380","0.02","2.0","0.10"),("N4","10000","0.002","3977","0.003","2.0","1.80"),
("N5","4700","0.01","3480","0.01","2.0","0.40"),("N6","47000","0.03","4050","0.01","1.5","0.35"),
("N7","100000","0.01","4250","0.01","1.5","0.55")]
ADCS=[("A10",10,3,"0.20"),("A12",12,4,"0.50"),("A16",16,12,"2.40")]
CLS=[("1","0.01","0.01"),("0.5","0.005","0.03"),("0.1","0.001","0.08")]
NONE_R="1000000000000"
E24=["1.0","1.1","1.2","1.3","1.5","1.6","1.8","2.0","2.2","2.4","2.7","3.0","3.3","3.6","3.9","4.3","4.7","5.1","5.6","6.2","6.8","7.5","8.2","9.1"]
def build(ntcs=None, adcs=None, rp_vals=None, rpar_vals=None, classes=None, bands=None, r3=True, r2=True,
          opts=None):
    ntcs=ntcs or [n[0] for n in NTCS]; adcs=adcs or [a[0] for a in ADCS]; classes=classes or [c[0] for c in CLS]
    d={"stand":"universal-stand/1"}
    q={
     "T":{"role":"given","range":["253.15","333.15"],"unit":"K","why":"true NTC temperature, -20..+60 degC (K because the law has 1/T)"},
     "T0":{"role":"given","value":"298.15","unit":"K","ground":"NTC model reference temperature 25 degC"},
     "Vsh":{"role":"given","value":"3.6","unit":"V","why":"self-heating is evaluated at Vcc = 3.6 V (continuous measurement)"},
    }
    der={"xn":("", "node ratio x = Rx/(Rx+Rp) at the true temperature"),
         "E_R25":("K","|T_inferred - T| from R25 at its tolerance limit (worse sign)"),
         "E_B":("K","same, from B"),"E_Rp":("K","same, from the pull-up"),
         "E_Rpar":("K","same, from the parallel resistor (about 0 when none)"),
         "E_adc":("K","ADC +-(TUE+0.5 LSB) expressed in temperature"),
         "Tsh":("K","self-heating dT_sh = V_NTC^2/R_NTC/delta"),
         "Etot":("K","sum of the absolute error items"),
         "BOM":("EUR","bill of materials per channel")}
    for k,(u,w) in der.items(): q[k]={"role":"derived","unit":u,"why":w}
    d["quantities"]=q
    d["slots"]={"NTC":{"from":["ntc"]},"ADC":{"from":["adc"]},
      "RP":{"from":["rp_%s"%c for c in classes]},
      "RPAR":{"from":([] if rpar_vals==[] else ["rpar_%s"%c for c in classes])+["none_%s"%c for c in classes]}}
    dfn={}
    dfn["Dxa"]="(ADC.tue + 1/2)*ADC.lsb"
    dfn["Du"]="(1/T - 1/T0)"
    dfn["Rn"]="NTC.R25*exp(NTC.B*Du)"
    dfn["Dg"]="Rn/RPAR.R"
    dfn["Dq"]="Dg/(1 + Dg)"
    dfn["Rxn"]="Rn*RPAR.R/(Rn + RPAR.R)"
    dfn["Dx"]="Rxn/(Rxn + RP.R)"
    # Every error item is  T_inferred - T  with 1/T_inferred = 1/T + delta/B,  delta = ln(Rn_inferred/Rn)  (exact),
    # i.e.  dT = -T*T*delta/(B + T*delta).  Each delta is derived BY HAND from the divider (see report).
    dfn["dR25p"]="ln(1 + NTC.tR)"
    dfn["dR25m"]="ln(1 - NTC.tR)"
    dfn["dBp"]="NTC.B*NTC.tB*Du"
    dfn["dBm"]="0 - NTC.B*NTC.tB*Du"
    dfn["dRpp"]="0 - ln(1 + RP.t*(1 + Dg))"
    dfn["dRpm"]="0 - ln(1 - RP.t*(1 + Dg))"
    dfn["dRparp"]="0 - ln(1 - RPAR.t*Dg/(1 + RPAR.t))"
    dfn["dRparm"]="0 - ln(1 + RPAR.t*Dg/(1 - RPAR.t))"
    # ADC: rho = Rx_inferred/Rx_nominal = (1 +- dx*(Rx+Rp)/Rx)/(1 -+ dx*(Rx+Rp)/Rp); delta = ln(rho) + ln((1-q)/(1-q*rho))
    for s_,sg in (("p","+"),("m","-")):
        inv="-" if sg=="+" else "+"
        rho="((1 %s Dxa*(Rxn + RP.R)/Rxn)/(1 %s Dxa*(Rxn + RP.R)/RP.R))"%(sg,inv)
        dfn["dAdc"+s_]="ln(%s) + ln((1 - Dq)/(1 - Dq*%s))"%(rho,rho)
    d["define"]=dfn
    FD=lambda dl:"(0 - T*T*(%s)/(NTC.B + T*(%s)))"%(dl,dl)
    def two(x,y): 
        fx,fy=FD(x),FD(y)
        return "max(max(%s, 0 - %s), max(%s, 0 - %s))"%(fx,fx,fy,fy)
    d["laws"]=[
     {"zfl":"xn == Dx","source":"divider: x = Rx/(Rx+Rp), Rx = R_NTC || R_par, R_NTC = R25 exp(B(1/T-1/T0))"},
     {"zfl":"E_R25 == "+two("dR25p","dR25m"),"source":"change of inferred T when R25 sits at +-tolerance, others nominal (hand-derived delta)"},
     {"zfl":"E_B == "+two("dBp","dBm"),"source":"same for B"},
     {"zfl":"E_Rp == "+two("dRpp","dRpm"),"source":"same for the pull-up resistor"},
     {"zfl":"E_Rpar == "+two("dRparp","dRparm"),"source":"same for the parallel resistor"},
     {"zfl":"E_adc == "+two("dAdcp","dAdcm"),"source":"ADC +-(TUE+0.5 LSB) in ratio units, inverted by the firmware"},
     {"zfl":"Tsh == (Vsh*Dx)*(Vsh*Dx)/(Rn*NTC.dl)","source":"P_NTC = V_NTC^2/R_NTC, dT_sh = P_NTC/delta; V_NTC = Vcc*x"},
     {"zfl":"Etot == E_R25 + E_B + E_Rp + E_Rpar + E_adc + Tsh","source":"error stack: sum of absolute items"},
     {"zfl":"BOM == NTC.price + ADC.price + RP.price + RPAR.price","source":"bill of materials"},
    ]
    d["where"]=["RP.cls == RPAR.cls"]
    # modes: bands of T, each with its own bound
    reqs=[]
    if r3: reqs.append({"quantity":"BOM","op":"<=","value":"2.2","why":"R3 BOM <= 2.20 EUR"})
    d["requirements"]=reqs
    modes={}
    for (lo,hi,bound,nm) in bands:
        mq={"T":{"range":[lo,hi]}}
        mr=[{"quantity":"Etot","op":"<=","value":bound,"why":"R1: total error <= %s K for T in [%s,%s] K"%(bound,lo,hi)}]
        if r2 and nm.startswith("wide"):
            mr.append({"quantity":"xn","op":"within","value":["0.03","0.97"],"why":"R2: node ratio in [0.03,0.97]"})
        modes[nm]={"quantities":mq,"requirements":mr}
    d["modes"]=modes
    d["objective"]={"minimize":"NTC.price + ADC.price + RP.price + RPAR.price","why":"cheapest BOM"}
    # catalogs
    cat={}
    ntc_items=[]
    for n in NTCS:
        if n[0] in ntcs:
            ntc_items.append({"R25":n[1],"tR":n[2],"B":n[3],"tB":n[4],"dl":n[5],"price":n[6],"name":n[0]})
    cat["ntc"]={"items":ntc_items,"ground":"problem statement NTC table",
       "fields":{"R25":{"unit":"ohm"},"tR":{"unit":""},"B":{"unit":"K"},"tB":{"unit":""},"dl":{"unit":"mW/K"},"price":{"unit":"EUR"}}}
    ai=[]
    for a in ADCS:
        if a[0] in adcs:
            ai.append({"lsb":str(F(1,2**a[1])),"tue":str(a[2]),"price":a[3],"name":a[0]})
    cat["adc"]={"items":ai,"ground":"problem statement ADC table","fields":{"lsb":{"unit":""},"tue":{"unit":""},"price":{"unit":"EUR"}}}
    for c,t,p in CLS:
        if c not in classes: continue
        for pre,vals in (("rp",rp_vals),("rpar",rpar_vals)):
            if vals==[]: continue
            if vals is None:
                cat["%s_%s"%(pre,c)]={"series":"E24","decades":[1000,10000,100000],"ground":"E24 resistor class %s%%"%c,
                  "fields":{"R":{"series":True,"unit":"ohm"},"t":{"value":t,"unit":""},"cls":{"value":c,"unit":""},"price":{"value":p,"unit":"EUR"}}}
            else:
                cat["%s_%s"%(pre,c)]={"items":[{"R":str(v),"t":t,"cls":c,"price":p} for v in vals],"ground":"E24 resistor class %s%%"%c,
                  "fields":{"R":{"unit":"ohm"},"t":{"unit":""},"cls":{"unit":""},"price":{"unit":"EUR"}}}
        cat["none_%s"%c]={"items":[{"R":NONE_R,"t":t,"cls":c,"price":"0"}],"ground":"no parallel resistor: 1e12 ohm placeholder",
           "fields":{"R":{"unit":"ohm"},"t":{"unit":""},"cls":{"unit":""},"price":{"unit":"EUR"}}}
    d["catalog"]=cat
    return d
if __name__=="__main__":
    pass
