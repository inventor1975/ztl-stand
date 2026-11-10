from fractions import Fraction as F
import itertools, math
Vs=[F(47),F(52)]; gs=[F(-4,100),F(-2,100)]; Ws=[F(112),F(120)]
def Yf(V,g): return 1+F(147,100)*V/(20+F(644,10)*g)
def Rf(V,W): return max(F(W+20)/(F(147,100)*min(V,55))-1,F(1))
# monotone, but scan a fine grid too
import numpy as np
Ymax=max(Yf(V,g) for V in Vs for g in gs); Rmax=max(Rf(V,W) for V in Vs for W in Ws)
print("corner Ymax",float(Ymax),"Rmax",float(Rmax),"sum",float(Ymax+Rmax),"excess over 6.4",float(Ymax+Rmax-F(32,5)))
ys=[F(47)+F(5)*i/50 for i in range(51)]; gg=[F(-4,100)+F(2,100)*i/50 for i in range(51)]; ww=[F(112)+F(8)*i/50 for i in range(51)]
print("grid Ymax",float(max(Yf(V,g) for V in ys for g in gg)),"grid Rmax",float(max(Rf(V,W) for V in ys for W in ww)))
up=lambda x: F(math.ceil(x*10),10)
Y,R=up(Ymax),up(Rmax); print("min Y,R",float(Y),float(R),"sum",float(Y+R))
ok=[(y/10,r/10) for y in range(30,61) for r in range(10,61) if F(y,10)>=Ymax and F(r,10)>=Rmax and y+r<=64]
print("designs meeting all rules+budget:",ok)
print("conflict with rounding:",float(Y+R-F(32,5)),"; unrounded:",float(Ymax+Rmax-F(32,5)))
