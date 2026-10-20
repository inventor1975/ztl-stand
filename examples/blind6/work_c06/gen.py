import json
import os
from decimal import Decimal, getcontext, ROUND_FLOOR, ROUND_CEILING
getcontext().prec=50
def Krange(K25,a):
    K25=Decimal(K25);a=Decimal(a)
    lo=K25*(-5*a).exp()   # T=30
    hi=K25*(10*a).exp()   # T=15
    q9=Decimal("1e-9")
    return str(lo.quantize(q9,rounding=ROUND_FLOOR)), str(hi.quantize(q9,rounding=ROUND_CEILING))
# generator for c06.json (flat brick). Stages are indexed z1..z4 FROM THE SOLVENT END (z1 = x_N raffinate).
def q(role,**k): d={"role":role}; d.update(k); return d
Q={
 "F":q("given",value="1.5",unit="m^3/h",why="wastewater flow"),
 "cF":q("given",range=["6.0","7.5"],unit="g/L",why="feed solute concentration"),
 "rho":q("given",range=["0.02","0.04"],unit="",why="recycle residual fraction, shared"),
 "qc":q("given",range=["0.10","0.14"],unit="kg/kg",why="carbon capacity"),
 "e":q("given",range=["0.90","0.96"],unit="",why="carbon removal efficiency"),
 "Hmo":q("given",value="700",unit="h",why="hours per month"),
 "Hyr":q("given",value="8000",unit="h",why="operating hours per year"),
 "Yrs":q("given",value="5",unit="",why="years"),
}
for i in range(1,5): Q["z%d"%i]=q("derived",unit="g/L",why="x_(N+1-%d): water concentration leaving the stage numbered %d from the solvent end"%(i,i))
Q["xN"]=q("derived",unit="g/L",why="raffinate x_N = z1")
Q["xf"]=q("derived",unit="g/L",why="x_1 (feed-end stage) = z_N")
Q["y1"]=q("derived",unit="g/L",why="loaded solvent y_1 = Keff x_1")
Q["Dis"]=q("derived",unit="g/L",why="final discharge (1-e) x_N")
Q["Life"]=q("derived",unit="",why="bed life, months")
# flags: a_j = 1 if stage j (from solvent end) exists
comp={}
for j in range(1,5): comp["a%d"%j]="min(1, max(0, EX.N - %d))"%(j-1)
for j in range(1,5): comp["b%d"%j]="1 - a%d"%j
comp["w1"]="a1 - a2"; comp["w2"]="a2 - a3"; comp["w3"]="a3 - a4"; comp["w4"]="a4"
laws=[]
def L(z,s): laws.append({"zfl":z,"source":s})
# stage j (from solvent end), active:  F (z_{j+1}-z_j) = S Keff (z_j - z_{j-1});  j=1: F (z2-z1) = S Keff (z1 - rho*x_1)
# dummy (j>N): z_j = cF.  z_{N+1} = cF is supplied by the dummy stage (j=4: cF itself)
L("a1*F*(z2 - z1) + b1*F*(z1 - cF) == a1*SS.x*Keff*(z1 - rho*xf)","stage N (solvent end): F (x_{N-1}-x_N) = S (Keff x_N - rho Keff x_1)")
L("a2*F*(z3 - z2) + b2*F*(z2 - cF) == a2*SS.x*Keff*(z2 - z1)","stage N-1: F (x_{N-2}-x_{N-1}) = S Keff (x_{N-1}-x_N)")
L("a3*F*(z4 - z3) + b3*F*(z3 - cF) == a3*SS.x*Keff*(z3 - z2)","stage N-2")
L("a4*F*(cF - z4) + b4*F*(z4 - cF) == a4*SS.x*Keff*(z4 - z3)","stage N-3 (x_0 = cF)")
L("xN == z1","raffinate is the solvent-end stage")
L("xf == w1*z1 + w2*z2 + w3*z3 + w4*z4","x_1 is stage number N from the solvent end")
L("y1 == Keff*xf","loaded solvent y_1 = Keff x_1")
L("Dis == (1 - e)*xN","final discharge")
L("Life == qc*BD.m/(F*xN*Hmo)","bed life = q m /(F x_N)/700")
req=[
 {"quantity":"xN","op":"<=","value":"0.12","why":"R1 raffinate x_N <= 0.12 g/L"},
 {"quantity":"Dis","op":"<=","value":"0.006","why":"R2 discharge <= 0.006 g/L"},
 {"quantity":"Life","op":">=","value":"2","why":"R3 bed life >= 2 months"},
 {"quantity":"y1","op":"<=","value":"8.5","why":"R5 loaded solvent <= 8.5 g/L"},
]
cat={
 "extractors":{"ground":"problem table","items":[
   {"name":"E2","N":"2","eta":"0.85","price":"12.0"},
   {"name":"E3","N":"3","eta":"0.80","price":"17.0"},
   {"name":"E4","N":"4","eta":"0.75","price":"22.0"},
   {"name":"E3H","N":"3","eta":"0.92","price":"20.0"}],
  "fields":{"N":{"unit":""},"eta":{"unit":""},"price":{"unit":"kEUR"}}},
 "solvents":{"ground":"problem table","items":[
   {"name":"SA","Kt":{"range":list(Krange("4.0","0.021"))},"cS":"1.2"},
   {"name":"SB","Kt":{"range":list(Krange("7.5","0.035"))},"cS":"2.6"},
   {"name":"SC","Kt":{"range":list(Krange("12.0","0.045"))},"cS":"4.5"}],
  "fields":{"Kt":{"unit":""},"cS":{"unit":"EUR/m^3"}}},
 "beds":{"ground":"problem table","items":[
   {"name":"G600","m":"600","price":"1.8"},
   {"name":"G1200","m":"1200","price":"3.2"},
   {"name":"G2000","m":"2000","price":"5.0"}],
  "fields":{"m":{"unit":"kg"},"price":{"unit":"kEUR"}}},
 "flow":{"continuous":{"field":"x","from":"0.5","to":"1.8","unit":"m^3/h"}},
}
brick={"stand":"ztl-stand/1",
 "quantities":Q,
 "slots":{"EX":{"from":["extractors"]},"SV":{"from":["solvents"]},"BD":{"from":["beds"]},"SS":{"from":["flow"]}},
 "define":{"Keff":"EX.eta*SV.Kt"},
 "computed":comp,
 "laws":laws,"requirements":req,
 "objective":{"minimize":"EX.price + BD.price + Yrs*Hyr*SS.x*SV.cS","unit":"kEUR","why":"5-year cost: extractor + bed + solvent circulation"},
 "catalog":cat}
json.dump(brick,open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "c06.json"),"w"),indent=1)
