import json,sys
from gen2 import *
def build3(ext,sol,bed,out):
    Q={"F":q("given",value="1.5",unit="m^3/h",why="wastewater flow"),
       "cF":q("given",range=["6.0","7.5"],unit="g/L",why="feed solute concentration"),
       "rho":q("given",range=["0.02","0.04"],unit="",why="recycle residual fraction, shared"),
       "qc":q("given",range=["0.10","0.14"],unit="kg/kg",why="carbon capacity"),
       "e":q("given",range=["0.90","0.96"],unit="",why="carbon removal efficiency"),
       "Hmo":q("given",value="700",unit="h",why="hours per month"),
       "Hyr":q("given",value="8000",unit="h",why="operating hours per year"),
       "Yrs":q("given",value="5",unit="",why="years")}
    for n,u,w in (("A","","absorption factor S Keff / F"),("Gs","","sum_{k<N} A^k"),("Gp","","sum_{k<N-1} A^k"),("xN","g/L","raffinate x_N"),("xf","g/L","x_1 (feed-end stage)"),("y1","g/L","loaded solvent y_1 = Keff x_1"),("Dis","g/L","final discharge (1-e) x_N"),("Life","","bed life, months")):
        Q[n]=q("derived",unit=u,why=w)
    comp={"g1":"min(1, max(0, EX.N - 1))","g2":"min(1, max(0, EX.N - 2))","g3":"min(1, max(0, EX.N - 3))",
          "p1":"min(1, max(0, EX.N - 2))","p2":"min(1, max(0, EX.N - 3))"}
    laws=[]
    def L(z,s): laws.append({"zfl":z,"source":s})
    L("A == SS.x*Keff/F","absorption factor")
    L("Gs == 1 + g1*A + g2*A*A + g3*A*A*A","geometric sum, N terms")
    L("Gp == 1 + p1*A + p2*A*A","geometric sum, N-1 terms")
    L("xN == cF*(1 + A*rho*Gp)/(1 + A*rho*Gp + A*(1 - rho)*Gs)","stage balances solved by hand (telescoping), x_N")
    L("xf == xN*(1 + A*Gp)/(1 + A*rho*Gp)","same, x_1")
    L("y1 == Keff*xf","loaded solvent")
    L("Dis == (1 - e)*xN","final discharge")
    L("Life == qc*BD.m/(F*xN*Hmo)","bed life")
    base=json.load(open("c06_n3.json"))
    b={"stand":"ztl-stand/1","quantities":Q,"slots":base["slots"],"define":base["define"],"computed":comp,"laws":laws,
       "requirements":base["requirements"],"objective":base["objective"],"catalog":base["catalog"]}
    c=b["catalog"]
    c["extractors"]["items"]=[i for i in c["extractors"]["items"] if i["name"] in ext] if ext else None
    json.dump(b,open(out,"w"),indent=1)
