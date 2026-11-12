# -*- coding: utf-8 -*-
"""ustand.hvac, layers 3 and 4 — cooling towers and chillers ported from EnergyPlus 26.2.0 (DESIGN-HVAC.md). Run:
USTAND_ZTL=../ZTL PYTHONPATH=. python3 tests/test_hvac_plant.py            (--fast: without the stand proofs)

The pattern of tests/test_hvac.py:
1. An INDEPENDENT transcription of the C++ — written here by hand from CondenserLoopTowers.cc, ChillerElectricEIR.cc,
   ChillerReformulatedEIR.cc, General.cc (SolveRoot) and Psychrometrics, NOT from the templates; the tower coefficient
   sets are READ from the C++ text itself — must agree with the templates over sweeps inside AND outside the clamps.
   What EnergyPlus iterates is compared with the root of our implicit law (bisection here; the stand proves it below).
2. EnergyPlus's OWN unit tests (tst/EnergyPlus/unit): every value our port can reach without running a simulation.
3. The stand: EARNED and REFUTED bricks of each layer, the refutation points recomputed with the transcription.
4. PLANTED errors (a changed coefficient, a lost clamp, a lost branch, a swapped order) must turn a check RED.
"""
import math
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import hvac as H, stand as S          # noqa: E402
from ustand.hvac import curves as CV, towers as TW, chillers as CH   # noqa: E402

_HV = os.path.dirname(os.path.abspath(CV.__file__))       # the EnergyPlus files shipped beside the port
DS = os.environ.get("EP_DATASETS", os.path.join(_HV, "datasets"))
SRC = os.environ.get("EP_SOURCES", os.path.join(_HV, "sources"))
FAST = "--fast" in sys.argv
CHECKS, FAILS = 0, []
K = 273.15
MEASURED = {}


T_START = time.time()


def check(c, what):
    global CHECKS
    CHECKS += 1
    if not c:
        FAILS.append(what)
        print("FAIL:", what, flush=True)
    elif "-v" in sys.argv:
        print(f"ok [{time.time() - T_START:.0f} s]: {what[:150]}", flush=True)


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


def bisect(f, lo, hi, it=200):
    """the root of f in [lo, hi] (a sign change assumed), or None"""
    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return lo
    if fhi == 0:
        return hi
    if (flo > 0) == (fhi > 0):
        return None
    for _ in range(it):
        mid = (lo + hi) / 2
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


# ======================================================================= the C++ by hand: psychrometrics it calls
def psat_cpp(Tc):                                   # Psychrometrics.cc PsyPsatFnTemp_raw
    Tk = Tc + 273.15
    if Tk < 173.15:
        return 0.001405102123874164
    if Tk < 273.16:
        return math.exp(-5674.5359 / Tk + 6.3925247 + Tk * (-0.9677843e-2 + Tk * (0.62215701e-6 + Tk * (
            0.20747825e-8 + -0.9484024e-12 * Tk))) + 4.1635019 * math.log(Tk))
    if Tk <= 473.15:
        return math.exp(-5800.2206 / Tk + 1.3914993 + Tk * (-0.048640239 + Tk * (0.41764768e-4 + Tk * -0.14452093e-7))
                        + 6.5459673 * math.log(Tk))
    return 1555073.745636215


def w_tdbrhpb_cpp(TDB, RH, PB):                     # .hh PsyWFnTdbRhPb
    PDEW = RH * psat_cpp(TDB)
    W = PDEW * 0.62198 / max(PB - PDEW, 1000.0)
    return 1.0e-5 if W < 1.0e-5 else W


def w_tdbtwbpb_cpp(TDB, TWBin, PB):                 # .hh PsyWFnTdbTwbPb
    TWB = TWBin
    if TWB > TDB:
        TWB = TDB
    PWET = psat_cpp(TWB)
    WET = 0.62198 * PWET / (PB - PWET)
    W = ((2501.0 - 2.381 * TWB) * WET - (TDB - TWB)) / (2501.0 + 1.805 * TDB - 4.186 * TWB)
    return w_tdbrhpb_cpp(TDB, 0.0001, PB) if W < 0.0 else W


def h_cpp(TDB, dW):                                 # .hh PsyHFnTdbW
    W = max(dW, 1.0e-5)
    return 1.00484e3 * TDB + W * (2.50094e6 + 1.85895e3 * TDB)


def h_tdbrhpb_cpp(TDB, RH, PB):                     # .hh PsyHFnTdbRhPb
    return h_cpp(TDB, w_tdbrhpb_cpp(TDB, RH, PB))


def cpair_cpp(dw):                                  # .hh PsyCpAirFnW
    return 1.00484e3 + max(dw, 1.0e-5) * 1.85895e3


def rhoair_cpp(pb, tdb, dw):                        # .hh PsyRhoAirFnPbTdbW
    return pb / (287.0 * (tdb + 273.15) * (1.0 + 1.6077687 * max(dw, 1.0e-5)))


def rho_h2o_cpp(TB):                                # .hh RhoH2O
    return 1000.1207 + 8.3215874e-04 * TB - 4.929976e-03 * TB ** 2 + 8.4791863e-06 * TB ** 3


def w_tdbh_cpp(TDB, H_):                            # .hh PsyWFnTdbH
    W = (H_ - 1.00484e3 * TDB) / (2.50094e6 + 1.85895e3 * TDB)
    return 1.0e-5 if W < 0.0 else W


def tsat_h_std_cpp(H_):
    """Psychrometrics.cc PsyTsatFnHPb at standard pressure: cases 3..6 of its nine (HH from -670 to 475 770 J/kg:
    saturation from -20 to 60 C — what a tower's exit air can be)"""
    HH = H_ + 1.78637e4

    def F6(X, A0, A1, A2, A3, A4, A5):
        return A0 + X * (A1 + X * (A2 + X * (A3 + X * (A4 + X * A5))))
    if -6.7012e2 < HH <= 2.7297e4:
        return F6(HH, -1.94224e1, 8.59061e-4, -4.4875e-9, -5.76696e-14, 7.72217e-19, 3.97894e-24)
    if 2.7297e4 < HH <= 7.5222e4:
        return F6(HH, -2.01147e1, 9.04936e-4, -6.83305e-9, 2.3261e-14, 7.27237e-20, -6.31939e-25)
    if 7.5222e4 < HH <= 1.8379e5:
        return F6(HH, -1.82124e1, 8.31683e-4, -6.16461e-9, 3.06411e-14, -8.60964e-20, 1.03003e-25)
    if 1.8379e5 < HH <= 4.7577e5:
        return F6(HH, -1.29419, 3.88538e-4, -1.30237e-9, 2.78254e-15, -3.27225e-21, 1.60969e-27)
    raise ValueError("outside the transcribed cases")


def solve_root_cpp(Eps, MaxIte, f, X_0, X_1):
    """General.cc SolveRoot, the regula falsi of its default case -> (Flag, XRes). Flag -2: no sign change (XRes = X_0);
    -1: the iteration limit."""
    SMALL = 1.e-10
    X0, X1 = X_0, X_1
    XTemp = X0
    NIte = 0
    Y0, Y1 = f(X0), f(X1)
    if Y0 * Y1 > 0:
        return -2, X0
    while True:
        DY = Y0 - Y1
        if abs(DY) < SMALL:
            DY = SMALL
        if abs(X1 - X0) < SMALL:
            break
        XTemp = (Y0 * X1 - Y1 * X0) / DY
        YTemp = f(XTemp)
        NIte += 1
        if abs(YTemp) < Eps:
            return NIte, XTemp
        if NIte > MaxIte:
            break
        if Y0 < 0.0:
            if YTemp < 0.0:
                X0, Y0 = XTemp, YTemp
            else:
                X1, Y1 = XTemp, YTemp
        else:
            if YTemp < 0.0:
                X1, Y1 = XTemp, YTemp
            else:
                X0, Y0 = XTemp, YTemp
    if NIte > MaxIte:
        return -1, XTemp
    return NIte, XTemp


# =============================================================================== layer 3: variable-speed towers
_cc = open(os.path.join(SRC, "CondenserLoopTowers.cc"), encoding="utf-8", errors="replace").read()


def coeffs_from_cpp(start, end):
    seg = _cc[_cc.index(start):_cc.index(end, _cc.index(start))]
    got = re.findall(r"vstower\.Coeff\[(\d+)\] = ([-0-9.eE]+);", seg)
    assert [int(i) for i, _ in got] == list(range(len(got)))
    lim = {k: float(v) for k, v in re.findall(r"vstower\.(M(?:in|ax)\w+) = ([-0-9.eE]+);", seg)}
    return [float(v) for _, v in got], lim


CT_C, CT_L = coeffs_from_cpp("ModelType::CoolToolsXFModel;", "ModelType::YorkCalcModel;")
YC_C, YC_L = coeffs_from_cpp("ModelType::YorkCalcModel;", "ModelType::CoolToolsUserDefined;")
check(len(CT_C) == 35 and len(YC_C) == 27 and CT_L["MaxInletAirWBTemp"] == 26.6667 and YC_L["MinInletAirWBTemp"] == -34.4
      and [float(x) for x in TW.COOLTOOLS_COEFFS] == CT_C and [float(x) for x in TW.YORKCALC_COEFFS] == YC_C,
      "tower coefficient sets: the 35 CoolTools and 27 YorkCalc coefficients in towers.py are the numbers "
      "GetTowerInput writes (read from CondenserLoopTowers.cc here, by code)")


def approach_cpp(york, Coeff, PctWaterFlow, airFlowRatioLocal, Twb, Tr):
    """calculateVariableSpeedApproach, as written"""
    if york:
        PctAirFlow = airFlowRatioLocal
        FlowFactor = PctWaterFlow / PctAirFlow
        return (Coeff[0] + Coeff[1] * Twb + Coeff[2] * Twb * Twb + Coeff[3] * Tr + Coeff[4] * Twb * Tr +
                Coeff[5] * Twb * Twb * Tr + Coeff[6] * Tr * Tr + Coeff[7] * Twb * Tr * Tr +
                Coeff[8] * Twb * Twb * Tr * Tr + Coeff[9] * FlowFactor + Coeff[10] * Twb * FlowFactor +
                Coeff[11] * Twb * Twb * FlowFactor + Coeff[12] * Tr * FlowFactor + Coeff[13] * Twb * Tr * FlowFactor +
                Coeff[14] * Twb * Twb * Tr * FlowFactor + Coeff[15] * Tr * Tr * FlowFactor +
                Coeff[16] * Twb * Tr * Tr * FlowFactor + Coeff[17] * Twb * Twb * Tr * Tr * FlowFactor +
                Coeff[18] * FlowFactor * FlowFactor + Coeff[19] * Twb * FlowFactor * FlowFactor +
                Coeff[20] * Twb * Twb * FlowFactor * FlowFactor + Coeff[21] * Tr * FlowFactor * FlowFactor +
                Coeff[22] * Twb * Tr * FlowFactor * FlowFactor + Coeff[23] * Twb * Twb * Tr * FlowFactor * FlowFactor +
                Coeff[24] * Tr * Tr * FlowFactor * FlowFactor + Coeff[25] * Twb * Tr * Tr * FlowFactor * FlowFactor +
                Coeff[26] * Twb * Twb * Tr * Tr * FlowFactor * FlowFactor)
    PctAirFlow = airFlowRatioLocal ** 3
    return (Coeff[0] + Coeff[1] * PctAirFlow + Coeff[2] * PctAirFlow * PctAirFlow +
            Coeff[3] * PctAirFlow * PctAirFlow * PctAirFlow + Coeff[4] * PctWaterFlow + Coeff[5] * PctAirFlow * PctWaterFlow +
            Coeff[6] * PctAirFlow * PctAirFlow * PctWaterFlow + Coeff[7] * PctWaterFlow * PctWaterFlow +
            Coeff[8] * PctAirFlow * PctWaterFlow * PctWaterFlow + Coeff[9] * PctWaterFlow * PctWaterFlow * PctWaterFlow +
            Coeff[10] * Twb + Coeff[11] * PctAirFlow * Twb + Coeff[12] * PctAirFlow * PctAirFlow * Twb +
            Coeff[13] * PctWaterFlow * Twb + Coeff[14] * PctAirFlow * PctWaterFlow * Twb +
            Coeff[15] * PctWaterFlow * PctWaterFlow * Twb + Coeff[16] * Twb * Twb + Coeff[17] * PctAirFlow * Twb * Twb +
            Coeff[18] * PctWaterFlow * Twb * Twb + Coeff[19] * Twb * Twb * Twb + Coeff[20] * Tr +
            Coeff[21] * PctAirFlow * Tr + Coeff[22] * PctAirFlow * PctAirFlow * Tr + Coeff[23] * PctWaterFlow * Tr +
            Coeff[24] * PctAirFlow * PctWaterFlow * Tr + Coeff[25] * PctWaterFlow * PctWaterFlow * Tr + Coeff[26] * Twb * Tr +
            Coeff[27] * PctAirFlow * Twb * Tr + Coeff[28] * PctWaterFlow * Twb * Tr + Coeff[29] * Twb * Twb * Tr +
            Coeff[30] * Tr * Tr + Coeff[31] * PctAirFlow * Tr * Tr + Coeff[32] * PctWaterFlow * Tr * Tr +
            Coeff[33] * Twb * Tr * Tr + Coeff[34] * Tr * Tr * Tr)


