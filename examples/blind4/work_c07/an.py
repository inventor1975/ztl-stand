from model import *
import pickle
res=pickle.load(open('scan.pkl','rb'))
ok_all=[r for r in res if r[5] and r[6]]
rows=sorted(((bom(r[0],r[1],r[2],r[4] is not None),)+r for r in ok_all),key=lambda z:z[0])
for z in rows[:12]: print(z)
print('min bom',rows[0][0],' <=2.2:',sum(1 for z in rows if z[0]<=2.2+1e-9))
from collections import Counter
print(Counter((z[1],z[2]) for z in rows))
# best error ignoring R2 and R3
best=min(res,key=lambda r:r[7]); print('best control err',best)
# R2 ok alone, count; R1 control-band alone
print(sum(1 for r in res if r[5]), sum(1 for r in res if r[6]))
