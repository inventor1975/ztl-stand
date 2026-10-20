#!/bin/bash
cd "$(git rev-parse --show-toplevel)"
for d in "P1 G1" "P2 G1" "P1 G2" "P3 G1" "P2 G2" "P3 G2" "P1 G3" "P2 G3" "P3 G3" "P4 G1" "P1 G4" "P5 G1" "P2 G4" "P4 G2" "P6 G1" "P5 G2"; do
 set -- $d
 python3 examples/blind4/work_c04/gen.py examples/blind4/work_c04/v_$1$2.json x $1 $2
 s=$(date +%s)
 OPENBLAS_NUM_THREADS=1 timeout 400 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand examples/blind4/work_c04/v_$1$2.json > examples/blind4/work_c04/o_$1$2.txt 2>&1
 e=$(date +%s)
 echo "$1 $2 $((e-s))s $(grep -m1 '^  "verdict"' examples/blind4/work_c04/o_$1$2.txt) $(grep -m1 '"failing_mode"' examples/blind4/work_c04/o_$1$2.txt)" >> examples/blind4/work_c04/timings.txt
done
echo ALLDONE >> examples/blind4/work_c04/timings.txt
