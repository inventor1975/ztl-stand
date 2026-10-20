#!/bin/bash
# usage: run.sh file.json
cd "$(git rev-parse --show-toplevel)"
OPENBLAS_NUM_THREADS=1 timeout 900 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand "$1"
