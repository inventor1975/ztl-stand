from hand import *
import itertools
# for each plate: min over A in grid of requirement needs, at A=610 (h decreasing in A, Q decreasing in A)
for d in (.06,.08,.1,.12,.15):
    w=worst(610,d)
    print("d=%g A=610: q10=%.2f q100=%.2f L/s, h100=%.4f  -> H needed %.4f"%(d*1000,w['q10']*1000,w['q100']*1000,w['h100'],w['h100']+0.3))
# smallest A such that d=100 meets H=2.0 (h<=1.7)
for d in (.08,.1):
    lo,hi=100,5000
    for _ in range(60):
        m=(lo+hi)/2
        if worst(m,d)['h100']<=1.7: hi=m
        else: lo=m
    w=worst(hi,d)
    print("d=%g: A needed for h<=1.7: %.1f  (q10=%.2f q100=%.2f L/s)"%(d*1000,hi,w['q10']*1000,w['q100']*1000))
