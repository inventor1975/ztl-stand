exec(open('check.py').read().split("def ok(")[0])
def rep(r,D,S,n):
    L,Qd,Qp=reach[r]; Dm=D/1000
    td=solve(Qd/1000,n,S,Dm); tp=solve(Qp/1000,n,S,Dm)
    vd=Qd/1000/geom(Dm,td)[0]; vp=Qp/1000/geom(Dm,tp)[0]; y=(1-math.cos(tp/2))/2
    return vd,y,vp
for r,D,S in (("A",250,0.005),("B",300,0.0035)):
    for n in (0.0095,0.0115):
        print(r,n,["%.6f"%x for x in rep(r,D,S,n)])
