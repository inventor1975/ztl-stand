from model import *
import random
random.seed(1)
worst=0
for i in range(300):
    n=random.choice(list(NTC)); a=random.choice(list(ADC)); cls=random.choice(list(CLS))
    Rp=random.choice(RV); Rpar=random.choice([None]+RV)
    with np.errstate(all='ignore'):
        x,e1=err(n,a,Rp,Rpar,cls)
        e2=err_alg(n,a,Rp,Rpar,cls)
    # the direct chain uses Rpar=None; the alg uses 1e12. Compare where finite
    m=np.isfinite(e1)&np.isfinite(e2)
    if m.sum()==0: continue
    d=np.max(abs(e1[m]-e2[m])); worst=max(worst,d)
    if d>1e-4: print('DIFF',n,a,cls,Rp,Rpar,d,m.sum())
print('max abs diff between direct chain and hand algebra (K):',worst)