def check_model_bounds_cpp(york, L, Twb, Tr, Ta, WaterFlowRateRatio):
    """checkModelBounds -> TwbCapped, TrCapped, TaCapped, WaterFlowRateRatioCapped"""
    TwbCapped, TrCapped, TaCapped, WaterFlowRateRatioCapped = Twb, Tr, Ta, WaterFlowRateRatio
    if Twb < L["MinInletAirWBTemp"] or Twb > L["MaxInletAirWBTemp"]:
        if Twb < L["MinInletAirWBTemp"]:
            TwbCapped = L["MinInletAirWBTemp"]
        if Twb > L["MaxInletAirWBTemp"]:
            TwbCapped = L["MaxInletAirWBTemp"]
    if Tr < L["MinRangeTemp"] or Tr > L["MaxRangeTemp"]:
        if Tr < L["MinRangeTemp"]:
            TrCapped = L["MinRangeTemp"]
        if Tr > L["MaxRangeTemp"]:
            TrCapped = L["MaxRangeTemp"]
    if Ta < L["MinApproachTemp"] or Ta > L["MaxApproachTemp"]:
        if Ta < L["MinApproachTemp"]:
            TaCapped = L["MinApproachTemp"]
        if Ta > L["MaxApproachTemp"]:
            TaCapped = L["MaxApproachTemp"]
    if not york:
        if WaterFlowRateRatio < L["MinWaterFlowRatio"] or WaterFlowRateRatio > L["MaxWaterFlowRatio"]:
            if WaterFlowRateRatio < L["MinWaterFlowRatio"]:
                WaterFlowRateRatioCapped = L["MinWaterFlowRatio"]
            if WaterFlowRateRatio > L["MaxWaterFlowRatio"]:
                WaterFlowRateRatioCapped = L["MaxWaterFlowRatio"]
    return TwbCapped, TrCapped, TaCapped, WaterFlowRateRatioCapped


def variable_tower_outlet_cpp(york, C, L, WaterTemp, WaterFlowRateRatio, airFlowRateRatioLocal, Twb):
    """calculateVariableTowerOutletTemp (Twb, WaterFlowRateRatio: capped by the caller if applicable)"""
    VSTowerMaxRangeTemp = 22.2222
    flag, Tr = solve_root_cpp(0.0001, 500, lambda Trange: (Twb + approach_cpp(york, C, WaterFlowRateRatio,
                              airFlowRateRatioLocal, Twb, Trange) + Trange) - WaterTemp,
                              0.001, max(L["MaxRangeTemp"], VSTowerMaxRangeTemp))
    out = WaterTemp - min(Tr, L["MaxRangeTemp"])
    if flag == -2:
        out = WaterTemp - L["MaxRangeTemp"]
    return out, flag


def variable_speed_tower_cpp(york, C, L, Twin, AirWetBulb, TempSetPoint, WaterFlowRateRatio, MinimumVSAirFlowFrac,
                             FreeConvectionCapacityFraction, HighSpeedFanPower, fan_curve=None):
    """calculateVariableSpeedTower, one cell -> (OutletWaterTemp, FanCyclingRatio, airFlowRateRatio, FanPower, regime)"""
    FanPower = 0.0
    OutletWaterTemp = Twin
    FanCyclingRatio = 0.0                     # (EnergyPlus keeps the previous call's value; 0 at the start)
    Twb = AirWetBulb
    Tr = Twin - TempSetPoint
    Ta = TempSetPoint - AirWetBulb
    TwbCapped, TrCapped, TaCapped, WaterFlowRateRatioCapped = check_model_bounds_cpp(york, L, Twb, Tr, Ta, WaterFlowRateRatio)
    airFlowRateRatio = 1.0
    OutletWaterTempOFF = Twin
    OutletWaterTemp = OutletWaterTempOFF
    FreeConvectionCapFrac = FreeConvectionCapacityFraction
    OutletWaterTempON, _ = variable_tower_outlet_cpp(york, C, L, Twin, WaterFlowRateRatioCapped, airFlowRateRatio, TwbCapped)
    regime = "none"
    if OutletWaterTempON > TempSetPoint:
        FanCyclingRatio = 1.0
        airFlowRateRatio = 1.0
        FanPower = HighSpeedFanPower
        OutletWaterTemp = OutletWaterTempON
        regime = "full"
    if OutletWaterTempON < TempSetPoint:
        OutletWaterTempOFF = Twin - FreeConvectionCapFrac * (Twin - OutletWaterTempON)
        FanCyclingRatio = 0.0
        airFlowRateRatio = FreeConvectionCapFrac
        FanPower = 0.0
        OutletWaterTemp = OutletWaterTempOFF
        regime = "off"
        if OutletWaterTempOFF > TempSetPoint:
            airFlowRateRatio = MinimumVSAirFlowFrac
            OutletWaterTempMIN, _ = variable_tower_outlet_cpp(york, C, L, Twin, WaterFlowRateRatioCapped, airFlowRateRatio, TwbCapped)
            if OutletWaterTempMIN < TempSetPoint:
                if fan_curve is None:
                    FanPower = airFlowRateRatio ** 3 * HighSpeedFanPower
                else:
                    FanPower = max(0.0, HighSpeedFanPower * fan_curve(airFlowRateRatio))
                FanCyclingRatio = (OutletWaterTempOFF - TempSetPoint) / (OutletWaterTempOFF - OutletWaterTempMIN)
                FanPower *= FanCyclingRatio
                OutletWaterTemp = TempSetPoint
                airFlowRateRatio = FanCyclingRatio * MinimumVSAirFlowFrac + (1 - FanCyclingRatio) * FreeConvectionCapFrac
                regime = "cycling"
            else:
                airFlowRateRatio = 1.0
                FanCyclingRatio = 1.0
                flag, airFlowRateRatio = solve_root_cpp(
                    0.0001, 500, lambda FlowRatio: Ta - approach_cpp(york, C, WaterFlowRateRatioCapped, FlowRatio, TwbCapped, Tr),
                    MinimumVSAirFlowFrac, 1.0)
                if fan_curve is None:
                    FanPower = airFlowRateRatio ** 3 * HighSpeedFanPower
                else:
                    FanPower = max(0.0, HighSpeedFanPower * fan_curve(airFlowRateRatio))
                OutletWaterTemp = Twb + Ta
                regime = "modulating" if flag != -2 else "modulating-unsolved"
    return OutletWaterTemp, FanCyclingRatio, airFlowRateRatio, FanPower, regime


def sweep_approach():
    """templates against the C++ over a box that runs OUTSIDE every model limit -> worst relative difference"""
    rnd = random.Random(3)
    worst = 0.0
    for _ in range(1500):
        frw, fra = rnd.uniform(0.4, 1.6), rnd.uniform(0.2, 1.0)
        twb, tr = rnd.uniform(-40, 35), rnd.uniform(0.2, 25)
        for york, C, L, nm in ((False, CT_C, CT_L, "cooltools"), (True, YC_C, YC_L, "yorkcalc")):
            twc, _, _, wc = check_model_bounds_cpp(york, L, twb, tr, 5.0, frw)
            worst = max(worst,
                        rel(H.evaluate(f"ep_tower_approach_{nm}", frw, fra, twb + K, tr), approach_cpp(york, C, wc, fra, twc, tr)),
                        rel(H.evaluate(f"ep_tower_approach_{nm}_raw", frw, fra, twb + K, tr), approach_cpp(york, C, frw, fra, twb, tr)),
                        abs(H.evaluate(f"ep_tower_twbcap_{nm}", twb + K) - K - twc))
    return worst


w_app = sweep_approach()
MEASURED["approach sweep worst relative"] = w_app
check(w_app < 1e-11, f"tower approach (CoolTools, YorkCalc; capped as checkModelBounds and raw): templates = the C++ at "
                    f"6000 points inside and outside the limits (worst relative {w_app:.1e})")

# the user-defined coefficient objects as CURVES: an IDF text with other limits and scaled coefficients
_user_idf = ("CoolingTowerPerformance:CoolTools, UserCT, 2.0, 24.0, 2.0, 10.0, 2.0, 9.0, 0.8, 1.2, "
             + ", ".join(repr(c * 1.03) for c in CT_C) + ";\n"
             "CoolingTowerPerformance:YorkCalc, UserYC, -5.0, 27.0, 1.5, 20.0, 1.5, 30.0, 0.8, 1.2, 7.5, "
             + ", ".join(repr(c * 0.97) for c in YC_C) + ";\n")
_user = CV.curves_from_idf(_user_idf)
_uL = {"UserCT": {"MinInletAirWBTemp": 2.0, "MaxInletAirWBTemp": 24.0, "MinRangeTemp": 2.0, "MaxRangeTemp": 10.0,
                  "MinApproachTemp": 2.0, "MaxApproachTemp": 9.0, "MinWaterFlowRatio": 0.8, "MaxWaterFlowRatio": 1.2},
       "UserYC": {"MinInletAirWBTemp": -5.0, "MaxInletAirWBTemp": 27.0, "MinRangeTemp": 1.5, "MaxRangeTemp": 20.0,
                  "MinApproachTemp": 1.5, "MaxApproachTemp": 30.0, "MinWaterFlowRatio": 0.8, "MaxWaterFlowRatio": 1.2}}
rnd = random.Random(5)
worst = 0.0
for _ in range(800):
    frw, fra, twb, tr = rnd.uniform(0.4, 1.6), rnd.uniform(0.2, 1.0), rnd.uniform(-20, 35), rnd.uniform(0.2, 25)
    for nm, york, C, f in (("UserCT", False, CT_C, 1.03), ("UserYC", True, YC_C, 0.97)):
        twc, _, _, wc = check_model_bounds_cpp(york, _uL[nm], twb, tr, 5.0, frw)
        worst = max(worst, rel(CV.evaluate(_user[nm], frw, fra, twb, tr), approach_cpp(york, [c * f for c in C], wc, fra, twc, tr)))
check(set(_user) == {"UserCT", "UserYC"} and _user["UserYC"].get("lg_max") == "7.5" and "x_min" not in _user["UserYC"]
      and worst < 1e-9,
      f"CoolingTowerPerformance:CoolTools / :YorkCalc read from IDF text as curves: = the C++ with the object's own "
      f"limits (wet bulb capped; water flow ratio capped for CoolTools only) at 1600 points (worst {worst:.1e})")

# EnergyPlus's OWN dataset states the two built-in models as user-defined objects (datasets/PerfCurves.idf)
_ds = CV.curves_from_idf(open(os.path.join(DS, "PerfCurves.idf"), encoding="latin-1").read())
_dct, _dyc = _ds["CoolTools CrossFlow Default Tower Model"], _ds["YorkCalc Default Tower Model"]
rnd = random.Random(6)
w_ct = w_yc_in = w_yc_out = 0.0
for _ in range(600):
    frw, fra, twb, tr = rnd.uniform(0.4, 1.6), rnd.uniform(0.2, 1.0), rnd.uniform(-40, 35), rnd.uniform(0.2, 25)
    w_ct = max(w_ct, rel(CV.evaluate(_dct, frw, fra, twb, tr), H.evaluate("ep_tower_approach_cooltools", frw, fra, twb + K, tr)))
    d = rel(CV.evaluate(_dyc, frw, fra, twb, tr), H.evaluate("ep_tower_approach_yorkcalc", frw, fra, twb + K, tr))
    if twb <= 26.6667:
        w_yc_in = max(w_yc_in, d)
    else:
        w_yc_out = max(w_yc_out, d)
