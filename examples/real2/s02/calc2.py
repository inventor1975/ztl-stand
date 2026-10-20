from math import sqrt,pi
P=1.75; d2=10.863; d3=9.853; d0=(d2+d3)/2; As=pi/4*d0**2
dw=16.63; dh=13.5; Dkm=(dw+dh)/2
print("As",As)
def K(mu): return P/(2*pi)+0.5775*d2*mu+0.5*Dkm*mu
def sred(MA,mu,kt=1.5):
    F=MA*1000/K(mu)
    r=kt*(d2/d0)*(P/(pi*d2)+1.155*mu)
    return F, F/As*sqrt(1+3*r*r)
tab={'8.8':(640,{0.08:(45.2,63),0.10:(44.1,73),0.12:(43.0,84),0.14:(41.9,93),0.16:(40.7,102),0.20:(38.3,117),0.24:(35.9,130)}),
     '10.9':(940,{0.14:(61.5,137),0.24:(52.8,191)}),'12.9':(1100,{0.14:(72.0,160),0.24:(61.8,223)})}
for c,(Rp,t) in tab.items():
  for mu,(F,MA) in t.items():
    f,s=sred(MA,mu); print(c,mu,"tabF",F,"calcF",round(f/1000,2),"util",round(s/Rp,4))
