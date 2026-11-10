# P2 signal timing (CDOT 2024 Eq.1, Eq.2, Table 1 clamps). worst case over corners.
import itertools, math
t=1.0;a=10.0;L=20.0;post=55.0
Vr=(47.0,52.0); g=(-0.04,-0.02); W=(112.0,120.0)
def Y(V,gr): return t+1.47*V/(2*a+64.4*gr)
def R(V,Wd): return max(1.0,(Wd+L)/(1.47*min(V,post))-1)
Ymax=max(Y(V,gr) for V in Vr for gr in g)
Rmax=max(R(V,Wd) for V in Vr for Wd in W)
Ymin_needed=max(3.0,Ymax); Rn=max(1.0,Rmax)
up=lambda x: math.ceil(x*10-1e-9)/10
print("Y worst %.4f -> %.1f ; R worst %.4f -> %.1f"%(Ymax,up(Ymin_needed),Rmax,up(Rn)))
print("Y<=6.0:",up(Ymin_needed)<=6.0,"; total unrounded %.4f, rounded %.1f"%(Ymin_needed+Rn,up(Ymin_needed)+up(Rn)))
print("limit total<=6.4 ->", "FEASIBLE" if up(Ymin_needed)+up(Rn)<=6.4 else "NO admissible (Y,R)")
