import json, sys
def build(win, ivr_names=("none","basic","advanced"), report=None):
    # win: {s:(lo,hi)}
    Q={}; laws=[]; req=[]; slots={}; cat={}
    lamr=[("180","220"),("230","280"),("170","210"),("90","120")]
    cost=["33","36","38","45"]
    for s in range(1,5):
        Q[f"lam{s}"]={"role":"given","range":list(lamr[s-1]),"unit":"1/h","why":f"arrival rate P{s} before deflection, calls/hour (independent per day part)"}
        Q[f"c{s}"]={"role":"given","value":cost[s-1],"unit":"EUR/h","ground":"problem statement","why":f"agent cost per hour P{s}"}
    Q["AHT"]={"role":"given","range":["4.8","5.6"],"unit":"min","why":"mean handling time incl. wrap-up, ONE value common to all day parts"}
    Q["Tw"]={"role":"given","value":"20","unit":"s","ground":"problem statement","why":"service-level threshold, 20 s"}
    Q["Hyr"]={"role":"given","value":"900","unit":"h","ground":"problem statement","why":"hours per year per day part: 3 h x 300 days"}
    for s in range(1,5):
        lo,hi=win[s]
        for nm,u in ((f"A{s}",""),(f"Pw{s}",""),(f"E{s}",""),(f"SL{s}",""),(f"Occ{s}","")):
            Q[nm]={"role":"derived","unit":u}
        for k in range(1,hi+1):
            Q[f"X{s}_{k}"]={"role":"derived","unit":"","why":"inverse Erlang-B recursion"}
        laws.append({"zfl":f"A{s} == lam{s}*(1 - IVR.d)*AHT","source":"offered load A = lambda_e*AHT/60 (lambda per hour, AHT minutes; units convert), lambda_e = lambda(1-d)"})
        for k in range(1,hi+1):
            prev = "1" if k==1 else f"X{s}_{k-1}"
            step = f"1 + {k}*{prev}/A{s}"
            if k>lo:
                step=f"if({k} > S{s}.N, {prev}, {step})"
            laws.append({"zfl":f"X{s}_{k} == {step}","source":"1/B(k) = 1 + (k/A)/B(k-1), Erlang B recursion (equivalent to the sum form)"+("; steps beyond n are held (n <= k)" if k>lo else "")})
        laws.append({"zfl":f"Pw{s} == 1/(1 + (1 - A{s}/S{s}.N)*(X{s}_{hi} - 1))","source":"Erlang C from Erlang B: C = B/(1-rho(1-B)), 1/C = 1+(1-rho)(1/B-1); equals the stated P_wait",
                     "valid":f"S{s}.N > lam{s}*(1 - IVR.d)*AHT"})
        laws.append({"zfl":f"E{s} == exp(Tw*(lam{s}*(1 - IVR.d) - S{s}.N/AHT))","source":"exp(-(n-A)*20/(60*AHT)) with A = lambda_e*AHT: (n-A)/AHT = n/AHT - lambda_e"})
        laws.append({"zfl":f"SL{s} == 1 - Pw{s}*E{s}","source":"service level SL = 1 - P_wait*exp(...)"})
        laws.append({"zfl":f"Occ{s} == A{s}/S{s}.N","source":"occupancy = A/n"})
        req.append({"quantity":f"SL{s}","op":">=","value":"0.7","why":f"R1: SL >= 0.70 in day part P{s}"})
        req.append({"quantity":f"Occ{s}","op":"<=","value":"0.92","why":f"R3: occupancy <= 0.92 in day part P{s}"})
        slots[f"S{s}"]={"from":[f"agents{s}"]}
        cat[f"agents{s}"]={"integers":{"field":"N","from":str(lo),"to":str(hi),"unit":""},"ground":"problem statement (R4 n<=60 met by the window; window computed outside the stand)"}
    Q["M"]={"role":"derived","unit":"1/h","why":"sum_s lambda_s*(SL_s - 0.87); R2 SL_day >= 0.87 <=> M >= 0 after dividing by (1-d) > 0"}
    laws.append({"zfl":"M == lam1*(SL1 - 0.87) + lam2*(SL2 - 0.87) + lam3*(SL3 - 0.87) + lam4*(SL4 - 0.87)","source":"SL_day >= 0.87  <=>  sum lambda_e,s (SL_s - 0.87) >= 0, lambda_e,s = lambda_s (1-d), the factor (1-d)>0 divided out"})
    req.append({"quantity":"M","op":">=","value":"0","why":"R2: SL_day >= 0.87 (worst case of the weighted average)"})
    slots["IVR"]={"from":["ivr"]}
    items=[]
    allit={"none":{"d":"0","price":"0","option":"none"},
           "basic":{"d":{"range":["0.06","0.10"]},"price":"14","option":"basic"},
           "advanced":{"d":{"range":["0.12","0.18"]},"price":"31","option":"advanced"}}
    cat["ivr"]={"items":[allit[n] for n in ivr_names],"fields":{"d":{"unit":""},"price":{"unit":"kEUR"}},"ground":"problem statement"}
    brick={"stand":"universal-stand/1","quantities":Q,"slots":slots,"laws":laws,"requirements":req,
      "objective":{"minimize":"(S1.N*c1 + S2.N*c2 + S3.N*c3 + S4.N*c4)*Hyr + IVR.price","unit":"kEUR","why":"annual cost: agents x EUR/h x 3 h x 300 days + IVR price"},
      "catalog":cat}
    if report: brick["report"]=report
    return brick
if __name__=="__main__":
    mode=sys.argv[1]
    if mode=="tiny":
        win={1:(25,25),2:(29,29),3:(22,22),4:(13,13)}
        b=build(win,("advanced",),"all")
    elif mode=="full":
        win={1:(22,28),2:(27,32),3:(21,26),4:(13,17)}
        b=build(win)
    json.dump(b,open(sys.argv[2],"w"),indent=1)
