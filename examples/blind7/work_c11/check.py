from fractions import Fraction as F
import math
def fm(v):
    if v<=80: return F(14,100)
    if v>=100: return F(12,100)
    if v<=90: return F(14,100)+(F(13,100)-F(14,100))*(v-80)/10
    return F(13,100)+(F(12,100)-F(13,100))*(v-90)/10
def Rmin(v,e): return (v/F(36,10))**2/(F(981,100)*(e+fm(v)))
vs=[F(88)+F(7)*i/700 for i in range(701)]; es=[F(5,100),F(6,100)]
vals=[(Rmin(v,e),v,e) for v in vs for e in es]
hi=max(vals); lo=min(vals)
print("Rmin range",float(lo[0]),float(hi[0]),hi[1:],lo[1:])
print("exact stand bounds",75625000/238383,225625000/556227)
for R,c in [(300,1.0),(350,1.2),(400,1.45),(450,1.7),(500,2.0),(600,2.6)]:
    arc=math.pi*R*40/180
    print(R,c,"arc",round(arc,3),"arc ok",arc<=330,"R>=Rmin worst",R>=float(hi[0]),"margin",R-float(hi[0]))
