#!/bin/bash
# usage: run.sh brick.json [--dev]
cd "$(git rev-parse --show-toplevel)"
b=$1; shift
s=$(date +%s)
OPENBLAS_NUM_THREADS=1 timeout 900 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand examples/real4/k05/$b "$@" > examples/real4/k05/out_${b%.json}$( [ "$1" = "--dev" ] && echo _dev || echo _work).txt 2>&1
echo "$b $@ rc=$? $(( $(date +%s)-s )) s"
