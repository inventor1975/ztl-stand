import json,sys
from decimal import Decimal, getcontext, ROUND_FLOOR, ROUND_CEILING
getcontext().prec=50
def Krange(K25,a):
    K25=Decimal(K25);a=Decimal(a)
    lo=K25*(-5*a).exp(); hi=K25*(10*a).exp(); q9=Decimal("1e-9")
    return [str(lo.quantize(q9,rounding=ROUND_FLOOR)), str(hi.quantize(q9,rounding=ROUND_CEILING))]
def q(role,**k): d={"role":role}; d.update(k); return d
EXT={"E2":("2","0.85","12.0"),"E3":("3","0.80","17.0"),"E4":("4","0.75","22.0"),"E3H":("3","0.92","20.0")}
SOL={"SA":("4.0","0.021","1.2"),"SB":("7.5","0.035","2.6"),"SC":("12.0","0.045","4.5")}
BED={"G600":("600","1.8"),"G1200":("1200","3.2"),"G2000":("2000","5.0")}
def build(N,ext,sol,bed,out,smin="0.5",smax="1.8",fixed_params=None):
    """N: stages (fixed, no dummy stages). stage j counted from the SOLVENT end: z1 = x_N, z_N = x_1."""
    Q={"F":q("given",value="1.5",unit="m^3/h",why="wastewater flow"),
       "cF":q("given",range=["6.0","7.5"],unit="g/L",why="feed solute concentration"),
       "rho":q("given",range=["0.02","0.04"],unit="",why="recycle residual fraction, shared (ONE quantity)"),
       "qc":q("given",range=["0.10","0.14"],unit="kg/kg",why="carbon capacity"),
       "e":q("given",range=["0.90","0.96"],unit="",why="carbon removal efficiency"),
       "Hmo":q("given",value="700",unit="h",why="hours per month"),
       "Hyr":q("given",value="8000",unit="h",why="operating hours per year"),
       "Yrs":q("given",value="5",unit="",why="years"),
       "Hs":q("given",value="1.2",unit="",why="hydraulic factor of the settlers")}
    if fixed_params:
        for k,v in fixed_params.items(): Q[k]=v
    for i in range(1,N+1): Q["z%d"%i]=q("derived",unit="g/L",why="water concentration leaving stage x_%d (z%d counted from the solvent end)"%(N+1-i,i))
    for n,u,w in (("xN","g/L","raffinate x_N = z1"),("y1","g/L","loaded solvent y_1 = Keff x_1"),("Dis","g/L","final discharge (1-e) x_N"),("Life","","bed life in months")):
        Q[n]=q("derived",unit=u,why=w)
    laws=[]
    def L(z,s): laws.append({"zfl":z,"source":s})
    # stage 1 from the solvent end = stage N: F (x_{N-1}-x_N) = S (Keff x_N - rho Keff x_1)
    zn="z%d"%N
    L("F*(z2 - z1) == SS.x*Keff*(z1 - rho*%s)"%zn,"stage N: F (x_{N-1}-x_N) = S (Keff x_N - y_in), y_in = rho Keff x_1")
    for j in range(2,N+1):
        up = "z%d"%(j+1) if j<N else "cF"
        L("F*(%s - z%d) == SS.x*Keff*(z%d - z%d)"%(up,j,j,j-1),"stage N+1-%d: F (x_{i-1}-x_i) = S Keff (x_i - x_{i+1})"%j)
    L("xN == z1","raffinate")
    L("y1 == Keff*%s"%zn,"loaded solvent y_1 = Keff x_1")
    L("Dis == (1 - e)*xN","final discharge")
    L("Life == qc*BD.m/(F*xN*Hmo)","bed life = q m /(F x_N)/700")
    req=[{"quantity":"xN","op":"<=","value":"0.12","why":"R1 raffinate x_N <= 0.12 g/L"},
         {"quantity":"Dis","op":"<=","value":"0.006","why":"R2 discharge <= 0.006 g/L"},
         {"quantity":"Life","op":">=","value":"2","why":"R3 bed life >= 2 months"},
         {"quantity":"SS.x","op":"<=","value":"Hs*F","why":"R4 S <= 1.2 F (hydraulic limit)"},
         {"quantity":"y1","op":"<=","value":"8.5","why":"R5 loaded solvent <= 8.5 g/L"}]
    cat={"extractors":{"ground":"problem table","items":[{"name":n,"N":EXT[n][0],"eta":EXT[n][1],"price":EXT[n][2]} for n in ext],
          "fields":{"N":{"unit":""},"eta":{"unit":""},"price":{"unit":"kEUR"}}},
         "solvents":{"ground":"problem table; Kt = K25*exp(-a(T-25)) over T in 15..30 C, rounded OUT to 1e-9","items":[{"name":n,"Kt":{"range":Krange(SOL[n][0],SOL[n][1])},"cS":SOL[n][2]} for n in sol],
          "fields":{"Kt":{"unit":""},"cS":{"unit":"EUR/m^3"}}},
         "beds":{"ground":"problem table","items":[{"name":n,"m":BED[n][0],"price":BED[n][1]} for n in bed],
          "fields":{"m":{"unit":"kg"},"price":{"unit":"kEUR"}}},
         "flow":{"continuous":{"field":"x","from":smin,"to":smax,"unit":"m^3/h"}}}
    b={"stand":"ztl-stand/1","quantities":Q,
       "slots":{"EX":{"from":["extractors"]},"SV":{"from":["solvents"]},"BD":{"from":["beds"]},"SS":{"from":["flow"]}},
       "define":{"Keff":"EX.eta*SV.Kt"},"laws":laws,"requirements":req,
       "objective":{"minimize":"EX.price + BD.price + Yrs*Hyr*SS.x*SV.cS","unit":"kEUR","why":"5-year cost: extractor + bed + solvent circulation"},
       "catalog":cat}
    json.dump(b,open(out,"w"),indent=1)
if __name__=="__main__":
    N=int(sys.argv[1]); build(N,sys.argv[2].split(","),sys.argv[3].split(","),sys.argv[4].split(","),sys.argv[5])
