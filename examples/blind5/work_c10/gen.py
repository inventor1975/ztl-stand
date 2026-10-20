import json,sys
# usage: gen.py out.json [mrange_json] 
def build(MLO="0",MHI="16",mlists=None, report=None, drop_floor=False):
    seasons = {
     "winter": dict(days=90, hrs=12, W=("4000","5000"), T=("8","11"), slot="MW"),
     "spring": dict(days=92, hrs=10, W=("9000","11000"), T=("16","19"), slot="MS"),
     "summer": dict(days=92, hrs=8, W=("16000","19000"), T=("26","30"), slot="MU"),
     "autumn": dict(days=91, hrs=11, W=("14000","16500"), T=("14","18"), slot="MA"),
    }
    q = {
     "T": {"role":"given","range":["5","35"],"unit":"C"},
     "W": {"role":"given","range":["4000","19000"],"unit":"kg"},
     "Tu": {"role":"given","value":"1","unit":"C"},
     "Cu": {"role":"given","value":"1","unit":"mg/L"},
     "Vp": {"role":"given","value":"24000","unit":"m^3"},
     "rf": {"role":"given","value":"0.30","unit":"g/(kg*h)"},
     "r0": {"role":"given","value":"0.15","unit":"g/(m^3*h)"},
     "kd0": {"role":"given","value":"0.015","unit":"1/h"},
     "Cstd": {"role":"given","value":"9.09","unit":"mg/L"},
     "t2": {"role":"given","value":"2","unit":"h"},
     "Css": {"role":"derived","unit":"mg/L"},
     "C2": {"role":"derived","unit":"mg/L"},
    }
    for s,d in seasons.items():
        q["days_"+s]={"role":"given","value":str(d["days"]),"unit":""}
        q["hrs_"+s]={"role":"given","value":str(d["hrs"]),"unit":"h"}
    q["Emax"]={"role":"given","value":"31000","unit":"kWh"}
    q["Pmax"]={"role":"given","value":"40","unit":"kW"}
    q["pe"]={"role":"given","value":"0.16","unit":"EUR/kWh"}
    q["yrs"]={"role":"given","value":"10","unit":""}
    knots=[(5,"12.8"),(10,"11.3"),(15,"10.1"),(20,"9.1"),(25,"8.3"),(30,"7.6"),(35,"7.0")]
    tab=", ".join(f"{a}, {b}" for a,b in knots)
    define = {
     "Cs": f"Cu*table(T/Tu, {tab})",
     "kd": "kd0*pow(1.024, T/Tu - 20)",
     "r": "rf*W*pow(1.08, T/Tu - 20)/Vp + r0*pow(1.065, T/Tu - 20)",
     "ox": "OX.rate/Vp",
     "mrun": "MW.k",
     "a": "mrun*AE.P*AE.SAE*0.90*pow(1.024, T/Tu - 20)/(Cstd*Vp)",
     "Cssd": "((kd + 0.95*a)*Cs - r)/(kd + a)",
    }
    inner = "Cs - (r - ox)/kd + (Cssd - (Cs - (r - ox)/kd))*exp(-kd*t2)"
    c2 = inner if drop_floor else f"max({inner}, 0*Cu)"
    laws=[
     {"zfl":"Css == Cssd","source":"night steady state: r = kd(Cs-C) + aerator transfer/V, solved for C"},
     {"zfl":"C2 == "+c2,"source":"closed form after 2 h power cut, floored at 0"},
    ]
    modes={}
    for s,d in seasons.items():
        modes[s]={"quantities":{"T":{"range":list(d["T"])},"W":{"range":list(d["W"])}},
                  "define":{"mrun":d["slot"]+".k"}}
    ml = mlists or {}
    cat={
     "aer":{"items":[
        {"name":"PW2","P":{"value":"2.0"},"SAE":{"value":"2.2"},"price":"3.6"},
        {"name":"PW37","P":{"value":"3.7"},"SAE":{"value":"2.0"},"price":"5.2"},
        {"name":"PROP","P":{"value":"1.5"},"SAE":{"value":"1.7"},"price":"2.3"},
        {"name":"DIFF","P":{"value":"5.5"},"SAE":{"value":"1.4"},"price":"6.8"}],
        "fields":{"P":{"unit":"kW"},"SAE":{"unit":"kg/kWh"},"price":{"unit":"kEUR"}}},
     "lox":{"items":[{"name":"none","price":"0","rate":"0"},{"name":"LOX","price":"6.5","rate":"6000"}],
        "fields":{"price":{"unit":"kEUR"},"rate":{"unit":"g/h"}}},
     "ncount":{"integers":{"field":"k","from":"1","to":"16","unit":""}},
     "mcount":{"integers":{"field":"k","from":MLO,"to":MHI,"unit":""}},
    }
    slots={"AE":{"from":["aer"]},"OX":{"from":["lox"]},"N":{"from":["ncount"]},
           "MW":{"from":["mcount"]},"MS":{"from":["mcount"]},"MU":{"from":["mcount"]},"MA":{"from":["mcount"]}}
    where=["N.k == max(max(MW.k, MS.k), max(MU.k, MA.k))",
           "N.k*AE.P <= Pmax",
           "Etot <= Emax"]
    computed={"Etot":{"value":"days_winter*hrs_winter*MW.k*AE.P + days_spring*hrs_spring*MS.k*AE.P + days_summer*hrs_summer*MU.k*AE.P + days_autumn*hrs_autumn*MA.k*AE.P","unit":"kWh"},
              "cost":{"value":"N.k*AE.price + OX.price + yrs*Etot*pe","unit":"kEUR"}}
    brick={"stand":"universal-stand/1","quantities":q,"slots":slots,"catalog":cat,"where":where,"computed":computed,
      "define":define,"laws":laws,
      "requirements":[
        {"quantity":"Css","op":">=","value":"4.0","why":"R1: night DO >= 4.0 mg/L in every season, worst case"},
        {"quantity":"C2","op":">=","value":"3.0","why":"R2: DO >= 3.0 mg/L after the 2 h power cut, every season"}],
      "modes":modes,
      "objective":{"minimize":"cost","unit":"kEUR","why":"10-year cost: installed prices + 10 y energy at 0.16 EUR/kWh"}}
    if report: brick["report"]=report
    return brick
if __name__=="__main__":
    json.dump(build(), open(sys.argv[1],"w"), indent=1)
