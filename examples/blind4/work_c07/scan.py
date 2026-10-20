from model import *
import sys
res=[]
for n in NTC:
  for a in ADC:
    for cls in CLS:
      for Rp in RV:
        for Rpar in [None]+RV:
          r2,r1,e1,e2=ok(n,a,Rp,Rpar,cls)
          res.append((n,a,cls,Rp,Rpar,r2,r1,e1,e2))
import pickle; pickle.dump(res,open('scan.pkl','wb'))
ok_all=[r for r in res if r[5] and r[6]]
print(len(res),len(ok_all))
