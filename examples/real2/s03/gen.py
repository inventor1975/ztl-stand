import json,sys
def rng(lo,hi,unit,why,ground="eCircuit Center EBA, amp+ADC page (device error table)"):
    return {"role":"given","range":[lo,hi],"unit":unit,"why":why,"ground":ground}
def val(v,unit,why,ground="eCircuit Center EBA, amp+ADC page (conditions)"):
    return {"role":"given","value":v,"unit":unit,"why":why,"ground":ground}
def build(voff="0.1", adc_tc="0.04", vref_tol="0.005", rtc="100", include=("off","gain"), extras=False):
    q={}
    q["dT"]=val("30","C","max temperature change from 25 C")
    if "off" in include:
        q["Rs"]=val("500","ohm","source resistance")
        q["R1n"]=val("10","kohm","nominal R1") ; q["R2n"]=val("40","kohm","nominal R2")
        q["Kn"]=val("5","","nominal gain 1+R2/R1")
        q["Vlsb"]=val("5/4095","V","12-bit LSB, 5 V ref")
        q["voff"]=rng("-"+voff,voff,"mV","U1 input offset voltage (+-)")
        q["voffTC"]=rng("-10","10","uV/C","U1 offset drift")
        q["ib"]=rng("-5","5","nA","U1 input bias current")
        q["ibTC"]=rng("-1","1","nA/C","ib drift")
        q["iboff"]=rng("-5","5","nA","U1 input offset current")
        q["iboffTC"]=rng("-1","1","nA/C","iboff drift")
        q["aoff"]=rng("-3","3","","ADC offset, LSB")
        q["aoffTC"]=rng("-"+adc_tc,adc_tc,"1/C","ADC offset drift, LSB per C")
        q["ares"]=rng("-1/2","1/2","","ADC resolution error, LSB")
        q["ainl"]=rng("-1","1","","ADC INL, LSB")
        q["Eoff"]={"role":"derived","unit":"mV"}
    if "gain" in include:
        q["Knom"]=val("5","","nominal amplifier gain")
        q["R1g"]=val("10","kohm","R1"); q["R2g"]=val("40","kohm","R2")
        q["t1"]=rng("-0.001","0.001","","R1 tolerance")
        q["t2"]=rng("-0.001","0.001","","R2 tolerance")
        q["c1"]=rng("-"+rtc,rtc,"ppm/C","R1 tempco")
        q["c2"]=rng("-"+rtc,rtc,"ppm/C","R2 tempco")
        q["ga"]=rng("-0.0005","0.0005","","ADC gain tolerance 2 LSB/4095 = 0.05 %")
        q["gc"]=rng("-20","20","ppm/C","ADC gain tempco 0.08 LSB/C = 20 ppm/C")
        q["vt"]=rng("-"+vref_tol,vref_tol,"","Vref tolerance")
        q["vc"]=rng("-50","50","ppm/C","Vref tempco")
        q["Eg"]={"role":"derived","unit":"","why":"relative gain error of the chain"}
    d={}
    laws=[];req=[]
    if "off" in include:
        laws.append({"zfl":"Eoff == (voff + voffTC*dT) + ((ib + ibTC*dT)*(Rs*Kn - R2n) + (iboff + iboffTC*dT)*(Rs*Kn + R2n)/2)/Kn + ((aoff + aoffTC*dT + ares + ainl)*Vlsb)/Kn","source":"source: voff referred to input; ib sensitivity Rs*K-R2, iboff sensitivity (Rs*K+R2)/2, divided by K; ADC terms in LSB*Vlsb divided by K"})
        req.append({"quantity":"Eoff","op":"within","value":["-5","5"],"why":"offset budget 5 mV (RTI), source"})
    if "gain" in include:
        d["R1T"]="R1g*(1+t1)*(1+c1*dT)"
        d["R2T"]="R2g*(1+t2)*(1+c2*dT)"
        laws.append({"zfl":"Eg == (1 + R2T/R1T)/Knom*(1+ga)*(1+gc*dT)/((1+vt)*(1+vc*dT)) - 1","source":"gain = (1+R2/R1) * Kadc, Kadc = 4095/Vref, each with tolerance and tempco; relative to nominal"})
        req.append({"quantity":"Eg","op":"within","value":["-0.01","0.01"],"why":"gain error budget 1 % of reading, source"})
    b={"stand":"ztl-stand/1","why":"real round 2, s03: eCircuit Center amp+ADC error budget","quantities":q,"slots":{},"define":d,"laws":laws,"requirements":req,"catalog":{}}
    if not d: del b["define"]
    return b
def w(name,b): json.dump(b,open(name,"w"),indent=1)
w("brick.json",build())
w("brick_offset.json",build(include=("off",)))
w("brick_gain.json",build(include=("gain",)))
w("brick_gain_vref01.json",build(include=("gain",),vref_tol="0.001"))
w("brick_offset_voff1.json",build(include=("off",),voff="1"))
