# P7 lumen method. E = N*lumens*CU*LLF/A ; CU linear interpolation in RCR; worst: LLF min, RCR giving min CU (max RCR)
import numpy as np
A=120.0; need=50.0; Wmax=120.0
RCR=(6.5,7.2); LLF=(0.75,0.85)
cat={'F3':(8550,96,{6:.57,7:.54,8:.51}),'F2':(5700,64,{6:.60,7:.57,8:.54}),
     'L1':(4800,41,{6:.62,7:.59,8:.56}),'L2':(6200,50,{6:.62,7:.59,8:.56})}
cu=lambda t,r: float(np.interp(r,[6,7,8],[t[6],t[7],t[8]]))
best=(0,)
for k,(lm,w,t) in cat.items():
    for N in range(1,6):
        E=N*lm*min(cu(t,r) for r in RCR)*LLF[0]/A
        ok_e=E>=need; ok_w=N*w<=Wmax
        print(k,N,"Emin %.2f fc"%E,"W=%d"%(N*w),"E ok" if ok_e else "E low","W ok" if ok_w else "W over")
        if ok_w: best=max(best,(E,k,N))
print("max worst-case illuminance within 120 W:",best)
