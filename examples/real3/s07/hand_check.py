from fractions import Fraction as F
def Pmax(od,w,S=20000,Y=F(2,5),tf=1):
    D=F(od)+F('0.005'); t=F(w)*F('0.9'); S=S*tf
    return 2*S*t/(D-2*Y*t)
for name,od,w in [("1/2x0.065","0.5","0.065"),("3/4x0.109","0.75","0.109")]:
    for tf in (1,F(68,100),F(82,100),F(58,100)):
        print(name,"TF",float(tf),"exact Pmax",float(Pmax(od,w,tf=tf)),"published-method (rating 5100/5800 x TF)",(5100 if name[0]=='1' else 5800)*float(tf))
# stand witness: P=3473, T=400, OD=0.505, wall=0.0585
P=F(3473);OD=F('0.505');wall=F('0.0585');S=20000*F(68,100)
treq=P*OD/(2*(S+P*F(2,5)));print("witness margin",float(wall-treq), "P=3472:",float(wall-F(3472)*OD/(2*(S+F(3472)*F(2,5)))))
# choice at P=3470, T=400
for w in ("0.035","0.049","0.065","0.083"):
    print(w, float(Pmax("0.5",w,tf=F(68,100))), "ok at 3470:", Pmax("0.5",w,tf=F(68,100))>=3470, "published-method ok:", {"0.035":2600,"0.049":3700,"0.065":5100,"0.083":6700}[w]*0.68>=3470)
