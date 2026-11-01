"""Stage 1 (2026-11-01): the energy path on growing plane-stress plates (CST, ustand/plate.py) — a clamped plate
NX x NY squares under a tip shear; prove "tip corner UY >= 1.02 x nominal" (UY < 0: at most 2 % more deflection),
every element's modulus +-0.5 %. Nominal from the stand's own solve at p = 1 (tol 0).
    ~/bin/heavy -m 18G --cores 24 python3 bench/stage0/scale_plate.py 44x22 100x50 200x100 316x158"""
import json, pathlib, sys, time
from fractions import Fraction as F
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples" / "plate"))
from ustand import plate as PL
import gen_plate as G
out = open(ROOT / "bench/stage0/scale_plate.jsonl", "a")
for nx, ny in [tuple(map(int, a.split("x"))) for a in sys.argv[1:]]:
    text = G.deck(nx, ny, "shear")
    tip = (nx + 1) * (ny + 1)                        # the top-right corner
    t0 = time.time()
    nom = F(PL.range_of(text, "0", f"U({tip},Y)")["nominal"].split()[0])
    t1 = time.time()
    r = PL.judge(text, "0.5%", [(tip, "Y", ">=", nom * F(102, 100))])
    t2 = time.time()
    lo = F(r["requirements"][0]["proved_range"][0].split()[0])
    row = {"nx": nx, "ny": ny, "unknowns": r["unknowns"], "elements": r["elements"], "verdict": r["verdict"],
           "nominal": float(nom), "proved_lo_rel_pct": (float(lo / nom) - 1) * 100,
           "nominal_s": round(t1 - t0, 2), "judge_s": round(t2 - t1, 2)}
    out.write(json.dumps(row) + "\n"); out.flush()
    print(f"{nx:4d} x {ny:4d}: {row['unknowns']:7d} unknowns {row['elements']:7d} elements  {row['verdict']:7s} "
          f"low end {row['proved_lo_rel_pct']:+.4f} % beyond nominal  nominal {row['nominal_s']:.1f} s  "
          f"judge {row['judge_s']:.1f} s", flush=True)
