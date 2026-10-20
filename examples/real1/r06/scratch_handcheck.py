from fractions import Fraction as F
import itertools
gal=F('3.785411784'); oz=F('29.5735295625'); Vw=10*gal*1000
ozs=[4,8,12,16,20,24,28,32,36,40,44,48,58,70,82,94,106,118,130,142,154,166,178,190,204,222,240,260,282,306,330,354,384]
def feed(o,D,Q,w,rho):
    Vb=o*oz; sw=Vb*rho*w/(Vw+Vb)   # g/mL
    return D*(Q*gal)*1000/F('0.9525')/(sw*1000*1000) *1  # D mg/L * Q L/min /(mg/mL) ... see below
# D[mg/L]*Q[L/min] = mg/min ; sw g/mL = 1000 mg/mL -> mL/min
def feed(o,D,Q,w,rho):
    Vb=o*oz; sw=Vb*rho*w/(Vw+Vb)*1000
    return D*Q/(F('0.9525')*sw)
for tol in [(F(0),F(0)),(F('0.04'),F('0.02'))]:
  print('tol',tol)
  for o in ozs:
    vals=[]
    for D,Qg,w,r in itertools.product([F(1),F(3,2)],[10,60],[F('0.125')*(1-tol[0]),F('0.125')*(1+tol[0])],[F('1.2')*(1-tol[1]),F('1.2')*(1+tol[1])]):
        vals.append(feed(o,D,Qg*gal,w,r))
    lo,hi=min(vals),max(vals)
    ok = lo>=8 and hi<=100
    if ok or o in (32,44): print(o, float(lo), float(hi), 'PASS' if ok else 'fail')
