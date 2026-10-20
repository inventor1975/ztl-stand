from fractions import Fraction as F
H=8760
# sec 2.3
cap=F(230,1000); I=F(25,10)/10**6
for f in (F(7,10),F(8,10),F(9,10)): print("2.3 life f=%s: %.3f y"%(f, float(cap/(H*I)*f)))
print("2.3 guaranteed hours at f=0.7:", float(cap*F(7,10)/I))
# sec 2.4
I=F(3)/10**6; t=15
for k in (F(11,10),F(12,10),F(13,10)): print("2.4 cap k=%s: %.3f mAh"%(k,float(t*H*I*k*1000)))
for f in (F(7,10),F(8,10),F(9,10)): print("2.4 via eq2.1 f=%s: %.3f mAh"%(f,float(t*H*I/f*1000)))
cap=F(473040,10**6)
for f in (F(7,10),F(8,10),F(9,10)): print("473.04 mAh cell life at f=%s: %.2f y"%(f,float(cap/(H*I)*f)))
print("1/0.7=%.3f 1/0.9=%.3f ; 1/1.1=%.3f 1/1.3=%.3f"%(1/0.7,1/0.9,1/1.1,1/1.3))
