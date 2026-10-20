import itertools
exec(open('check.py').read().split("res=[]")[0])
allc=[];filt=[]
for m in mats:
  for DA,SA,DB,SB in itertools.product(Ds,Ss,Ds,Ss):
    c=cost(m,DA,SA,DB,SB); allc.append(c)
    if SA>0 and SB>0 and DB>=DA and 1.5+SA*420+SB*380<=5.0: filt.append((c,m,DA,SA,DB,SB))
opt=191573.18692875846
print(len(allc),sum(c<opt for c in allc),len(filt),sum(f[0]<opt for f in filt))
