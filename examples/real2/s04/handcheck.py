import itertools
tcq=(30,50); g=(25,35)
def corners(n_extra): 
    return itertools.product(tcq,*([g]*n_extra))
# setup: 3 gates, skew s in {-50,0,50}
for skews,name in (((0,),"noskew"),((-50,50),"skew50")):
    worst=max(q+sum(gs)+60-s for q in tcq for gs in itertools.product(g,repeat=3) for s in skews)
    print("min Tc",name,worst, "fc GHz",1000/worst)
for ng in (1,2):
    for smax in (0,50):
        w=min(q+sum(hs)-70-s for q in tcq for hs in itertools.product(g,repeat=ng) for s in (0,smax))
        print("hold slack worst, short gates",ng,"skew up to",smax,w)
