import json
def g(v,unit,why=None,**kw):
    d={"role":"given","unit":unit}
    if isinstance(v,list): d["range"]=v
    else: d["value"]=v
    if why: d["why"]=why
    d.update(kw); return d
q={
 "Pout":g("400","W","controller load at converter output"),
 "eta":g("0.92","","converter efficiency"),
 "Vmin":g("10","V","converter works while bank terminal voltage >= 10 V"),
 "Vsmin":g("21.6","V","minimum supply = initial capacitor voltage for R2"),
 "Vsmax":g("26.4","V","maximum supply for R1"),
 "Vfloat":g("24","V","float voltage of the bank (lifetime profile)"),
 "kpk":g("1.06","","imbalance factor, peak"),
 "kfl":g("1.03","","imbalance factor, float"),
 "kC":g(["0.72","0.80"],"","EOL capacitance factor: 0.80 x nominal after a further -10 % = 0.72; range [0.72,0.80]"),
 "kESRe":g("2","","EOL ESR = 2.0 x (nominal x temperature multiplier)"),
 "T":g(["-20","65"],"C","ambient range for R2"),
 "Tu":g("1","C","unit temperature, to make T dimensionless"),
 "Cbal":g("0.5","EUR","balancing circuit per cell"),
 "L0":g("1500","h","life at 65 C and rated voltage"),
 "Tref":g("65","C"),"dTL":g("10","C","life halves per 10 C"),
 "dVL":g("0.1","V","life halves per 0.1 V over rated"),
 "T1":g("25","C"),"T2":g("45","C"),"T3":g("60","C"),
 "f1":g("0.6",""),"f2":g("0.3",""),"f3":g("0.1",""),
 "thold":{"role":"derived","unit":"s"},
 "mB":{"role":"derived","unit":"V^2"},
 "dis":{"role":"derived","unit":"V^2"},
 "Vpk":{"role":"derived","unit":"V"},
 "life":{"role":"derived","unit":"h"},
}
define={
 "u":"T/Tu",
 "kT":"if(u < -10, 12/5 - 2/25*(u + 10), if(u < 0, 12/5 - 7/100*(u + 10), if(u < 25, 17/10 - 7/250*u, if(u < 45, 1 - 1/200*(u - 25), 9/10 - 1/400*(u - 45)))))",
 "Pin":"Pout/eta",
 "Rb":"NS.N*CELL.ESR*kESRe*kT/NP.N",
 "Cb":"NP.N*CELL.C*kC/NS.N",
 "v1":"Vmin + Rb*Pin/Vmin",
 "s0":"sqrt(Vsmin*Vsmin - 4*Rb*Pin)",
 "s1":"sqrt(v1*v1 - 4*Rb*Pin)",
 "Vc":"Vfloat/NS.N*kfl",
 "Lf":"pow(2, (CELL.Vr - Vc)/dVL)",
 "Li1":"L0*pow(2, (Tref - T1)/dTL)*Lf",
 "Li2":"L0*pow(2, (Tref - T2)/dTL)*Lf",
 "Li3":"L0*pow(2, (Tref - T3)/dTL)*Lf",
}
laws=[
 {"zfl":"dis == Vsmin*Vsmin - 4*Rb*Pin","source":"discriminant of v_t = (v_c + sqrt(v_c^2 - 4 R P_in))/2 at the start; negative = load cannot be supplied"},
 {"zfl":"mB == Vmin*Vmin - Rb*Pin","source":"closed form valid on the upper-root branch: v_c at vt=Vmin is Vmin + R P/Vmin, upper root iff R P <= Vmin^2 (see report)"},
 {"zfl":"thold == Cb/Pin*((Vsmin*Vsmin - v1*v1)/4 + (Vsmin*s0 - v1*s1 - 4*Rb*Pin*ln((Vsmin + s0)/(v1 + s1)))/4)",
  "source":"hand integral: dt = C_bank v_t dv_c / P_in, v_t=(v+sqrt(v^2-4RP))/2, from v_c=Vsmin down to v_c1 where v_t = Vmin"},
 {"zfl":"Vpk == Vsmax/NS.N*kpk","source":"worst cell voltage = bank voltage/n_s x 1.06"},
 {"zfl":"life == 1/(f1/Li1 + f2/Li2 + f3/Li3)","source":"L(T,Vc)=1500h*2^((65-T)/10)*2^((Vr-Vc)/0.1V); damage = sum fraction/L"},
]
req=[
 {"quantity":"Vpk","op":"<=","value":"CELL.Vr","why":"R1 peak cell voltage <= rated"},
 {"quantity":"dis","op":">=","value":"0","why":"R2: load must be suppliable (discriminant >= 0)"},
 {"quantity":"mB","op":">=","value":"0","why":"R2 validity of closed form (branch), see report"},
 {"quantity":"thold","op":">=","value":"8","why":"R2 hold >= 8.0 s at EOL, min supply, all ambients"},
 {"quantity":"life","op":">=","value":"131400","why":"R3 life >= 15 years"},
]
items=[]
for n,vr,c,e,p in [("S1","2.70","100","10.0","4.20"),("S2","2.70","150","7.0","5.60"),("S3","2.70","310","2.2","10.50"),("S4","3.00","60","18.0","3.40"),("S5","3.00","120","9.0","6.20"),("S6","2.50","350","3.0","9.40"),("S7","2.70","50","22.0","2.20"),("S8","2.85","200","5.5","7.80")]:
    items.append({"name":n,"Vr":vr,"C":c,"ESR":e,"price":p})
b={"stand":"universal-stand/1","quantities":q,
 "slots":{"CELL":{"from":["cells"]},"NS":{"from":["ns"]},"NP":{"from":["np"]}},
 "where":["NS.N*NP.N <= 100"],
 "define":define,"laws":laws,"requirements":req,
 "objective":{"minimize":"NS.N*NP.N*(CELL.price + Cbal)","why":"bank cost = n_s n_p (price + 0.50 balancing)"},
 "catalog":{
  "cells":{"ground":"problem statement cell table","items":items,
    "fields":{"Vr":{"unit":"V"},"C":{"unit":"F"},"ESR":{"unit":"mohm"},"price":{"unit":"EUR"}}},
  "ns":{"ground":"problem: n_s 6..15","integers":{"field":"N","from":"6","to":"15","unit":""}},
  "np":{"ground":"problem: n_p integer; n_s*n_p<=100 and n_s>=6 give n_p<=16","integers":{"field":"N","from":"1","to":"16","unit":""}}}}
json.dump(b,open("c08.json","w"),indent=1)
