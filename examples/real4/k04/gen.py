import json
def base(nominal=False, kl=True, dropvref=False):
    q={}
    if nominal:
        q["Vin"]={"role":"given","value":"28","unit":"V","ground":"TI datasheet Table 8-1 (max of 7-28 V)"}
        q["Vo"]={"role":"given","value":"3.3","unit":"V","ground":"TI datasheet Table 8-1"}
        q["fsw"]={"role":"given","value":"570","unit":"kHz","ground":"TI datasheet 6.6 typ"}
    else:
        q["Vin"]={"role":"given","range":["7","28"],"unit":"V","ground":"TI datasheet Table 8-1 input voltage range"}
        q["Vref"]={"role":"given","range":["0.772","0.828"],"unit":"V","ground":"TI datasheet 6.5 voltage reference min/max"}
        q["R5"]={"role":"given","value":"10.2","unit":"kohm","ground":"TI datasheet 8.2.2.3 (R4=10.2k)"}
        q["R6"]={"role":"given","value":"3.24","unit":"kohm","ground":"TI datasheet 8.2.2.3"}
        q["fsw"]={"role":"given","range":["456","684"],"unit":"kHz","ground":"TI datasheet 6.6 switching frequency min/max"}
        q["Vo"]={"role":"derived","unit":"V"}
    if kl and not nominal:
        q["kL"]={"role":"given","range":["0.8","1"],"unit":"","ground":"factor 0.8 in the datasheet's Eq. 9 read as inductance derating (an interpretation)"}
    q["Io"]={"role":"given","value":"3","unit":"A","ground":"TI datasheet Table 8-1 output current rating"}
    q["Isat"]={"role":"given","value":"3.84","unit":"A","ground":"TI datasheet 8.2.2.5.1, Sumida CDRH103-6R8 saturation rating"}
    q["Irmsmax"]={"role":"given","value":"3.6","unit":"A","ground":"TI datasheet 8.2.2.5.1, Sumida CDRH103-6R8 RMS rating"}
    q["Lind"]={"role":"given","value":"10","unit":"uH","why":"the inductance searched (find): nominal value of the inductor"}
    for n,u in (("ILPP","A"),("Kr",""),("ILpk","A"),("ILrms","A")):
        q[n]={"role":"derived","unit":u}
    return q
def laws(nominal, kl):
    leff="Lind*kL" if (kl and not nominal) else "Lind"
    L=[]
    if not nominal:
        L.append({"zfl":"Vo == Vref*(1 + R5/R6)","source":"datasheet Eq. 5"})
    L+= [{"zfl":"ILPP == Vo*(Vin - Vo)/(Vin*%s*fsw)"%leff,"source":"datasheet Eq. 8/9 (ripple current)"},
         {"zfl":"Kr == ILPP/Io","source":"definition of KIND, Eq. 8"},
         {"zfl":"ILpk == Io + ILPP/2","source":"datasheet Eq. 11"},
         {"zfl":"ILrms == sqrt(Io*Io + ILPP*ILPP/12)","source":"datasheet Eq. 10"}]
    return L
R_K={"quantity":"Kr","op":"<=","value":"0.3","why":"KIND = 0.3 (low-ESR ceramic output caps), Eq. 8 guideline"}
R_P={"quantity":"ILpk","op":"<=","value":"Isat","why":"peak inductor current below the part's saturation rating"}
R_R={"quantity":"ILrms","op":"<=","value":"Irmsmax","why":"RMS inductor current below the part's RMS rating"}
def mk(name,nominal=False,kl=True,finds="all",prec="0.01"):
    fl=[]
    for r,lab in ((R_K,"ripple ratio"),(R_P,"peak"),(R_R,"rms")):
        if finds=="all" or finds==lab:
            fl.append({"smallest":"Lind","from":"1","to":"30","precision":prec,"requirements":[r]})
    d={"stand":"ztl-stand/1","quantities":base(nominal,kl),"slots":{},"laws":laws(nominal,kl),
       "requirements":[R_K],"catalog":{},"find":fl if len(fl)>1 else fl[0],"conflicts":False}
    json.dump(d,open(name,"w"),indent=1)
mk("brick_nominal.json",nominal=True,finds="ripple ratio")
mk("brick.json")
mk("brick_nokL.json",kl=False)
