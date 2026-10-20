import json
from gen import NTCS, ADCS, CLS
from fractions import Fraction as F
def build1(with_cls=False):
    d={"stand":"universal-stand/1"}
    d["quantities"]={
     "T":{"role":"given","range":["253.15","333.15"],"unit":"K"},
     "T0":{"role":"given","value":"298.15","unit":"K","ground":"NTC model reference temperature 25 degC"},
     "Dk":{"role":"given","value":"1","unit":"K","why":"safety margin in the slope bound: slope evaluated at T-1 K"},
     "E_R25":{"role":"derived","unit":"K"},"E_B":{"role":"derived","unit":"K"},
     "E_adc_lb":{"role":"derived","unit":"K","why":"ADC error >= dx / max slope of x(T); max slope of x(T) <= B/(4 T^2) for ANY Rp, Rpar"},
     "E_rp_lb":{"role":"derived","unit":"K","why":"pull-up tolerance error >= its value at Rpar = infinity limit g=0 (monotone in g)"},
     "Elb":{"role":"derived","unit":"K","why":"lower bound of the total error, valid for every Rp, Rpar"}}
    d["slots"]={"NTC":{"from":["ntc"]},"ADC":{"from":["adc"]}}
    if with_cls: d["slots"]["CL"]={"from":["cls"]}
    dfn={"Dxa":"(ADC.tue + 1/2)*ADC.lsb","Du":"(1/T - 1/T0)",
      "dR25p":"ln(1 + NTC.tR)","dR25m":"ln(1 - NTC.tR)","dBp":"NTC.B*NTC.tB*Du","dBm":"0 - NTC.B*NTC.tB*Du"}
    if with_cls:
        dfn["dRpp"]="0 - ln(1 + CL.t)"; dfn["dRpm"]="0 - ln(1 - CL.t)"
    d["define"]=dfn
    FD=lambda dl:"(0 - T*T*(%s)/(NTC.B + T*(%s)))"%(dl,dl)
    def two(x,y):
        fx,fy=FD(x),FD(y)
        return "max(max(%s, 0 - %s), max(%s, 0 - %s))"%(fx,fx,fy,fy)
    laws=[{"zfl":"E_R25 == "+two("dR25p","dR25m"),"source":"same as c07.json"},
          {"zfl":"E_B == "+two("dBp","dBm"),"source":"same as c07.json"},
          {"zfl":"E_adc_lb == Dxa*4*(T - Dk)*(T - Dk)/NTC.B","source":"dx(x)/dT = x(1-x) * Rpar/(Rn+Rpar) * B/T^2 <= B/(4 T^2) (hand derivation)"}]
    if with_cls:
        laws.append({"zfl":"E_rp_lb == "+two("dRpp","dRpm"),"source":"c07.json E_Rp at g = Rn/Rpar = 0 (|delta| grows with g)"})
        laws.append({"zfl":"Elb == E_R25 + E_B + E_adc_lb + E_rp_lb","source":"sum of lower bounds"})
    else:
        laws.append({"zfl":"Elb == E_R25 + E_B + E_adc_lb","source":"sum of lower bounds"})
    d["laws"]=laws
    d["requirements"]=[]
    d["modes"]={"wide":{"quantities":{"T":{"range":["253.15","333.15"]}},"requirements":[{"quantity":"Elb","op":"<=","value":"1","why":"R1 outer: lower bound of error must not exceed 1 K"}]},
                "control":{"quantities":{"T":{"range":["273.15","313.15"]}},"requirements":[{"quantity":"Elb","op":"<=","value":"0.4","why":"R1 control band"}]}}
    d["objective"]={"minimize":"NTC.price + ADC.price","why":"cheapest"}
    d["report"]="all"
    cat={}
    cat["ntc"]={"items":[{"R25":n[1],"tR":n[2],"B":n[3],"tB":n[4],"dl":n[5],"price":n[6],"name":n[0]} for n in NTCS],"ground":"problem statement NTC table",
       "fields":{"R25":{"unit":"ohm"},"tR":{"unit":""},"B":{"unit":"K"},"tB":{"unit":""},"dl":{"unit":"mW/K"},"price":{"unit":"EUR"}}}
    cat["adc"]={"items":[{"lsb":str(F(1,2**a[1])),"tue":str(a[2]),"price":a[3],"name":a[0]} for a in ADCS],"ground":"problem statement ADC table",
       "fields":{"lsb":{"unit":""},"tue":{"unit":""},"price":{"unit":"EUR"}}}
    if with_cls:
        cat["cls"]={"items":[{"t":t,"cls":c,"price":p} for c,t,p in CLS],"ground":"resistor classes","fields":{"t":{"unit":""},"cls":{"unit":""},"price":{"unit":"EUR"}}}
    d["catalog"]=cat
    return d
json.dump(build1(False),open('stage1.json','w'),indent=1)
json.dump(build1(True),open('stage2.json','w'),indent=1)
