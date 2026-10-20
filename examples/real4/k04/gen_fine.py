import json,sys
name,vstep,vobands,lstep=sys.argv[1],float(sys.argv[2]),sys.argv[3].split(","),float(sys.argv[4])
def fmt(x): 
    s=("%.4f"%x).rstrip("0").rstrip("."); return s
vb=[];x=7.0
while x<28-1e-9: vb.append(fmt(x)); x+=vstep
vb.append("28")
lb=[];x=1.0
while x<12-1e-9:
    lb.append(fmt(x)); x+= (lstep if x>=3.999 else 1.0)
lb+=["12","15","20","30"]
d=json.load(open("comp_ls.json"))
d["interface"]["inputs"]["Vin"]["bands"]=vb
d["interface"]["inputs"]["Vo"]["bands"]=vobands
d["interface"]["inputs"]["L"]["bands"]=lb
json.dump(d,open(f"comp_ls_{name}.json","w"),indent=1)
s=json.load(open("system_one.json")); s["components"]["LS"]["file"]=f"comp_ls_{name}.json"
s["find"]["precision"]="0.25"
json.dump(s,open(f"system_{name}.json","w"),indent=1)
print(len(vb)-1,len(vobands)-1,len(lb)-1)
