import itertools
exec(open('count2.py').read().split("opt=")[0])
opt=191573.18692875846
Sx=[0.002,0.0035,0.005]
allc=[];nomp=[]
okc={}
for m in mats:
    for r in "AB":
        for D in Ds:
            for S in Sx: okc[(m,r,D,S)]=okn(m,r,D,S)
for m in mats:
  for DA,SA,DB,SB in itertools.product(Ds,Sx,Ds,Sx):
    c=cost(m,DA,SA,DB,SB)
    if c<opt:
        allc.append(c)
        ex = DB>=DA and 1.5+SA*420+SB*380<=5.0
        np_ = okc[(m,'A',DA,SA)] and okc[(m,'B',DB,SB)] and ex
        if np_: nomp.append((round(c),m,DA,SA,DB,SB))
print(len(allc),len(nomp)); print(sorted(nomp))
