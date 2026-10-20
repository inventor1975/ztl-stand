from gen import *
import json
d=build(ntcs=["N4"],adcs=["A12"],rp_vals=[20000],rpar_vals=[],classes=["0.1"],
   bands=[("253.15","333.15","1","wide"),("273.15","313.15","0.4","control")],r3=False)
# rpar_vals=[] -> empty; use none only
json.dump(d,open('small.json','w'),indent=1)