MEASURED["dataset tower objects vs built-in (CoolTools, YorkCalc below / above 26.6667 C)"] = (w_ct, w_yc_in, w_yc_out)
check([float(x) for x in _dct["coeffs"]] == CT_C and [float(x) for x in _dyc["coeffs"]] == YC_C and w_ct < 1e-11
      and w_yc_in < 1e-11 and _dyc["z_max"] == "26.6667" and YC_L["MaxInletAirWBTemp"] == 29.4444 and w_yc_out > 1e-4,
      f"datasets/PerfCurves.idf states both built-in models as CoolingTowerPerformance objects: read by code, the same "
      f"coefficients, the same approach (CoolTools {w_ct:.1e}; YorkCalc {w_yc_in:.1e} up to a wet bulb of 26.6667 C). "
      f"FOUND: the dataset's YorkCalc object caps the wet bulb at 26.6667 C, the code's built-in YorkCalc at 29.4444 C "
      f"— above 26.6667 C the two differ (up to {w_yc_out:.1e} relative)")

# ---- the implicit laws against what EnergyPlus iterates
def tpl_fixed_outlet(nm, L, Twin, frw, fra, twb):
    """our fixed-speed law: Twin == twbcap + approach + Tr, Tr in [0.001, max(MaxRange, 22.2222)]; where it has no
    root EnergyPlus's stated fallback (Twin - MaxRange) — in a brick that is OPEN"""
    cap = H.evaluate(f"ep_tower_twbcap_{nm}", twb + K) - K
    tr = bisect(lambda t: cap + H.evaluate(f"ep_tower_approach_{nm}", frw, fra, twb + K, t) + t - Twin,
                0.001, max(L["MaxRangeTemp"], 22.2222))
    if tr is None:
        return Twin - L["MaxRangeTemp"], False
    return Twin - min(tr, L["MaxRangeTemp"]), True


# a fan power ratio curve (the one EnergyPlus's own tower tests use): Curve:Cubic 0.02 + 0.98 x^3 on 0.2..1, output 0..1
FAN_IDF = "Curve:Cubic, VSTowerFanPowerFFF, 0.02, 0.0, 0.0, 0.98, 0.2, 1.0, 0.0, 1.0, Dimensionless, Dimensionless;"
FAN = CV.curves_from_idf(FAN_IDF)["VSTowerFanPowerFFF"]


def fan_cpp(x):
    """Curve::value of that cubic by hand: the input clamped, then the output"""
    x = max(min(x, 1.0), 0.2)
    return min(max(0.02 + x * (0.0 + x * (0.0 + x * 0.98)), 0.0), 1.0)


def tpl_vs_tower(nm, L, Twin, twb, tset, frw, afr_min, fc, pdes, fan=None):
    ton, _ = tpl_fixed_outlet(nm, L, Twin, frw, 1.0, twb)
    tmin, _ = tpl_fixed_outlet(nm, L, Twin, frw, afr_min, twb)
    afr = bisect(lambda a: (tset - twb) - H.evaluate(f"ep_tower_approach_{nm}", frw, a, twb + K, Twin - tset), afr_min, 1.0)
    solved = afr is not None
    if afr is None:
        afr = afr_min                               # SolveRoot's first bound
    a = [x + K for x in (ton, tmin, Twin, tset)]
    return (H.evaluate("ep_tower_vs_tout", a[0], a[2], a[3], fc) - K,
            H.evaluate("ep_tower_vs_cycling", a[0], a[1], a[2], a[3], fc),
            H.evaluate("ep_tower_vs_afr", a[0], a[1], a[2], a[3], fc, afr_min, afr),
            H.evaluate("ep_tower_vs_power", a[0], a[1], a[2], a[3], fc,
                       CV.evaluate(fan, afr_min) if fan else H.evaluate("ep_tower_fpr_cube", afr_min),
                       CV.evaluate(fan, afr) if fan else H.evaluate("ep_tower_fpr_cube", afr), pdes), solved)


def sweep_vs_tower(n=400):
    rnd = random.Random(11)
    worst = {"Tout": 0.0, "cycling": 0.0, "afr": 0.0, "power": 0.0}
    regimes = {}
    skipped = 0
    for _ in range(n):
        york = rnd.random() < 0.5
        nm, C, L = ("yorkcalc", YC_C, YC_L) if york else ("cooltools", CT_C, CT_L)
        Twin, twb = rnd.uniform(24, 40), rnd.uniform(-5, 30)
        tset = rnd.uniform(max(twb + 1.0, 15), Twin - 0.5) if Twin - 0.5 > max(twb + 1.0, 15) else Twin - 0.5
        frw, afr_min, fc = rnd.uniform(0.6, 1.4), rnd.uniform(0.2, 0.5), rnd.uniform(0.0, 0.2)
        curve = rnd.random() < 0.5                  # half with the fan power curve, half with the default cube law
        e = variable_speed_tower_cpp(york, C, L, Twin, twb, tset, frw, afr_min, fc, 1000.0, fan_cpp if curve else None)
        t = tpl_vs_tower(nm, L, Twin, twb, tset, frw, afr_min, fc, 1000.0, FAN if curve else None)
        regimes[e[4]] = regimes.get(e[4], 0) + 1
        if e[4] == "modulating-unsolved" or (e[4] == "modulating" and not t[4]):
            skipped += 1                            # no sign change: EnergyPlus keeps the minimum ratio; a brick is OPEN
            continue
        worst["Tout"] = max(worst["Tout"], abs(e[0] - t[0]))
        worst["cycling"] = max(worst["cycling"], abs(e[1] - t[1]))
        worst["afr"] = max(worst["afr"], abs(e[2] - t[2]))
        worst["power"] = max(worst["power"], abs(e[3] - t[3]))
    return worst, regimes, skipped


t0 = time.time()
w_vs, regimes, skipped = sweep_vs_tower()
MEASURED["VS tower sweep"] = (w_vs, regimes, skipped, round(time.time() - t0, 1))
check(w_vs["Tout"] < 1e-3 and w_vs["cycling"] < 2e-3 and w_vs["afr"] < 2e-3 and w_vs["power"] < 5.0
      and all(regimes.get(r, 0) > 5 for r in ("full", "off", "cycling", "modulating")),
      f"variable-speed tower: EnergyPlus's own sequence (SolveRoot to 1e-4, calculateVariableSpeedTower transcribed) "
      f"= our implicit laws' roots through ep_tower_vs_* over 400 operating points in every regime {regimes}: worst "
      f"outlet {w_vs['Tout']:.1e} K, cycling ratio {w_vs['cycling']:.1e}, air flow ratio {w_vs['afr']:.1e}, fan power "
      f"{w_vs['power']:.2f} W of 1000 (cube law and a fan power curve; {skipped} points where the air-flow solve has no sign change skipped)")


# =============================================================================== layer 3: the UA (Merkel) tower
def simple_tower_pass_cpp(UAdesign, MdotCpWater, AirMassFlowRate, CpAir, InletWaterTemp, InletAirWetBulb, AirPress,
                          OutletAirWetBulb):
    """one pass of the loop of calculateSimpleTowerOutletTemp -> (QactualLocal, AirCapacity)"""
    InletAirEnthalpy = h_tdbrhpb_cpp(InletAirWetBulb, 1.0, AirPress)
    OutletAirEnthalpy = h_tdbrhpb_cpp(OutletAirWetBulb, 1.0, AirPress)
    CpAirside = (OutletAirEnthalpy - InletAirEnthalpy) / (OutletAirWetBulb - InletAirWetBulb)
    AirCapacity = AirMassFlowRate * CpAirside
    CapacityRatioMin = min(AirCapacity, MdotCpWater)
    CapacityRatioMax = max(AirCapacity, MdotCpWater)
    CapacityRatio = CapacityRatioMin / CapacityRatioMax
    UAactual = UAdesign * CpAirside / CpAir
    NumTransferUnits = UAactual / CapacityRatioMin
    if CapacityRatio <= 0.995:
        Exponent = NumTransferUnits * (1.0 - CapacityRatio)
        if Exponent >= 700.0:
            effectiveness = NumTransferUnits / (1.0 + NumTransferUnits)
        else:
            effectiveness = ((1.0 - math.exp(-1.0 * NumTransferUnits * (1.0 - CapacityRatio))) /
                             (1.0 - CapacityRatio * math.exp(-1.0 * NumTransferUnits * (1.0 - CapacityRatio))))
    else:
        effectiveness = NumTransferUnits / (1.0 + NumTransferUnits)
    return effectiveness * CapacityRatioMin * (InletWaterTemp - InletAirWetBulb), AirCapacity


def simple_tower_cpp(UAdesign, waterMassFlowRate, CpWater, AirFlowRate, WaterTemp, AirTemp, AirWetBulb, AirPress, AirHumRat):
    """calculateSimpleTowerOutletTemp -> (OutletWaterTemp, OutletAirWetBulb, iterations)"""
    QactualLocal = 0.0
    InletWaterTemp = WaterTemp
    OutletWaterTempLocal = InletWaterTemp
    InletAirWetBulb = AirWetBulb
    if UAdesign == 0.0:
        return OutletWaterTempLocal, None, 0
    AirDensity = rhoair_cpp(AirPress, AirTemp, AirHumRat)
    AirMassFlowRate = AirFlowRate * AirDensity
    CpAir = cpair_cpp(AirHumRat)
    OutletAirWetBulb = InletAirWetBulb + 6.0
    if waterMassFlowRate <= 0.0:
        return InletWaterTemp, None, 0
    MdotCpWater = waterMassFlowRate * CpWater
    Iter, WetBulbError, DeltaTwb = 0, 1.0, 1.0
    while WetBulbError > 0.00001 and Iter <= 50 and DeltaTwb > 0.001:
        Iter += 1
        QactualLocal, AirCapacity = simple_tower_pass_cpp(UAdesign, MdotCpWater, AirMassFlowRate, CpAir, InletWaterTemp,
                                                          InletAirWetBulb, AirPress, OutletAirWetBulb)
        OutletAirWetBulbLast = OutletAirWetBulb
        OutletAirWetBulb = InletAirWetBulb + QactualLocal / AirCapacity
        DeltaTwb = abs(OutletAirWetBulb - InletAirWetBulb)
        WetBulbError = abs((OutletAirWetBulb - OutletAirWetBulbLast) / (OutletAirWetBulbLast + 273.15))
    if QactualLocal >= 0.0:
        OutletWaterTempLocal = InletWaterTemp - QactualLocal / MdotCpWater
    else:
        OutletWaterTempLocal = InletWaterTemp
    return OutletWaterTempLocal, OutletAirWetBulb, Iter


def tpl_q_ua(UA, MCW, MA, twb, x, P, W, twin):
    cps = H.evaluate("ep_tower_cpairside", twb + K, x + K, P)
    return H.evaluate("ep_tower_q_ua", UA, MCW, MA, cps, H.evaluate("ep_cpair", W), twin + K, twb + K)


def tpl_simple_tower(UA, MCW, MA, twb, P, W, twin):
    """the fixed point as our implicit law: ep_tower_q_air(X) == ep_tower_q_ua(X), X in (Twb, Twin]"""
    x = bisect(lambda x: H.evaluate("ep_tower_q_air", MA, twb + K, x + K, P) - tpl_q_ua(UA, MCW, MA, twb, x, P, W, twin),
               twb + 1e-6, twin)
    if x is None:
        return None, None
    return H.evaluate("ep_tower_tout", twin + K, H.evaluate("ep_tower_q_air", MA, twb + K, x + K, P), MCW) - K, x


def sweep_simple_tower(n=300):
    rnd = random.Random(17)
    w_pass, w_out, branches = 0.0, 0.0, set()
    for i in range(n):
        twb = rnd.uniform(5, 28)
        tdb = twb + rnd.uniform(0, 12)
        twin = twb + rnd.uniform(3, 18)
        P = rnd.choice([101325.0, 95000.0, 84000.0])
        W = w_tdbtwbpb_cpp(tdb, twb, P)
        mw, cpw, vair = rnd.uniform(1, 30), rnd.uniform(4150, 4200), rnd.uniform(1, 40)
        UA = 10 ** rnd.uniform(2, 5) if i % 25 else 10 ** rnd.uniform(8, 9)      # every 25th: the Exponent >= 700 branch
        ma = vair * rhoair_cpp(P, tdb, W)
        check_ma = H.evaluate("ep_rhoair", P, tdb + K, W) * vair
        if i % 7 == 0:                                                           # the capacity-ratio > 0.995 branch
            x0 = twb + 4.0
            cps = (h_tdbrhpb_cpp(x0, 1.0, P) - h_tdbrhpb_cpp(twb, 1.0, P)) / (x0 - twb)
            mw = ma * cps / cpw * rnd.uniform(0.996, 1.004)
        for x in (twb + 0.5, twb + 4.0, twb + 6.0, twin):
            q, aircap = simple_tower_pass_cpp(UA, mw * cpw, ma, cpair_cpp(W), twin, twb, P, x)
            cr = min(aircap, mw * cpw) / max(aircap, mw * cpw)
            ntu = UA * (aircap / ma) / cpair_cpp(W) / min(aircap, mw * cpw)
            branches.add("cr>0.995" if cr > 0.995 else ("exp>=700" if ntu * (1 - cr) >= 700 else "normal"))
            branches.add("air min" if aircap < mw * cpw else "water min")
            w_pass = max(w_pass, rel(tpl_q_ua(UA, mw * cpw, check_ma, twb, x, P, W, twin), q))
        e_out, e_x, _ = simple_tower_cpp(UA, mw, cpw, vair, twin, tdb, twb, P, W)
        t_out, _ = tpl_simple_tower(UA, mw * cpw, check_ma, twb, P, W, twin)
        w_out = max(w_out, abs(e_out - t_out) if t_out is not None else 99.0)
    return w_pass, w_out, branches


