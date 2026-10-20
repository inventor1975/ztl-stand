import json,sys
props=[("P1","1.30","0.28","0.62","0.030",5200),("P2","1.30","0.33","0.78","0.036",5400),("P3","1.30","0.38","0.92","0.042",5600),
("P4","1.45","0.27","0.64","0.030",6900),("P5","1.45","0.32","0.80","0.036",7100),("P6","1.45","0.37","0.94","0.042",7400),
("P7","1.60","0.26","0.66","0.030",9100),("P8","1.60","0.31","0.82","0.036",9500)]
gears=[("G1","3.0",4800),("G2","3.5",5200),("G3","4.0",5900),("G4","4.5",6700),("G5","5.0",7500)]
g=lambda v,u,why="":{"role":"given","value":v,"unit":u,**({"why":why} if why else {})}
Q={
 "rho":g("1025","kg/m^3","sea water density, problem statement"),
 "w":g("0.12","","wake fraction"),
 "t":g("0.10","","thrust deduction"),
 "eg":g("0.97","","gear efficiency"),
 "KN":g("0.5144","m/s","1 knot, the statement's own value"),
 "URPM":g("1","rpm","unit constant: 1 rpm"),
 "HZ":g("1","1/s","unit constant"),
 "TQ1":g("1","N*m","unit constant"),
 "KNF":g("1","kN","unit constant"),
 "fKT":{"role":"given","range":["0.97","1.03"],"unit":"","why":"propeller K_T tolerance factor +-3%"},
 "fKQ":{"role":"given","range":["0.97","1.03"],"unit":"","why":"propeller K_Q tolerance factor +-3%"},
 "fE":{"role":"given","range":["0.96","1.00"],"unit":"","why":"engine torque factor, aged..new"},
 "fres":g("1.365","","resistance factor: heavy 1.30*1.05; set per mode"),
 "bol":g("0","","1 = bollard mode (J=0, no hull resistance), 0 = free running; set per mode"),
 "N":{"role":"derived","unit":"rpm","search":["300","2400"],"why":"engine rpm at the operating point"},
 "Tnet":{"role":"derived","unit":"kN","why":"net thrust T(1-t)"},
 "Vkn":{"role":"derived","unit":"","why":"boat speed in knots (numeric)"},
 "Tip":{"role":"derived","unit":"m/s","why":"propeller tip speed pi n D"},
 "Jm":{"role":"derived","unit":"","why":"J0 - J, validity of the linear K_T,K_Q (J <= J0)"},
}
Nr="(N/URPM)"
tab=("if(Nr > 800, if(Nr > 1000, if(Nr > 1400, if(Nr > 1800, if(Nr > 2000, if(Nr > 2150, 0, 1430 - (1430/150)*(Nr - 2000)),"
     " 1450 - (1/10)*(Nr - 1800)), 1500 - (1/8)*(Nr - 1400)), 1250 + (5/8)*(Nr - 1000)), 1000 + (1/4)*(Nr - 800)), 1000)")
rt=("if(Vk > 4, if(Vk > 6, if(Vk > 8, if(Vk > 9, if(Vk > 10, if(Vk > 11, if(Vk > 12, if(Vk > 13, 64 + 17*(Vk - 13), 47 + 17*(Vk - 12)),"
    " 34 + 13*(Vk - 11)), 25 + 9*(Vk - 10)), 18.5 + (13/2)*(Vk - 9)), 13.5 + 5*(Vk - 8)), 7 + (13/4)*(Vk - 6)), 3 + 2*(Vk - 4)), (3/4)*Vk)")
D={
 "Nr":"N/URPM",
 "nn":"Nr/(60*GR.i)*HZ",
 "Tab":tab,
 "Te":"fE*Tab*TQ1",
 "KQn":"Te*GR.i*eg/(rho*nn*nn*PR.D*PR.D*PR.D*PR.D*PR.D)",
 "Jt":"(PR.J0/(3/4))*(1 - KQn/(PR.KQ0*fKQ))",
 "Jd":"if(bol > 0.5, 0, Jt)",
 "Vk":"Jd*nn*PR.D/(1 - w)/KN",
 "Rtab":rt,
}
for k in ("Tab","Rtab"):
    D[k]=D[k].replace("Nr","Nr")
