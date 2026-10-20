"""REFERENCE where enumeration is impossible (2^25, 2^33 vertices): the stand's PROVED exact extremes — descent to the
extreme vertex, zlin's certificate checked by ZTL's kernel, then RE-CHECKED by the checker's own code (no shared code),
and the extreme vertex's value re-solved exactly by reference.py's own builder.
    python3 ref_stand.py T09 n11"""
import sys, time, json
sys.path.insert(0, "../.."); sys.path.insert(0, "../../../ZTL")
from fractions import Fraction as F
from ustand import spice as SP, certify as K, checker as C, judge_ztl as J
from znumjudge import parse_quantities
task, node = sys.argv[1], sys.argv[2]
br = SP.to_brick(open(f"tasks/{task}/circuit.cir").read(), SP.read_bom(f"tasks/{task}/bom.csv"), [])
qs_ = br["quantities"]
fixed = {n: F(q["value"]) for n, q in qs_.items() if q["role"] == "given" and not q.get("tolerance")}
boxes = {n: (F(q["value"]) * (1 - F(q["tolerance"])), F(q["value"]) * (1 + F(q["tolerance"])))
         for n, q in qs_.items() if q["role"] == "given" and q.get("tolerance")}
unknowns = [n for n, q in qs_.items() if q["role"] == "derived"]
laws = [l["zfl"] for l in br["laws"]]
target = "V_" + node
t0 = time.time()
got = K.prove_linear_range(laws, unknowns, target, fixed, boxes)
if "range" not in got:
    print(json.dumps({"task": task, "open": got.get("open")})); sys.exit(1)
lo, hi = got["range"]
rechecked = all(C.check_linear_certificate(laws, fixed, boxes, unknowns, target, op, bd, cert)[0]
                for op, bd, cert in got["certs"])
print(json.dumps({"task": task, "target": target, "tolerances": len(boxes), "min": str(lo), "max": str(hi),
                  "min_f": float(lo), "max_f": float(hi), "pieces": got["pieces"], "checker_rechecked": rechecked,
                  "s": round(time.time() - t0, 1)}))
