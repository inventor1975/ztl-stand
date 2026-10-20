cd "$(git rev-parse --show-toplevel)"
for s in winter spring summer autumn; do
 /usr/bin/time -f "%e s" env OPENBLAS_NUM_THREADS=1 timeout 900 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand examples/blind5/work_c10/sub_$s.json > examples/blind5/work_c10/sub_$s.out 2> examples/blind5/work_c10/sub_$s.err
done
echo done > examples/blind5/work_c10/subs.done
