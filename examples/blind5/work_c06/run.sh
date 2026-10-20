#!/bin/bash
# usage: run.sh name limit_s
cd "$(git rev-parse --show-toplevel)"
n=$1; lim=${2:-900}
/usr/bin/time -f "%e s wall %M KB" -o examples/blind5/work_c06/$n.time env OPENBLAS_NUM_THREADS=1 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand examples/blind5/work_c06/$n.json > examples/blind5/work_c06/$n.out 2> examples/blind5/work_c06/$n.err &
P=$!
for i in $(seq $lim); do kill -0 $P 2>/dev/null || break; sleep 1; done
if kill -0 $P 2>/dev/null; then for c in $(pgrep -P $P) $P; do kill -9 $c; done; pkill -9 -f "work_c06/$n.json"; echo KILLED_AT_LIMIT >> examples/blind5/work_c06/$n.err; fi
echo end >> examples/blind5/work_c06/$n.err
