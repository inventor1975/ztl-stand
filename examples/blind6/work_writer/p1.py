import itertools, numpy as np
g=9.81
ropes={ # d mm: MBF kN, mass kg/m, price EUR/m
 8:(35,0.24,2.1),10:(55,0.37,3.2),12:(79,0.53,4.6),14:(108,0.73,6.5),16:(141,0.95,8.8)}
H=36.0; L=84.0
classes={'A':(26000,(400,600)),'B':(11000,(900,1100)),'C':(60,(1200,1300))}
phi=(0.10,0.25); eta=(0.95,0.98); ksp=(0.88,0.95) # termination efficiency
N0=(7.0e5,9.0e5)  # fatigue constant lower..upper
def worst_tension(d,cls):
    mbf,mm,_=ropes[d]; n,(m1,m2)=classes[cls]
    F=g*((m2+60)/(2*eta[0])+mm*H)*(1+phi[1])/1000  # kN
    return F, mbf*ksp[0]
def life_ok(d,D):
    dmg=0
    mbf,mm,_=ropes[d]
    for c,(n,(m1,m2)) in classes.items():
        F,Mb=worst_tension(d,c)
        rho=F/Mb
        N=N0[0]*(D*1000/d/24)**2.4*(0.10/rho)**2.2
        dmg+=n/N
    return dmg
def feas(d,D):
    if d>14: return False
    if D/(d/1000)<18 or D>0.45 or D<0.15: return False
    # safety factor class C: MBF*ksp / F >=5
    F,Mb=worst_tension(d,'C')
    if Mb/F<5: return False
    return life_ok(d,D)*10<=1.0
best=None
for d in ropes:
    for D in np.arange(0.15,0.4501,0.0005):
        if feas(d,D):
            cost=ropes[d][2]*L/1000+0.50+16.0*D**2
            if best is None or cost<best[0]: best=(cost,d,D)
            break
    # report min D per rope
    for D in np.arange(0.15,0.4501,0.0005):
        if feas(d,D): print(d,'minD',round(D,4),'cost',round(ropes[d][2]*L/1000+0.50+16.0*D**2,4)); break
    else: print(d,'infeasible')
print(best)
for d in ropes:
  for c in classes: 
    F,Mb=worst_tension(d,c); print(d,c,round(F,2),round(Mb,1),round(Mb/F,2))
