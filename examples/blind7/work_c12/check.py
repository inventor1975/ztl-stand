from itertools import combinations
from fractions import Fraction as F
inv=dict(A=150,B=100,C=70,D=50,E=30,F=20,G=10)
npv=dict(A=60,B=25,C=10,D=15,E=11,F=7,G=2)
best=[]
for r in range(8):
    for s in combinations(inv,r):
        if sum(inv[k] for k in s)<=200:
            best.append((F(95,100)*sum(npv[k] for k in s),s))
best.sort(reverse=True)
for b in best[:4]:print(float(b[0]),b[1])
w=best[0][0];print("margin %",float((w-F(74))/74*100))
