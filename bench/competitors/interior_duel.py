"""THE INTERIOR SHOWCASE — bricks whose worst case lies INSIDE the tolerance box, against SCIP (nominal and corners),
Z3, cvc5, dReal.

2026-10-20, the curator's "Хорошо, проверь худшие случаи".

The twelve blind bricks all had their worst case at a corner, so SCIP posed at every corner found the stand's answers.
These three do not (examples/interior):
  i01  power into a load behind a series resistor — the peak at RL = Rs, inside RL's range;
  i02  a point load anywhere on a simple span — the moment peaks at mid-span, zero at both supports;
  i03  a machine on mounts, speed anywhere in a band — transmissibility peaks at resonance, inside the band.
Each tool's design is JUDGED BY THE STAND on the brick pinned to it (stand._pinned): EARNED, or REFUTED with the
failing point. SCIP via scip_duel.build (binaries per item, nominal / every corner); Z3, cvc5, dReal via
blind_duel.discrete (designs in cost order, each checked over the whole box; an UNSAT is a proof).

    ~/venvs/competitors/bin/python bench/competitors/interior_duel.py
"""
import json
import pathlib
import random
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import blind_duel as BD  # noqa: E402
import scip_duel as SD  # noqa: E402
from blind_duel import B, S  # noqa: E402

BD.BLIND = HERE.parent.parent / "examples" / "interior"
OUT = HERE / "interior_results.jsonl"
BRICKS = ["i01", "i02", "i03"]


def stand_on(b, design):
    """The stand's verdict on one design (the brick pinned to it), with its failing point when refuted."""
    raw = S._pinned(b, design)
    raw.pop("objective", None)
    raw["conflicts"] = False
    r = S._run(raw, conflicts=False)
    out = {"verdict": r.get("verdict")}
    if r.get("verdict") == "REFUTED":
        out["at"] = r.get("its_violating_point")
        out["value_there"] = r.get("value_there")
    return out


def scip(cid, form):
    b = BD.load(cid)
    m, ys, xs, nsc = SD.build(b, [mb for _, mb in BD.mode_bricks(b)], form, random.Random(18))
    m.setParam("limits/time", 300)
    m.setParam("numerics/feastol", 1e-9)
    t0 = time.time()
    m.optimize()
    r = {"tool": f"scip-{form}", "status": m.getStatus(), "s": round(time.time() - t0, 2), "scenarios": nsc}
    if m.getNSols():
        design, _x = SD.answer(b, m, ys, xs)
        r.update(design=S._label(design), cost=m.getObjVal(), stand_on_it=stand_on(b, design))
    return r


def solver(cid, tool):
    t0 = time.time()
    r = BD.discrete(cid, tool, 60, 600)
    r.update(tool=tool, s=round(time.time() - t0, 2))
    if r.get("result") == "FOUND":
        b = BD.load(cid)
        d = next(d for d in S.designs(b) if S._label(d) == r["design"])
        r["stand_on_it"] = stand_on(b, d)
    return r


def main():
    rows = []
    for cid in BRICKS:
        raw = json.load(open(BD.BLIND / f"{cid}.json"))
        t0 = time.time()
        st = S.run(raw, conflicts=False)
        rows.append(dict(brick=cid, tool="stand", verdict=st.get("verdict"), s=round(time.time() - t0, 2),
                         cost=(st.get("objective") or {}).get("value"),
                         optimal=(st.get("objective") or {}).get("optimal"),
                         design=json.dumps(st.get("design"), ensure_ascii=False)[:160]))
        for form in ("nominal", "corners"):
            try:
                rows.append(dict(brick=cid, **scip(cid, form)))
            except Exception as e:  # noqa: BLE001
                rows.append(dict(brick=cid, tool=f"scip-{form}", error=f"{type(e).__name__}: {str(e)[:200]}"))
        for tool in ("z3", "cvc5", "dreal"):
            try:
                rows.append(dict(brick=cid, **solver(cid, tool)))
            except Exception as e:  # noqa: BLE001
                rows.append(dict(brick=cid, tool=tool, error=f"{type(e).__name__}: {str(e)[:200]}"))
    with open(OUT, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            print(json.dumps(r, ensure_ascii=False, default=str)[:400], flush=True)


if __name__ == "__main__":
    main()
