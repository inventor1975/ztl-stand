import json,sys
# usage: genv.py out.json strikeLabel h1,h2,h3,h4 o1,o2,o3,o4
out,lab=sys.argv[1],sys.argv[2]
h=sys.argv[3].split(","); o=sys.argv[4].split(",")
import subprocess
subprocess.check_call([sys.executable,"gen.py",out,"",lab] if False else [sys.executable,"gen.py",out])
b=json.load(open(out))
b["catalog"]["strikes"]["items"]=[it for it in b["catalog"]["strikes"]["items"] if it["label"]==lab]
for i in range(4):
    b["catalog"][f"hf{i+1}"]={"items":[{"x":h[i]}],"fields":{"x":{"unit":""}}}
    b["catalog"][f"of{i+1}"]={"items":[{"x":o[i]}],"fields":{"x":{"unit":""}}}
b["report"]="all"
json.dump(b,open(out,"w"),indent=1)
