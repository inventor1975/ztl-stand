# P11 horizontal curve: R >= (v/3.6)^2/(9.81(e+f)), v km/h. f_max(v) linear interp 80:.14 90:.13 100:.12 ; e in [0.05,0.06]; v85 in [88,95]; corridor: arc length pi*R*Delta/180 <= 330 m, Delta=40 deg
import numpy as np, math
fm=lambda v: float(np.interp(v,[80,90,100],[.14,.13,.12]))
Rcat={300:1.0,350:1.2,400:1.45,450:1.7,500:2.0,600:2.6}
need=max((v/3.6)**2/(9.81*(e+fm(v))) for v in (88,95) for e in (0.05,0.06))
print("required R (worst) %.2f m"%need)
for R,c in Rcat.items():
    L=math.pi*R*40/180
    print(R,"cost",c,"speed ok" if R>=need else "R too small","arc %.1f m"%L,"corridor ok" if L<=330 else "arc too long")
