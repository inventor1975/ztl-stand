import json, sys
variant = sys.argv[1] if len(sys.argv)>1 else "closed"
out = sys.argv[2] if len(sys.argv)>2 else "../c07.json"
opts = sys.argv[3:]
GROUP = "group" in opts
WIDE = "wide" in opts
storms = [("1","10",900,("85","92")),("2","10",1800,("62","68")),("3","10",3600,("40","44")),
          ("4","100",900,("125","135")),("5","100",1800,("92","100")),("6","100",3600,("62","66"))]
q = {
 "Ac": {"role":"given","value":"22000","unit":"m^2","ground":"problem statement","why":"paved catchment 2.2 ha"},
 "C":  {"role":"given","range":["0.70","0.80"],"unit":"","why":"runoff coefficient, one value for all storms"},
 "Cd": {"role":"given","range":["0.58","0.64"],"unit":"","why":"orifice discharge coefficient, one value for all storms"},
 "g":  {"role":"given","value":"9.81","unit":"m/s^2","why":"g = 9.81 as the problem states (not g0)"},
 "cp": {"role":"given","value":"0.12","unit":"kEUR/m^3","why":"pond price per m3 of plan area x depth"},
 "fb": {"role":"given","value":"0.30","unit":"m","why":"freeboard"},
}
define = {"Ao":"pi*PL.d*PL.d/4"}
laws = []
reqs = []
for k,rp,t,(lo,hi) in storms:
    q["t"+k] = {"role":"given","value":str(t),"unit":"s","why":f"storm duration {t} s"}
    q["i"+k] = {"role":"given","range":[lo,hi],"unit":"mm/h","why":f"{rp}-year, {t//60} min intensity, independent"}
    define["Qin"+k] = f"C*i{k}*Ac"
    q["h"+k] = {"role":"derived","unit":"m","why":f"water depth at end of storm {rp}y/{t}s"}
    q["Qp"+k] = {"role":"derived","unit":"m^3/s","why":f"peak outflow storm {rp}y/{t}s"}
    if variant=="implicit":
        q["h"+k]["search"]=["0.01","12"]
        laws.append({"zfl":f"PA.A*h{k} + Cd*Ao*sqrt(1.2*g*h{k})*t{k} == Qin{k}*t{k}","source":f"storage balance, storm {rp}y/{t}s (mean head 0.6 h)"})
    else:
        # closed form root: s = sqrt(h) = (-kk + sqrt(kk^2 + 4 A Qin t)) / (2A)
        define["kk"+k] = f"Cd*Ao*sqrt(1.2*g)*t{k}"
        q["s"+k] = {"role":"derived","unit":"m^0.5","why":"sqrt(h)"}
        laws.append({"zfl":f"s{k} == (sqrt(kk{k}*kk{k} + 4*PA.A*Qin{k}*t{k}) - kk{k})/(2*PA.A)","source":"positive root of A s^2 + kk s = Qin t"})
        laws.append({"zfl":f"h{k} == s{k}*s{k}","source":"h = s^2"})
    laws.append({"zfl":f"Qp{k} == Cd*Ao*sqrt(2*g*h{k})","source":"orifice peak outflow"})
    if rp=="100":
        q["M"+k] = {"role":"derived","unit":"m","why":"depth margin H - h"}
        laws.append({"zfl":f"M{k} == PH.H - h{k}","source":"freeboard margin"})
    if not GROUP:
        if rp=="10":
            reqs.append({"quantity":"Qp"+k,"op":"<=","value":"0.025","why":f"R1: 10-year Qpeak <= 25 L/s (storm {t}s)"})
        else:
            reqs.append({"quantity":"Qp"+k,"op":"<=","value":"0.045","why":f"R2: 100-year Qpeak <= 45 L/s (storm {t}s)"})
            reqs.append({"quantity":"M"+k,"op":">=","value":"fb","why":f"R3: h <= H - 0.30 m (storm {t}s)"})
if GROUP:
    q["Q10"]={"role":"derived","unit":"m^3/s","why":"largest 10-year peak outflow over the three durations"}
    q["Q100"]={"role":"derived","unit":"m^3/s","why":"largest 100-year peak outflow over the three durations"}
    q["Mmin"]={"role":"derived","unit":"m","why":"smallest 100-year freeboard margin H - h"}
    laws.append({"zfl":"Q10 == max(max(Qp1, Qp2), Qp3)","source":"max over the three 10-year storms"})
    laws.append({"zfl":"Q100 == max(max(Qp4, Qp5), Qp6)","source":"max over the three 100-year storms"})
    laws.append({"zfl":"Mmin == min(min(M4, M5), M6)","source":"min over the three 100-year storms"})
    reqs.append({"quantity":"Q10","op":"<=","value":"0.025","why":"R1: 10-year Qpeak <= 25 L/s, every storm"})
    reqs.append({"quantity":"Q100","op":"<=","value":"0.045","why":"R2: 100-year Qpeak <= 45 L/s, every storm"})
    reqs.append({"quantity":"Mmin","op":">=","value":"fb","why":"R3: h <= H - 0.30 m, every 100-year storm"})
reqs.append({"quantity":"PL.d","op":">=","value":"80","why":"R4: d >= 80 mm (clogging)"})
cat = {
 "plates":{"ground":"problem statement","items":[
   {"name":"O60","d":"60","price":"0.30"},{"name":"O80","d":"80","price":"0.45"},{"name":"O100","d":"100","price":"0.60"},
   {"name":"O120","d":"120","price":"0.80"},{"name":"O150","d":"150","price":"1.10"}],
   "fields":{"d":{"unit":"mm"},"price":{"unit":"kEUR"}}},
 "pondA":{"continuous":{"field":"A","from":"100","to":("1500" if WIDE else "610"),"unit":"m^2"}},
 "pondH":{"continuous":{"field":"H","from":"0.8","to":("3.0" if WIDE else "2.0"),"unit":"m"}},
}
if WIDE:
    reqs.append({"quantity":"PA.A","op":"<=","value":"610","why":"R5a: site limit A <= 610 m2"})
    reqs.append({"quantity":"PH.H","op":"<=","value":"2.0","why":"R5b: site limit H <= 2.0 m"})
drops=[o[5:] for o in opts if o.startswith('drop:')]
reqs=[r for r in reqs if not any(r['why'].startswith(d+':') or r['why'].startswith(d+'a:') or r['why'].startswith(d+'b:') for d in drops)]
brick = {"stand":"ztl-stand/1","note":"c07 stormwater detention pond, variant "+variant,
 "quantities":q,"slots":{"PL":{"from":["plates"]},"PA":{"from":["pondA"]},"PH":{"from":["pondH"]}},
 "define":define,"laws":laws,"requirements":reqs,
 "objective":{"minimize":"cp*PA.A*PH.H + PL.price","unit":"kEUR","why":"pond + plate price"},
 "catalog":cat}
json.dump(brick,open(out,"w"),indent=1)
