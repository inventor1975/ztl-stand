import math
r1=0.045
ins={'MW-30':(30,0.040,0.30,7.5),'MW-50':(50,0.040,0.30,11.0),'PIR-30':(30,0.026,0.08,13.0),'PIR-40':(40,0.026,0.08,16.0)} # mm,k10,wmax,price
cab={'T10':(10,4.8),'T15':(15,6.2),'T20':(20,8.0),'T30':(30,11.5)}  # W/m at 10C pipe, price
Vlo,Vhi=207,253; ho=(8,25); fac=1.3; Tp_req=3.0; cap_liner=24.0
def loss(i,Ta,Tp=Tp_req):
    t,k10,w,_=ins[i]; r2=r1+t/1000
    Tm=(Tp+Ta)/2
    k=k10*(1+0.0018*(Tm-10))*(1+w)
    Rins=math.log(r2/r1)/(2*math.pi*k); Ro=1/(2*math.pi*r2*ho[1])
    return fac*(Tp-Ta)/(Rins+Ro)
def out(c,Tp,V):
    return cab[c][0]*(1+0.012*(10-Tp))*(V/230)**1.6
def margins(i,c,Ta):
    # R1: output at pipe temperature 3C, low voltage >= loss
    m1=out(c,Tp_req,Vlo)/loss(i,Ta)-1
    # R2: output cap at lowest pipe temp Ta.. cable never sees pipe below 3? worst: pipe at 3, high V
    m2=cap_liner/out(c,Tp_req,Vhi)-1
    # R3: space: thickness <=50 (all) ; circuit length: 140 m run; max circuit length by cable: 
    return m1,m2
def feasible(Ta):
    res=[]
    for i in ins:
        for c in cab:
            m1,m2=margins(i,c,Ta)
            if m1>=0 and m2>=0: res.append((ins[i][3]*140+cab[c][1]*140,i,c,round(m1,4),round(m2,4)))
    return sorted(res)
if __name__=='__main__':
    for Ta in (-20,-25,-30,-35,-40,-45):
        print(Ta,feasible(Ta)[:3], {i:round(loss(i,Ta),1) for i in ins})
    for c in cab: print(c,out(c,3,Vlo),out(c,3,Vhi))
