# P9 stopping sight distance. f taken at posted speed; actual speed posted+5; downhill: f-G
f={60:.33,70:.31,80:.30,90:.30,100:.29}
ASD=(170.0,190.0); G=(0.02,0.04); tr=2.5
for v,fv in f.items():
    vv=v+5
    ssd=max(0.278*tr*vv+(0.278*vv)**2/(19.6*(fv-g)) for g in G)
    print(v,"worst SSD %.3f"%ssd,"margin vs 170: %.3f%%"%((ASD[0]-ssd)/ASD[0]*100),"PASS" if ssd<=ASD[0] else "fail")
