#!/bin/bash
# The P2 sweep over SimJEB decks (2026-11-12): every deck between MIN and MAX bytes, smallest first, one run at a
# time, skipping parts that already have a result. Survives a reboot: state is the result files themselves.
#   research/cad/sweep_p2.sh MIN_BYTES MAX_BYTES CAP TIMEOUT_S
# Results: research/cad/sweep_p2/{part}.json; log: research/cad/sweep_p2/status.log (ok / FAIL lines).
MIN=${1:-1024}; MAX=${2:-26214400}; CAP=${3:-16G}; TMO=${4:-2700}
R=$(cd "$(dirname "$0")/../.." && pwd)
D=/media/vitaly/SSD_1000GB/Projects/ext-data/simjeb/fem
O=$R/research/cad/sweep_p2
mkdir -p $O
cd $R || exit 1
export PYTHONPATH=. OPENBLAS_NUM_THREADS=6 OMP_NUM_THREADS=6
find $D -name '*.fem' -size +${MIN}c -size -${MAX}c -printf '%s %f\n' | sort -n | awk '{print $2}' | sed 's/.fem$//' |
while read part; do
  J=$O/$part.json
  [ -s $J ] && continue
  t0=$(date +%s)
  ~/bin/heavy -m $CAP --cores 6 timeout $TMO python3 -u -m ustand.cadbracket $D/$part.fem --subcase 1 --matfree yes \
    --zdtype 64 --lower p2 > $J.tmp 2> $O/$part.err
  rc=$?
  if [ $rc -eq 0 ] && [ -s $J.tmp ]; then
    mv $J.tmp $J
    rm -f $O/$part.err
    echo "$part ok $(python3 -c "import json;d=json.load(open('$J'));print(d['tets'],round(100*d['gap'],3),d['seconds'])") $(date '+%F %H:%M')" >> $O/status.log
  else
    rm -f $J.tmp
    echo "$part FAIL rc=$rc $(( $(date +%s) - t0 ))s :: $(grep -v '^\s*\[equil\|^heavy\|^lower\|^upper\|^exact' $O/$part.err | tail -1 | cut -c1-160) $(date '+%F %H:%M')" >> $O/status.log
  fi
done
echo "sweep done $(date '+%F %H:%M')" >> $O/status.log
