# -*- coding: utf-8 -*-
"""One round of indicator-driven refinement (2026-11-11; PLAN-level3 "Refining where the error lives").

  python3 research/cad/adapt_mark.py DECK OUT.deck.pkl --eta a.npy b.npy ... --scl SPEC.json [--theta 0.5]
                                     [--root COARSE.fem] [--stats STATS.json]

Sums the per-tet hypercircle indicators of the brackets just run (cadbracket --dump-eta), marks by Doerfler (the
smallest set carrying theta of the sum), refines red-green (ustand.refine.graded_refine) and checks conformity. The
indicator only CHOOSES the mesh; every bracket on the new deck is exact on its own. --root names the ORIGINAL coarse
deck, so --omega-children keeps omega the same region on every round. Stats: tets before / after, the marked share,
and the share of the marked tets OUTSIDE a ball of 3 wall thicknesses around the SCL point (the load path)."""
import argparse
import hashlib
import json
import os
import pickle
import sys
from fractions import Fraction

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ustand import tetfea as TF, refine as RF, cadbracket as CB                       # noqa: E402


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("out")
    ap.add_argument("--eta", nargs="+", required=True)
    ap.add_argument("--scl", required=True)
    ap.add_argument("--theta", type=float, default=0.5)
    ap.add_argument("--root")
    ap.add_argument("--stats")
    a = ap.parse_args(argv)
    d = TF.read_deck(a.deck)
    eta = sum(np.load(f) for f in a.eta)
    if len(eta) != len(d["tets"]):
        raise SystemExit(f"eta has {len(eta)} entries, the deck {len(d['tets'])} tets")
    mk = CB.doerfler(eta, a.theta)
    spec = json.load(open(a.scl))
    pt = np.array([float(x) for x in spec["point"]])
    tw = float(Fraction(str(spec["tw"])))
    g = d["grids"]
    cen = np.array([np.mean([[float(TF._nas(x)) for x in g[n]] for n in t], axis=0) for t in d["tets"]])
    off = np.linalg.norm(cen - pt, axis=1) > 3 * tw
    nd = RF.graded_refine(d, mk)
    if "deck" not in nd["refined_from"]:
        root = a.root or a.deck
        nd["refined_from"]["deck"] = root
        nd["refined_from"]["sha256"] = hashlib.sha256(open(root, "rb").read()).hexdigest()
    over, hang = RF.conformity(nd)
    if over or hang:
        raise SystemExit(f"NOT conforming: {over} faces in > 2 tets, {hang} hanging edges")
    with open(a.out, "wb") as f:
        pickle.dump(nd, f, protocol=pickle.HIGHEST_PROTOCOL)
    st = {"deck": a.deck, "out": a.out, "tets_in": len(d["tets"]), "tets_out": len(nd["tets"]),
          "marked": int(mk.sum()), "marked_share": float(mk.mean()), "eta_share_marked": float(eta[mk].sum() / eta.sum()),
          "marked_off_ball_share": float(off[mk].mean()), "eta_off_ball_share": float(eta[off].sum() / eta.sum()),
          "ball": {"centre": pt.tolist(), "radius": 3 * tw}, "patterns": nd["refined_from"]["patterns"],
          "closure_rounds": nd["refined_from"]["closure_rounds"], "conforming": True}
    print(json.dumps(st))
    if a.stats:
        json.dump(st, open(a.stats, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
