# -*- coding: utf-8 -*-
"""
The CERTIFIED stiffness-to-mass ranking of SimJEB brackets from proved compliance brackets (2026-11-10).

For a load F with |F| fixed, the stiffness along F is k = |F|^2 / C, and C is proved in [C_lo, C_hi]
(cadbracket: lower from minimum potential energy, upper from complementary energy). So k is in
[|F|^2 / C_hi, |F|^2 / C_lo]. Mass = rho * V, where V is the EXACT volume of the closed surface mesh (level 1) and rho is
the same for every part (premise: one material for all, as the SimJEB metadata states). So k/m is ordered as k/V.
Two parts are ORDERED (proved) when their k/V intervals do not overlap; otherwise the order is OPEN.

    python3 -I rank_certified.py <dir with cadbracket JSONs> [level-1 results jsonl]
"""
import json
import os
import sys
from fractions import Fraction as Fr


def load(rank_dir, l1_path):
    vol = {}
    for line in open(l1_path):
        r = json.loads(line)
        if r.get("volume_proved"):
            vol[r["id"]] = Fr(r["volume"])
    rows, skipped = [], []
    for fn in sorted(os.listdir(rank_dir)):
        if not fn.endswith(".json"):
            continue
        pid = fn[:-5]
        try:
            r = json.load(open(os.path.join(rank_dir, fn)))
        except (json.JSONDecodeError, OSError):
            skipped.append((pid, "no result (empty or unreadable JSON)"))
            continue
        if pid not in vol:
            skipped.append((pid, "no proved volume"))
            continue
        F2 = sum(Fr(x) ** 2 for x in r["F"]) + sum(Fr(x) ** 2 for x in r["M"])
        lo, hi = Fr(r["compliance"][0]), Fr(r["compliance"][1])
        V = vol[pid]
        rows.append({"id": pid, "subcase": r["subcase"], "tets": r["tets"], "gap": r["gap"],
                     "kV": (F2 / hi / V, F2 / lo / V)})
    return rows, skipped


def ranking(rows):
    rows = sorted(rows, key=lambda r: -(r["kV"][0] + r["kV"][1]))
    pairs = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a["kV"][0] > b["kV"][1]:
                pairs.append((a["id"], ">", b["id"]))
            elif b["kV"][0] > a["kV"][1]:
                pairs.append((b["id"], ">", a["id"]))
            else:
                pairs.append((a["id"], "?", b["id"]))
    return rows, pairs


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    rank_dir = argv[0]
    l1 = argv[1] if len(argv) > 1 else os.path.join(here, "simjeb_level1_results.jsonl")
    rows, skipped = load(rank_dir, l1)
    rows, pairs = ranking(rows)
    print("k/V interval (N/mm per mm^3), subcase as computed; ordered by midpoint")
    for r in rows:
        print(f"  {r['id']:>5}  tets {r['tets']:>7}  gap {100 * r['gap']:5.1f} %  k/V in "
              f"[{float(r['kV'][0]):.6e}, {float(r['kV'][1]):.6e}]")
    proved = [p for p in pairs if p[1] == ">"]
    print(f"pairs: {len(pairs)}, ORDERED (proved) {len(proved)}, OPEN {len(pairs) - len(proved)}")
    for p in pairs:
        print("  ", " ".join(p))
    for pid, why in skipped:
        print(f"  skipped {pid}: {why}")


if __name__ == "__main__":
    main(sys.argv[1:])
