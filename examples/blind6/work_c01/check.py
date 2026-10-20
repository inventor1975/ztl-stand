from math import *
ropes={'W-8':(8,35,.24,2.1),'W-10':(10,55,.37,3.2),'W-12':(12,79,.53,4.6),'W-14':(14,108,.73,6.5),'W-16':(16,141,.95,8.8)}
g=9.81;H=36
def worst(r,D):
    d,MBF,mu,p=ropes[r]
    eta,phi,kt,N0=.95,.25,.88,7e5
    cls=[(600,26000),(1100,11000),(1300,60)]
    Dm=0;
    for m,n in cls:
        F=g*((m+60)/(2*eta)+mu*H)*(1+phi)/1000
        rho=F/(kt*MBF)
        N=N0*(D/(.024*d/1)*0+ D/(24*d/1000))**2.4*(0.1/rho)**2.2
        Dm+=n/N
        if m==1300: SF=kt*MBF/F
    return Dm,SF
for r,(d,MBF,mu,p) in ropes.items():
    # smallest D for Dm<=0.1: Dm ~ D^-2.4
    Dm1,SF=worst(r,0.3)
    Dneed=0.3*(Dm1/0.1)**(1/2.4)
    Dmin=max(Dneed,0.015*d*1.2, 0.15)  # 18d
    Dmin=max(Dneed,18*d/1000,0.15)
    cost=p*84+500+16000*Dmin**2
    print(r,'SF',round(SF,3),'Dneed',round(Dneed,4),'D>=',round(Dmin,4),'feasible',Dmin<=0.45 and SF>=5 and d<=14,'cost',round(cost,2))

print('---- precise')
from math import *
def Dm_at(r,D,best=False):
    d,MBF,mu,p=ropes[r]
    eta,phi,kt,N0=(.98,.10,.95,9e5) if best else (.95,.25,.88,7e5)
    cls=[(400,26000),(900,11000),(1200,60)] if best else [(600,26000),(1100,11000),(1300,60)]
    s=0
    for m,n in cls:
        F=g*((m+60)/(2*eta)+mu*H)*(1+phi)/1000
        s+=n/(N0*(D/(24*d/1000))**2.4*(0.1/(F/(kt*MBF)))**2.2)
    return s
lo,hi=0.15,0.45
for _ in range(200):
    mid=(lo+hi)/2
    if Dm_at('W-10',mid)>0.1: lo=mid
    else: hi=mid
print('Dneed W-10',hi, 'cost',3.2*84+500+16000*hi**2)
D=2059452/9738227
print('stand D',D,'Dm worst',Dm_at('W-10',D),'Dm best',Dm_at('W-10',D,True))
F=g*((1200+60)/(2*.95)+.37*36)*1.25/1000; print('SFmin',.88*55/F)
F=g*((1300+60)/(2*.95)+.37*36)*1.25/1000; print('SFmin(m=1300)',.88*55/F)
F=g*((1200+60)/(2*.98)+.37*36)*1.10/1000; print('SFmax',.95*55/F)
print('Rdd',D/.010)
