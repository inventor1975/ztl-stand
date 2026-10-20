import itertools
exec(open('check.py').read().split("res=[]")[0])
def okn(mat,r,D,S):
    (n0,n1),k,vmax=mats[mat]; L,Qd,Qp=reach[r]; Dm=D/1000; n=(n0+n1)/2
    td=solve(Qd/1000,n,S,Dm); tp=solve(Qp/1000,n,S,Dm)
    if td is None or tp is None: return False
    vd=Qd/1000/geom(Dm,td)[0]; vp=Qp/1000/geom(Dm,tp)[0]; y=(1-math.cos(tp/2))/2
    return vd>=0.6 and y<=0.7 and vp<=vmax
opt=191573.18692875846
cnt={}
for m in mats:
    okA={(D,S):okn(m,"A",D,S) for D in Ds for S in Ss}
    okB={(D,S):okn(m,"B",D,S) for D in Ds for S in Ss}
    for DA,SA,DB,SB in itertools.product(Ds,Ss,Ds,Ss):
        if SA==0 or SB==0 or DB<DA or 1.5+SA*420+SB*380>5.0: continue
        c=cost(m,DA,SA,DB,SB)
        if c<opt and okA[(DA,SA)] and okB[(DB,SB)]: cnt.setdefault(m,[]).append((round(c),DA,SA,DB,SB))
for m,v in cnt.items(): print(m,len(v),sorted(v)[:5])
