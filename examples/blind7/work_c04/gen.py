import json
periods=[("1","2.5","97","101","Press line"),("2","3.0","91","94","Grinding"),("3","2.0","84","87","Assembly"),("4","0.5","74","79","Inspection booth")]
def base(mode):
    q={"T0":{"role":"given","value":"8","unit":"h","why":"reference allowed time at 90 dBA"},
       "L0":{"role":"given","value":"90","unit":"dBA","why":"criterion level"},
       "S":{"role":"given","value":"5","unit":"dBA","why":"exchange rate: time halves per 5 dB"},
       "Lth":{"role":"given","value":"80","unit":"dBA","why":"below 80 dBA does not count"},
       "N7":{"role":"given","value":"7","unit":"dB","why":"NRR derating offset (NRR-7)"}}
    laws=[]
    for i,c,lo,hi,nm in periods:
        q["C"+i]={"role":"given","value":c,"unit":"h","why":nm+" duration"}
        q["L"+i]={"role":"given","range":[lo,hi],"unit":"dBA","why":nm+" level range"}
        q["Le"+i]={"role":"derived","unit":"dBA","why":"level after protector"}
        q["d"+i]={"role":"derived","unit":"","why":"dose fraction C/T (0 below 80 dBA)"}
        laws.append({"zfl":f"Le{i} == L{i} - (P.NRR - N7)","source":"protector lowers level by NRR-7"})
        laws.append({"zfl":f"d{i} == if(Le{i} >= Lth, C{i}/T0*pow(2,(Le{i}-L0)/S), 0)","source":"C/T with T=8/2^((L-90)/5); zero below 80 dBA"})
    q["D"]={"role":"derived","unit":"","why":"daily dose, fraction (x100 = percent)"}
    laws.append({"zfl":"D == 100*(d1+d2+d3+d4)","source":"D=100*sum(C/T)"})
    return q,laws
# brick a: no protector, TWA
q,laws=base("a")
q["TWA"]={"role":"derived","unit":"dBA","why":"equivalent 8h level"}
laws.append({"zfl":"TWA == 16.61*log10(D/100) + L0","source":"TWA formula"})
cat={"nop":{"items":[{"NRR":{"value":"7"},"price":"0"}],"fields":{"NRR":{"unit":"dB"},"price":{"unit":"USD"}},"ground":"problem: no protector, level unchanged (NRR-7=0)"}}
a={"stand":"ztl-stand/1","quantities":q,"slots":{"P":{"from":["nop"]}},"laws":laws,
 "requirements":[{"quantity":"D","op":">=","value":"0","why":"measure only: worst-case range of dose (no protector)"},
  {"quantity":"TWA","op":">=","value":"0","why":"measure only: range of TWA"}],
 "catalog":cat}
json.dump(a,open("c04a.json","w"),indent=1)
# brick b
q,laws=base("b")
prot=[("P1","15","0.20"),("P2","19","0.30"),("P3","22","0.45"),("P4","24","0.80"),("P5","27","1.10"),("P6","30","1.60")]
b={"stand":"ztl-stand/1","quantities":q,"slots":{"P":{"from":["prot"]}},"laws":laws,
 "requirements":[{"quantity":"D","op":"<=","value":"15","why":"dose must not exceed 15 %"}],
 "objective":{"minimize":"P.price","why":"cheapest admissible protector"},
 "report":"all",
 "catalog":{"prot":{"items":[{"name":n,"NRR":{"value":r},"price":p} for n,r,p in prot],"fields":{"NRR":{"unit":"dB"},"price":{"unit":"USD"}},"ground":"problem table"}}}
json.dump(b,open("c04.json","w"),indent=1)
