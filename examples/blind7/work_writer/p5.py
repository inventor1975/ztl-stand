# P5 machines: NPV, r in [9%,11%], all inflows -3%..+3% independently, requirement NPV>=1165 in all scenarios
R=[-16000,2000,4000,5000,5000,5000,5000]; H=[-25000,2000,4000,8000,9000,9000,9000]
npv=lambda r,cf,s: cf[0]+sum(c*s/(1+r)**i for i,c in enumerate(cf) if i>0)
for nm,cf in (('Regular',R),('Heavy',H)):
    print(nm,"nominal 9%%: %.2f"%npv(.09,cf,1),"worst(11%%,-3%%): %.2f"%npv(.11,cf,.97),"best %.2f"%npv(.09,cf,1.03))
# crossover nominal rate
lo,hi=.09,.2
for _ in range(80):
    m=(lo+hi)/2
    if npv(m,H,1)-npv(m,R,1)>0: lo=m
    else: hi=m
print("nominal-inflow crossover rate %.4f%%"%(lo*100))
w=npv(.11,H,.97);print("Heavy margin over 1165: %.3f%%"%((w-1165)/1165*100), "Regular fails:",npv(.11,R,.97)<1165)
