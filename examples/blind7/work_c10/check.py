from fractions import Fraction as F
import itertools
Ths=[F('313.15'),F('318.15')]; Tcs=[F('253.15'),F('263.15')]; Qs=[F('8.5'),F('9.5')]
def P(eta,Th,Tc,Q):
    e=eta*(F(9,10) if Tc<F('258.15') else 1)
    return Q*(Th-Tc)/(Th*e)
# Tc is in the derate zone for [253.15,258.15); sup there is at Tc->258.15 limit? check both pieces
for n,eta in [('U1','0.42'),('U2','0.47'),('U3','0.52'),('U4','0.55')]:
    eta=F(eta)
    # piece A: Tc in [253.15,258.15) derated: monotone, worst at Tc=253.15 (P increases as Tc falls)
    a=max(P(eta,Th,Tc,Q) for Th in Ths for Tc in [F('253.15')] for Q in Qs)
    # piece B: Tc in [258.15,263.15] no derate; worst at Tc=258.15 (exactly -15, not derated)
    b=max(P(eta,Th,F('258.15'),Q) for Th in Ths for Q in Qs)
    w=max(a,b)
    print(n,float(a),float(b),float(w),'OK' if w<=4 else 'FAIL')
# smallest eta: worst corner Th=318.15,Tc=253.15,Q=9.5 derated
Th,Tc,Q=F('318.15'),F('253.15'),F('9.5')
eta_min=Q*(Th-Tc)/(Th*4*F(9,10))
print(eta_min,float(eta_min))
# derate-free piece needs eta>=?
print(float(Q*(Th-F('258.15'))/(Th*4)))
# brute scan
import numpy as np
worst=0
for Th in np.linspace(313.15,318.15,11):
  for Tc in np.linspace(253.15,263.15,101):
    for Q in (8.5,9.5):
      e=0.5392*(0.9 if Tc<258.15 else 1)
      worst=max(worst,Q*(Th-Tc)/(Th*e))
print(worst)
