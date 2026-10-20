import itertools
comp={'K32':(32,6.8,8.0,6900),'K40':(40,6.8,8.0,8200),'K40M':(40,7.3,8.4,8900),'K50':(50,7.3,8.4,10600),'K50H':(50,8.0,9.0,11800)}
dry={'D30':(30,0.40,1100),'D40':(40,0.35,1450),'D50':(50,0.30,1900),'D60':(60,0.30,2500)}
pipe={25:6.0,32:9.0,40:14.0,50:21.0,63:33.0}
L=180.0
QA=(14,18); QB=(8.5,10.5); leak=(1.5,2.5)
fouling=(1.0,1.7); tol=0.15
hA=(19,12); hB=(16,8)
pminA,pminB=6.0,6.2; pmaxA,pmaxB=8.5,9.0
def dp_pipe(Q,Lm,d,pg):
    return 1.6e3*Q**1.85*Lm/(d**5*(pg+1.013))
def margins(c,dr,d):
    FAD,pci,pco,_=comp[c]; Qr,dpr,_=dry[dr]
    m={}
    pci_lo=pci-tol
    # flows worst
    # scenarios: S1 A only; S2 B only; S3 both
    sc={'S1':(QA[1]+leak[1],QA[1],0),'S2':(QB[1]+leak[1],0,QB[1]),'S3':(QA[1]+QB[1]+leak[1],QA[1],QB[1])}
    for s,(Qt,qa,qb) in sc.items():
        dd=dpr*(Qt/Qr)**2*fouling[1]
        pg=pci_lo-0.5
        dm=dp_pipe(Qt,L,d,pg)
        if qa>0:
            pa=pci_lo-dd-dm-dp_pipe(qa,hA[1],hA[0],pg)
            m[s+'A']=pa/pminA-1
        if qb>0:
            pb=pci_lo-dd-dm-dp_pipe(qb,hB[1],hB[0],pg)
            m[s+'B']=pb/pminB-1
    m['Rcap']=0.94*FAD/(QA[1]+QB[1]+leak[1])-1
    m['RmaxA']=pmaxA/(pco+tol)-1; m['RmaxB']=pmaxB/(pco+tol)-1
    m['Rdry']=Qr/(QA[1]+QB[1]+leak[1])-1   # dryer rated flow >= peak flow
    return m
def sweep():
    out=[]
    for c in comp:
      for dr in dry:
        for d in pipe:
            m=margins(c,dr,d)
            if min(m.values())>=0:
                out.append((comp[c][3]+dry[dr][2]+pipe[d]*L,c,dr,d,min(m,key=m.get),round(min(m.values()),4)))
    return sorted(out)
if __name__=='__main__':
    for r in sweep()[:8]: print(r)
