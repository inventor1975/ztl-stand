import itertools
cyl={'CY5':(5,200,7.5,95),'CY7':(7,200,10.4,120),'CY10':(10,200,14.0,165),'CY5H':(5,300,4.2,480),'CY7H':(7,300,5.6,640)}
reg={'RA':(0.10,0.30,10,60),'RB':(0.05,0.15,10,140),'RC':(0.02,0.05,10,320)}  # acc, leak L/min, pmin bar, price
conserver_price=450; kappa_lo=0.30; pmin_cons=25
manifold=40; massmax=16.0
Ta=263.15  # worst: -10C
def Z(p): return 1-4.8e-4*p+1.3e-6*p*p
def avail(c,n,pmin,pf_factor=0.97):
    Vw,pf,_,_=cyl[c]
    Nf=n*Vw*pf*pf_factor/Z(pf*pf_factor)*273.15/288.15/1.013
    Nr=n*Vw*pmin/Z(pmin)*273.15/Ta/1.013
    return Nf-Nr
def need(r1,r2,cons,Tt):
    ph=[(20,(7.5,8.5),(9,10)),(Tt,(8,9),(6,8)),(40,(4,5),(5,6))]
    tot=0
    for t,(a1,b1),(a2,b2) in ph:
        q1=b1*(1+reg[r1][0])*((1-kappa_lo) if cons else 1)
        q2=b2*(1+reg[r2][0])
        tot+=t*(q1+q2+reg[r1][1]+reg[r2][1])
    return 1.2*tot
def margins(c,n,r1,r2,cons,Tt):
    m={}
    pmin=max(reg[r1][2],reg[r2][2],pmin_cons if cons else 0)
    m['R1']=avail(c,n,pmin)/need(r1,r2,cons,Tt)-1
    m['R2']=massmax/(n*cyl[c][2])-1
    return m
def cheapest(Tt):
    best=None
    for c in cyl:
        for n in (1,2):
            for r1 in reg:
                for r2 in reg:
                    for cons in (0,1):
                        m=margins(c,n,r1,r2,cons,Tt)
                        if min(m.values())>=0:
                            pr=n*cyl[c][3]+(manifold if n==2 else 0)+reg[r1][3]+reg[r2][3]+(conserver_price if cons else 0)
                            if best is None or pr<best[0]: best=(pr,c,n,r1,r2,cons,round(m['R1'],4))
    return best
if __name__=='__main__':
    for Tt in (30,45,55,65,80,100):
        print(Tt,cheapest(Tt))
