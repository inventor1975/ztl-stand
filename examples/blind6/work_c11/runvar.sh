#!/bin/bash
cd "$(git rev-parse --show-toplevel)"
for v in "$@"; do
  s=$(date +%s)
  OPENBLAS_NUM_THREADS=1 timeout 900 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand examples/blind6/work_c11/$v.json > examples/blind6/work_c11/out_$v.txt 2> examples/blind6/work_c11/err_$v.txt
  echo "$v rc=$? secs=$(( $(date +%s)-s ))" >> examples/blind6/work_c11/times.txt
done