t0 = time.time()
w_pass, w_out, branches = sweep_simple_tower()
MEASURED["UA tower sweep"] = (w_pass, w_out, sorted(branches), round(time.time() - t0, 1))
check(w_pass < 1e-9 and branches == {"cr>0.995", "exp>=700", "normal", "air min", "water min"},
      f"UA tower, one pass of calculateSimpleTowerOutletTemp (effectiveness-NTU, both capacity sides, the ratio > 0.995 "
      f"and the exponent >= 700 branches {sorted(branches)}): templates = the C++ at 1200 points (worst relative {w_pass:.1e})")
check(w_out < 0.02,
      f"UA tower outlet: EnergyPlus's iteration (it stops when the exit wet bulb moves < 1e-5 of its absolute value) "
      f"against the root of our implicit law, 300 towers: worst {w_out:.1e} K (the iteration's own stopping error)")
worst = max(rel(H.evaluate("ep_hsat", t + K, p), h_tdbrhpb_cpp(t, 1.0, p)) for t in range(-30, 70, 3) for p in (101325.0, 70000.0, 1500.0))
worst = max(worst, max(rel(H.evaluate("ep_hsat", t + K, p), H.evaluate("ep_h_tdbrhpb", t + K, 1.0, p))
                       for t in range(-30, 70, 3) for p in (101325.0, 70000.0, 1500.0)))
worst = max(worst, max(rel(H.evaluate("ep_rhoair", p, t + K, w), rhoair_cpp(p, t, w)) for t in (-10, 20, 40)
                       for p in (101325.0, 80000.0) for w in (0, 0.01)),
            max(rel(H.evaluate("ep_rho_h2o", t + K), rho_h2o_cpp(t)) for t in (0, 5.05, 20, 60, 99)))
check(worst < 1e-12, f"ep_hsat = PsyHFnTdbRhPb(T, 1, Pb) by hand and = layer 1's ep_h_tdbrhpb; ep_rhoair = "
                     f"PsyRhoAirFnPbTdbW; ep_rho_h2o = RhoH2O (worst {worst:.1e})")


# ---- fan control of the single- and two-speed towers (one cell, FanCycling)
def single_speed_cpp(Toff, Ton, TempSetPoint, FanPowerOn, Twin):
    FanPower, OutletWaterTemp = 0.0, Toff
    if Toff > TempSetPoint:
        OutletWaterTemp = Ton
        if OutletWaterTemp <= TempSetPoint:
            FanModeFrac = (TempSetPoint - Toff) / (OutletWaterTemp - Toff)
            FanPower = FanModeFrac * FanPowerOn
            OutletWaterTemp = TempSetPoint
        else:
            FanPower = FanPowerOn
    return OutletWaterTemp, FanPower


def two_speed_cpp(Toff, T1, T2, TempSetPoint, FanPowerLow, FanPowerHigh):
    FanPower, OutletWaterTemp = 0.0, Toff
    if Toff > TempSetPoint:
        if T1 <= TempSetPoint:
            FanModeFrac = (TempSetPoint - Toff) / (T1 - Toff)
            FanPower = FanModeFrac * FanPowerLow
            OutletWaterTemp = TempSetPoint
        else:
            if T2 <= TempSetPoint:
                FanModeFrac = (TempSetPoint - T1) / (T2 - T1)
                FanPower = FanModeFrac * FanPowerHigh + (1.0 - FanModeFrac) * FanPowerLow
                OutletWaterTemp = TempSetPoint
            else:
                OutletWaterTemp = T2
                FanPower = FanPowerHigh
    return OutletWaterTemp, FanPower


def sweep_stage_control():
    rnd = random.Random(23)
    worst = 0.0
    for _ in range(2000):
        twin = rnd.uniform(25, 40)
        toff = twin - rnd.uniform(0, 2)
        t1 = toff - rnd.uniform(0.1, 5)
        t2 = t1 - rnd.uniform(0.1, 5)
        tset = rnd.uniform(t2 - 2, twin + 1)
        e1 = single_speed_cpp(toff, t2, tset, 1500.0, twin)
        e2 = two_speed_cpp(toff, t1, t2, tset, 400.0, 1500.0)
        worst = max(worst, abs(H.evaluate("ep_tower_ss_tout", toff + K, t2 + K, tset + K) - K - e1[0]),
                    abs(H.evaluate("ep_tower_ss_power", toff + K, t2 + K, tset + K, 1500.0) - e1[1]),
                    abs(H.evaluate("ep_tower_ts_tout", toff + K, t1 + K, t2 + K, tset + K) - K - e2[0]),
                    abs(H.evaluate("ep_tower_ts_power", toff + K, t1 + K, t2 + K, tset + K, 400.0, 1500.0) - e2[1]))
    return worst


w_st = sweep_stage_control()
check(w_st < 1e-9, f"single- and two-speed fan control (fan cycling between the stages): templates = "
                   f"calculateSingleSpeedTower / calculateTwoSpeedTower by hand at 2000 points (worst {w_st:.1e})")


# =============================================================================== layer 3: water use
def water_usage_cpp(mode, AirPress, AirTemp, AirHumRat, AirWetBulb, airFlowRateRatio, HighSpeedAirFlowRate, Qactual,
                    rho, UserEvapLossFactor, InletWaterTemp, OutletWaterTemp, WaterMassFlowRate, DesignWaterFlowRate,
                    DriftLossFraction, ConcentrationRatio):
    """calculateWaterUsage, one cell, blowdown by concentration ratio -> (EvapVdot, driftVdot, BlowDownVdot, makeUpVdot);
    rho = the loop fluid's density at the temperature EnergyPlus asks it for (an input: FluidProperties is not ported)"""
    EvapVdot = 0.0
    if mode == "MoistTheory":
        AirDensity = rhoair_cpp(AirPress, AirTemp, AirHumRat)
        AirMassFlowRate = airFlowRateRatio * HighSpeedAirFlowRate * AirDensity
        InletAirEnthalpy = h_tdbrhpb_cpp(AirWetBulb, 1.0, AirPress)
        if AirMassFlowRate > 0.0:
            OutletAirEnthalpy = InletAirEnthalpy + Qactual / AirMassFlowRate
            OutletAirTSat = tsat_h_std_cpp(OutletAirEnthalpy)
            OutletAirHumRatSat = w_tdbh_cpp(OutletAirTSat, OutletAirEnthalpy)
            InSpecificHumRat = AirHumRat / (1 + AirHumRat)
            OutSpecificHumRat = OutletAirHumRatSat / (1 + OutletAirHumRatSat)
            EvapVdot = (AirMassFlowRate * (OutSpecificHumRat - InSpecificHumRat)) / rho
            if EvapVdot < 0.0:
                EvapVdot = 0.0
        else:
            EvapVdot = 0.0
    elif mode == "UserFactor":
        EvapVdot = UserEvapLossFactor * (InletWaterTemp - OutletWaterTemp) * (WaterMassFlowRate / rho)
        if EvapVdot < 0.0:
            EvapVdot = 0.0
    driftVdot = DesignWaterFlowRate * DriftLossFraction * airFlowRateRatio
    if ConcentrationRatio > 2.0:
        BlowDownVdot = EvapVdot / (ConcentrationRatio - 1) - driftVdot
    else:
        BlowDownVdot = EvapVdot - driftVdot
    if BlowDownVdot < 0.0:
        BlowDownVdot = 0.0
    return EvapVdot, driftVdot, BlowDownVdot, EvapVdot + driftVdot + BlowDownVdot


def tpl_water(mode, P, tdb, W, twb, afr, vair, Q, rho, F, twin, tout, mw, vdes, df, cr):
    """the chain of towers.water_use_laws evaluated law by law"""
    if mode == "MoistTheory":
        ma = afr * vair * H.evaluate("ep_rhoair", P, tdb + K, W)
        h_out = H.evaluate("ep_hsat", twb + K, P) + Q / ma
        tsat = H.evaluate("ep_tsat_h_std", h_out)
        wout = H.evaluate("ep_w_tdbh", tsat, h_out)
        evap = H.evaluate("ep_tower_evap_satexit", ma, W, wout, rho)
    else:
        evap = H.evaluate("ep_tower_evap_lossfactor", F, twin + K, tout + K, mw, rho)
    drift = H.evaluate("ep_tower_drift", vdes, df, afr)
    blow = H.evaluate("ep_tower_blowdown", evap, drift, cr)
    return evap, drift, blow, evap + drift + blow


def sweep_water():
    rnd = random.Random(29)
    worst, seen = 0.0, set()
    for i in range(1500):
        P = 101325.0 * rnd.uniform(0.992, 1.008)             # within 1 % of 101 330 Pa: EnergyPlus uses its fits alone
        twb = rnd.uniform(5, 27)
        tdb = twb + rnd.uniform(0, 12)
        W = w_tdbtwbpb_cpp(tdb, twb, P)
        afr, vair = rnd.uniform(0.2, 1.0), rnd.uniform(5, 40)
        Q = rnd.uniform(-2e4, 6e5) if i % 9 == 0 else rnd.uniform(2e4, 6e5)
        twin = rnd.uniform(25, 40)
        tout = twin - rnd.uniform(-1, 8)
        mw = rnd.uniform(2, 40)
        cr = rnd.choice([1.5, 2.0, 2.0001, 3.0, 5.0, 40.0, 4000.0])
        args = (P, tdb, W, twb, afr, vair, Q, rnd.uniform(985, 1000), rnd.uniform(0.001, 0.3), twin, tout, mw,
                rnd.uniform(0.002, 0.05), rnd.choice([0.00008, 0.002, 0.2]), cr)
        for mode in ("MoistTheory", "UserFactor"):
            e = water_usage_cpp(mode, args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7], args[8],
                                args[9], args[10], args[11], args[12], args[13], args[14])
            t = tpl_water(mode, *args)
            seen.add((mode, "evap0" if e[0] == 0 else "evap+", "cr>2" if cr > 2 else "cr<=2", "blow0" if e[2] == 0 else "blow+"))
            worst = max(worst, max(abs(a - b) / max(abs(a), 1e-9) for a, b in zip(e, t)))
    return worst, seen


w_wat, seen = sweep_water()
MEASURED["water sweep worst"] = w_wat
check(w_wat < 1e-9 and len(seen) >= 10,
      f"water use (evaporation by saturated exit and by loss factor, drift, blowdown by concentration ratio above and "
      f"at/below 2, makeup): the chain of templates = calculateWaterUsage by hand at 3000 points, {len(seen)} "
      f"combinations of branches (worst relative {w_wat:.1e})")
_q, _l = TW.water_use_laws("SaturatedExit")
_q2, _l2 = TW.water_use_laws("LossFactor")
check(len(_l) == 7 and len(_l2) == 4 and all(H.expand(x["zfl"].split("==")[1])[0] for x in _l + _l2),
      "water_use_laws: the saturated-exit chain (7 laws) and the loss-factor chain (4) read by the library")


# =============================================================================== layer 4: chillers
def curve_cpp(spec, *v):
    """Curve::value by hand (CurveManager.cc): clamp inputs, formula, clamp output — the types chillers use"""
    t, c = spec["type"], [float(x) for x in spec["coeffs"]]
    lim = ("x", "y", "z")
    v = [max(min(x, float(spec.get(f"{lim[j]}_max", 1e300))), float(spec.get(f"{lim[j]}_min", -1e300))) for j, x in enumerate(v)]
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
    else:
        raise ValueError(t)
    if "out_min" in spec:
        val = max(val, float(spec["out_min"]))
    if "out_max" in spec:
        val = min(val, float(spec["out_max"]))
    return val


SMALL_LOAD = 1.0          # HVAC::SmallLoad — outside the ported files; see chillers.py


