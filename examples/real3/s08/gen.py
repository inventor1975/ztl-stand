import json, sys
nominal = len(sys.argv) > 1 and sys.argv[1] == "nominal"
def fac(name, lo, hi, mid, why, ground):
    if nominal:
        return {"role": "given", "value": mid, "unit": "", "why": why + " (NOMINAL point only)", "ground": ground}
    return {"role": "given", "range": [lo, hi], "unit": "", "why": why, "ground": ground}
G = "congatec AN9 rev 1.3, sec 2.1/2.2 notes"
q = {
 "Treq": {"role": "given", "value": "131400", "unit": "h", "why": "15 years x 24 x 365 (source sec 2.4)", "ground": G},
 "I3":   {"role": "given", "value": "3", "unit": "uA", "why": "maximum RTC battery current, sec 2.4", "ground": G},
 "k":    fac("k", "1.1", "1.3", "1.2", "capacity multiplier 1.2, 'can vary from 1.1 to 1.3'", G),
 "Cap1": {"role": "given", "value": "1000", "unit": "mAh", "why": "searched (find 1): nominal capacity of the cell, formula-2.2 check", "ground": "placeholder"},
 "margin1": {"role": "derived", "unit": "Ah", "why": "Cap1 minus the capacity the source's eq 2.2 demands"},
 "Cap2": {"role": "given", "value": "230", "unit": "mAh", "why": "CR2032 nominal capacity, sec 2.3", "ground": G},
 "I2":   {"role": "given", "value": "2.5", "unit": "uA", "why": "maximum RTC battery current, sec 2.3", "ground": G},
 "f2":   fac("f2", "0.7", "0.9", "0.8", "life factor 0.8, 'can vary from 0.7 to 0.9'", G),
 "T2":   {"role": "given", "value": "73584", "unit": "h", "why": "searched (find 2): guaranteed lifetime in hours (placeholder = 8.4 y published)", "ground": "placeholder"},
 "margin2": {"role": "derived", "unit": "Ah", "why": "charge available (Cap2*f2) minus charge drawn over T2"},
 "Cap3": {"role": "given", "value": "1000", "unit": "mAh", "why": "searched (find 3): capacity needed so that 15 y holds under formula 2.1's factor range", "ground": "placeholder"},
 "f3":   fac("f3", "0.7", "0.9", "0.8", "life factor 0.8, 'can vary from 0.7 to 0.9' (same source note as f2, a separate draw)", G),
 "margin3": {"role": "derived", "unit": "Ah", "why": "Cap3*f3 minus charge drawn over Treq"},
}
laws = [
 {"zfl": "margin1 == Cap1 - Treq*I3*k", "source": "congatec AN9 eq 2.2: BatNomCap = tmin*24*365*IBatMax*k, required Cap >= that"},
 {"zfl": "margin2 == Cap2*f2 - T2*I2", "source": "congatec AN9 eq 2.1: tmax = Cap/(24*365*I)*f, lifetime >= T2 iff Cap*f >= T2*I"},
 {"zfl": "margin3 == Cap3*f3 - Treq*I3", "source": "congatec AN9 eq 2.1 applied to the 15 y / 3 uA case of sec 2.4"},
]
def req(m, why): return [{"quantity": m, "op": ">=", "value": "0", "why": why}]
r1 = req("margin1", "cell capacity covers eq 2.2 for every k in the source's range")
r2 = req("margin2", "the cell lasts at least T2 for every f2 in the source's range")
r3 = req("margin3", "the cell lasts at least 15 y for every f3 in the source's range")
b = {"stand": "ztl-stand/1",
 "why": "s08 round 3: congatec AN9 RTC battery calculations; uncertainty = the source's own stated factor ranges" + (" [NOMINAL variant: factors at the published point values]" if nominal else ""),
 "quantities": q, "slots": {}, "laws": laws, "requirements": r1, "catalog": {},
 "conflicts": False,
 "find": [
  {"smallest": "Cap1", "from": "0", "to": "1500", "precision": "0.01", "requirements": r1},
  {"largest": "T2", "from": "0", "to": "100000", "precision": "1", "requirements": r2},
  {"smallest": "Cap3", "from": "0", "to": "1500", "precision": "0.01", "requirements": r3},
 ]}
json.dump(b, open("brick_nominal.json" if nominal else "brick.json", "w"), indent=1)
