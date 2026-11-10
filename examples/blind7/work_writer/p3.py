# P3 trucks: equivalent annual annuity, replacement chain forever. corners.
import itertools
def npv(r,c0,cf,n): return -c0+sum(cf/(1+r)**i for i in range(1,n+1))
def eaa(r,c0,cf,n): return npv(r,c0,cf,n)*r/(1-(1+r)**-n)
opts={'Old':(50000,(38000,42000),3),'New':(50000,(28500,31500),6)}
rs=(0.09,0.11)
print("nominal 10%:",{k:round(eaa(.10,c0,sum(cf)/2,n),1) for k,(c0,cf,n) in opts.items()})
for k,(c0,cf,n) in opts.items():
    ws=min(eaa(r,c0,x,n) for r in rs for x in cf); bs=max(eaa(r,c0,x,n) for r in rs for x in cf)
    print(k,"worst EAA",round(ws,1),"best",round(bs,1),"PASS(>=17000)" if ws>=17000 else "fail")