def eir_calculate_cpp(sp, MyLoad, EvapOutletTempSetPoint, condInletTemp, FalsiCondOutTemp=None, CondMassFlowRate=None,
                      CpCond=None):
    """ElectricEIRChillerSpecs::calculate (FalsiCondOutTemp None) / ReformulatedEIRChillerSpecs::calculate, the path of
    a running chiller whose load is what the evaporator asks for (QEvaporator = |MyLoad|, then its cuts)
    -> dict; MyLoad < 0 as EnergyPlus passes it"""
    c = sp["curves"]
    RefCap, RefCOP = float(sp["RefCap"]), float(sp["COP"])
    MinPartLoadRat, MaxPartLoadRat, MinUnloadRat = float(sp["MinPLR"]), float(sp["MaxPLR"]), float(sp["MinUnl"])
    CompPowerToCondenserFrac = float(sp["Fcond"])
    reform = FalsiCondOutTemp is not None
    FRAC = 1.0
    AvgCondSinkTemp = FalsiCondOutTemp if reform else condInletTemp
    ChillerCapFT = curve_cpp(c["CAPFT"], EvapOutletTempSetPoint, AvgCondSinkTemp)
    if ChillerCapFT < 0:
        ChillerCapFT = 0.0
    AvailChillerCap = RefCap * ChillerCapFT
    QEvaporator = abs(MyLoad)
    EvapOutletTemp = EvapOutletTempSetPoint
    if QEvaporator > AvailChillerCap * MaxPartLoadRat:
        QEvaporator = AvailChillerCap * MaxPartLoadRat
    if AvailChillerCap > 0.0:
        PartLoadRat = max(0.0, min(QEvaporator / AvailChillerCap, MaxPartLoadRat))
    else:
        PartLoadRat = 0.0
    if PartLoadRat < MinPartLoadRat:
        FRAC = min(1.0, PartLoadRat / MinPartLoadRat)
    if AvailChillerCap > 0.0:
        PartLoadRat = max(PartLoadRat, MinUnloadRat)
    else:
        PartLoadRat = 0.0
    ChillerFalseLoadRate = (AvailChillerCap * PartLoadRat * FRAC) - QEvaporator
    if ChillerFalseLoadRate < SMALL_LOAD:
        ChillerFalseLoadRate = 0.0
    if reform:
        ChillerEIRFT = max(0.0, curve_cpp(c["EIRFT"], EvapOutletTemp, AvgCondSinkTemp))
        ChillerEIRFPLR = max(0.0, curve_cpp(c["EIRFPLR"], AvgCondSinkTemp, PartLoadRat))
        if RefCOP <= 0:
            RefCOP = 5.5
    else:
        ChillerEIRFT = curve_cpp(c["EIRFT"], EvapOutletTemp, AvgCondSinkTemp)
        if ChillerEIRFT < 0.0:
            ChillerEIRFT = 0.0
        ChillerEIRFPLR = curve_cpp(c["EIRFPLR"], PartLoadRat)
        if ChillerEIRFPLR < 0.0:
            ChillerEIRFPLR = 0.0
    Power = (AvailChillerCap / RefCOP) * ChillerEIRFPLR * ChillerEIRFT * FRAC
    QCondenser = Power * CompPowerToCondenserFrac + QEvaporator + ChillerFalseLoadRate
    out = {"Avail": AvailChillerCap, "Qevap": QEvaporator, "PLR": PartLoadRat, "FRAC": FRAC,
           "Qfalse": ChillerFalseLoadRate, "Power": Power, "Qcond": QCondenser}
    if CondMassFlowRate:
        out["CondOutletTemp"] = QCondenser / CondMassFlowRate / CpCond + condInletTemp
    return out


def reform_control_cpp(sp, MyLoad, Tset, condInletTemp, CondMassFlowRate, CpCond):
    """ReformulatedEIRChillerSpecs::control -> (result of the final calculate, how)"""
    c = sp["curves"]
    Tmin = min(float(c["CAPFT"]["y_min"]), float(c["EIRFT"]["y_min"]), float(c["EIRFPLR"]["x_min"]))
    Tmax = max(float(c["CAPFT"]["y_max"]), float(c["EIRFT"]["y_max"]), float(c["EIRFPLR"]["x_max"]))
    CondTempMin = eir_calculate_cpp(sp, MyLoad, Tset, condInletTemp, Tmin, CondMassFlowRate, CpCond)["CondOutletTemp"]
    CondTempMax = eir_calculate_cpp(sp, MyLoad, Tset, condInletTemp, Tmax, CondMassFlowRate, CpCond)["CondOutletTemp"]
    if CondTempMin > Tmin and CondTempMax < Tmax:
        flag, t = solve_root_cpp(0.0001, 500, lambda x: x - eir_calculate_cpp(sp, MyLoad, Tset, condInletTemp, x,
                                 CondMassFlowRate, CpCond)["CondOutletTemp"], Tmin, Tmax)
        if flag == -2:
            return eir_calculate_cpp(sp, MyLoad, Tset, condInletTemp, condInletTemp, CondMassFlowRate, CpCond), "inlet"
        r = eir_calculate_cpp(sp, MyLoad, Tset, condInletTemp, t, CondMassFlowRate, CpCond)
        return r, "root"
    r = eir_calculate_cpp(sp, MyLoad, Tset, condInletTemp, (CondTempMin + CondTempMax) / 2.0, CondMassFlowRate, CpCond)
    r = eir_calculate_cpp(sp, MyLoad, Tset, condInletTemp, r["CondOutletTemp"], CondMassFlowRate, CpCond)
    return r, "substitution"


def ev_law(text, curves, env, trees):
    """a law's right-hand side evaluated in double precision as the stand will read it: curves, then the library
    (`trees`: the syntax trees of ONE chiller's laws, kept by the caller — a sweep evaluates a law hundreds of times)"""
    import ast
    tree = trees.get(text)
    if tree is None or tree[0] != tuple(v["expr"] for v in H.LIBRARY.values()):
        t = H.expand(CV.expand_text(text, curves))[0]
        tree = (tuple(v["expr"] for v in H.LIBRARY.values()),
                ast.parse(re.sub(r"(?<![\w.])if\s*\(", "__if__(", t), mode="eval").body)
        trees[text] = tree
    e = dict(env)
    e.update({c: 1.0 for c in H.UNIT_CONSTANTS})
    return H._ev(tree[1], e)


_chillers_idf = open(os.path.join(DS, "Chillers.idf"), encoding="latin-1").read()
_objs = CV.idf_objects(_chillers_idf)
EIR_NAMES = [f[0] for c, f in _objs if c.lower() == "chiller:electric:eir"]
REF_NAMES = [f[0] for c, f in _objs if c.lower() == "chiller:electric:reformulatedeir"]


autosized = set()


def sweep_eir(names, per=6):
    rnd = random.Random(31)
    worst, n, seen = 0.0, 0, set()
    for nm in names:
        sp = CH.chiller_spec_from_idf(_chillers_idf, nm)
        parts = CH.chiller_parts(sp)
        rhs = {law["zfl"].split(" == ")[0]: law["zfl"].split(" == ", 1)[1] for law in parts["laws"]}
        cap = sp["curves"]["CAPFT"]
        trees = {}
        if sp["RefCap"] is None:                   # autosized in the dataset: the brick's to state
            autosized.add(nm)
            sp["RefCap"] = "500000"
        for _ in range(per):
            tset = rnd.uniform(float(cap["x_min"]) - 2, float(cap["x_max"]) + 2)
            tcond = rnd.uniform(float(cap["y_min"]) - 4, float(cap["y_max"]) + 4)
            load = float(sp["RefCap"]) * rnd.choice([rnd.uniform(0, 0.12), rnd.uniform(0.1, 1.0), rnd.uniform(0.9, 1.4)])
            e = eir_calculate_cpp(sp, -load, tset, tcond)
            env = {"RefCap": float(sp["RefCap"]), "COP": float(sp["COP"]), "MinPLR": float(sp["MinPLR"]),
                   "MaxPLR": float(sp["MaxPLR"]), "MinUnl": float(sp["MinUnl"]), "Fcond": float(sp["Fcond"]),
                   "SmallLoad": 1.0, "Load": load, "Tchw": tset + K, "Tcond": tcond + K}
            for k in ("Avail", "Qevap", "PLR", "FRAC", "Qfalse", "Power", "Qcond"):
                worst = max(worst, abs(ev_law(rhs[k], parts["curves"], env, trees) - e[k]) / max(abs(e[k]), 1.0))
            seen.add(("cycling" if e["FRAC"] < 1 else "on", "false" if e["Qfalse"] > 0 else "nofalse",
                      "capped" if e["Qevap"] < load else "met"))
            n += 1
    return worst, n, seen


t0 = time.time()
w_eir, n_eir, seen_eir = sweep_eir(EIR_NAMES)
MEASURED["EIR sweep"] = (w_eir, n_eir, sorted(seen_eir), round(time.time() - t0, 1))
check(len(EIR_NAMES) == 162 and w_eir < 1e-9 and len(seen_eir) >= 5,
      f"Chiller:Electric:EIR: all {len(EIR_NAMES)} chillers of datasets/Chillers.idf built by chiller_from_idf; the laws "
      f"(Avail, Qevap, PLR, FRAC, Qfalse, Power, Qcond) = ElectricEIRChillerSpecs::calculate by hand at {n_eir} points "
      f"inside and outside the curve limits, loads 0..1.4 of reference: cycling, false loading, capacity-limited "
      f"{sorted(seen_eir)} (worst relative {w_eir:.1e})")


def sweep_reform(names, per=3):
    rnd = random.Random(37)
    worst_t, worst_p, how, n = 0.0, 0.0, {}, 0
    for nm in names:
        sp = CH.chiller_spec_from_idf(_chillers_idf, nm)
        parts = CH.chiller_parts(sp)
        laws = {law["zfl"].split(" == ")[0]: law["zfl"].split(" == ", 1)[1] for law in parts["laws"]}
        lo, hi = [float(x) for x in parts["quantities"]["Tco"]["search"]]
        if sp["RefCap"] is None:
            autosized.add(nm)
            continue
        mc = float(sp["Vcond_ref"]) * 995.0
        trees = {}
        for _ in range(per):
            tset = rnd.uniform(float(sp["curves"]["CAPFT"]["x_min"]), float(sp["curves"]["CAPFT"]["x_max"]))
            tcin = float(sp["Tref_cond"]) - rnd.uniform(2, 9)
            load = float(sp["RefCap"]) * rnd.uniform(0.05, 1.1)
            e, h = reform_control_cpp(sp, -load, tset, tcin, mc, 4180.0)
            how[h] = how.get(h, 0) + 1
            if h != "root":
                continue
            env = {"RefCap": float(sp["RefCap"]), "COP": float(sp["COP"]), "MinPLR": float(sp["MinPLR"]),
                   "MaxPLR": float(sp["MaxPLR"]), "MinUnl": float(sp["MinUnl"]), "Fcond": float(sp["Fcond"]),
                   "SmallLoad": 1.0, "Load": load, "Tchw": tset + K, "Tcin": tcin + K, "Mcond": mc, "CpCond": 4180.0}
            tco = bisect(lambda x: x - ev_law(laws["Tco"], parts["curves"], dict(env, Tco=x), trees), lo, hi, it=50)
            if tco is None:
                worst_t = 99.0
                continue
            worst_t = max(worst_t, abs(tco - K - e["CondOutletTemp"]))
            worst_p = max(worst_p, rel(ev_law(laws["Power"], parts["curves"], dict(env, Tco=tco), trees), e["Power"]))
            n += 1
    return worst_t, worst_p, how, n


t0 = time.time()
w_rt, w_rp, how_r, n_r = sweep_reform(REF_NAMES)
MEASURED["Reformulated sweep"] = (w_rt, w_rp, how_r, n_r, round(time.time() - t0, 1))
check(len(REF_NAMES) == 161 and n_r > 300 and w_rt < 1e-3 and w_rp < 1e-3,
      f"Chiller:Electric:ReformulatedEIR: all {len(REF_NAMES)} of the dataset; the leaving condenser temperature "
      f"EnergyPlus iterates to (control: SolveRoot to 1e-4 K) = the root of our implicit law at {n_r} points "
      f"(worst {w_rt:.1e} K, power {w_rp:.1e} relative); how EnergyPlus ended over the sweep: {how_r}")

