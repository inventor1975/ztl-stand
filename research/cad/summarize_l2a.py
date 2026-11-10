"""Summary of level 2a over all SimJEB brackets: consistency with SimJEB's own maxima, and a ranking by PROVED
stiffness per mass (the GE challenge's question: a light bracket that is stiff). Usage:
python3 research/cad/summarize_l2a.py <l2a.jsonl> <metadata.tab> <level1.jsonl>"""
import csv, json, sys
R = [json.loads(l) for l in open(sys.argv[1])]
meta = {r["id"]: r for r in csv.DictReader(open(sys.argv[2]))}
L1 = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[3])}
ok = [r for r in R if "error" not in r]
print(f"{len(R)} decks run: {len(ok)} bounded, {len(R) - len(ok)} errors: " + ", ".join(f"{r['id']} ({r['error'][:50]})" for r in R if "error" in r))
key = {"vertical": "max_ver_magdisp", "horizontal": "max_hor_magdisp", "diagonal": "max_dia_magdisp"}
viol = []
for r in ok:
    for c in r["cases"]:
        if c["label"] in key and c["disp_lower"] and c["disp_lower"] > float(meta[r["id"]][key[c["label"]]]):
            viol.append((r["id"], c["label"]))
print(f"cases where the PROVED load-point displacement exceeds SimJEB's maximum vertex displacement: {len(viol)} {viol[:10]}")
# stiffness per mass: the proved lower bound on the vertical compliance -> an UPPER bound on the stiffness |F|^2 / C;
# mass from OUR exact volume (level 1) x the deck's density 4.43e-6 kg/mm^3
rows = []
for r in ok:
    c = next((c for c in r["cases"] if c["label"] == "vertical"), None)
    if not c:
        continue
    k_up = 35585.77 ** 2 / c["compliance_lower_proved"]          # N/mm: the stiffness is AT MOST this
    m = L1[r["id"]]["volume"] * 4.43e-6
    rows.append((k_up / m, r["id"], round(k_up), round(m, 4), meta[r["id"]]["category"]))
rows.sort(reverse=True)
print("vertical stiffness per mass, PROVED UPPER bounds (N/mm per kg) — top 10. NOT a certified ranking: an upper bound\n  alone cannot order two designs; with both bounds (cadbracket), non-overlapping brackets order them:")
for x in rows[:10]:
    print(f"  bracket {x[1]:>4} ({x[4]}): k <= {x[2]} N/mm, mass {x[3]} kg, k/m <= {x[0]:.0f}")
