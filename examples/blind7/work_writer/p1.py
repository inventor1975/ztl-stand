# P1 fracture: steel selection. a_crit = (1/pi) * (K/(Q*sigma_design))^2, sigma_design = 0.6*sy, Q=1.12
import math
steels={'A36':(36,60),'A441':(50,53),'A572':(50,100),'A514':(100,60)}
Q=1.12; req=2.5
def a(K,sy): return (K/(Q*0.6*sy))**2/math.pi
print("nominal (source Table 1):")
for k,(sy,K) in steels.items(): print(k,round(a(K,sy),3))
print("worst case K_IC -10 pct, requirement a_crit >= %.2f in"%req)
best=0
for k,(sy,K) in steels.items():
    w=a(0.9*K,sy); best=max(best,w); print(k,round(w,3),"PASS" if w>=req else "fail")
print("largest requirement any steel meets in worst case:",round(best,3))
