import json, copy
def g(v=None,tol=None,rng=None,unit=""):
    d={"role":"given","unit":unit}
    if rng: d["range"]=rng
    else: d["value"]=v
    if tol is not None: d["tolerance"]=tol
    return d
def der(unit=""): return {"role":"derived","unit":unit}

def front(variant="sheet"):
    q={}
    q["R1"]=g("10000","0.001",unit="ohm")
    q["R2"]=g("40000","0.001",unit="ohm")
    q["dR1"]=g(rng=["-3/1000","3/1000"])   # 100 ppm/C x 30 C
    q["dR2"]=g(rng=["-3/1000","3/1000"])
    q["Rs"]=g("500",unit="ohm")
    if variant=="sheet":
        q["voff"]=g(rng=["-4/10000","4/10000"],unit="V")   # 0.1 mV initial (sheet) + 10 uV/C*30 C
        q["ibn"]=g(rng=["-40/1000000000","40/1000000000"],unit="A") # 10 nA + 1 nA/C*30
        q["ibp"]=g(rng=["-40/1000000000","40/1000000000"],unit="A")
        q["oadc"]=g(rng=["-45/10","45/10"])                 # 3 LSB + 0.05 LSB/C*30 (prose table; reproduces published 2.2 mV)
    else:  # prose table
        q["voff"]=g(rng=["-13/10000","13/10000"],unit="V")  # 1 mV + 10 uV/C*30
        q["ibn"]=g(rng=["-525/10000000000","525/10000000000"],unit="A") # prose: Ib 5 nA +- Ios/2 = 7.5 nA, + (1+0.5)nA/C*30
        q["ibp"]=g(rng=["-525/10000000000","525/10000000000"],unit="A")
        q["oadc"]=g(rng=["-45/10","45/10"])                 # 3 LSB + 0.05 LSB/C*30
    q["ores"]=g(rng=["-1/2","1/2"])
    q["oinl"]=g(rng=["-1","1"])
    q["Vref"]=g("5","0.005",unit="V")
    q["dVref"]=g(rng=["-15/10000","15/10000"])  # 50 ppm/C x 30 C
    q["eg"]=g(rng=["-22/20475","22/20475"]) # 2 LSB + 0.08 LSB/C*30
    q["Vq"]=g("1/4095",unit="V")
    q["vin"]=g("0",unit="V")
    for n,u in [("vo1","V"),("code",""),("Vmeas","V"),("Err","V")]:
        q[n]=der(u)
    return q
define={"R1e":"R1*(1+dR1)","R2e":"R2*(1+dR2)","Vrefe":"Vref*(1+dVref)"}
laws=[
 {"zfl":"vo1 == (1 + R2e/R1e)*(vin + voff + ibp*Rs) - ibn*R2e","source":"non-inverting amp: gain 1+R2/R1 on input+offset+Ibp*Rs, minus Ibn*R2 (eCircuit Center sheet: S(ibn)=-R2, S(ibp)=Rs*Ka)"},
 {"zfl":"code == 4095*vo1/Vrefe*(1+eg) + oadc + ores + oinl","source":"ADC: Kadc=(2^N-1)/Vref, gain error, offset+resolution+INL as LSB terms"},
 {"zfl":"Vmeas == code*Vq","source":"reading referred to input: code/(Kadc_nom*Ka_nom)=code/4095 V"},
 {"zfl":"Err == Vmeas - vin","source":"error referred to input (RTI)"},
]
def flat(variant="sheet"):
    zero={k:{"value":"0"} for k in ["voff","ibn","ibp","oadc","ores","oinl"]}
    return {"stand":"ztl-stand/1","why":"k02 flat: non-inverting amp (gain 5) + 12-bit ADC with 5 V ref; eCircuit Center EBA example",
     "quantities":front(variant),"slots":{},"catalog":{},"define":define,"laws":laws,"requirements":[],
     "modes":{
      "offset_vin0":{"quantities":{"vin":{"value":"0"}},"requirements":[{"quantity":"Err","op":"within","value":["-5/1000","5/1000"],"why":"offset budget 5 mV RTI (source)"}]},
      "gain_only_vin1":{"quantities":dict(zero,vin={"value":"1"}),"requirements":[{"quantity":"Err","op":"within","value":["-1/100","1/100"],"why":"gain budget 1% of reading (1 V), offsets zeroed (source)"}]},
      "total_vin1":{"quantities":{"vin":{"value":"1"}},"requirements":[{"quantity":"Err","op":"within","value":["-15/1000","15/1000"],"why":"5 mV offset + 1% of 1 V reading (source's combined form)"}]},
     }}
