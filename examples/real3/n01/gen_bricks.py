import json
def brick(name, R, Rm, tol, bound_uA, why):
    b={"stand":"ztl-stand/1","why":why,
     "quantities":{
      "V":{"role":"given","value":"5","unit":"V"},
      **{f"R{i}":{"role":"given","value":R,"tolerance":tol,"unit":"ohm"} for i in range(1,5)},
      "Rm":{"role":"given","value":Rm,"unit":"ohm"}},
     "network":{"branches":{
        "b1":{"from":"a","to":"n1","R":"R1"},"b2":{"from":"n1","to":"gnd","R":"R2"},
        "b3":{"from":"a","to":"n2","R":"R3"},"b4":{"from":"n2","to":"gnd","R":"R4"},
        "b5":{"from":"n1","to":"n2","R":"Rm"}},
       "source":{"from":"a","to":"gnd","V":"V"}},
     "requirements":[{"quantity":"I(b5)","op":"within","value":["-"+bound_uA,bound_uA],"unit":"uA",
        "why":"detector current times Rm = offset bound"}]}
    json.dump(b,open(name,"w"),indent=1)
# main: 0.1%, 5 V, R=10k (assumed), Rm=1 Gohm (assumed), bound = 5 mV / 1 Gohm = 5e-12 A = 0.000005 uA
brick("brick.json","10000","1000000000","0.001","0.000005","published claim: offset <= 5 mV (0.1 % elements, 5 V)")
brick("brick_tight.json","10000","1000000000","0.001","0.000004999","same, bound 4.999 mV-equivalent: published says worst case reaches 5 mV")
brick("brick_R1k.json","1000","1000000000","0.001","0.000005","R nominal 1k instead of 10k")
brick("brick_Rm10M.json","10000","10000000","0.001","0.0005","detector 10 Mohm, bound 5 mV/10 Mohm")
brick("brick_Rm10M_tight.json","10000","10000000","0.001","0.000499","detector 10 Mohm, bound 4.99 mV/10 Mohm")
brick("brick_tol1pct.json","10000","1000000000","0.01","0.00005","1 % elements, formula extended: 50 mV")
