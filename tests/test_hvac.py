# -*- coding: utf-8 -*-
"""ustand.hvac, layer 1 — psychrometrics ported from EnergyPlus 26.2.0 (DESIGN-HVAC.md). Run:
USTAND_ZTL=../ZTL PYTHONPATH=. python3 tests/test_hvac.py

1. An INDEPENDENT transcription of the C++ (written here by hand from Psychrometrics.cc / .hh, not from the
   templates) must agree with the templates to rounding over a sweep — it catches a typo in a coefficient or a branch.
2. EnergyPlus's OWN unit tests (tst/EnergyPlus/unit/Psychrometrics.unit.cc): their reference values at their tolerances.
   The iterative EnergyPlus functions are roots of ours (bisection here; the implicit law in the stand below).
3. The stand: a saturation-pressure range EARNED and refuted 0.2 Pa above its true minimum; the wet bulb of
   EnergyPlus's test as an IMPLICIT law, proved in a 0.002 K window.
4. PLANTED: a changed coefficient and a lost branch in a template are caught by 1.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import hvac as H, stand as S   # noqa: E402

CHECKS, FAILS = 0, []
K = 273.15


def check(c, what):
    global CHECKS
    CHECKS += 1
    if not c:
        FAILS.append(what)
        print("FAIL:", what)


# ---- 1. the C++ by hand (Psychrometrics.cc PsyPsatFnTemp raw; .hh PsyWFnTdbTwbPb, PsyHFnTdbW, PsyWFnTdbRhPb)
def psat_cpp(Tc):
    Tk = Tc + 273.15
    if Tk < 173.15:
        return 0.001405102123874164
    if Tk < 273.16:
        C1, C2, C3, C4, C5, C6, C7 = -5674.5359, 6.3925247, -0.9677843e-2, 0.62215701e-6, 0.20747825e-8, -0.9484024e-12, 4.1635019
        return math.exp(C1 / Tk + C2 + Tk * (C3 + Tk * (C4 + Tk * (C5 + C6 * Tk))) + C7 * math.log(Tk))
    if Tk <= 473.15:
        C8, C9, C10, C11, C12, C13 = -5800.2206, 1.3914993, -0.048640239, 0.41764768e-4, -0.14452093e-7, 6.5459673
        return math.exp(C8 / Tk + C9 + Tk * (C10 + Tk * (C11 + Tk * C12)) + C13 * math.log(Tk))
    return 1555073.745636215


def w_tdbrhpb_cpp(Tc, RH, PB):
    PDEW = RH * psat_cpp(Tc)
    W = PDEW * 0.62198 / max(PB - PDEW, 1000.0)
    return 1.0e-5 if W < 1.0e-5 else W


def w_tdbtwbpb_cpp(Tc, TWB, PB):
    TWB = min(TWB, Tc)
    PWET = psat_cpp(TWB)
    WET = 0.62198 * PWET / (PB - PWET)
    W = ((2501.0 - 2.381 * TWB) * WET - (Tc - TWB)) / (2501.0 + 1.805 * Tc - 4.186 * TWB)
    return w_tdbrhpb_cpp(Tc, 0.0001, PB) if W < 0 else W


def h_cpp(Tc, W):
    return 1.00484e3 * Tc + max(W, 1.0e-5) * (2.50094e6 + 1.85895e3 * Tc)


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


sweep = [x / 4 for x in range(-480, 840)]              # -120 .. 210 C, every 0.25 C: all four branches
worst = max(rel(H.evaluate("ep_psat", t + K), psat_cpp(t)) for t in sweep)
check(worst < 1e-12, f"psat: template = the C++ over -120..210 C, every branch (worst relative {worst:.1e})")
pairs = [(t, t - d) for t in range(-10, 50, 3) for d in (0, 0.5, 2, 5, 12)]
worst = max(rel(H.evaluate("ep_w_tdbtwbpb", t + K, w + K, 101325), w_tdbtwbpb_cpp(t, w, 101325)) for t, w in pairs)
check(worst < 1e-12, f"w from (Tdb, Twb, Pb): template = the C++ (worst {worst:.1e})")
worst = max(rel(H.evaluate("ep_h", t + K, w), h_cpp(t, w)) for t in range(-30, 60, 7) for w in (0, 1e-6, 0.004, 0.02))
check(worst < 1e-12, f"h from (Tdb, W): template = the C++, the max(w, 1e-5) guard included (worst {worst:.1e})")
check(H.evaluate("ep_cpair", 0.01) == 1.00484e3 + 0.01 * 1.85895e3 and H.evaluate("ep_cpair", 0) == 1.00484e3 + 1e-5 * 1.85895e3,
      "cp of moist air = 1.00484e3 + w 1.85895e3 (EnergyPlus CpAirAverageValue test), w >= 1e-5")


# ---- 2. EnergyPlus's own unit tests
def root(f, lo, hi, it=200):
    flo = f(lo)
    for _ in range(it):
        mid = (lo + hi) / 2
        if (f(mid) > 0) == (flo > 0):
            lo, flo = mid, f(mid)
        else:
            hi = mid
    return (lo + hi) / 2


def tsat_from_h(Hj, PB):
    """PsyTsatFnHPb: at standard pressure EnergyPlus's own fits (ep_tsat_h_std); elsewhere its secant iteration, i.e.
    the root of h(T, w(T, T, Pb)) = H (EnergyPlus stops at |dH/H| <= 1e-5)"""
    if abs(PB - 1.0133e5) / 1.0133e5 <= 0.01:
        return H.evaluate("ep_tsat_h_std", Hj) - K
    return root(lambda t: H.evaluate("ep_h", t + K, H.evaluate("ep_w_tdbtwbpb", t + K, t + K, PB)) - Hj, -100, 200)


cases = [(7.5223e4, 1.01325e5, 20.0, 0.001), (2.7298e4, 1.01325e5, 0.0, 0.001), (-6.7011e2, 1.01325e5, -20.0, 0.001),
         (-2.21379e4, 1.01325e5, -40.0, 0.001), (1.8379e5, 1.01325e5, 40.0, 0.001), (4.7577e5, 1.01325e5, 60.0, 0.001),
         (1.5445e6, 1.01325e5, 80.0, 0.001), (3.8353e6, 1.01325e5, 90.0, 0.001), (7.5223e4, 0.91325e5, 18.819, 0.001)]
bad = [(h, pb, want, round(tsat_from_h(h - 1.78637e4, pb), 4)) for h, pb, want, tol in cases
       if abs(tsat_from_h(h - 1.78637e4, pb) - want) > tol]
check(not bad, f"PsyTsatFnHPb's nine reference points (20, 0, -20, -40, 40, 60, 80, 90 C; 18.819 C at 91 325 Pa) as "
               f"roots of ours, at EnergyPlus's tolerance 0.001 C ({bad})")
ts = root(lambda t: H.evaluate("ep_psat", t + K) - 101325.0, 50, 150)
check(abs(ts - 99.974) < 0.001, f"PsyTsatFnPb(101 325 Pa) = 99.974 C (EnergyPlus test): ours {ts:.4f}")
twb = root(lambda t: H.evaluate("ep_w_twb_newW", 1 + K, t + K, 101325) - 0.002, -20, 1)
check(abs(twb - (-2.200)) < 0.001, f"PsyTwbFnTdbWPb(1 C, 0.002, 101 325) = -2.200 C (EnergyPlus test): ours {twb:.4f}")
w99 = H.evaluate("ep_w_tdppb", 99 + K, 101325.0)
check(abs(w99 - 17.5250143) < 0.0001, f"PsyWFnTdpPb(99 C, 101 325) = 17.5250143 (EnergyPlus test): ours {w99:.7f}")

# ---- 3. the stand
ZTL = os.environ.get("USTAND_ZTL")


def psat_brick(lo, hi):
    return {"stand": "ztl-stand/1",
            "quantities": {"T": {"role": "given", "range": ["293.15", "303.15"], "unit": "K", "ground": "air 20..30 C"},
                           "Pw": {"role": "derived", "unit": "Pa"}},
            "laws": [{"zfl": "Pw == ep_psat(T)", "source": "EnergyPlus PsyPsatFnTemp"}],
            "requirements": [{"quantity": "Pw", "op": "within", "value": [lo, hi], "why": "saturation 20..30 C"}]}


r1, r2 = S.run(psat_brick("2338.8", "4246.1")), S.run(psat_brick("2339", "4247"))
check(r1["verdict"] == "EARNED" and r1["units"].startswith("checked"),
      f"stand: Psat over 20..30 C EARNED within [2338.8, 4246.1] Pa, units checked ({r1.get('verdict')}, {r1.get('why')})")
check(r2["verdict"] == "REFUTED" and str(r2["its_violating_point"]["T"]).startswith("5863/20"),
      f"stand: >= 2339 Pa REFUTED at T = 293.15 K exactly ({r2.get('its_violating_point')})")
wb = {"stand": "ztl-stand/1",
      "quantities": {"T": {"role": "given", "value": "274.15", "unit": "K", "ground": "EnergyPlus test"},
                     "P": {"role": "given", "value": "101325", "unit": "Pa", "ground": "EnergyPlus test"},
                     "W": {"role": "given", "value": "0.002", "unit": "", "ground": "EnergyPlus test"},
                     "Twb": {"role": "derived", "unit": "K", "search": ["253.15", "274.15"]}},
      "laws": [{"zfl": "W == ep_w_twb_newW(T, Twb, P)", "source": "EnergyPlus PsyTwbFnTdbWPb: Twb is its root"}],
      "requirements": [{"quantity": "Twb", "op": "within", "value": ["270.949", "270.951"], "why": "-2.200 C +- 0.001"}]}
rw = S.run(wb)
check(rw["verdict"] == "EARNED", f"stand: the wet bulb of EnergyPlus's test as an IMPLICIT law, EARNED in "
                                 f"[-2.201, -2.199] C ({rw.get('verdict')}, {str(rw.get('why'))[:120]}, {rw.get('guaranteed')})")

# ---- 4. planted
save = dict(H.LIBRARY["ep_psat"])
H.LIBRARY["ep_psat"]["expr"] = save["expr"].replace("-5800.2206", "-5800.2306")
w1 = max(rel(H.evaluate("ep_psat", t + K), psat_cpp(t)) for t in sweep)
H.LIBRARY["ep_psat"]["expr"] = save["expr"].replace("if((_T/ep_K) < 273.16,", "if((_T/ep_K) < 0,", 1)
try:
    w2 = max(rel(H.evaluate("ep_psat", t + K), psat_cpp(t)) for t in sweep)
except (ValueError, OverflowError):
    w2 = float("inf")
H.LIBRARY["ep_psat"] = save
check(w1 > 1e-6 and w2 > 1e-6, f"PLANTED a changed coefficient ({w1:.1e}) and a lost ice branch ({w2:.1e}) are caught")

# ================================================================================ layer 2: performance curves
from ustand.hvac import curves as CV      # noqa: E402
import random                              # noqa: E402
DS = os.environ.get("EP_DATASETS", os.path.join(os.path.dirname(os.path.abspath(CV.__file__)), "datasets"))


def direct(spec, *v):
    """Curve::value written again by hand from CurveManager.cc (NOT from curves.TYPES): clamp inputs, formula, clamp out"""
    t, c = spec["type"], [float(x) for x in spec["coeffs"]]
    lim = ("x", "y", "z")
    v = [max(min(x, float(spec.get(f"{lim[j]}_max", 1e300))), float(spec.get(f"{lim[j]}_min", -1e300)))
         for j, x in enumerate(v)]
    if t == "Curve:Quadratic":
        val = c[0] + v[0] * (c[1] + v[0] * c[2])
    elif t == "Curve:Cubic":
        val = c[0] + v[0] * (c[1] + v[0] * (c[2] + v[0] * c[3]))
    elif t == "Curve:Linear":
        val = c[0] + v[0] * c[1]
    elif t == "Curve:Biquadratic":
        val = c[0] + v[0] * (c[1] + v[0] * c[2]) + v[1] * (c[3] + v[1] * c[4]) + v[0] * v[1] * c[5]
    elif t == "Curve:Bicubic":
        x, y = v
        val = (c[0] + x * c[1] + x * x * c[2] + y * c[3] + y * y * c[4] + x * y * c[5] + x ** 3 * c[6] + y ** 3 * c[7]
               + x * x * y * c[8] + x * y * y * c[9])
    elif t == "Curve:QuadraticLinear":
        val = (c[0] + v[0] * (c[1] + v[0] * c[2])) + (c[3] + v[0] * (c[4] + v[0] * c[5])) * v[1]
    else:
        return None
    if "out_min" in spec:
        val = max(val, float(spec["out_min"]))
    if "out_max" in spec:
        val = min(val, float(spec["out_max"]))
    return val


allc = {}
for f in ("PerfCurves.idf", "Chillers.idf"):
    allc.update(CV.curves_from_idf(open(os.path.join(DS, f), encoding="latin-1").read()))
# the two CoolingTowerPerformance objects of PerfCurves.idf are layer 3's (tests/test_hvac_plant.py)
allc = {k: v for k, v in allc.items() if v["type"].startswith("Curve:")}
rnd = random.Random(7)
worst, n_eval = 0.0, 0
for name, sp in allc.items():
    n = CV.TYPES[sp["type"]][0]
    for _ in range(6):
        pts = []
        for j in range(n):
            lo = float(sp.get(f"{'xyz'[j]}_min", -10)) - 3
            hi = float(sp.get(f"{'xyz'[j]}_max", 40)) + 3          # outside the limits too: the clamp is tested
            pts.append(rnd.uniform(lo, hi))
        d = direct(sp, *pts)
        if d is None:
            continue
        e = CV.evaluate(sp, *pts)
        worst = max(worst, abs(e - d) / max(abs(d), 1e-9))
        n_eval += 1
check(len(allc) == 976 and n_eval > 5000 and worst < 1e-12,
      f"curves: all {len(allc)} curves of EnergyPlus's datasets read from their IDF by code; the template = Curve::value "
      f"by hand at {n_eval} points inside AND outside the limits (worst {worst:.1e})")
cap = {"stand": "ztl-stand/1",
       "quantities": {"Tchw": {"role": "given", "range": ["279.15", "280.15"], "unit": "K", "ground": "6..7 C"},
                      "Tcond": {"role": "given", "range": ["302.15", "308.15"], "unit": "K", "ground": "29..35 C"},
                      "f": {"role": "derived", "unit": ""}},
       "curves": {"CAPFT": {"type": "Curve:Biquadratic", "coeffs": ["0.257896", "0.0389016", "-0.00021708", "0.0468684",
                                                                   "-0.00094284", "-0.00034344"],
                            "x_min": "5", "x_max": "10", "y_min": "24", "y_max": "35", "inputs": ["degC", "degC"]}},
       "laws": [{"zfl": "f == curve(CAPFT, Tchw, Tcond)", "source": "capacity f(T)"}],
       "requirements": [{"quantity": "f", "op": ">=", "value": "0.89", "why": "capacity >= 89 %"}]}
rc1 = S.run(cap)
cap["requirements"][0]["value"] = "0.9"
rc2 = S.run(cap)
f635 = CV.evaluate(cap["curves"]["CAPFT"], 6, 35)
check(rc1["verdict"] == "EARNED" and rc2["verdict"] == "REFUTED"
      and str(rc2["its_violating_point"].get("Tcond", "")).startswith("6163/20"),
      f"curves in the stand: a chiller capacity curve over 6..7 C x 29..35 C EARNS >= 0.89 and is REFUTED at >= 0.9 "
      f"at 35 C (f there {f635:.5f}) ({rc1.get('verdict')}, {rc2.get('verdict')}, {rc2.get('its_violating_point')})")
bad = dict(cap, curves={"X": {"type": "Curve:ExponentialSkewNormal", "coeffs": ["1", "1", "1", "1"]}},
           laws=[{"zfl": "f == curve(X, Tchw)", "source": "t"}])
rb = S.run(bad)
check(rb["verdict"] == "BRICK ERROR" and "not ported" in rb["why"], f"a curve type not ported is refused aloud ({rb.get('why')})")
save = CV.TYPES["Curve:Biquadratic"]
CV.TYPES["Curve:Biquadratic"] = (2, 6, "c0 + V1*(c1 + V1*c2) + V2*(c4 + V2*c3) + V1*V2*c5")      # PLANTED: c3, c4 swapped
sp = allc[next(n for n, x in allc.items() if x["type"] == "Curve:Biquadratic")]
w_p = abs(CV.evaluate(sp, 7, 30) - direct(sp, 7, 30))
CV.TYPES["Curve:Biquadratic"] = save
check(w_p > 1e-6, f"PLANTED two coefficients swapped in the biquadratic: caught ({w_p:.2e})")

if FAILS:
    print(f"HVAC RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"HVAC GREEN ({CHECKS} checks)")
