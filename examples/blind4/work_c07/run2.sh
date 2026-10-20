#!/bin/bash
cd "$(git rev-parse --show-toplevel)"
OPENBLAS_NUM_THREADS=1 timeout ${2:-200} ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand "$1"
