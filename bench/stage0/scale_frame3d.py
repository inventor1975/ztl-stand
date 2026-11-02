"""The space frame's SIZE (2026-11-02, the curator: what is the largest 3D model the stand proves, and how long):
regular steel space frames, storeys x bays(X) x bays(Y), columns and beams in X and Y, beams with a uniform load,
lateral wind at every floor, every member's modulus +-0.5 %. Measured per size: first-order proof of the roof sway,
the stability bracket's lower bound, the physical second-order sway, EN 6.3.3 biaxial interaction (all members).
Each phase separately timed; a phase is skipped above --max-phase-unknowns for the slower ones.

    PYTHONPATH=. python3 bench/stage0/scale_frame3d.py 2x2x2 4x3x3 8x4x4 ... [--skip so,en]"""
import json, pathlib, sys, time
from fractions import Fraction as F
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from ustand import frame3d as F3


def gen(ns, bx, by, B=6, C=5, H=4, lumped=False, graded=True):
    nid = lambda f_, a_, b_: f_ * (bx + 1) * (by + 1) + b_ * (bx + 1) + a_ + 1
    L = ["ET, 1, BEAM4", "MP, EX, 1, 210e9", "MP, PRXY, 1, 0.3",
         "R, 1, 0.0149, 2.52e-4, 0.92e-4, 0.3, 0.3, 0, 0, 2.9e-6",          # columns, an HEB 300-like section
         "R, 2, 0.0116, 4.82e-4, 0.20e-4, 0.4, 0.18, 0, 0, 1.0e-6"]         # beams, an IPE 400-like section
    for f_ in range(ns + 1):
        for b_ in range(by + 1):
            for a_ in range(bx + 1):
                L.append(f"N, {nid(f_, a_, b_)}, {B * a_}, {C * b_}, {H * f_}")
    el, beams, seen = [], [], set()
    for f_ in range(ns):
        # HEAVIER COLUMNS below (2026-11-02: one HEB 300 for 20 storeys put alpha_cr under 1): section factor c =
        # the storeys carried / 2 (at least 1) — area x c, inertias x c^2 (a deeper section), its own REAL id
        cfac = max(1, (ns - f_) // 2)
        rid = 10 + cfac
        if rid not in seen:
            seen.add(rid)
            L.append(f"R, {rid}, {0.0149 * cfac:.6g}, {2.52e-4 * cfac * cfac:.6g}, {0.92e-4 * cfac * cfac:.6g}, "
                     f"{0.3 * cfac:.6g}, {0.3 * cfac:.6g}, 0, 0, {2.9e-6 * cfac * cfac:.6g}")
        for b_ in range(by + 1):
            for a_ in range(bx + 1):
                el.append((nid(f_, a_, b_), nid(f_ + 1, a_, b_), rid if graded else 1))
    for f_ in range(1, ns + 1):
        for b_ in range(by + 1):
            for a_ in range(bx):
                el.append((nid(f_, a_, b_), nid(f_, a_ + 1, b_), 2)); beams.append(len(el))
        for a_ in range(bx + 1):
            for b_ in range(by):
                el.append((nid(f_, a_, b_), nid(f_, a_, b_ + 1), 2)); beams.append(len(el))
    for a, b, r_ in el:
        L += [f"REAL, {r_}", f"E, {a}, {b}"]
    for b_ in range(by + 1):
        for a_ in range(bx + 1):
            L.append(f"D, {nid(0, a_, b_)}, ALL, 0")
    for f_ in range(1, ns + 1):
        for b_ in range(by + 1):
            L.append(f"F, {nid(f_, 0, b_)}, FX, 6000")
        for a_ in range(bx + 1):
            L.append(f"F, {nid(f_, a_, 0)}, FY, 4000")
    if lumped:          # the beam loads as nodal forces (EN 6.3.3 in 3D refuses QLOAD, 2026-11-02 — a named gap)
        acc = {}
        for k in beams:
            a, b, _ = el[k - 1]
            span = B if (a - 1) % (bx + 1) != (b - 1) % (bx + 1) else C
            for nd in (a, b):
                acc[nd] = acc.get(nd, 0) + 12000 * span // 2
        L += [f"F, {nd}, FZ, -{v}" for nd, v in sorted(acc.items())]
    else:
        for k in beams:
            L.append(f"QLOAD, {k}, FZ, -12000")
    return "\n".join(L), nid(ns, bx, by), len(el)


def main(argv):
    skip = set(argv[argv.index("--skip") + 1].split(",")) if "--skip" in argv else set()
    sizes = [a for a in argv if "x" in a and not a.startswith("--")]
    out = open(ROOT / "bench/stage0/scale_frame3d.jsonl", "a")
    for sz in sizes:
        ns, bx, by = map(int, sz.split("x"))
        text, roof, ne = gen(ns, bx, by)
        row = {"size": sz, "members": ne, "date": time.strftime("%Y-%m-%d %H:%M"), "columns": "graded"}
        t0 = time.time()
        r = F3.range_of(text, "0.5%", f"U({roof},X)")
        row["first_order_s"] = round(time.time() - t0, 1)
        row["sway_mm"] = [round(float(r["lo"]) * 1000, 4), round(float(r["hi"]) * 1000, 4)]
        row["unknowns"] = len(F3.energy_system(text, "0")[2])
        print(f"{sz}: {ne} members, {row['unknowns']} unknowns; first order {row['first_order_s']} s, sway {row['sway_mm']} mm",
              flush=True)
        if "st" not in skip:
            t0 = time.time()
            st = F3.stability_lower(text, "0.5%")
            row["stability_s"] = round(time.time() - t0, 1)
            row["lam_low"] = float(st["lam_low"]) if st.get("lam_low") is not None else None
            print(f"   stability lower {row['lam_low']}  {row['stability_s']} s", flush=True)
        if "so" not in skip:
            t0 = time.time()
            so = F3.second_order_disp(text, "0.5%", [f"U({roof},X)"])["BASE"]
            row["second_order_s"] = round(time.time() - t0, 1)
            if f"U({roof},X)" in so:
                row["sway2_mm"] = [round(float(x) * 1000, 4) for x in so[f"U({roof},X)"][:2]]
            else:
                row["sway2_mm"] = so.get("why")
            print(f"   second order sway {row['sway2_mm']} mm  {row['second_order_s']} s", flush=True)
        if "en" not in skip:
            t0 = time.time()
            en = F3.judge_interaction(text, "0.5%", F(355) * 10 ** 6, "b", "c")
            row["en_s"] = round(time.time() - t0, 1)
            u_ = en.get("utilisation_max")
            row["en_verdict"], row["en_loads"] = en.get("verdict"), "QLOAD on the beams"
            row["en_util"] = float(u_.split("~")[1].rstrip(")")) if u_ and "~" in u_ else u_
            print(f"   EN 6.3.3 {row['en_verdict']} util {row['en_util']}  {row['en_s']} s", flush=True)
        out.write(json.dumps(row) + "\n"); out.flush()


if __name__ == "__main__":
    main(sys.argv[1:])
