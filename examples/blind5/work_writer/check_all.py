import itertools, math, numpy as np
def hdr(s): print("\n=====",s)
# P1
hdr("P1 bearing")
import p01
res=[]
for b in p01.B:
  for l in p01.LUB:
    for k in p01.KIT:
      if b[3]>150: continue
      P0=40*(1+0.6*p01.ax)
      if b[2]/P0<2.5: continue
      Lh=p01.life(b,l,k)
      res.append((round(b[4]+l[2]+k[2],3),b[0],l[0],k[0],round(Lh),round(Lh/56000-1,4)))
res.sort()
print([r for r in res if r[5]>=0][:3]); print("cheaper infeasible:",[r for r in res if r[0]<1.7][:4])
# P2
hdr("P2 transformer")
import subprocess; print(subprocess.run(["python3","p02.py"],capture_output=True,text=True).stdout)
# P3
hdr("P3 solar")
import p03
def g5(lo,hi): return list(np.linspace(lo,hi,5))
best=None
rows=[]
for col in p03.COL:
  for n in range(1,17):
    for V in p03.TANKS:
      for ins in (0,1):
        e=p03.evaluate(col,n,V,ins); 
        if e["aux"]<=3700 and e["Tmax"]<=80 and 50<=e["ratio"]<=100: rows.append((e["cost"],col,n,V,ins,e["aux"],e["Tmax"]))
rows.sort(); print(len(rows),rows[:3])
w=rows[0]; e5=p03.evaluate(w[1],w[2],w[3],w[4],grd=g5); print("5-pt grid winner:",e5)
# P4
hdr("P4 sewer"); print(subprocess.run(["python3","p04.py"],capture_output=True,text=True).stdout[:800])
# P5
hdr("P5 cooling tower")
import p05
rows=[]
for src in p05.SRC:
  for inh in p05.INH:
    for rk in p05.ACID:
      d=p05.design(src,inh,rk)
      if d and d["M"]<=26000: rows.append((round(d["cost"],3),src,inh,rk,round(d["M"]),[round(b,3) for b in d["B"]]))
rows.sort(); print(len(rows)); [print(r) for r in rows[:4]]
# P6, P7, P9: separate script outputs
hdr("P6/P7/P9"); print(subprocess.run(["python3","check_p06_p07_p09.py"],capture_output=True,text=True).stdout)
# P8
hdr("P8 van"); print(subprocess.run(["python3","p08.py"],capture_output=True,text=True).stdout[:700])
# P10
hdr("P10 aquaculture")
import p10
b=p10.search(4.0,3.0,40.0,31000)
print(len(b)); [print([round(x,2) if isinstance(x,float) else x for x in r]) for r in b[:3]]
# fine T grid on winner
tot,a,lox,ms,n,E,capex=b[0]
cmin=1e9; fmin=1e9
for (nm,d,h,wl,wh,tl,th),m in zip(p10.SEAS,ms):
    for T in np.linspace(tl,th,81):
        for Wb in np.linspace(wl,wh,9):
            C=p10.Css(T,Wb,m,a); cmin=min(cmin,C); fmin=min(fmin,p10.after_fail(T,Wb,C,lox))
print("fine grid winner Cmin,Fmin:",cmin,fmin)
# P11
hdr("P11 FX")
import p11
for st in p11.OPT:
    r=p11.solve(st,qloss=-0.10,annual=0.30)
    print(st,None if r.status else (round(r.fun*1000,2),"kEUR",np.round(r.x[:8],3)))
# P12
hdr("P12 call centre"); print(subprocess.run(["python3","p12.py"],capture_output=True,text=True).stdout)