# the small templates around them
rnd = random.Random(41)
worst = 0.0
for _ in range(500):
    load, avail, mx = rnd.uniform(0, 5e5), rnd.uniform(1e5, 5e5), rnd.uniform(1.0, 1.2)
    me, cp, tin, tlow = rnd.uniform(5, 30), 4190.0, rnd.uniform(6, 16), rnd.uniform(2, 9)
    q = min(load, avail * mx)                                    # the order of the C++: |load|, the low limit, the cut
    q_lim = load
    if tin - q_lim / me / cp < tlow:
        q_lim = me * cp * (tin - tlow) if tin - tlow > 0 else 0.0
    if q_lim > avail * mx:
        q_lim = avail * mx
    m, mmax, mr = rnd.uniform(0, 30), 20.0, rnd.uniform(0, 0.5)
    worst = max(worst, rel(H.evaluate("ep_chiller_qevap", load, avail, mx), q),
                abs(H.evaluate("ep_chiller_qevap_lim", load, avail, mx, me, cp, tin + K, tlow + K) - q_lim) / 1e5,
                abs(H.evaluate("ep_chiller_condflow", m, mmax, mr) - max(min(m, mmax), mr * mmax)),
                abs(H.evaluate("ep_chiller_tcondout", q, me, cp, tin + K) - K - (q / me / cp + tin)))
check(worst < 1e-9 and H.evaluate("ep_chiller_cop_reform", 0.0) == 5.5 and H.evaluate("ep_chiller_cop_reform", 6.1) == 6.1,
      f"chiller: the evaporator's low-temperature limit, the condenser flow limits, the condenser outlet temperature, "
      f"the reformulated chiller's COP <= 0 -> 5.5 (worst {worst:.1e})")

# =============================================================================== EnergyPlus's own unit tests
# -- CondenserLoopTowers.unit.cc, CondenserLoopTowers_CalculateVariableTowerOutletTemp: YorkCalc, water in at 40 C,
#    calculateVariableTowerOutletTemp(0.25, 1.0, 14.1) == 40 - 22.2222 within 0.01
e_out, e_flag = variable_tower_outlet_cpp(True, YC_C, YC_L, 40.0, 0.25, 1.0, 14.1)
t_out, t_root = tpl_fixed_outlet("yorkcalc", YC_L, 40.0, 0.25, 1.0, 14.1)
check(abs(e_out - (40 - 22.2222)) < 0.01 and abs(t_out - (40 - 22.2222)) < 0.01,
      f"EnergyPlus test CalculateVariableTowerOutletTemp (YorkCalc, 40 C in, flow ratio 0.25, wet bulb 14.1 C): "
      f"outlet 40 - 22.2222 within 0.01 — the C++ by hand {e_out:.4f} (SolveRoot flag {e_flag}), ours {t_out:.4f} "
      f"({'a root' if t_root else 'no root in the range: the maximum range, as EnergyPlus'})")
# -- VSCoolingTowers_WaterOutletTempTest: CoolToolsCrossFlow, design wet bulb 23.25, approach 3.8889, range 5.5556,
#    minimum air flow ratio 0.2, free convection 0.125; water in at 35 C, setpoint 30 C, water flow ratio 0.75.
#    The tower's water flow ratio there is 0.75 * (calibration ratio) * (a ratio of water densities); the calibration
#    ratio is the root of DesignApproach == approach_raw(FRW, 1, DesignWB, DesignRange) — below 1, so the ratio is
#    under 0.75 and checkModelBounds caps it AT 0.75 whatever the densities (within 5 %).
frw_cal = bisect(lambda w: 3.88888888888889 - H.evaluate("ep_tower_approach_cooltools_raw", w, 1.0, 23.25 + K, 5.55555555555556), 0.5, 1.25)
flag_c, frw_cal_e = solve_root_cpp(0.0001, 500, lambda w: 3.88888888888889 - approach_cpp(False, CT_C, w, 1.0, 23.25, 5.55555555555556), 0.5, 1.0)
MEASURED["CoolTools calibration ratio (test tower)"] = frw_cal
check(frw_cal is not None and abs(frw_cal - frw_cal_e) < 2e-4 and 0.75 * frw_cal * 1.05 < 0.75,
      f"the calibration of that test's tower as an implicit law: water flow ratio {frw_cal:.5f} (SolveRoot by hand "
      f"{frw_cal_e:.5f}) — the operating ratio 0.75 x {frw_cal:.3f} x (a density ratio within 5 %) is below 0.75, so "
      f"checkModelBounds caps it AT 0.75")
# case 2 (wet bulb 10 C): outlet at continuous minimum fan 26.9537 +- 1e-4; FanCyclingRatio 0.5424 +- 1e-4; outlet 30
t_min, _ = tpl_fixed_outlet("cooltools", CT_L, 35.0, 0.75, 0.2, 10.0)
t2 = tpl_vs_tower("cooltools", CT_L, 35.0, 10.0, 30.0, 0.75 * frw_cal, 0.2, 0.125, 1000.0)
e2 = variable_speed_tower_cpp(False, CT_C, CT_L, 35.0, 10.0, 30.0, 0.75 * frw_cal, 0.2, 0.125, 1000.0)
check(abs(t_min - 26.9537) < 1e-4 and abs(t2[1] - 0.5424) < 1e-4 and t2[0] == 30.0 and e2[4] == "cycling"
      and abs(e2[1] - 0.5424) < 1e-4,
      f"EnergyPlus test VSCoolingTowers_WaterOutletTempTest, case 2: outlet at minimum fan 26.9537 (ours {t_min:.4f}), "
      f"FanCyclingRatio 0.5424 (ours {t2[1]:.4f}, the C++ by hand {e2[1]:.4f}), outlet 30.0 (ours {t2[0]})")
# case 1 (wet bulb 26 C): outlet 30.0, FanCyclingRatio 1.0, and the outlet recomputed at the solved air flow = 30 +- 1e-4
t1 = tpl_vs_tower("cooltools", CT_L, 35.0, 26.0, 30.0, 0.75 * frw_cal, 0.2, 0.125, 1000.0)
t1_out, _ = tpl_fixed_outlet("cooltools", CT_L, 35.0, 0.75, t1[2], 26.0)
check(t1[0] == 30.0 and t1[1] == 1.0 and abs(t1_out - 30.0) < 1e-4,
      f"EnergyPlus test VSCoolingTowers_WaterOutletTempTest, case 1: outlet 30.0 and FanCyclingRatio 1.0 (ours {t1[0]}, "
      f"{t1[1]}); the outlet at the solved air flow ratio {t1[2]:.4f} is 30 +- 1e-4 (ours {t1_out:.5f})")

# -- ChillerElectricEIR.unit.cc, ChillerElectricEIR_EvaporativelyCooled_Calculate: its three curves, load 18 kW,
#    leaving setpoint 6.67 C, condenser at the outdoor WET bulb 23.0 C (below the curves' 24 C minimum: the clamp
#    decides). The test asserts CondVolFlowRate = RefCap * 0.000114 = 2.3925760323498 and CondMassFlowRateMax =
#    2.7918772761695 — RefCap follows from the first; then CondMassFlowRate = max * PLR = 2.31460814 +- 1e-7 and the
#    water use 6.22019725e-06 +- 1e-9 m3/s.
_t_idf = ("Curve:Biquadratic, Evap cooled CentCapFT, 0.257896, 0.0389016, -0.00021708, 0.0468684, -0.00094284, -0.00034344, 5, 10, 24, 35, , , , , ;"
          "Curve:Biquadratic, Evap cooled CentEIRFT, 0.933884, -0.058212,  0.00450036, 0.00243,    0.000486,   -0.001215,   5, 10, 24, 35, , , , , ;"
          "Curve:Quadratic, Evap cooled CentEIRFPLR, 0.222903,  0.313387,  0.46371,    0, 1, , , , ;")
_tc = CV.curves_from_idf(_t_idf)
refcap = 2.3925760323498 / 0.000114
capft = CV.evaluate(_tc["Evap cooled CentCapFT"], 6.67, 23.0)
avail = H.evaluate("ep_chiller_avail", refcap, capft)
qev = H.evaluate("ep_chiller_qevap", 18000.0, avail, 1.0)
plr = H.evaluate("ep_chiller_plr", qev, avail, 0.25, 1.0)
mcond = 2.7918772761695 * plr
w_in = H.evaluate("ep_w_tdbtwbpb", 29.4 + K, 23.0 + K, 101325.0)
INIT_CONV_TEMP = 5.05     # Constant::InitConvTemp — outside the ported files; this test's 1e-9 confirms the value
wat = H.evaluate("ep_chiller_evapcond_water", mcond, w_in, 23.0 + K, 101325.0, INIT_CONV_TEMP + K)
MEASURED["EIR evap-cooled test"] = (mcond, wat, capft)
check(abs(mcond - 2.31460814) < 1e-7 and abs(wat - 6.22019725e-06) < 1e-9
      and abs(capft - CV.evaluate(_tc["Evap cooled CentCapFT"], 6.67, 24.0)) < 1e-15,
      f"EnergyPlus test ChillerElectricEIR_EvaporativelyCooled_Calculate: condenser air flow 2.31460814 kg/s +- 1e-7 "
      f"(ours {mcond:.8f}), evaporative water use 6.22019725e-06 m3/s +- 1e-9 (ours {wat:.8e}); the wet bulb 23 C is "
      f"clamped to the curve's 24 C")
# -- ChillerElectricEIR_WaterCooledChillerVariableSpeedCondenser: COP 1, the three curves identically 1, the same
#    sizing (so the same RefCap); load 10 kW at constant condenser flow: Power 20987 +- 1 W, QCondenser = load + Power;
#    ModulatedChillerPLR at half load: flow = max/2; at 500 W: the minimum flow fraction 0.35; ModulatedDeltaTemperature
#    at half load: QCondenser = 3 * load (flow = 3*load/(cp*10))
av = H.evaluate("ep_chiller_avail", refcap, 1.0)


def run_dummy(load):
    q = H.evaluate("ep_chiller_qevap", load, av, 1.0)
    p = H.evaluate("ep_chiller_plr", q, av, 0.25, 1.0)
    f = H.evaluate("ep_chiller_frac", q, av, 0.10, 1.0)
    fl = H.evaluate("ep_chiller_falseload", q, av, p, f, 1.0)
    pw = H.evaluate("ep_chiller_power", av, 1.0, 1.0, 1.0, f)
    return q, p, f, fl, pw, H.evaluate("ep_chiller_qcond", pw, 1.0, q, fl)


d10 = run_dummy(10000.0)
dh = run_dummy(refcap / 2)
d5 = run_dummy(500.0)
check(abs(d10[4] - 20987) < 1.0 and abs(d10[0] - 10000) < 1.0 and abs(d10[5] - (10000 + d10[4])) < 1.0
      and abs(H.evaluate("ep_chiller_condflow", 1.0 * dh[1], 1.0, 0.35) - 0.5) < 1e-5
      and abs(H.evaluate("ep_chiller_condflow", 1.0 * d5[1], 1.0, 0.35) - 0.35) < 1e-5
      and abs(dh[5] / (refcap / 2) - 3.0) < 1e-9,
      f"EnergyPlus test ChillerElectricEIR_WaterCooledChillerVariableSpeedCondenser: Power 20987 +- 1 W (ours "
      f"{d10[4]:.2f}), QEvaporator = the load, QCondenser = load + Power; condenser flow max/2 at half load under "
      f"ModulatedChillerPLR, 0.35 max at 500 W (the minimum flow fraction), QCondenser = 3 x load under "
      f"ModulatedDeltaTemperature (ours {dh[5] / (refcap / 2):.6f})")


# =============================================================================== planted errors
def planted(name, old, new, sweep, count=1):
    save = dict(H.LIBRARY[name])
    assert old in save["expr"], (name, old)
    H.LIBRARY[name]["expr"] = save["expr"].replace(old, new, count)
    try:
        return sweep()
    finally:
        H.LIBRARY[name] = save


p1 = planted("ep_tower_approach_cooltools", "(1.43600088336017)", "(1.43600188336017)", sweep_approach)
p2 = planted("ep_tower_approach_yorkcalc", "max(min((_Twb/ep_K - 273.15), 29.4444), -34.4)", "(_Twb/ep_K - 273.15)", sweep_approach, 99)
p3 = planted("ep_tower_approach_cooltools", "max(min(_FRW, 1.25), 0.75)", "_FRW", sweep_approach, 99)
p4 = planted("ep_tower_blowdown", "if(_CR > 2, max(_Evap/(_CR - 1) - _Drift, 0*_Evap), max(_Evap - _Drift, 0*_Evap))",
             "max(_Evap/(_CR - 1) - _Drift, 0*_Evap)", lambda: sweep_water()[0])
p5 = planted("ep_tower_q_ua", "<= 0.995", "<= 2", lambda: sweep_simple_tower(60)[0])
p6 = planted("ep_chiller_plr", "max(max(0, min(_Q/_Avail, _MaxPLR)), _MinUnl)", "max(0, min(_Q/_Avail, _MaxPLR))",
             lambda: sweep_eir(EIR_NAMES[:25])[0])
