import itertools
from fractions import Fraction as F
def run(variant="sheet", zero=False, vin=F(0)):
    R1=(F(10000)*F(999,1000),F(10000)*F(1001,1000)); R2=(F(40000)*F(999,1000),F(40000)*F(1001,1000))
    d=(F(-3,1000),F(3,1000))
    if variant=="sheet":
        voff=F(4,10000); ib=F(40,10**9); oadc=F(45,10)
    else:
        voff=F(13,10000); ib=F(525,10**10); oadc=F(45,10)
    if zero: voff=ib=oadc=F(0); ores=oinl=F(0)
    else: ores=F(1,2); oinl=F(1)
    Vr=(F(5)*F(995,1000),F(5)*F(1005,1000)); dV=(F(-15,10000),F(15,10000)); eg=F(44,10)/4095
    Rs=F(500)
    lo=hi=None
    for r1,r2,dr1,dr2,vr,dv,e,vo,ibn,ibp,oa,orr,oi in itertools.product(R1,R2,d,d,Vr,dV,(-eg,eg),(-voff,voff),(-ib,ib),(-ib,ib),(-oadc,oadc),(-ores,ores),(-oinl,oinl)):
        R1e=r1*(1+dr1);R2e=r2*(1+dr2);Vre=vr*(1+dv)
        vo1=(1+R2e/R1e)*(vin+vo+ibp*Rs)-ibn*R2e
        code=4095*vo1/Vre*(1+e)+oa+orr+oi
        err=code/4095-vin
        lo=err if lo is None or err<lo else lo; hi=err if hi is None or err>hi else hi
    return float(lo),float(hi)
if __name__=="__main__":
    for v in ("sheet","prose"):
        print(v,"offset vin0",run(v,False,F(0)))
        print(v,"gain only vin1",run(v,True,F(1)))
        print(v,"total vin1",run(v,False,F(1)))
