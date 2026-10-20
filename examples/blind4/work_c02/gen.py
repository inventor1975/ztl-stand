import json,sys
from fractions import Fraction as F
T=[("Mg-S-8","8","1.55","1100","0.60","0.15","45"),
("Mg-S-17","17","1.55","1100","1.00","0.20","78"),
("Mg-S-32","32","1.55","1100","1.40","0.25","130"),
("Mg-H-8","8","1.75","1150","0.60","0.15","52"),
("Mg-H-17","17","1.75","1150","1.00","0.20","90"),
("Zn-12","12","1.10","780","0.80","0.12","60"),
("Zn-25","25","1.10","780","1.20","0.16","110")]
items=[]
for name,m,ea,cap,L,d,pr in T:
    ea=F(ea); cap=F(cap)
    items.append({"m":m,
      "Ea":{"range":[str(ea-F("0.05")),str(ea+F("0.05"))]},
      "cap":{"range":[str(cap*F(92,100)),str(cap)]},
      "L":L,"d":d,"price":pr,"grade":name})
q={
 "rho_w":{"role":"given","value":"12","unit":"ohm*m","why":"wet-season soil resistivity (half of life)"},
 "rho_d":{"role":"given","value":"140","unit":"ohm*m","why":"dry-season soil resistivity (half of life)"},
 "Rc":{"role":"given","value":"0.2","unit":"ohm","why":"cable and structure resistance in series"},
 "Vp":{"role":"given","value":"0.85","unit":"V","why":"polarisation potential at I = Ip"},
 "beta":{"role":"given","range":["0.12","0.18"],"unit":"V","why":"Tafel slope, V per decade"},
 "Ip":{"role":"given","range":["0.012","0.06"],"unit":"A","why":"protection-current demand (protection mode); the life mode sets 0.030"},
 "Util":{"role":"given","value":"0.9","unit":"","why":"utilisation factor"},
 "Iw":{"role":"derived","unit":"A","search":["0.0005","5"],"why":"anode group current at the wet-season operating point"},
 "Id":{"role":"derived","unit":"A","search":["0.0005","5"],"why":"anode group current at the dry-season operating point"},
 "Esw":{"role":"derived","unit":"V","why":"structure potential magnitude, wet"},
 "Esd":{"role":"derived","unit":"V","why":"structure potential magnitude, dry"},
 "Iavg":{"role":"derived","unit":"A","why":"time-average anode current"},
 "Life":{"role":"derived","unit":"h","why":"anode life in hours"},
 "Cinst":{"role":"given","value":"40","unit":"EUR","why":"install cost per anode"},
}
define={
 "R1w":"rho_w/(2*pi*AN.L)*(ln(4*AN.L/AN.d) - 1)",
 "R1d":"rho_d/(2*pi*AN.L)*(ln(4*AN.L/AN.d) - 1)",
 "Rtw":"R1w/CNT.N*(1 + 0.15*ln(CNT.N)) + Rc",
 "Rtd":"R1d/CNT.N*(1 + 0.15*ln(CNT.N)) + Rc",
}
laws=[
 {"zfl":"Iw*Rtw == AN.Ea - Vp - beta*log10(Iw/Ip)","source":"circuit I*(Rgroup+Rc)=Ea-Es with steel polarisation Es=0.85+beta*log10(I/Ip), wet season (implicit)"},
 {"zfl":"Id*Rtd == AN.Ea - Vp - beta*log10(Id/Ip)","source":"same, dry season (implicit)"},
 {"zfl":"Esw == AN.Ea - Iw*Rtw","source":"circuit equation, wet"},
 {"zfl":"Esd == AN.Ea - Id*Rtd","source":"circuit equation, dry"},
 {"zfl":"Iavg == 0.5*Iw + 0.5*Id","source":"each season is half of the life"},
 {"zfl":"Life == CNT.N*AN.m*AN.cap*Util/Iavg","source":"Faraday: charge = n*m*capacity*utilisation, delivered at Iavg"},
]
modes={
 "protection":{"quantities":{"Ip":{"range":["0.012","0.06"]}},
   "requirements":[
    {"quantity":"Esw","op":"within","value":["0.85","1.18"],"why":"R1 wet: 0.85 <= Es <= 1.18 V"},
    {"quantity":"Esd","op":"within","value":["0.85","1.18"],"why":"R1 dry: 0.85 <= Es <= 1.18 V"}]},
 "life":{"quantities":{"Ip":{"value":"0.030"}},
   "requirements":[{"quantity":"Life","op":">=","value":"262800","why":"R2: 30 years x 8760 h, worst case over cap, Ea, beta"}]},
}
catalog={
 "anodes":{"ground":"anode datasheet (fictional)","items":items,
   "fields":{"m":{"unit":"kg"},"Ea":{"unit":"V"},"cap":{"unit":"A*h/kg"},"L":{"unit":"m"},"d":{"unit":"m"},"price":{"unit":"EUR"}}},
 "counts":{"integers":{"field":"N","from":"1","to":"60","unit":""}},
}
b={"stand":"universal-stand/1","quantities":q,"slots":{"AN":{"from":["anodes"]},"CNT":{"from":["counts"]}},
 "define":define,"laws":laws,"requirements":[],"modes":modes,
 "objective":{"minimize":"CNT.N*(AN.price + Cinst)","why":"n*(price+40)"},
 "catalog":catalog}
json.dump(b,open(sys.argv[1],"w"),indent=1)
