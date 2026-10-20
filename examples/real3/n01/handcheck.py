from fractions import Fraction as F
from itertools import product
import numpy as np
def i5(R,Rm,t,V=5):
    best=0
    for s in product([-1,1],repeat=4):
        r=[F(R)*(1+t*x) for x in s]
        # node eqs for n1,n2 (exact, 2x2)
        g=[1/x for x in r]; gm=1/F(Rm)
        # n1: (V-v1)g1 - v1 g2 - (v1-v2)gm =0 ; n2: (V-v2)g3 - v2 g4 - (v2-v1)gm=0
        a11=g[0]+g[1]+gm; a22=g[2]+g[3]+gm; a12=-gm
        b1=V*g[0]; b2=V*g[2]
        det=a11*a22-a12*a12
        v1=(b1*a22-a12*b2)/det; v2=(a11*b2-a12*b1)/det
        best=max(best,abs((v1-v2)*gm))
    return best
for R,Rm,t in [(10000,10**9,F(1,1000)),(1000,10**9,F(1,1000)),(10000,10**7,F(1,1000)),(10000,10**9,F(1,100))]:
    m=i5(R,Rm,t); print(R,Rm,t,"max|I5| =",float(m),"A  = ",float(m*Rm*1000),"mV across Rm; unloaded t*V =",float(t*5*1000),"mV")
# random sampling inside the box (not only corners)
rng=np.random.default_rng(1); R=1e4;Rm=1e9;t=1e-3;V=5;mx=0
for _ in range(200000):
    r=R*(1+t*rng.uniform(-1,1,4)); 
    v1=V*r[1]/(r[0]+r[1]); v2=V*r[3]/(r[2]+r[3]); mx=max(mx,abs(v1-v2))
print("random interior unloaded max (mV):",mx*1000)
