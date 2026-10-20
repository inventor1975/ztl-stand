import itertools
comp=[("K32",32,6.8,8.0,6900),("K40",40,6.8,8.0,8200),("K40M",40,7.3,8.4,8900),("K50",50,7.3,8.4,10600),("K50H",50,8.0,9.0,11800)]
dry=[("D30",30,.40,1100),("D40",40,.35,1450),("D50",50,.30,1900),("D60",60,.30,2500)]
pipe=[(25,6.),(32,9.),(40,14.),(50,21.),(63,33.)]
def dp(Q,L,d,pabs): return 1.6e3*Q**1.85*L/(d**5*pabs)
res=[]
for (cn,fad,ci,co,cp),(dn,qr,dpr,dpri),(d,pp) in itertools.product(comp,dry,pipe):
    pc=ci-0.15; pabs=pc-0.5+1.013
    # monotone: worst at upper ends (flow up, f up)
    def pin(Qs, hoseQ, hl, hd, fl=2.5, f=1.7):
        Qt=sum(Qs)+fl
        return pc-dpr*(Qt/qr)**2*f-dp(Qt,180,d,pabs)-dp(hoseQ,hl,hd,pabs), Qt
    a1,_=pin([18],18,12,19); b2,_=pin([10.5],10.5,8,16); a3,Q3=pin([18,10.5],18,12,19); b3,_=pin([18,10.5],10.5,8,16)
    ok1=a1>=6.0 and b2>=6.2 and a3>=6.0 and b3>=6.2
    ok2=0.94*fad>=Q3; ok3=co+0.15<=8.5; ok4=qr>=Q3
    price=cp+dpri+pp*180
    res.append((price,cn,dn,d,ok1,ok2,ok3,ok4,round(min(a1,a3)-6,4),round(min(b2,b3)-6.2,4)))
res.sort()
good=[r for r in res if all(r[4:8])]
print("passing",len(good)); 
for r in good[:6]: print(r)
print("cheapest 12 overall"); 
for r in res[:12]: print(r)
# the stand's S3 ranges for K40/D50/d50
c=comp[1];pc=6.65;pabs=pc-.5+1.013
for fl,f,QA,QB in [(2.5,1.7,18,10.5),(1.5,1.0,14,8.5)]:
    Qt=QA+QB+fl
    print(fl,f,"PinA",pc-.3*(Qt/50)**2*f-dp(Qt,180,50,pabs)-dp(QA,12,19,pabs),"PinB",pc-.3*(Qt/50)**2*f-dp(Qt,180,50,pabs)-dp(QB,8,16,pabs))