p7 = planted("ep_chiller_frac", "min(_Q/_Avail, _MaxPLR)", "max(min(_Q/_Avail, _MaxPLR), 0.3)",
             lambda: sweep_eir(EIR_NAMES[:25])[0], 99)
p8 = planted("ep_tower_vs_tout", "if(_Ton < _Tset, if(", "if(_Ton < _Tset - 100*ep_K, if(", lambda: sweep_vs_tower(120)[0]["Tout"])
MEASURED["planted"] = (p1, p2, p3, p4, p5, p6, p7, p8)
check(p1 > 1e-11 and p2 > 1e-3 and p3 > 1e-3 and p4 > 1e-3 and p5 > 1e-9 and p6 > 1e-3 and p7 > 1e-3 and p8 > 1e-3,
      f"PLANTED, each turns its sweep RED: a CoolTools coefficient changed in its 7th digit ({p1:.1e}; one changed in its 12th "
      f"digit moves the approach by 3e-12 and is NOT caught — the sweep's tolerance is 1e-11); the wet-bulb "
      f"clamp of YorkCalc lost ({p2:.1e}); the water-flow clamp of CoolTools lost ({p3:.1e}); the blowdown branch at "
      f"a concentration ratio <= 2 lost ({p4:.1e}); the effectiveness branch above 0.995 lost ({p5:.1e}); the minimum "
      f"unloading ratio lost ({p6:.1e}); the cycling ratio taken after a floor on the part load ratio ({p7:.1e}); "
      f"the free-convection / cycling branch of the variable-speed sequence lost ({p8:.1e})")

# =============================================================================== the stand
def num(s):
    """'5863/20 (~293.15)' or '~302.4 (an exact fraction ...)' -> float"""
    from fractions import Fraction
    s = str(s).strip()
    if s.startswith("~"):
        return float(s[1:].split()[0])
    return float(Fraction(s.split()[0]))


def g(value=None, unit="", rng=None, ground="the test's operating point"):
    d = {"role": "given", "unit": unit, "ground": ground}
    if rng:
        d["range"] = [str(x) for x in rng]
    else:
        d["value"] = str(value)
    return d


def b3(x):
    return repr(round(x, 3))


def vs_brick(bound):
    """a CoolTools tower at full fan over a wet-bulb range: the outlet water against a chiller's condenser limit"""
    return {"stand": "ztl-stand/1",
            "quantities": {"Twb": g(unit="K", rng=("288.15", "298.15"), ground="wet bulb 15..25 C"),
                           "Twin": g("308.15", "K"), "FRW": g("1"), "FRA": g("1"),
                           "MaxRange": g("11.1111", "K", ground="CoolTools model limit"),
                           "Tr": {"role": "derived", "unit": "K", "search": ["0.001", "22.2222"]},
                           "Tout": {"role": "derived", "unit": "K"}},
            "laws": [{"zfl": "Twin == ep_tower_twbcap_cooltools(Twb) + ep_tower_approach_cooltools(FRW, FRA, Twb, Tr) + Tr",
                      "source": "EnergyPlus calculateVariableTowerOutletTemp: the range it iterates to"},
                     {"zfl": "Tout == Twin - min(Tr, MaxRange)", "source": "EnergyPlus calculateVariableTowerOutletTemp"}],
            "requirements": [{"quantity": "Tout", "op": "<=", "value": bound, "why": "the chiller's entering condenser limit"}]}


def fan_brick(bound):
    """the air flow ratio that meets a 30 C setpoint (modulating fan) and the cube-law fan power"""
    return {"stand": "ztl-stand/1",
            "quantities": {"Twb": g(unit="K", rng=("294.15", "296.15"), ground="wet bulb 21..23 C"),
                           "Twin": g("308.15", "K"), "Tset": g("303.15", "K"), "FRW": g("1"), "Pdes": g("1000", "W"),
                           "FRA": {"role": "derived", "unit": "", "search": ["0.2", "1"]},
                           "Pfan": {"role": "derived", "unit": "W"}},
            "laws": [{"zfl": "Tset - Twb == ep_tower_approach_cooltools(FRW, FRA, Twb, Twin - Tset)",
                      "source": "EnergyPlus calculateVariableSpeedTower: the air flow ratio that meets the setpoint"},
                     {"zfl": "Pfan == Pdes*ep_tower_fpr_cube(FRA)", "source": "EnergyPlus: fan power, the cube law"}],
            "requirements": [{"quantity": "Pfan", "op": "<=", "value": bound, "why": "fan power budget"}]}


UA_IN = dict(UA=7000.0, MCW=22000.0, MA=4.0, twb=25.0, tdb=35.0, W=0.016, P=101325.0, twin=35.0)


def ua_brick(lo, hi):
    """a single-speed tower by its UA: the exit wet bulb X is the implicit unknown"""
    return {"stand": "ztl-stand/1",
            "quantities": {"Twb": g("298.15", "K"), "W": g("0.016"), "P": g("101325", "Pa"), "Twin": g("308.15", "K"),
                           "UA": g("7000", "W/K"), "MCW": g("22000", "W/K", ground="water flow * specific heat"),
                           "MA": g("4", "kg/s", ground="air flow * ep_rhoair"),
                           "X": {"role": "derived", "unit": "K", "search": ["298.65", "308.15"]},
                           "Tout": {"role": "derived", "unit": "K"}},
            "laws": [{"zfl": "ep_tower_q_air(MA, Twb, X, P) == ep_tower_q_ua(UA, MCW, MA, ep_tower_cpairside(Twb, X, P), "
                             "ep_cpair(W), Twin, Twb)",
                      "source": "EnergyPlus calculateSimpleTowerOutletTemp: the fixed point of its iteration"},
                     {"zfl": "Tout == ep_tower_tout(Twin, ep_tower_q_air(MA, Twb, X, P), MCW)",
                      "source": "EnergyPlus calculateSimpleTowerOutletTemp"}],
            "requirements": [{"quantity": "Tout", "op": "within", "value": [lo, hi], "why": "EnergyPlus's own iterate"}]}


WAT_IN = dict(P=101325.0, tdb=35.0, W=0.016, twb=25.0, afr=1.0, rho=995.0, vdes=0.0053, df=0.00008, cr=3.0)


def water_brick(bound):
    q, laws = TW.water_use_laws("SaturatedExit")
    q.update({"MA": g("4", "kg/s"), "Twb": g("298.15", "K"), "P": g("101325", "Pa"), "Win": g("0.016"),
              "Q": g(unit="W", rng=("80000", "90000"), ground="heat rejected"), "RHOW": g("995", "kg/m^3"),
              "Vdes": g("0.0053", "m^3/s"), "DF": g("0.00008"), "AFR": g("1"), "CR": g("3")})
    return {"stand": "ztl-stand/1", "quantities": q, "laws": laws,
            "requirements": [{"quantity": "Makeup", "op": "<=", "value": bound, "why": "makeup water budget"}]}


def control_brick(bound):
    """the control sequences as explicit laws, given the stage outlet temperatures (here: the fan cycling at the
    minimum air flow); single- and two-speed fan cycling beside it"""
    d = {"role": "derived"}
    return {"stand": "ztl-stand/1",
            "quantities": {"Ton": g(unit="K", rng=("297.15", "299.15"), ground="outlet at full fan 24..26 C"),
                           "Tmin": g(unit="K", rng=("301.15", "302.15"), ground="outlet at minimum fan 28..29 C"),
                           "Twin": g("308.15", "K"), "Tset": g("303.15", "K"), "FC": g("0.125"), "AFRmin": g("0.2"),
                           "AFRsol": g(unit="", rng=("0.3", "0.5")), "Pdes": g("1000", "W"), "Plow": g("300", "W"),
                           "Tout": dict(d, unit="K"), "CYC": dict(d, unit=""), "AFR": dict(d, unit=""),
                           "Pfan": dict(d, unit="W"), "Tss": dict(d, unit="K"), "Pss": dict(d, unit="W"),
                           "Tts": dict(d, unit="K"), "Pts": dict(d, unit="W")},
            "laws": [{"zfl": "Tout == ep_tower_vs_tout(Ton, Twin, Tset, FC)", "source": "calculateVariableSpeedTower"},
                     {"zfl": "CYC == ep_tower_vs_cycling(Ton, Tmin, Twin, Tset, FC)", "source": "calculateVariableSpeedTower"},
                     {"zfl": "AFR == ep_tower_vs_afr(Ton, Tmin, Twin, Tset, FC, AFRmin, AFRsol)", "source": "calculateVariableSpeedTower"},
                     {"zfl": "Pfan == ep_tower_vs_power(Ton, Tmin, Twin, Tset, FC, ep_tower_fpr_cube(AFRmin), "
                             "ep_tower_fpr_cube(AFRsol), Pdes)", "source": "calculateVariableSpeedTower"},
                     {"zfl": "Tss == ep_tower_ss_tout(Twin, Ton, Tset)", "source": "calculateSingleSpeedTower"},
                     {"zfl": "Pss == ep_tower_ss_power(Twin, Ton, Tset, Pdes)", "source": "calculateSingleSpeedTower"},
                     {"zfl": "Tts == ep_tower_ts_tout(Twin, Tmin, Ton, Tset)", "source": "calculateTwoSpeedTower"},
                     {"zfl": "Pts == ep_tower_ts_power(Twin, Tmin, Ton, Tset, Plow, Pdes)", "source": "calculateTwoSpeedTower"}],
            "requirements": [{"quantity": "Pfan", "op": "<=", "value": bound, "why": "fan power while cycling"},
                             {"quantity": "Tout", "op": "<=", "value": "303.15", "why": "the setpoint is met"},
                             {"quantity": "Pts", "op": "<=", "value": "300", "why": "the low speed suffices"}]}


def lossfactor_brick():
    q, laws = TW.water_use_laws("LossFactor")
    q.update({"F": g("0.002", "1/K"), "Twin": g("308.15", "K"), "Tout": g(unit="K", rng=("302.15", "303.15")),
              "MW": g("5.3", "kg/s"), "RHOW": g("995", "kg/m^3"), "Vdes": g("0.0053", "m^3/s"), "DF": g("0.00008"),
              "AFR": g("1"), "CR": g("3")})
    return {"stand": "ztl-stand/1", "quantities": q, "laws": laws,
            "requirements": [{"quantity": "Makeup", "op": "within", "value": ["0.0000798", "0.0000959"], "why": "by hand"}]}


def chiller_small_brick():
    d = {"role": "derived"}
    return {"stand": "ztl-stand/1",
            "quantities": {"Load": g(unit="W", rng=("100000", "300000")), "Avail": g("250000", "W"), "MaxPLR": g("1.05"),
                           "ME": g("10", "kg/s"), "CP": g("4190", "J/(kg*K)"), "Tin": g("285.15", "K"),
                           "Tlow": g("278.15", "K"), "Mmax": g("20", "kg/s"), "MinR": g("0.35"), "MinUnl": g("0.25"),
                           "Win": g("0.0149"), "Twb": g("296.15", "K"), "P": g("101325", "Pa"), "Tconv": g("278.2", "K"),
                           "Q": dict(d, unit="W"), "PLR": dict(d, unit=""), "MC": dict(d, unit="kg/s"),
                           "Vw": dict(d, unit="m^3/s")},
            "laws": [{"zfl": "Q == ep_chiller_qevap_lim(Load, Avail, MaxPLR, ME, CP, Tin, Tlow)", "source": "EIR calculate"},
                     {"zfl": "PLR == ep_chiller_plr(Q, Avail, MinUnl, MaxPLR)", "source": "EIR calculate"},
                     {"zfl": "MC == ep_chiller_condflow(Mmax*PLR, Mmax, MinR)", "source": "EIR calculate"},
                     {"zfl": "Vw == ep_chiller_evapcond_water(MC, Win, Twb, P, Tconv)", "source": "EIR calculate"}],
            "requirements": [{"quantity": "Q", "op": "<=", "value": "262500", "why": "Avail * MaxPLR"},
                             {"quantity": "MC", "op": ">=", "value": "7.9", "why": "40 % of the maximum (8 kg/s) at the lowest load"}]}


EIR_NAME, REF_NAME = "ElectricEIRChiller McQuay WSC 471kW/5.89COP/Vanes", "ReformEIRChiller McQuay WSC 471kW/5.89COP/Vanes"


def eir_brick(bound):
    parts = CH.chiller_from_idf(_chillers_idf, EIR_NAME)
    return {"stand": "ztl-stand/1", "curves": parts["curves"],
            "quantities": dict(parts["quantities"], Load=g(unit="W", rng=("200000", "450000"), ground="cooling load"),
                               Tchw=g("281.15", "K"), Tcond=g(unit="K", rng=("295.15", "303.15"), ground="22..30 C")),
            "laws": parts["laws"],
            "requirements": [{"quantity": "Power", "op": "<=", "value": bound, "why": "electrical budget"}]}


