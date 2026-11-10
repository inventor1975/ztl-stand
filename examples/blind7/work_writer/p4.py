# P4 noise dose: OSHA T=8/2^((L-90)/5), levels <80 dBA ignored (Table G-16a range 80-130), protector: attenuation=NRR-7 dB per period
import itertools
per=[((97,101),2.5),((91,94),3.0),((84,87),2.0),((74,79),0.5)]
T=lambda L: 8/2**((L-90)/5)
def dose(levels,nrr):
    att=max(nrr-7,0) if nrr else 0
    d=0
    for L,(r,h) in zip(levels,per):
        e=L-att
        if e>=80: d+=h/T(e)
    return 100*d
cat={'none':(0,0),'P1 NRR15':(15,0.20),'P2 NRR19':(19,0.30),'P3 NRR22':(22,0.45),'P4 NRR24':(24,0.80),'P5 NRR27':(27,1.10),'P6 NRR30':(30,1.60)}
req=15.0
for k,(nrr,price) in cat.items():
    w=max(dose(c,nrr) for c in itertools.product(*[p[0][::1] for p in per]))
    # check interior monotone: dose monotone in L, so corners suffice
    print(k,"worst dose %.2f%%"%w,"TWA %s"%('n/a (all periods below 80 dBA)' if w<1e-9 else round(16.61*__import__('math').log10(w/100)+90,1)),"PASS" if w<=req else "fail",price)
