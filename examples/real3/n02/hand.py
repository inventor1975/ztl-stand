from math import sqrt
# Tj = Ta + I^2*RDS*Rtot  ->  I = sqrt((Tj-Ta)/(RDS*Rtot)); worst corner = every "max" value
Ta=40
rows=[("s2",175,.45+.5+7,4.9e-3,58.9),("s3",175,.45+2.9+7,4.9e-3,51.6),("s4",150,.45+2.9+7,4.5e-3,48.6),
      ("s5",150,.45+2.9+19,4.5e-3,33.1),("s6",150,40,4.5e-3,24.7)]
for n,tj,R,rds,pub in rows:
    print(n,"hand %.3f"%sqrt((tj-Ta)/(rds*R)),"published",pub)
print("added (pad 3.41 at 25 psi):")
for n,tj,R,rds,pub in rows[1:4]:
    print(n,"hand %.3f"%sqrt((tj-Ta)/(rds*(R-2.9+3.41))))
