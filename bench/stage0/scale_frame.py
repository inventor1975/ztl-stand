"""Stage 1 (2026-11-01): the energy path on growing plane frames — prove "roof sway <= nominal + 2 %", every element's
modulus +-0.5 %. Nominal from the stand's own exact solve at p = 1 (tol 0)."""
import json, pathlib, subprocess, sys, time
from fractions import Fraction as F
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from ustand import frame as FR
out = open(ROOT / "bench/stage0/scale_frame.jsonl", "a")
for ns, nb in [tuple(map(int, a.split("x"))) for a in sys.argv[1:]]:
    text = subprocess.run([sys.executable, str(ROOT / "examples/frame/gen_frame.py"), str(ns), str(nb)],
                          capture_output=True, text=True, check=True).stdout
    roof = ns * (nb + 1) + 1
    t0 = time.time()
    nom = F(FR.range_of(text, "0", f"U({roof},X)")["nominal"].split()[0])
    t1 = time.time()
    r = FR.judge(text, "0.5%", [(roof, "X", "<=", nom * F(102, 100))])
    t2 = time.time()
    row = {"storeys": ns, "bays": nb, "unknowns": r["unknowns"], "elements": r["elements"], "verdict": r["verdict"],
           "nominal": float(nom), "proved_hi_rel_pct": (float(F(r["requirements"][0]["proved_range"][1].split()[0]) / nom) - 1) * 100,
           "nominal_s": round(t1 - t0, 2), "judge_s": round(t2 - t1, 2)}
    out.write(json.dumps(row) + "\n"); out.flush()
    print(f"{ns:3d} x {nb:2d}: {row['unknowns']:6d} unknowns {row['elements']:6d} elements  {row['verdict']:7s} "
          f"upper +{row['proved_hi_rel_pct']:.4f} %  judge {row['judge_s']:.1f} s", flush=True)