def reform_brick(bound):
    parts = CH.chiller_from_idf(_chillers_idf, REF_NAME)
    return {"stand": "ztl-stand/1", "curves": parts["curves"],
            "quantities": dict(parts["quantities"], Load=g("400000", "W"), Tchw=g("281.15", "K"),
                               Tcin=g(unit="K", rng=("297.15", "299.15"), ground="entering condenser water 24..26 C"),
                               Mcond=g("19.2", "kg/s"), CpCond=g("4180", "J/(kg*K)")),
            "laws": parts["laws"],
            "requirements": [{"quantity": "Power", "op": "<=", "value": bound, "why": "electrical budget"}]}


def run_stand_proofs():
    from concurrent.futures import ProcessPoolExecutor
    # the bounds come from the TRANSCRIPTION (the C++ by hand), never from the stand: each is set a little above and a
    # little below the extreme the transcription finds, and the stand must earn the one and refute the other
    vs_max = max(variable_tower_outlet_cpp(False, CT_C, CT_L, 35.0, 1.0, 1.0, 15.0 + i / 10)[0] for i in range(101))
    fan_pts = []
    for i in range(21):
        twb = 21.0 + i / 10
        flag, a = solve_root_cpp(0.0001, 500, lambda fr: (30.0 - twb) - approach_cpp(False, CT_C, 1.0, fr, twb, 5.0), 0.2, 1.0)
        fan_pts.append((flag, 1000.0 * a ** 3))
    fan_max = max(p for _, p in fan_pts)
    u = UA_IN
    vair = u["MA"] / rhoair_cpp(u["P"], u["tdb"], u["W"])
    ua_e = simple_tower_cpp(u["UA"], u["MCW"] / 4180.0, 4180.0, vair, u["twin"], u["tdb"], u["twb"], u["P"], u["W"])[0]
    w = WAT_IN
    vair_w = 4.0 / rhoair_cpp(w["P"], w["tdb"], w["W"])
    wat_max = max(water_usage_cpp("MoistTheory", w["P"], w["tdb"], w["W"], w["twb"], w["afr"], vair_w, q, w["rho"], 0.0,
                                  0, 0, 0, w["vdes"], w["df"], w["cr"])[3] for q in (80000.0, 85000.0, 90000.0))
    sp_e = CH.chiller_spec_from_idf(_chillers_idf, EIR_NAME)
    eir_max = max(eir_calculate_cpp(sp_e, -(200000.0 + 2500.0 * i), 8.0, 22.0 + 0.2 * j)["Power"]
                  for i in range(101) for j in range(41))
    sp_r = CH.chiller_spec_from_idf(_chillers_idf, REF_NAME)
    ref_pts = [reform_control_cpp(sp_r, -400000.0, 8.0, 24.0 + 0.1 * j, 19.2, 4180.0) for j in range(21)]
    ref_max = max(r["Power"] for r, _ in ref_pts)
    jobs = {"vs+": vs_brick(b3(vs_max + 0.3 + K)), "vs-": vs_brick(b3(vs_max - 0.3 + K)),
            "fan+": fan_brick(b3(fan_max * 1.05)), "fan-": fan_brick(b3(fan_max * 0.95)),
            "ua+": ua_brick(b3(ua_e - 0.02 + K), b3(ua_e + 0.02 + K)),
            "wat+": water_brick(repr(round(wat_max * 1.02, 9))), "wat-": water_brick(repr(round(wat_max * 0.98, 9))),
            "eir+": eir_brick(b3(eir_max * 1.02)), "eir-": eir_brick(b3(eir_max * 0.98)),
            "ref+": reform_brick(b3(ref_max * 1.02)), "ref-": reform_brick(b3(ref_max * 0.98)),
            "ctl+": control_brick("7"), "ctl-": control_brick("6"), "lf+": lossfactor_brick(), "chs+": chiller_small_brick()}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=int(os.environ.get("HVAC_PLANT_WORKERS", "6"))) as ex:
        futs = {k: ex.submit(_timed_run, b) for k, b in jobs.items()}
        res = {k: f.result() for k, f in futs.items()}
    times = {k: v[1] for k, v in res.items()}
    r = {k: v[0] for k, v in res.items()}
    MEASURED["stand proofs, seconds each / wall"] = (times, round(time.time() - t0, 1))

    def v(k):
        return r[k].get("verdict")

    def why(k):
        return f"{v(k)}, {str(r[k].get('why'))[:160]}, {r[k].get('guaranteed')}, {r[k].get('its_violating_point')}"
    ok_units = all(str(x.get("units", "")).startswith("checked") for x in r.values())
    check(ok_units, f"stand: every law of the fifteen tower and chiller bricks passes the unit check "
                    f"({[(k, x.get('units')) for k, x in r.items() if not str(x.get('units', '')).startswith('checked')]})")
    # layer 3
    pt = r["vs-"].get("its_violating_point") or {}
    re_out = variable_tower_outlet_cpp(False, CT_C, CT_L, 35.0, 1.0, 1.0, num(pt["Twb"]) - K)[0] if "Twb" in pt else -99
    check(v("vs+") == "EARNED" and v("vs-") == "REFUTED" and re_out > vs_max - 0.3,
          f"stand, layer 3: a CoolTools tower at full fan, wet bulb 15..25 C, water in at 35 C — outlet <= "
          f"{vs_max + 0.3:.3f} C EARNED, <= {vs_max - 0.3:.3f} C REFUTED at its point (the C++ by hand there: {re_out:.3f} C; "
          f"the transcription's maximum {vs_max:.3f} C) ({why('vs+')} | {why('vs-')})")
    pt = r["fan-"].get("its_violating_point") or {}
    if "Twb" in pt:
        twb_p = num(pt["Twb"]) - K
        _, a_p = solve_root_cpp(0.0001, 500, lambda fr: (30.0 - twb_p) - approach_cpp(False, CT_C, 1.0, fr, twb_p, 5.0), 0.2, 1.0)
    else:
        a_p = 0.0
    check(all(f != -2 for f, _ in fan_pts) and v("fan+") == "EARNED" and v("fan-") == "REFUTED" and 1000 * a_p ** 3 > fan_max * 0.95,
          f"stand, layer 3: the air flow ratio that meets a 30 C setpoint (implicit) and the cube-law fan power, wet bulb "
          f"21..23 C — fan power <= {fan_max * 1.05:.1f} W EARNED, <= {fan_max * 0.95:.1f} W REFUTED at its point (by hand "
          f"there {1000 * a_p ** 3:.1f} W) ({why('fan+')} | {why('fan-')})")
    # NOT here, MEASURED 2026-11-12 (four runs, 641..728 s each): the same brick with a bound the proved range lies
    # wholly past ('Tout <= 302.35 K', 'Tout <= 301.4 K', 'X <= 304.6 K', a window below) ends OPEN — "proved within [302.4, 302.4] K, which
    # reaches past the bound, yet no corner violates it": with every given exact and the root not a fraction, the
    # stand finds no corner witness for this long law. A gap of the stand, not of the port (DESIGN-HVAC.md).
    check(v("ua+") == "EARNED",
          f"stand, layer 3: a UA tower (effectiveness-NTU; the exit wet bulb implicit) — its outlet PROVED within "
          f"+-0.02 K of EnergyPlus's own iterate {ua_e:.4f} C ({why('ua+')})")
    pt = r["wat-"].get("its_violating_point") or {}
    wat_p = water_usage_cpp("MoistTheory", w["P"], w["tdb"], w["W"], w["twb"], w["afr"], vair_w, num(pt["Q"]), w["rho"], 0.0,
                            0, 0, 0, w["vdes"], w["df"], w["cr"])[3] if "Q" in pt else 0.0
    check(v("wat+") == "EARNED" and v("wat-") == "REFUTED" and wat_p > wat_max * 0.98,
          f"stand, layer 3: makeup water by the saturated-exit chain (evaporation + drift + blowdown at 3 cycles), heat "
          f"80..90 kW — <= {wat_max * 1.02:.3e} m3/s EARNED, <= {wat_max * 0.98:.3e} REFUTED at its point (by hand there "
          f"{wat_p:.3e}) ({why('wat+')} | {why('wat-')})")
    # the control sequence: the fan cycles at the minimum air flow; FanPower = AFRmin^3 * Pdes * (OFF - Tset)/(OFF - Tmin),
    # OFF = Twin - FC*(Twin - Ton): by hand its maximum is at Ton = 26 C, Tmin = 29 C
    def cyc_power(ton, tmin):
        off = 35.0 - 0.125 * (35.0 - ton)
        return 0.2 ** 3 * 1000.0 * (off - 30.0) / (off - tmin)
    pt = r["ctl-"].get("its_violating_point") or {}
    ctl_p = cyc_power(num(pt["Ton"]) - K, num(pt["Tmin"]) - K) if "Ton" in pt and "Tmin" in pt else 0.0
    check(v("ctl+") == "EARNED" and v("ctl-") == "REFUTED" and ctl_p > 6.0 and 6.0 < cyc_power(26.0, 29.0) < 7.0,
          f"stand, layer 3: the control sequences as explicit laws (variable-speed: outlet, cycling ratio, air flow ratio, "
          f"fan power; single- and two-speed fan cycling) — cycling fan power <= 7 W EARNED, <= 6 W REFUTED at its point "
          f"(by hand there {ctl_p:.3f} W; the maximum by hand {cyc_power(26.0, 29.0):.3f} W) ({why('ctl+')} | {why('ctl-')})")
    # the loss factor by hand: Evap = F*(Twin - Tout)*MW/RHOW, Drift = Vdes*DF*AFR, Blowdown = Evap/(CR - 1) - Drift
    lf = [water_usage_cpp("UserFactor", 0, 0, 0, 0, 1.0, 0, 0, 995.0, 0.002, 35.0, to, 5.3, 0.0053, 0.00008, 3.0)[3] for to in (29.0, 30.0)]
    check(v("lf+") == "EARNED" and 0.0000798 < min(lf) and max(lf) < 0.0000959 and max(lf) - min(lf) > 0.000015,
          f"stand, layer 3: makeup water by the loss-factor chain, outlet 29..30 C — PROVED within [7.98e-05, 9.59e-05] m3/s; "
          f"by hand {min(lf):.4e} .. {max(lf):.4e} ({why('lf+')})")
    check(v("chs+") == "EARNED",
          f"stand, layer 4: the evaporator's low-temperature limit, the part load ratio, the condenser flow limits and the "
          f"evaporative condenser's water use as laws — the load cut at Avail x MaxPLR and the flow at the lowest load "
          f"EARNED ({why('chs+')})")
    # layer 4
    pt = r["eir-"].get("its_violating_point") or {}
    eir_p = eir_calculate_cpp(sp_e, -num(pt["Load"]), 8.0, num(pt["Tcond"]) - K)["Power"] if "Load" in pt and "Tcond" in pt else 0.0
    check(v("eir+") == "EARNED" and v("eir-") == "REFUTED" and eir_p > eir_max * 0.98,
          f"stand, layer 4: a Chiller:Electric:EIR built from datasets/Chillers.idf by code, load 200..450 kW, entering "
          f"condenser 22..30 C — power <= {eir_max * 1.02:.0f} W EARNED, <= {eir_max * 0.98:.0f} W REFUTED at its point "
          f"(by hand there {eir_p:.0f} W) ({why('eir+')} | {why('eir-')})")
    pt = r["ref-"].get("its_violating_point") or {}
    ref_p = reform_control_cpp(sp_r, -400000.0, 8.0, num(pt["Tcin"]) - K, 19.2, 4180.0)[0]["Power"] if "Tcin" in pt else 0.0
    check(all(h == "root" for _, h in ref_pts) and v("ref+") == "EARNED" and v("ref-") == "REFUTED" and ref_p > ref_max * 0.98,
          f"stand, layer 4: a Chiller:Electric:ReformulatedEIR from the dataset, its leaving condenser temperature the "
          f"implicit unknown, entering water 24..26 C — power <= {ref_max * 1.02:.0f} W EARNED, <= {ref_max * 0.98:.0f} W "
          f"REFUTED at its point (by hand there {ref_p:.0f} W) ({why('ref+')} | {why('ref-')})")


def _timed_run(b):
    t = time.time()
    r = S.run(b)
    return r, round(time.time() - t, 1)


if not FAST:
    run_stand_proofs()

for k, v in MEASURED.items():
    print(f"MEASURED {k}: {v}")
if FAILS:
    print(f"HVAC PLANT RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"HVAC PLANT GREEN ({CHECKS} checks{', the stand proofs skipped (--fast)' if FAST else ''})")
