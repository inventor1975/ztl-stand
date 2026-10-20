import json,sys
from fractions import Fraction as Fr
def build(pvals, maxn=4, report=None):
    q=[500,1200,300,800,2000]; r=["0.60","0.45","0.85","0.70","0.30"]; cost=[9000,13000,14000,15500,16000]
    Q={}
    def g(name,val,unit,why,**kw):
        d={"role":"given","unit":unit,"why":why}
        if val is not None: d["value"]=val
        d.update(kw); Q[name]=d
    for i in range(5):
        g(f"Q{i+1}",str(q[i]),"kg/h",f"M{i+1} new capacity")
        g(f"RJ{i+1}",r[i],"",f"M{i+1} new rejection")
        g(f"C{i+1}",str(cost[i]),"EUR",f"M{i+1} annualised cost per module, EUR/yr (year not in unit list)")
    g("kq","0.85","","end-of-life capacity factor")
    g("dr","0.05","","end-of-life rejection loss (absolute)")
    g("FA","3000","kg/h","tank to stage A"); g("FB","2000","kg/h","stage B total feed")
    g("x","800","kg/h","stage A outlet to stage B"); g("FH","4200","kg/h","header flow = (FA-x)+FB")
    g("gA",None,"kg/h","impurity 1 pickup stage A",range=["6","10"])
    g("gB",None,"kg/h","impurity 1 pickup stage B",range=["3","6"])
    g("cm",None,"","make-up concentration imp.1",range=["0.0002","0.0006"])
    g("g2",None,"kg/h","impurity 2 pickup stage A",range=["0.10","0.18"])
    g("cm2","0.0001","","make-up concentration imp.2")
    g("hrs","8000","h","operating hours per year"); g("price","0.25","EUR/kg","purge and make-up price")
    g("qmax","0.6","","max treated fraction of FH")
    for n in ["cT","cAo","cBi","cBo","cH","cT2","cAo2","cBi2","cBo2","cH2"]:
        Q[n]={"role":"derived","unit":""}
    laws=[]
    def L(z,s): laws.append({"zfl":z,"source":s})
    L("cAo == cT + gA/FA","stage A balance, imp.1")
    L("FB*cBi == x*cAo + (FB - x)*cT","stage B inlet mix, imp.1")
    L("cBo == cBi + gB/FB","stage B balance, imp.1")
    L("FH*cH == (FA - x)*cAo + FB*cBo","header mix, imp.1")
    L("FH*cT == ((1 - P.p)*FH - Rcap)*cH + P.p*FH*cm","tank balance with purge and module removal, imp.1")
    L("cAo2 == cT2 + g2/FA","stage A balance, imp.2")
    L("FB*cBi2 == x*cAo2 + (FB - x)*cT2","stage B inlet mix, imp.2")
    L("cBo2 == cBi2","stage B balance, imp.2 (gB = 0)")
    L("FH*cH2 == (FA - x)*cAo2 + FB*cBo2","header mix, imp.2")
    L("FH*cT2 == (1 - P.p)*FH*cH2 + P.p*FH*cm2","tank balance, imp.2 (no removal)")
    slots={f"M{i+1}":{"from":["cnt"]} for i in range(5)}
    slots["P"]={"from":["purge"]}
    N=lambda i:f"M{i}.N"
    sumN=" + ".join(N(i) for i in range(1,6))
    cat={"cnt":{"integers":{"field":"N","from":"0","to":str(maxn),"unit":""}},
         "purge":{"items":[{"p":v} for v in pvals],"fields":{"p":{"unit":""}}}}
    comp={"Rcap":{"value":"kq*("+" + ".join(f"M{i}.N*Q{i}*(RJ{i} - dr)" for i in range(1,6))+")","unit":"kg/h"},
          "Qtot":{"value":"kq*("+" + ".join(f"M{i}.N*Q{i}" for i in range(1,6))+")","unit":"kg/h"}}
    where=[sumN+" <= 8","Qtot <= qmax*FH"]
    req=[{"quantity":"cT","op":"<=","value":"0.008","why":"R1 c_T <= 0.8 wt%"},
         {"quantity":"cBi","op":"<=","value":"0.011","why":"R2 c_Bi <= 1.1 wt%"},
         {"quantity":"cBo","op":"<=","value":"0.015","why":"R2 c_Bo <= 1.5 wt%"},
         {"quantity":"cT2","op":"<=","value":"0.004","why":"R3 c_T2 <= 0.4 wt%"}]
    obj={"minimize":"("+" + ".join(f"M{i}.N*C{i}" for i in range(1,6))+") + P.p*FH*hrs*price","unit":"EUR",
         "why":"annual cost: modules + purge/make-up"}
    b={"stand":"universal-stand/1","quantities":Q,"slots":slots,"define":{},"computed":comp,"where":where,
       "laws":laws,"requirements":req,"objective":obj,"catalog":cat}
    if not b["define"]: del b["define"]
    if report: b["report"]=report
    return b
if __name__=="__main__":
    step=Fr(sys.argv[1]); out=sys.argv[2]
    vals=[]; v=Fr(0)
    while v<=Fr(4,100): vals.append(str(v) if v.denominator==1 else f"{v.numerator}/{v.denominator}"); v+=step
    json.dump(build(vals),open(out,"w"),indent=1)
    print(len(vals))
