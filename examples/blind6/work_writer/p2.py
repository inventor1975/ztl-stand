import itertools, math
cab={16:(1.15,100,5.5),25:(0.727,130,8.0),35:(0.524,160,10.5),50:(0.387,190,14.0),70:(0.268,240,19.0),95:(0.193,290,26.0)}
brk={40:48,50:58,63:70,80:95,100:120,125:160,160:230}
X=0.08e-3
V0=(395,415); ks=(0.060,0.085)
I1=(50,56); I2=(30,35)
Ils1=53.0; Ils2=32.0; kls=(5.8,6.4)
def Rp(S,I,Tamb):
    R20,Iz,_=cab[S]
    th=Tamb+60*(I/Iz)**2
    return R20*1e-3*(1+0.00393*(th-20))
def drop(S,I,L,Tamb,Irun,cos):
    sin=math.sqrt(1-cos**2)
    return math.sqrt(3)*I*L*(Rp(S,Irun,Tamb)*cos+X*sin)
def check(S1,S2,B1,B2,L1,L2,Tmax,detail=False):
    marg={}
    # breakers
    for nm,B,S,Imax,Ils in (('1',B1,S1,I1[1],Ils1*kls[1]),('2',B2,S2,I2[1],Ils2*kls[1])):
        Iz=cab[S][1]*math.sqrt((90-Tmax)/60)
        marg['R4a'+nm]=B/(1.1*Imax)-1
        marg['R4b'+nm]=8*B/(1.25*Ils)-1
        marg['R4c'+nm]=Iz/B-1
    # scenarios worst-case: V0 low, ks high
    Vb=lambda Itot: V0[0]-ks[1]*Itot
    # both running
    Vb_r=Vb(I1[1]+I2[1])
    marg['R1_1']=(Vb_r-drop(S1,I1[1],L1,Tmax,I1[1],0.85))/380-1
    marg['R1_2']=(Vb_r-drop(S2,I2[1],L2,Tmax,I2[1],0.85))/380-1
    Is1=Ils1*kls[1]; Is2=Ils2*kls[1]
    Vb1=Vb(Is1+I2[1]); marg['R2_1']=(Vb1-drop(S1,Is1,L1,Tmax,I1[1],0.40))/340-1
    Vb2=Vb(Is2+I1[1]); marg['R2_2']=(Vb2-drop(S2,Is2,L2,Tmax,I2[1],0.40))/340-1
    # R3 busbar during starts >= 0.88*400? 
    marg['R3_1']=Vb1/352-1; marg['R3_2']=Vb2/352-1
    return marg
def cheapest(L1,L2,Tmax):
    best=None
    for S1 in cab:
      for S2 in cab:
        for B1 in brk:
          for B2 in brk:
            m=check(S1,S2,B1,B2,L1,L2,Tmax)
            if min(m.values())>=0:
                c=(cab[S1][2]*L1+cab[S2][2]*L2+brk[B1]+brk[B2])/1000
                if best is None or c<best[0]-1e-12: best=(c,S1,S2,B1,B2,min(m,key=m.get),min(m.values()))
    return best
if __name__=='__main__':
    for L1 in (120,140,160,180):
        print(L1,cheapest(L1,85,38))
