#!/bin/bash
# The night battery (2026-11-01). Everything through ~/bin/heavy with the 18 GB cap; logs in bench/night/logs/.
set -u
STAND=/media/vitaly/SSD_1000GB/Projects/ztl-stand
ZTL=/media/vitaly/SSD_1000GB/Projects/ZTL
LOG=$STAND/bench/night/logs
mkdir -p "$LOG"
stamp() { date '+%F %T'; }
echo "$(stamp) START" > "$LOG/00_timeline.txt"

echo "$(stamp) 1 ZTL preflight" >> "$LOG/00_timeline.txt"
( cd "$ZTL" && ~/bin/heavy -m 18G --cores 16 python3 preflight.py ) > "$LOG/01_ztl_preflight.log" 2>&1
echo "$(stamp) 2 ZTL run_all" >> "$LOG/00_timeline.txt"
( cd "$ZTL" && ~/bin/heavy -m 18G --cores 24 python3 run_all.py ) > "$LOG/02_ztl_run_all.log" 2>&1
echo "$(stamp) 3 ZTL axiom audit" >> "$LOG/00_timeline.txt"
( cd "$ZTL" && ~/bin/heavy -m 18G --cores 8 python3 inventory/axiom_audit.py ) > "$LOG/03_ztl_axiom_audit.log" 2>&1

echo "$(stamp) 4 stand suite, one core" >> "$LOG/00_timeline.txt"
( cd "$STAND" && PYTHONPATH=. ~/bin/heavy -m 18G --cores 1 python3 tests/test_stand.py ) > "$LOG/04_stand_sequential.log" 2>&1
echo "$(stamp) 5 stand suite, 24 shards, compared with the sequential run" >> "$LOG/00_timeline.txt"
( cd "$STAND" && PYTHONPATH=. ~/bin/heavy -m 18G --cores 24 python3 -m tests.run_parallel --jobs 24 \
    --compare "$LOG/04_stand_sequential.log" ) > "$LOG/05_stand_parallel.log" 2>&1

echo "$(stamp) 6 randomised battery x30" >> "$LOG/00_timeline.txt"
( cd "$STAND" && PYTHONPATH=. ~/bin/heavy -m 18G --cores 22 python3 bench/night/verify_all.py --jobs 22 --scale 30 ) \
    > "$LOG/06_battery.log" 2>&1

echo "$(stamp) 7 stage-0 benchmarks" >> "$LOG/00_timeline.txt"
( cd "$STAND" && PYTHONPATH=. ~/bin/heavy -m 18G --cores 24 python3 bench/stage0/scale_frame.py 40x8 100x24 250x48 ) \
    > "$LOG/07_scale_frame.log" 2>&1
( cd "$STAND" && PYTHONPATH=. ~/bin/heavy -m 18G --cores 24 python3 bench/stage0/scale_plate.py 100x50 316x158 ) \
    > "$LOG/08_scale_plate.log" 2>&1
echo "$(stamp) DONE" >> "$LOG/00_timeline.txt"
