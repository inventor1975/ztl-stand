import math
f=[.33,.25,.42]; Tlo=[5,24,12]; Thi=[12,32,20]; Hhi=[60,40,25]; Hlo=[40,25,15]
B=3000.
def lam_r(l0,T,H,k): return l0*math.exp(B*(1/293.15-1/(T+273.15)))*(H/50)**.35*k
Tov=2190.
M={'TS':(.20,.30,.2,.3,.35),'TL':(.80,.88,.6,.9,1.6),'TF':(.92,.97,1.6,2.0,4.2)}
def Uwc(m,tau,mon):
    clo,chi,tdlo,tdhi,ct=M[m]; k=.92 if mon else 1.
    s=0
    for i in range(3):
        l=lam_r(2.4e-6,Thi[i],Hhi[i],k)
        s+=f[i]*(clo*l*tau/2+(1-clo)*l*Tov/2+tdhi/tau)
    return s
for m in M:
  for mon in (0,1):
    taus=[24+i*0.1 for i in range(int((2190-24)/0.1)+1)]
    ok=[t for t in taus if Uwc(m,t,mon)<=2.25e-3]
    if ok:
        hi=ok[-1]; cost=8760/hi*M[m][4]+2.2*mon
        print(m,mon,'lo',ok[0],'hi',hi,'cost@hi',cost,'min U',min(Uwc(m,t,mon) for t in taus))
    else: print(m,mon,'none; minU',min(Uwc(m,t,mon) for t in taus))