laws=[
 {"zfl":"if(bol > 0.5, PR.KQ0*fKQ*rho*nn*nn*PR.D*PR.D*PR.D*PR.D, (1 - t)*fKT*PR.KT0*(1 - Jd/PR.J0)*rho*nn*nn*PR.D*PR.D*PR.D*PR.D) == if(bol > 0.5, Te*GR.i*eg/PR.D, fres*Rtab*KNF)",
  "source":"operating point: free running = net thrust equals hull resistance while propeller torque (through J from the torque balance) equals engine torque curve; bollard (bol=1) = J=0, propeller torque equals engine torque, force form Q_p/D"},
 {"zfl":"Tnet == (1 - t)*fKT*PR.KT0*(1 - Jd/PR.J0)*rho*nn*nn*PR.D*PR.D*PR.D*PR.D","source":"T = K_T rho n^2 D^4, net T(1-t)"},
 {"zfl":"Vkn == Vk","source":"speed through water V from J = V(1-w)/(nD), in knots"},
 {"zfl":"Tip == pi*nn*PR.D","source":"tip speed"},
 {"zfl":"Jm == PR.J0 - Jd","source":"linear K_T/K_Q model valid for J <= J0"},
]
fav={"fKT":{"value":"0.97"},"fKQ":{"value":"1.03"},"fE":{"value":"0.96"}}
modes={
 "bollard R1":{"quantities":{**fav,"bol":{"value":"1"},"fres":{"value":"1"}},
   "requirements":[{"quantity":"Tnet","op":">=","value":"30","why":"R1 bollard pull >= 30 kN, unfavourable tolerances"},
                   {"quantity":"Jm","op":">=","value":"0","why":"validity (J=0 here, trivial)"}]},
 "heavy R2":{"quantities":{**fav,"bol":{"value":"0"},"fres":{"value":"1.365"}},
   "requirements":[{"quantity":"Vkn","op":">=","value":"9","why":"R2 heavy speed >= 9 kn, unfavourable tolerances"},
                   {"quantity":"Jm","op":">=","value":"0","why":"linear K_T/K_Q valid for J<=J0"}]},
 "heavy R3":{"quantities":{"bol":{"value":"0"},"fres":{"value":"1.365"}},
   "requirements":[{"quantity":"N","op":">=","value":"1900","why":"R3 heavy engine rpm >= 1900, whole tolerance box"},
                   {"quantity":"Jm","op":">=","value":"0","why":"validity"}]},
 "light R4":{"quantities":{"fKT":{"value":"1.03"},"fKQ":{"value":"0.97"},"fE":{"value":"1.00"},"bol":{"value":"0"},"fres":{"value":"0.76"}},
   "requirements":[{"quantity":"N","op":"<=","value":"2060","why":"R4 light over-speed margin"},
                   {"quantity":"Tip","op":"<=","value":"32","why":"R4 tip speed <= 32 m/s"},
                   {"quantity":"Jm","op":">=","value":"0","why":"validity"}]},
}
cat={
 "propellers":{"ground":"problem statement table","fields":{"D":{"unit":"m"},"KT0":{"unit":""},"J0":{"unit":""},"KQ0":{"unit":""},"price":{"unit":"EUR"}},
   "items":[{"D":d,"KT0":a,"J0":b,"KQ0":c,"price":str(p),"grade":n} for n,d,a,b,c,p in props]},
 "gears":{"ground":"problem statement table","fields":{"i":{"unit":""},"price":{"unit":"EUR"}},
   "items":[{"i":i,"price":str(p),"grade":n} for n,i,p in gears]},
}
brick={"stand":"universal-stand/1","quantities":Q,"slots":{"PR":{"from":["propellers"]},"GR":{"from":["gears"]}},
 "define":D,"laws":laws,"requirements":[],"modes":modes,
 "objective":{"minimize":"PR.price + GR.price","why":"cheapest propeller + gear"},"catalog":cat}
if len(sys.argv)>2 and sys.argv[2]=="all": brick["report"]="all"
if len(sys.argv)>3:
    P=sys.argv[3].split(",");G=sys.argv[4].split(",")
    cat["propellers"]["items"]=[x for x in cat["propellers"]["items"] if x["grade"] in P]
    cat["gears"]["items"]=[x for x in cat["gears"]["items"] if x["grade"] in G]
if len(sys.argv)>5:
    keep=sys.argv[5].split(",")
    brick["modes"]={k:v for k,v in brick["modes"].items() if k.split()[1] in keep or k in keep}

order=["heavy R2","bollard R1","light R4","heavy R3"]
brick["modes"]={k:brick["modes"][k] for k in order if k in brick["modes"]}
json.dump(brick,open(sys.argv[1],"w"),indent=1)
