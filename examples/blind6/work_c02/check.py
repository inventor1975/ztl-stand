# independent check: float, worst-case by direct corner enumeration of all uncertain data (no stand code)
import itertools, math, sys
sys.path.insert(0,'.')
from gen import cables, breakers
def feas(c1,b1,c2,b2,L1=160.0,L2=85.0, full=True):
    # returns list of violated requirement names (worst case over data corners)
    viol=[]
    def cab(c): return dict(R20=float(c[2]),Iz=float(c[3]),price=float(c[4]))
    C=[cab(c1),cab(c2)]; B=[float(b1[1]),float(b2[1])]; L=[L1,L2]
    Irun=[56.0,35.0]
    th=[38+60*(Irun[i]/C[i]['Iz'])**2 for i in range(2)]
    Rp=[C[i]['R20']*(1+0.00393*(th[i]-20)) for i in range(2)]
    # R4-R6
    for i in range(2):
        if B[i]<1.1*Irun[i]: viol.append(f'R4_{i+1}')
        if 8*B[i]<1.25*6.4*[53,32][i]: viol.append(f'R5_{i+1}')
        if B[i]>C[i]['Iz']*math.sqrt(52/60): viol.append(f'R6_{i+1}')
    def vt(i,I,cos,Ioth,v0,ks):
        s=math.sqrt(1-cos**2)
        vbus=v0-ks*(I[0]+I[1])
        dV=math.sqrt(3)*I[i]*L[i]*(Rp[i]*cos+0.08*s)/1000
        return vbus, vbus-dV
    ranges=dict(v0=(395,415),ks=(0.06,0.085))
    worst={}
    for v0 in (395,415):
      for ks in (0.06,0.085):
        for i1 in (50,56):
          for i2 in (30,35):
            vb,v1=vt(0,[i1,i2],0.85,None,v0,ks); _,v2=vt(1,[i1,i2],0.85,None,v0,ks)
            worst['S1_Vt1']=min(worst.get('S1_Vt1',1e9),v1); worst['S1_Vt2']=min(worst.get('S1_Vt2',1e9),v2)
        for k in (5.8,6.4):
          for i2 in (30,35):
            I=[53*k,i2]; vb,v1=vt(0,I,0.4,None,v0,ks)
            worst['S2_Vt1']=min(worst.get('S2_Vt1',1e9),v1); worst['S2_Vbus']=min(worst.get('S2_Vbus',1e9),vb)
          for i1 in (50,56):
            I=[i1,32*k]
            # M2 starting: cos2=0.4 but feeder1 running at 0.85 -> need Vt2
            s=math.sqrt(1-0.16); vbus=v0-ks*(I[0]+I[1]); dV=math.sqrt(3)*I[1]*L[1]*(Rp[1]*0.4+0.08*s)/1000
            worst['S3_Vt2']=min(worst.get('S3_Vt2',1e9),vbus-dV); worst['S3_Vbus']=min(worst.get('S3_Vbus',1e9),vbus)
    lim={'S1_Vt1':380,'S1_Vt2':380,'S2_Vt1':340,'S2_Vbus':352,'S3_Vt2':340,'S3_Vbus':352}
    for k,v in lim.items():
        if worst[k]<v: viol.append(k)
    return viol,worst
if __name__=="__main__":
    L1=float(sys.argv[1]) if len(sys.argv)>1 else 160.0
    best=None; ok=[]
    for c1 in cables:
      for c2 in cables:
        for b1 in breakers:
          for b2 in breakers:
            v,w=feas(c1,b1,c2,b2,L1)
            if not v:
                cost=float(c1[4])*L1+float(c2[4])*85+float(b1[2])+float(b2[2])
                ok.append((cost,c1[0],b1[0],c2[0],b2[0]))
    ok.sort(); print(len(ok),'feasible'); print(ok[:6])
    if ok:
        c=[x for x in cables if x[0]==ok[0][1]][0]; c2=[x for x in cables if x[0]==ok[0][3]][0]
        b1=[x for x in breakers if x[0]==ok[0][2]][0]; b2=[x for x in breakers if x[0]==ok[0][4]][0]
        print(feas(c,b1,c2,b2,L1))
