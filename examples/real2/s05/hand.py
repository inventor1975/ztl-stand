from math import exp, log
from fractions import Fraction
beta=3435.0; R25=10000.0; T25=298.15
def Rn(Tc): T=Tc+273.15; return R25*exp(beta*(1/T-1/T25))
def Tof(R): return 1/(1/T25+log(R/R25)/beta)-273.15
print("RHOT",Rn(45),"RCOLD",Rn(10))
Ib=(76.8e-6,80e-6,83.2e-6); Rp=(11880.,12000.,12120.)
def Vts(Tc,Ibv,Rpv): r=Rn(Tc); return Ibv*Rpv*r/(Rpv+r)
def Rneeded(V,Ibv,Rpv): Req=V/Ibv; return Req*Rpv/(Rpv-Req)
# hot
print("hot Rmax",Rneeded(0.280,Ib[0],Rp[0]),"->T",Tof(Rneeded(0.280,Ib[0],Rp[0])))
print("hot Rmin",Rneeded(0.272,Ib[2],Rp[2]),"->T",Tof(Rneeded(0.272,Ib[2],Rp[2])))
print("cold Rmax",Rneeded(0.584,Ib[0],Rp[0]),"->T",Tof(Rneeded(0.584,Ib[0],Rp[0])))
print("cold Rmin",Rneeded(0.576,Ib[2],Rp[2]),"->T",Tof(Rneeded(0.576,Ib[2],Rp[2])))
# nominal
print("nom hot",Tof(Rneeded(0.276,Ib[1],Rp[1])),"nom cold",Tof(Rneeded(0.580,Ib[1],Rp[1])))
