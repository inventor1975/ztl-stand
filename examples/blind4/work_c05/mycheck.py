import itertools, math
t=210/365
Z={1:dict(A=6000,H=8,Cc=.45,e0=1.4,s0=30,cv=(1.4,3.0)),2:dict(A=9000,H=5,Cc=.38,e0=1.2,s0=24,cv=(1.8,4.5))}
D={'A':(0.0663,.55),'B':(.078,.70),'C':(.09,.95)}
SP=[0.9,1.0,1.1,1.2,1.35,1.5,1.7,1.9,2.2,2.5]
def S(z,fill): return z['Cc']*z['H']/(1+z['e0'])*math.log10((z['s0']+fill*19)/z['s0'])
def U(z,sp,dw,h,cv,rch,rk,sm):
    Tv=cv*t/z['H']**2
    Uv=2*math.sqrt(Tv/math.pi) if Tv<.2 else 1-8/math.pi**2*math.exp(-math.pi**2*Tv/4)
    De=1.05*sp; n=De/dw; F=math.log(n/sm)+rk*math.log(sm)-.75
    Tr=cv*rch*t/De**2; Ur=1-math.exp(-8*Tr/F)
    return 1-(1-Uv)*(1-Ur)
def margin(z,sp,dw,h):  # worst over all 16 corners... cv,rch,rk,sm = 2^4
    w=1e9
    for cv in z['cv']:
        for rch in (2,3):
            for rk in (2,4):
                for sm in (2,3):
                    w=min(w,U(z,sp,dw,h,cv,rch,rk,sm)*S(z,4+h)-S(z,4)+.03)
    return w
def cost(d,s1,s2,h):
    dw,pm=D[d]; c=0
    for z,s in ((Z[1],s1),(Z[2],s2)): c+=z['A']/(.866*s*s)*(z['H']*pm+4)
    return c+7.5*15000*h
best=None
import sys
step=float(sys.argv[1]) if len(sys.argv)>1 else .05
for N in range(0,int(2.5/step+1e-9)+1):
    h=N*step
    for d in D:
        # zones independent given d,h: cheapest feasible spacing per zone
        pick=[]
        for z in Z.values():
            ok=[s for s in SP if margin(z,s,D[d][0],h)>=0]
            if not ok: break
            pick.append(max(ok))  # larger spacing = cheaper
        else:
            c=cost(d,pick[0],pick[1],h)
            if best is None or c<best[0]: best=(c,d,pick,h)
print(step,best)
