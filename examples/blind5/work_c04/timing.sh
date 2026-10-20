cd "$(git rev-parse --show-toplevel)"
i=0
for spec in "250|250|0.0035|0.0035" "250|250|0.005|0.005" "300|300|0.0035|0.0035" "250|300|0.005|0.0035"; do
 i=$((i+1)); IFS='|' read DA DB SA SB <<< "$spec"
 python3 - "$DA" "$DB" "$SA" "$SB" $i <<'PY'
import json,sys
b=json.load(open("examples/blind5/c04.json"))
DA,DB,SA,SB,i=sys.argv[1:]
c=b["catalog"]
# one design: per-slot catalogs need distinct entries for DA/DB, SA/SB
c["diamA"]={**c["diam"],"items":[{"D":DA}]}; c["diamB"]={**c["diam"],"items":[{"D":DB}]}
c["slopeA"]={**c["slope"],"items":[{"S":SA}]}; c["slopeB"]={**c["slope"],"items":[{"S":SB}]}
c["mats"]["items"]=[x for x in c["mats"]["items"] if x["name"]=="PVC"]
b["slots"]["DA"]["from"]=["diamA"];b["slots"]["DB"]["from"]=["diamB"];b["slots"]["SA"]["from"]=["slopeA"];b["slots"]["SB"]["from"]=["slopeB"]
json.dump(b,open("examples/blind5/work_c04/tm%s.json"%i,"w"))
PY
 s=$(date +%s)
 OPENBLAS_NUM_THREADS=1 timeout 400 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand examples/blind5/work_c04/tm$i.json > examples/blind5/work_c04/tm$i.out 2>examples/blind5/work_c04/tm$i.err
 echo "tm$i $spec $(( $(date +%s)-s )) s" >> examples/blind5/work_c04/timing.log
done
