from fractions import Fraction as F
import itertools
Vref0=F(1275,1000)
pub={ # Vout: {(dref,tol):val}
}
table={
1.8:{0.5:(0.82,1.14,3.85),1.0:(1.32,1.65,4.37),2.0:(2.32,2.65,5.40),5.0:(5.33,5.67,8.50)},
2.5:{0.5:(1.01,1.53,5.87),1.0:(1.52,2.04,6.40),2.0:(2.52,3.05,7.45),5.0:(5.54,6.08,10.61)},
3.3:{0.5:(1.13,1.77,7.14),1.0:(1.64,2.28,7.67),2.0:(2.64,3.29,8.73),5.0:(2.64,6.33,11.93)},
5.0:{0.5:(1.26,2.03,8.48),1.0:(1.77,2.54,9.02),2.0:(2.77,3.55,10.10),5.0:(5.80,6.60,13.33)},
12:{0.5:(1.41,2.32,9.99),1.0:(1.91,2.83,10.54),2.0:(2.92,3.85,11.64),5.0:(5.95,6.90,14.92)},
15:{0.5:(1.43,2.36,10.21),1.0:(1.93,2.87,10.76),2.0:(2.94,3.89,11.86),5.0:(5.97,6.95,15.15)}}
def worst(Vout,dref,tol):
    Vout=F(str(Vout)); r=Vout/Vref0-1  # R2/R1 ; R1=1
    dref=F(str(dref))/100; tol=F(str(tol))/100
    def v(a,b,c): # a=vref factor, b=R1 factor, c=R2 factor
        return Vref0*(1+a*0)*0
    best=[]
    vals=[]
    for a in (-dref,dref):
      for b in (-tol,tol):
        for c in (-tol,tol):
            vals.append(Vref0*(1+a)*(1+(r*(1+c))/(1+b)))
    return (min(vals)/Vout-1)*100,(max(vals)/Vout-1)*100
for Vout,rows in table.items():
    for dref,vals in rows.items():
        out=[]
        for tol,pubv in zip((0.5,1,5),vals):
            lo,hi=worst(Vout,dref,tol)
            m=max(abs(lo),abs(hi))
            out.append("%.2f(pub %.2f)%s"%(m,pubv,"" if abs(round(float(m),2)-pubv)<0.006 else " <<"))
        print(Vout,dref,out)
