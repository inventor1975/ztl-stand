import math, itertools, numpy as np
dryers={'DR4':(4.0,85,26.0),'DR6':(6.0,85,33.0),'DR8':(8.0,80,40.0),'DR10':(10.0,75,46.0)}  # batch wet t, Tmax, kEUR
fans={'none':(0.0,0.0),'F8':(8.0,2.4),'F15':(15.0,4.1),'F25':(25.0,7.5)}   # q_a m3/(h t), kEUR
M0=(0.30,0.36)  # d.b.
k0m=(0.90,1.10); nP=(0.82,0.88); RH0=(0.55,0.80); T0=(12.0,22.0); Tamb=(10.0,16.0)
K0=6.5e4; EaR=4400
Mf_stor_days=360.0
season=900.0   # t wet
def Me(Td,RH0_,T0_):
    RHd=RH0_*math.exp(17.27*T0_/(T0_+237.3)-17.27*Td/(Td+237.3))
    return ((-math.log(1-RHd))/(8.6541e-5*(Td+49.81)))**(1/1.8634)/100
def tdry(Td,Mf,M0_,k0f,n,RH,T0_):
    me=Me(Td,RH,T0_)
    MR=(Mf-me)/(M0_-me)
    k=K0*k0f*math.exp(-EaR/(Td+273.15))
    return (-math.log(MR)/k)**(1/n)
def worst_tdry(Td,Mf):
    w=0
    for M0_ in M0:
      for k0f in k0m:
        for n in nP:
          for RH in RH0:
            for T0_ in T0:
                w=max(w,tdry(Td,Mf,M0_,k0f,n,RH,T0_))
    return w
def ST(Mf,Ts):
    Mwb=100*Mf/(1+Mf)
    return math.exp(7.4-0.60*(Mwb-14)-0.075*(Ts-10))
def Ts(fan,Ta):
    q=fans[fan][0]
    return max(Ta,Ta+6-0.3*q)
def design_eval(dr,fan,Td,Mf):
    B,Tmax,_=dryers[dr]
    if Td>Tmax: return None
    t=worst_tdry(Td,Mf)
    m={}
    m['thru']=B/(t+1.0)/0.8-1
    m['damage']=0.6/(0.04*t*math.exp(0.08*(Td-60)))-1
    m['store']=ST(Mf,Ts(fan,Tamb[1]))/Mf_stor_days-1
    return m,t
def cost(dr,fan,Td,Mf):
    # worst-case season cost: water removed per t wet grain at M0 max
    M0m=M0[1]
    water=(M0m-Mf)/(1+M0m)*1000   # kg water per t wet grain
    energy=season*water*0.09*(1+0.012*(Td-60))/1000   # kEUR
    return dryers[dr][2]+fans[fan][1]+energy
if __name__=='__main__':
    best=None
    res=[]
    for dr in dryers:
        for fan in fans:
            bd=None
            for Td in np.arange(55,85.01,1.0):
                for Mf in np.arange(0.14,0.2001,0.0025):
                    r=design_eval(dr,fan,Td,Mf)
                    if r is None: continue
                    m,t=r
                    if min(m.values())>=0:
                        c=cost(dr,fan,Td,Mf)
                        if bd is None or c<bd[0]: bd=(c,dr,fan,Td,round(Mf,4),round(t,2),round(min(m.values()),3))
            if bd: res.append(bd)
    for r in sorted(res)[:10]: print(r)
