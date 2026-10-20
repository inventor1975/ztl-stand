import math, json
cells={"S1":(2.70,100,10.0,4.20),"S2":(2.70,150,7.0,5.60),"S3":(2.70,310,2.2,10.50),"S4":(3.00,60,18.0,3.40),"S5":(3.00,120,9.0,6.20),"S6":(2.50,350,3.0,9.40),"S7":(2.70,50,22.0,2.20),"S8":(2.85,200,5.5,7.80)}
Pin=400/0.92
def kT(T):
    pts=[(-30,4.0),(-10,2.4),(0,1.7),(25,1.0),(45,0.9),(65,0.85)]
    for (a,ka),(b,kb) in zip(pts,pts[1:]):
        if a<=T<=b: return ka+(kb-ka)*(T-a)/(b-a)
def hold_ode(C,R,v0=21.6,tmax=8.0,dt=1e-4):
    # returns time until failure (vt<10 or disc<0), capped tmax+; RK-free fine Euler w/ small dt
    v=v0;t=0
    while t<tmax:
        d=v*v-4*R*Pin
        if d<0: return t,'disc'
        vt=(v+math.sqrt(d))/2
        if vt<10: return t,'vt'
        v-=Pin/vt/C*dt; t+=dt
    return t,'ok'
def hold_closed(C,R,v0=21.6):
    d0=v0*v0-4*R*Pin
    if d0<0: return None
    s0=math.sqrt(d0); v1=10+R*Pin/10; s1=math.sqrt(v1*v1-4*R*Pin)
    return C/Pin*((v0*v0-v1*v1)/4+(v0*s0-v1*s1-4*R*Pin*math.log((v0+s0)/(v1+s1)))/4)
def life(Vr,ns):
    Vc=24/ns*1.03
    D=sum(f/(1500*2**((65-T)/10)*2**((Vr-Vc)/0.1)) for f,T in((.6,25),(.3,45),(.1,60)))
    return 1/D
rows=[]
for n,(Vr,C,E,p) in cells.items():
    for ns in range(6,16):
        for np_ in range(1,17):
            if ns*np_>100: continue
            Cb=np_*C*0.72/ns
            Rb=ns*E/1000*2*3.2/np_
            cost=ns*np_*(p+0.5)
            r1=26.4/ns*1.06<=Vr
            th,why=hold_ode(Cb,Rb)
            rows.append(dict(cell=n,ns=ns,np=np_,cost=cost,r1=r1,hold_ok=(why=='ok'),why=why,tfail=th,life=life(Vr,ns),lifeok=life(Vr,ns)>=131400,RP=Rb*Pin,dis=21.6**2-4*Rb*Pin))
for r in rows: r['pass']=r['r1'] and r['hold_ok'] and r['lifeok']
json.dump(rows,open('ref.json','w'))
ok=sorted([r for r in rows if r['pass']],key=lambda r:r['cost'])
print(len(rows),len(ok))
for r in ok[:20]: print(r['cell'],r['ns'],r['np'],r['cost'],round(r['life']),round(r['RP'],1))
print('R1-only fails',sum(not r['r1'] for r in rows),'life fails',sum(not r['lifeok'] for r in rows))
print('hold ok count',sum(r['hold_ok'] for r in rows), 'RP>100 and hold_ok:',[ (r['cell'],r['ns'],r['np']) for r in rows if r['hold_ok'] and r['RP']>100])
