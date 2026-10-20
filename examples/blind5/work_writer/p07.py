import math, itertools
# procedures: N lo,hi per week ; K1 lo,hi (mGy at 1 m per exam, primary) ; HVL Pb mm (nom), barite mm, concrete mm ; HVL tol +-10 %
PROC=[("Extremity 60 kVp",140,180,1.1,1.3,0.10,2.0,10.0),
      ("Chest 125 kVp",90,120,0.8,1.0,0.28,6.0,21.0),
      ("Spine 85 kVp",40,60,5.0,6.0,0.16,3.4,14.0),
      ("Pelvis 100 kVp",20,30,7.5,9.0,0.21,4.4,17.0)]
LEAD=[0,0.5,1.0,1.5,2.0,2.5,3.0]; BAR=[0,10,20,30]; CON=[0,50,100,150]
HTOL=0.10; U=0.25; T=1.0; D=2.2; CONV=1.14; PLIM=0.02
KGPL=11.34; KGPB=2.7; KGPC=2.35
def dose(pb,ba,co,tol=HTOL):
    H=0
    for nm,nl,nh,kl,kh,hp,hb,hc in PROC:
        B=2**(-(pb/(hp*(1+tol))+ba/(hb*(1+tol))+co/(hc*(1+tol))))
        H+=nh*kh*B
    return CONV*U*T/D**2*H
def mass(pb,ba,co): return KGPL*pb+KGPB*ba+KGPC*co
def thick(pb,ba,co): return pb+ba+co
if __name__=="__main__":
    rows=[]
    for pb,ba,co in itertools.product(LEAD,BAR,CON):
        rows.append((dose(pb,ba,co),mass(pb,ba,co),thick(pb,ba,co),pb,ba,co))
    rows.sort()
    print("lowest doses overall:")
    for r in rows[:5]: print([round(x,4) for x in r])
    MASS,THK=55,60
    ok=[r for r in rows if r[1]<=MASS and r[2]<=THK]
    print("best under limits:",[round(x,4) for x in ok[0]])
    feas=[r for r in rows if r[0]<=PLIM]
    print("designs meeting dose alone:",len(feas)); 
    for r in sorted(feas,key=lambda r:r[1])[:6]: print([round(x,4) for x in r])
    for r in sorted(feas,key=lambda r:r[2])[:4]: print("thin",[round(x,4) for x in r])