json.dump(flat("sheet"),open("brick.json","w"),indent=1)
json.dump(flat("prose"),open("brick-prose.json","w"),indent=1)

# find brick: largest Vref tolerance such that gain-only error <= 1%
f=flat("sheet"); f.pop("modes")
f["quantities"]["tV"]=g("0",unit="")
f["quantities"]["Vref"]=g("5","tV",unit="V")
for k in ["voff","ibn","ibp","oadc","ores","oinl"]: f["quantities"][k]=g("0",unit=("V" if k=="voff" else "A" if k in("ibn","ibp") else ""))
f["quantities"]["vin"]=g("1",unit="V")
f["requirements"]=[{"quantity":"Err","op":"within","value":["-1/100","1/100"],"why":"gain budget 1% of 1 V reading"}]
f["find"]={"largest":"tV","from":"0","to":"1/100","precision":"1/100000"}
json.dump(f,open("brick-find.json","w"),indent=1)

# components
amp={"stand":"ztl-stand/1","why":"k02 amp component","interface":{"inputs":{"vin":{"assume":["0","1"],"bands":["0","1/100000","99999/100000","1"]}},"outputs":["vo1"]},
 "quantities":{k:v for k,v in front("sheet").items() if k in ["R1","R2","dR1","dR2","Rs","voff","ibn","ibp","vin","vo1"]},
 "slots":{},"catalog":{},"define":{k:v for k,v in define.items() if k!="Vrefe"},"laws":[laws[0]],"requirements":[]}
json.dump(amp,open("k02-amp.json","w"),indent=1)
adq={k:v for k,v in front("sheet").items() if k in ["Vref","dVref","eg","oadc","ores","oinl","vo1","code"]}
adq["vo1"]=g("0",unit="V"); adq["vrec"]=der("V"); adq["Vrefnom"]=g("5",unit="V")
adc={"stand":"ztl-stand/1","why":"k02 ADC component; vrec = reading in volts at the amp output, using the nominal Vref","interface":{"inputs":{"vo1":{"assume":["-1/10","11/2"],"bands":["-1/10","-1/200","1/200","496/100","504/100","11/2"]}},"outputs":["vrec"]},
 "quantities":adq,"slots":{},"catalog":{},"define":{"Vrefe":define["Vrefe"]},
 "laws":[{"zfl":"code == 4095*vo1/Vrefe*(1+eg) + oadc + ores + oinl","source":laws[1]["source"]},
         {"zfl":"vrec == code*Vrefnom/4095","source":"reading in volts with nominal reference"}],"requirements":[]}
json.dump(adc,open("k02-adc.json","w"),indent=1)
def system(vin,req,why):
    return {"stand":"ztl-stand/1","why":"k02 system: amp component -> ADC component","components":{"AMP":{"file":"k02-amp.json"},"ADC":{"file":"k02-adc.json"}},
     "connect":{"AMP.vin":"vin","ADC.vo1":"AMP.vo1"},
     "quantities":{"vin":g(vin,unit="V"),"KAnom":g("5"),"Vmeas":der("V"),"Err":der("V")},
     "slots":{},"catalog":{},
     "laws":[{"zfl":"Vmeas == ADC.vrec/KAnom","source":"RTI: divide by nominal amp gain 1+40k/10k"},{"zfl":"Err == Vmeas - vin","source":"error RTI"}],
     "requirements":[{"quantity":"Err","op":"within","value":req,"why":why}]}
json.dump(system("0",["-5/1000","5/1000"],"offset budget 5 mV"),open("sys-offset.json","w"),indent=1)
json.dump(system("1",["-15/1000","15/1000"],"5 mV + 1% of 1 V"),open("sys-total.json","w"),indent=1)

# per-mode single bricks and range bricks
b=flat("sheet")
for name,m in b["modes"].items():
    x=copy.deepcopy(b); x.pop("modes")
    for k,v in m["quantities"].items():
        q=x["quantities"][k]; q.pop("range",None); q.pop("tolerance",None); q["value"]=v["value"]
    x["requirements"]=m["requirements"]
    json.dump(x,open("mode-%s.json"%name,"w"),indent=1)
    y=copy.deepcopy(x); y["requirements"]=[{"quantity":"Err","op":"within","value":["-1","1"],"why":"wide window: only to read the guaranteed range"}]
    json.dump(y,open("range-%s.json"%name,"w"),indent=1)

json.dump(system("1",["-20/1000","20/1000"],"20 mV (MY loosened bound, not the source's)"),open("sys-total20.json","w"),indent=1)

for n in ("25","35","50"):
    json.dump(system("1",["-%s/1000"%n,"%s/1000"%n],"%s mV (MY loosened bound, not the source's)"%n),open("sys-total%s.json"%n,"w"),indent=1)
