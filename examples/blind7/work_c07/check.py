from fractions import Fraction as F
L={"F3":(8550,96,[F(57,100),F(54,100),F(51,100)]),"F2":(5700,64,[F(60,100),F(57,100),F(54,100)]),
"L1":(4800,41,[F(62,100),F(59,100),F(56,100)]),"L2":(6200,50,[F(62,100),F(59,100),F(56,100)])}
def cu(c,r):
    i=0 if r<=7 else 1
    return c[i]+(c[i+1]-c[i])*(r-(6+i))
res=[]
for k,(phi,w,c) in L.items():
    for n in range(1,6):
        # E monotone in LLF, CU monotone in RCR piecewise -> min at LLF=.75, RCR in {6.5,7.2} (check dense scan too)
        mn=min(n*phi*cu(c,F(r,1000))*F(3,4)/120 for r in range(6500,7201,5))
        mn2=n*phi*min(cu(c,F(13,2)),cu(c,F(36,5)))*F(3,4)/120
        assert mn==mn2
        res.append((float(mn2),k,n,n*w,n*w<=120))
for r in sorted(res,reverse=True): print(r)
print("both ok:",[r for r in res if r[0]>=50 and r[4]])
print("best within power:",max(r for r in res if r[4]))
print("best ignoring power:",max(res))
