import itertools, math
cells=[("P15",1.5,11,30,2.4),("H20",2.0,16,22,2.0),("H25",2.5,17,20,2.9),("E25",2.5,24,12,1.7),("E30",3.0,33,9,1.6)]
bms=[("M30",30,9.0,3.2),("M40",40,6.0,4.5),("M60",60,3.5,7.5),("M80",80,2.5,11.0)]
def worst(cell,Np,b,heat,Ta=263.15,verbose=False):
    name,cap,R25,Im25,pr=cell
    res=dict(Vt=1e9,Rt=1e9,I=-1e9,Imarg=1e9,Vc=1e9)
    for P,Voc,a,B,cf,kb,dT in itertools.product((540,640),(3.46,3.52),(1.0,1.1),(2000,2400),(0.97,1.03),(1.0,1.2),((9,13) if heat else (0,))):
        Tc=Ta+dT
        Rc=a*R25*math.exp(B*(1/Tc-1/298.15))
        Rt=5*Rc/Np+b[2]*kb+4
        V0=5*Voc; R=Rt/1000
        disc=V0*V0-4*R*P
        if disc<0: return None
        I=(V0-math.sqrt(disc))/(2*R); Vt=V0-I*R
        kT=max(0.5,1-0.007*(298.15-Tc))
        E=5*Np*cap*cf*3.6*0.8*kT-(3.5 if heat else 0)
        rt=60*E/P
        Icell=I/Np
        Imax=Im25*(1-0.012*(298.15-Tc))
        Vc=Voc-Icell*Rc/1000
        res['Vt']=min(res['Vt'],Vt);res['Rt']=min(res['Rt'],rt);res['I']=max(res['I'],I)
        res['Imarg']=min(res['Imarg'],Imax-Icell);res['Vc']=min(res['Vc'],Vc)
    ok = res['Vt']>=14.2 and res['Rt']>=9 and res['I']<=b[1] and res['Imarg']>=0 and res['Vc']>=2.9
    return ok,res
def all_designs(Ta=263.15):
    out=[]
    for c in cells:
        for Np in (1,2,3,4):
            for b in bms:
                for h in (0,1):
                    price=5*Np*c[4]+b[3]+4.5*h
                    r=worst(c,Np,b,h,Ta)
                    out.append((price,c[0],Np,b[0],h,r))
    out.sort(key=lambda x:x[0]); return out
if __name__=="__main__":
    o=all_designs()
    n=0
    for price,c,Np,b,h,r in o:
        if r and r[0]:
            print("PASS",round(price,2),c,Np,b,h,{k:round(v,3) for k,v in r[1].items()}); n+=1
            if n>8:break
