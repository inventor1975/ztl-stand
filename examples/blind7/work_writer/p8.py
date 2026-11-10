# P8 capacitor bank. corners over kW, pf, capacitor delivered tolerance
import numpy as np
tan=lambda pf: np.tan(np.arccos(pf))
banks={100:4100,150:5850,175:6725,200:7000,225:7875,250:8750,300:10500}
for kvar,price in banks.items():
    pfmin=1;sav=1e9
    for kw in (380,420):
        for pf in (0.75,0.79):
            for tol in (0.95,1.05):
                q=kw*tan(pf)-kvar*tol
                pfn=kw/np.hypot(kw,q); pfmin=min(pfmin,pfn)
                sav=min(sav,3.0*(kw/pf-np.hypot(kw,q)))
    pb=price/sav
    ok=pfmin>=0.95 and pb<=32
    print(kvar,price,"worst PF %.4f"%pfmin,"min saving $%.1f/mo"%sav,"payback %.1f mo"%pb,"PASS" if ok else "fail")
# source check: 400 kW, pf .769 -> to .95
q0=400*tan(.769);q1=400*tan(.95);print("source check: kVAr needed %.1f; kVA before %.1f after %.1f; saving $%.1f/mo"%(q0-q1,400/.769,400/.95,3*(400/.769-400/.95)))
