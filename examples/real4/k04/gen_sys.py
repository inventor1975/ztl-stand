import json
def w(n,d): json.dump(d,open(n,"w"),indent=1)
w("comp_fb.json",{"stand":"ztl-stand/1","why":"TPS54331 reference + feedback divider (datasheet Eq. 5, R5=10.2k, R6=3.24k)",
 "interface":{"inputs":{},"outputs":["Vo"]},
 "quantities":{"Vref":{"role":"given","range":["0.772","0.828"],"unit":"V","ground":"datasheet 6.5"},
   "R5":{"role":"given","value":"10.2","unit":"kohm"},"R6":{"role":"given","value":"3.24","unit":"kohm"},
   "Vo":{"role":"derived","unit":"V"}},
 "slots":{},"laws":[{"zfl":"Vo == Vref*(1 + R5/R6)","source":"datasheet Eq. 5"}],"requirements":[],"catalog":{}})
vb=["7","20","28"]
Lb=[str(x/2) for x in range(2,25)]
Lb=[x.rstrip("0").rstrip(".") if "." in x else x for x in Lb]+["15","20","30"]
w("comp_ls.json",{"stand":"ztl-stand/1","why":"output inductor current: ripple, peak, RMS (datasheet Eq. 9-11) for a given inductance L",
 "interface":{"inputs":{"Vin":{"assume":["7","28"],"bands":vb},
                        "Vo":{"assume":["3.2","3.44"]},
                        "L":{"assume":["1","30"],"bands":Lb}},
              "outputs":["ILPP","ILpk","ILrms"]},
 "quantities":{"Vin":{"role":"given","value":"28","unit":"V"},"Vo":{"role":"given","value":"3.3","unit":"V"},
   "L":{"role":"given","value":"10","unit":"uH"},
   "fsw":{"role":"given","range":["456","684"],"unit":"kHz","ground":"datasheet 6.6"},
   "kL":{"role":"given","range":["0.8","1"],"unit":"","ground":"factor 0.8 of datasheet Eq. 9 read as inductance derating (interpretation)"},
   "Io":{"role":"given","value":"3","unit":"A"},
   "ILPP":{"role":"derived","unit":"A"},"ILpk":{"role":"derived","unit":"A"},"ILrms":{"role":"derived","unit":"A"}},
 "slots":{},"laws":[{"zfl":"ILPP == Vo*(Vin - Vo)/(Vin*L*kL*fsw)","source":"Eq. 9"},
   {"zfl":"ILpk == Io + ILPP/2","source":"Eq. 11"},
   {"zfl":"ILrms == sqrt(Io*Io + ILPP*ILPP/12)","source":"Eq. 10"}],"requirements":[],"catalog":{}})
w("comp_co.json",{"stand":"ztl-stand/1","why":"output capacitors 2 x 47 uF, ESR max 2 mOhm each (parallel 1 mOhm); standard ripple formula, NOT the datasheet's Eq. 13 (see report)",
 "interface":{"inputs":{"ILPP":{"assume":["0","4"],"bands":["0","1","2","4"]}},"outputs":["Vopp"]},
 "quantities":{"ILPP":{"role":"given","value":"1","unit":"A"},
   "fsw":{"role":"given","range":["456","684"],"unit":"kHz"},
   "Co":{"role":"given","value":"94","unit":"uF","ground":"datasheet 8.2.2.6: two 47 uF"},
   "Resr":{"role":"given","value":"1","unit":"mohm","ground":"datasheet 8.2.2.6: 2 mohm max each, two in parallel"},
   "Vopp":{"role":"derived","unit":"V"}},
 "slots":{},"laws":[{"zfl":"Vopp == ILPP*(1/(8*fsw*Co) + Resr)","source":"standard buck output ripple (capacitive part + ESR part)"}],
 "requirements":[],"catalog":{}})
def sysd(find):
    return {"stand":"ztl-stand/1","why":"TPS54331 output filter as a chain FB -> inductor stage -> output capacitor; smallest L",
 "components":{"FB":{"file":"comp_fb.json"},"LS":{"file":"comp_ls.json"},"CO":{"file":"comp_co.json"}},
 "connect":{"LS.Vin":"Vin","LS.Vo":"FB.Vo","LS.L":"Lsys","CO.ILPP":"LS.ILPP"},
 "quantities":{"Vin":{"role":"given","range":["7","28"],"unit":"V"},
   "Lsys":{"role":"given","value":"10","unit":"uH"},
   "Io":{"role":"given","value":"3","unit":"A"},"Isat":{"role":"given","value":"3.84","unit":"A"},
   "Irmsmax":{"role":"given","value":"3.6","unit":"A"},
   "Kr":{"role":"derived","unit":""},"Pk":{"role":"derived","unit":"A"},"Rms":{"role":"derived","unit":"A"},"Vrip":{"role":"derived","unit":"V"}},
 "laws":[{"zfl":"Kr == LS.ILPP/Io"},{"zfl":"Pk == LS.ILpk"},{"zfl":"Rms == LS.ILrms"},{"zfl":"Vrip == CO.Vopp"}],
 "requirements":[{"quantity":"Kr","op":"<=","value":"0.3","why":"KIND 0.3"},
   {"quantity":"Pk","op":"<=","value":"Isat","why":"saturation"},
   {"quantity":"Rms","op":"<=","value":"Irmsmax","why":"RMS rating"},
   {"quantity":"Vrip","op":"<=","value":"0.03","why":"30 mV output ripple, datasheet Table 8-1"}],
 "find":find}
def fnd(req,prec="0.1"):
    return {"smallest":"Lsys","from":"1","to":"30","precision":prec,"requirements":req}
reqs={"k":{"quantity":"Kr","op":"<=","value":"0.3","why":"KIND 0.3"},
      "p":{"quantity":"Pk","op":"<=","value":"Isat","why":"saturation"},
      "r":{"quantity":"Rms","op":"<=","value":"Irmsmax","why":"RMS rating"},
      "v":{"quantity":"Vrip","op":"<=","value":"0.03","why":"30 mV output ripple"}}
w("system.json",sysd([fnd([reqs[k]],"0.5") for k in "kpv"]))
w("system_one.json",sysd(fnd([reqs["p"]],"0.5")))
