import math
from fractions import Fraction as F
# exact hand check of U at tau=8017118536477/5823096600 worst corner, TL + monitoring
tau=F(8017118536477,5823096600)
f=[F(33,100),F(25,100),F(42,100)]; Thi=[F('285.15'),F('305.15'),F('293.15')]; Hhi=[60,40,25]
c=F(4,5); td=F(9,10); k=F(23,25); l0=F(24,10**7); Tov=2190
U=0
for i in range(3):
    l=l0*F(math.exp(3000*(1/293.15-1/float(Thi[i]))))*F(((Hhi[i]/50)**0.35))*k
    U+=f[i]*(c*l*tau/2+(1-c)*l*Tov/2+td/tau)
print(float(U))
# independent: U_wc(tau) polynomial a*tau + b + d/tau; bound roots
A=B=D=0
for i in range(3):
    lam=2.4e-6*math.exp(3000*(1/293.15-1/float(Thi[i])))*(Hhi[i]/50)**0.35*0.92
    A+=float(f[i])*0.8*lam/2; B+=float(f[i])*0.2*lam*Tov/2; D+=float(f[i])*0.9
# A t + B + D/t = 2.25e-3 -> A t^2 + (B-2.25e-3) t + D = 0
b=B-2.25e-3; disc=b*b-4*A*D
print((-b-math.sqrt(disc))/(2*A),(-b+math.sqrt(disc))/(2*A))
