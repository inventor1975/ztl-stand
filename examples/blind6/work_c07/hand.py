import math, itertools
g=9.81; Ac=22000
I={('10',900):(85,92),('10',1800):(62,68),('10',3600):(40,44),('100',900):(125,135),('100',1800):(92,100),('100',3600):(62,66)}
def sol(A,d,C,Cd,i,t):
    Qin=C*i*Ac/3.6e6; Ao=math.pi*d*d/4
    k=Cd*Ao*math.sqrt(1.2*g)*t
    s=(-k+math.sqrt(k*k+4*A*Qin*t))/(2*A); h=s*s
    return h, Cd*Ao*math.sqrt(2*g*h)
def worst(A,d):
    r={'q10':0,'q100':0,'h100':0}
    for (rp,t),(lo,hi) in I.items():
        for C in (.7,.8):
            for Cd in (.58,.64):
                for i in (lo,hi):
                    h,q=sol(A,d,C,Cd,i,t)
                    if rp=='10': r['q10']=max(r['q10'],q)
                    else: r['q100']=max(r['q100'],q); r['h100']=max(r['h100'],h)
    return r
if __name__=="__main__":
  for d in (.06,.08,.1,.12,.15):
    for A in (100,300,610):
        print(d,A,worst(A,d))
