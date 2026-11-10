from fractions import Fraction as F
tab={60:F(33,100),70:F(31,100),80:F(30,100),90:F(30,100),100:F(29,100)}
for vp,f in tab.items():
    vals=[]
    for v in (F(vp),F(vp+5)):
        for G in (F(2,100),F(4,100)):
            ds=F(278,1000)*F(5,2)*v+(F(278,1000)*v)**2/(F(196,10)*(f-G))
            vals.append(ds)
    mx,mn=max(vals),min(vals)
    print(vp,float(mn),float(mx),"ok" if mx<=170 else "FAIL", "pct below 170: %.4f%%"%(float((170-mx)/170*100)), "exact",mx)
