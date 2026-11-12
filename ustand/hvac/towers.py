# -*- coding: utf-8 -*-
"""Layer 3: COOLING TOWERS, ported from EnergyPlus 26.2.0 src/EnergyPlus/CondenserLoopTowers.cc (DESIGN-HVAC.md).

Arguments are SI with units: temperatures absolute (K), temperature differences (range, approach) in K, flows in
kg/s or m^3/s, powers in W, UA and capacity rates in W/K, flow ratios pure numbers. What EnergyPlus solves by
iteration is NOT a template: it is an IMPLICIT law over these templates (a derived quantity with `search`), listed
with each group below and in BRICKS.md 7i.

A. Variable-speed towers (CoolingTower:VariableSpeed) — calculateVariableSpeedApproach, checkModelBounds,
   calculateVariableTowerOutletTemp, calculateVariableSpeedTower.
   ep_tower_approach_cooltools / _yorkcalc (FRW, FRA, Twb, Tr): the approach (K) of the built-in CoolToolsCrossFlow /
   YorkCalc coefficient sets, WITH the capping the operating tower applies before every evaluation (checkModelBounds):
   the inlet wet bulb is clamped to the model's limits (CoolTools -1 .. 26.6667 C, YorkCalc -34.4 .. 29.4444 C) and,
   for CoolTools ONLY, the water flow ratio to 0.75 .. 1.25 (for YorkCalc EnergyPlus only warns on the liquid-to-gas
   ratio above 8). The range and the approach are compared with their limits for a WARNING only: TrCapped and
   TaCapped are computed and never used, so the range enters the polynomial as it is. The air flow ratio is not
   clamped (the solver keeps it in [minimum, 1]). `_raw`: no capping at all — what the sizing (the calibration of
   the water flow ratio) and a direct call evaluate. ep_tower_twbcap_*: the capped wet bulb itself (K).
   User coefficients (CoolingTowerPerformance:CoolTools / :YorkCalc) are CURVE types of ustand/hvac/curves.py:
   curve(NAME, FRW, FRA, Twb, Tr), capped by the limits its object states, in the same way.
   Implicit laws EnergyPlus solves (General::SolveRoot, |residual| < 1e-4):
   - the range Tr at a FIXED fan speed:  Twin == ep_tower_twbcap_X(Twb) + ep_tower_approach_X(FRW, FRA, Twb, Tr) + Tr,
     Tr searched in [0.001, max(the model's maximum range, 22.2222)] K; then Tout == Twin - min(Tr, maximum range).
     (No sign change in that interval: EnergyPlus sets Tout = Twin - maximum range and warns; the stand says OPEN.)
   - the air flow ratio that MEETS the setpoint:  Tset - Twb == ep_tower_approach_X(FRW, FRA, Twb, Twin - Tset),
     FRA searched in [minimum air flow ratio, 1]; then Tout == Tset. Note the two wet bulbs: the requested approach
     is taken from the UNCAPPED wet bulb, the model reads the capped one. (No sign change: EnergyPlus keeps the
     minimum ratio — SolveRoot returns its first bound — and still reports Tout = Tset.)
   - the calibration at sizing:  DesignApproach == ep_tower_approach_X_raw(FRW, 1, DesignWB, DesignRange), FRW
     searched from 0.5; the calibrated water flow is DesignWaterFlow/FRW, and the operating water flow ratio is
     mdot/(rho*calibrated flow).
   ep_tower_vs_tout / _cycling / _afr / _power: the control sequence of calculateVariableSpeedTower over its regimes
   (full speed; fan off in free convection; the fan cycling at the minimum ratio; the fan modulating), given the
   outlet temperatures at full and at minimum air flow. One cell (NumCellOn/NumCell = 1).
B. Single- and two-speed towers (CoolingTower:SingleSpeed / :TwoSpeed) — calculateSimpleTowerOutletTemp (the
   UA / effectiveness-NTU model of Merkel's theory), calculateSingleSpeedTower, calculateTwoSpeedTower.
   EnergyPlus iterates the exit air wet bulb X:  X <- Twb + Q(X)/(mair*cpe(X)),  cpe(X) = (hsat(X) - hsat(Twb))/(X - Twb),
   until it moves by less than 1e-5 of its absolute value. Its FIXED POINT is the implicit law
       ep_tower_q_air(MA, Twb, X, P) == ep_tower_q_ua(UA, MCW, MA, ep_tower_cpairside(Twb, X, P), ep_cpair(W), Twin, Twb)
   with X searched in (Twb, Twin]; then  Tout == ep_tower_tout(Twin, ep_tower_q_air(MA, Twb, X, P), MCW).
   MA = air volume flow * ep_rhoair(P, Tdb, W); MCW = water mass flow * its specific heat.
   ep_tower_ss_* / ep_tower_ts_*: the fan cycling of the single-speed tower (FanCycling control) and the two stages
   of the two-speed tower, given the outlet temperatures at each stage. One cell.
C. Water use — calculateWaterUsage: evaporation by the saturated-exit method (a chain of laws over layer 1, see
   water_use_laws) and by the loss factor, drift, blowdown by concentration ratio, makeup.

NOT ported, said: multi-cell staging (NumCellOn); the fluid-bypass capacity control of the single-speed tower; the
basin heater; the fault models (fouling, sensor offset); sizing other than the variable-speed calibration; the
control sequence of CoolingTower:VariableSpeed:Merkel (its tower is B with UA multiplied by three curves — written
with `curve(...)`, see BRICKS.md 7i); the WATER properties of the plant loop (density, specific heat: EnergyPlus's
FluidProperties tables are not among the ported files — they are quantities of the brick).
"""
from . import register

SRC = "EnergyPlus 26.2.0, src/EnergyPlus/CondenserLoopTowers.cc"

# ------------------------------------------------------------------------------------------------ A. variable speed
# coefficient sets as GetTowerInput writes them (Coeff[0..34] CoolToolsCrossFlow, Coeff[0..26] YorkCalc)
COOLTOOLS_COEFFS = [
    "0.52049709836241", "-10.617046395344", "10.7292974722538", "-2.74988377158227", "4.73629943913743",
    "-8.25759700874711", "1.57640938114136", "6.51119643791324", "1.50433525206692", "-3.2888529287801",
    "0.0257786145353773", "0.182464289315254", "-0.0818947291400898", "-0.215010003996285", "0.0186741309635284",
    "0.0536824177590012", "-0.00270968955115031", "0.00112277498589279", "-0.00127758497497718",
    "0.0000760420796601607", "1.43600088336017", "-0.5198695909109", "0.117339576910507", "1.50492810819924",
    "-0.135898905926974", "-0.152577581866506", "-0.0533843828114562", "0.00493294869565511", "-0.00796260394174197",
    "0.000222619828621544", "-0.0543952001568055", "0.00474266879161693", "-0.0185854671815598", "0.00115667701293848",
    "0.000807370664460284"]
YORKCALC_COEFFS = [
    "-0.359741205", "-0.055053608", "0.0023850432", "0.173926877", "-0.0248473764", "0.00048430224",
    "-0.005589849456", "0.0005770079712", "-0.00001342427256", "2.84765801111111", "-0.121765149", "0.0014599242",
    "1.680428651", "-0.0166920786", "-0.0007190532", "-0.025485194448", "0.0000487491696", "0.00002719234152",
    "-0.0653766255555556", "-0.002278167", "0.0002500254", "-0.0910565458", "0.00318176316", "0.000038621772",
    "-0.0034285382352", "0.00000856589904", "-0.000001516821552"]
# the model limits GetTowerInput sets (deg C / K differences / ratios)
COOLTOOLS_LIMITS = {"twb_min": "-1.0", "twb_max": "26.6667", "range_min": "1.1111", "range_max": "11.1111",
                    "approach_min": "1.1111", "approach_max": "11.1111", "frw_min": "0.75", "frw_max": "1.25"}
YORKCALC_LIMITS = {"twb_min": "-34.4", "twb_max": "29.4444", "range_min": "1.1111", "range_max": "22.2222",
                   "approach_min": "1.1111", "approach_max": "40.0", "frw_min": "0.75", "frw_max": "1.25",
                   "lg_max": "8.0"}
# the monomial of each coefficient, in the order of calculateVariableSpeedApproach.
# CoolTools: A = (air flow ratio)^3 ("the CoolTools model actually uses PctFanPower = AirFlowRatio^3"), W = water flow
# ratio, T = wet bulb (C), R = range. YorkCalc: T, R, F = water flow ratio / air flow ratio.
COOLTOOLS_TERMS = ["", "A", "AA", "AAA", "W", "AW", "AAW", "WW", "AWW", "WWW", "T", "AT", "AAT", "WT", "AWT", "WWT",
                   "TT", "ATT", "WTT", "TTT", "R", "AR", "AAR", "WR", "AWR", "WWR", "TR", "ATR", "WTR", "TTR", "RR",
                   "ARR", "WRR", "TRR", "RRR"]
YORKCALC_TERMS = ["", "T", "TT", "R", "TR", "TTR", "RR", "TRR", "TTRR", "F", "TF", "TTF", "RF", "TRF", "TTRF", "RRF",
                  "TRRF", "TTRRF", "FF", "TFF", "TTFF", "RFF", "TRFF", "TTRFF", "RRFF", "TRRFF", "TTRRFF"]


def polynomial(terms, coeffs, symbols):
    """sum of coeff_i * monomial_i, each letter of a monomial replaced by its expression (in parentheses)"""
    out = []
    for c, mono in zip(coeffs, terms):
        out.append("*".join([f"({c})"] + [f"({symbols[ch]})" for ch in mono]))
    return "(" + " + ".join(out) + ")"


def _clamp(x, lo, hi):
    return f"max(min({x}, {hi}), {lo})"


_TWB_C = "(_Twb/ep_K - 273.15)"
_ARGS = ["_FRW", "_FRA", "_Twb", "_Tr"]
for _nm, _terms, _co, _lim, _capw in (("cooltools", COOLTOOLS_TERMS, COOLTOOLS_COEFFS, COOLTOOLS_LIMITS, True),
                                      ("yorkcalc", YORKCALC_TERMS, YORKCALC_COEFFS, YORKCALC_LIMITS, False)):
    _twb_cap = _clamp(_TWB_C, _lim["twb_min"], _lim["twb_max"])
    _w_cap = _clamp("_FRW", _lim["frw_min"], _lim["frw_max"]) if _capw else "_FRW"
    for _suffix, _T, _W in (("", _twb_cap, _w_cap), ("_raw", _TWB_C, "_FRW")):
        _sym = {"A": "_FRA*_FRA*_FRA", "W": _W, "T": _T, "R": "_Tr/ep_K", "F": f"({_W})/_FRA"}
        register(f"ep_tower_approach_{_nm}{_suffix}", _ARGS, polynomial(_terms, _co, _sym) + "*ep_K", "K",
                 SRC + " calculateVariableSpeedApproach" + ("" if _suffix else " after checkModelBounds"),
                 note=("no capping (sizing / calibration)" if _suffix else
                       "wet bulb capped to the model limits" + (", water flow ratio to 0.75..1.25" if _capw else
                                                                 "; the water flow ratio is NOT capped (YorkCalc)")))
    register(f"ep_tower_twbcap_{_nm}", ["_Twb"], f"({_twb_cap} + 273.15)*ep_K", "K",
             SRC + " checkModelBounds (TwbCapped)")

# the control sequence of calculateVariableSpeedTower. _Ton, _Tmin: the outlet temperatures at air flow ratio 1 and at
# the minimum ratio (each a fixed-speed implicit law); _FC: the fraction of capacity in free convection; _AFRsol: the
# ratio that meets the setpoint (the modulating implicit law); _FPRmin, _FPRsol: the fan power ratio at the minimum
# ratio and at _AFRsol — the fan power curve's value, or ep_tower_fpr_cube (the default when no curve is named).
# EnergyPlus's comparisons are kept as written: ON > Tset: full speed; ON < Tset: the sequence below; ON == Tset
# exactly: NEITHER branch runs and the tower reports the INLET temperature with zero fan power (its initial values).
_OFF = "(_Twin - _FC*(_Twin - _Ton))"                      # outlet in free convection (fan off)
_CYC = f"(({_OFF} - _Tset)/({_OFF} - _Tmin))"              # fan cycling ratio at the minimum air flow
register("ep_tower_vs_tout", ["_Ton", "_Twin", "_Tset", "_FC"],
         f"if(_Ton > _Tset, _Ton, if(_Ton < _Tset, if({_OFF} > _Tset, _Tset, {_OFF}), _Twin))", "K",
         SRC + " calculateVariableSpeedTower (outlet water temperature over the regimes)")
register("ep_tower_vs_cycling", ["_Ton", "_Tmin", "_Twin", "_Tset", "_FC"],
         f"if(_Ton > _Tset, 1, if(_Ton < _Tset, if({_OFF} > _Tset, if(_Tmin < _Tset, {_CYC}, 1), 0), 0))", "",
         SRC + " calculateVariableSpeedTower (FanCyclingRatio)",
         note="at ON == Tset EnergyPlus leaves the ratio of the previous call; 0 here")
register("ep_tower_vs_afr", ["_Ton", "_Tmin", "_Twin", "_Tset", "_FC", "_AFRmin", "_AFRsol"],
         f"if(_Ton > _Tset, 1, if(_Ton < _Tset, if({_OFF} > _Tset, if(_Tmin < _Tset, "
         f"{_CYC}*_AFRmin + (1 - {_CYC})*_FC, _AFRsol), _FC), 1))", "",
         SRC + " calculateVariableSpeedTower (airFlowRateRatio)")
register("ep_tower_vs_power", ["_Ton", "_Tmin", "_Twin", "_Tset", "_FC", "_FPRmin", "_FPRsol", "_Pdes"],
         f"if(_Ton > _Tset, _Pdes, if(_Ton < _Tset, if({_OFF} > _Tset, if(_Tmin < _Tset, "
         f"_Pdes*max(_FPRmin, 0)*{_CYC}, _Pdes*max(_FPRsol, 0)), 0*_Pdes), 0*_Pdes))", "W",
         SRC + " calculateVariableSpeedTower (FanPower)",
         note="at full speed the fan power is the design power itself, NOT design power * curve(1)")
register("ep_tower_fpr_cube", ["_FRA"], "(_FRA*_FRA*_FRA)", "",
         SRC + " calculateVariableSpeedTower (pow_3(airFlowRateRatio): the fan law used when no curve is named)")

# ----------------------------------------------------------------------------------- B. single- and two-speed (UA)
# PsyHFnTdbRhPb at RH = 1, written with max() where layer 1 writes its branch: the same value (tests/test_hvac_plant
# compares them), a third of the text — a tower law holds this dozens of times
_PS = "(ep_psat(_T)/ep_Pa)"
_TC = "(_T/ep_K - 273.15)"
register("ep_hsat", ["_T", "_P"],
         f"(1.00484e3*{_TC} + max({_PS}*0.62198/max(_P/ep_Pa - {_PS}, 1000), 1.0e-5)*(2.50094e6 + 1.85895e3*{_TC}))"
         "*ep_J_kg", "J/kg", "EnergyPlus 26.2.0, Psychrometrics.hh PsyHFnTdbRhPb(T, 1.0, Pb)")
register("ep_tower_cpairside", ["_Twb", "_TwbOut", "_P"],
         "(ep_hsat(_TwbOut, _P) - ep_hsat(_Twb, _P))/(_TwbOut - _Twb)", "J/(kg*K)",
         SRC + " calculateSimpleTowerOutletTemp (CpAirside)")
register("ep_tower_q_air", ["_MA", "_Twb", "_TwbOut", "_P"], "_MA*(ep_hsat(_TwbOut, _P) - ep_hsat(_Twb, _P))", "W",
         SRC + " calculateSimpleTowerOutletTemp (the air side at the iteration's fixed point: "
               "OutletAirWetBulb = InletAirWetBulb + Qactual/AirCapacity)")
# effectiveness-NTU: _CPS the air-side specific heat (ep_tower_cpairside), _CPA the moist-air cp (ep_cpair(W)),
# _MCW water mass flow * cp, _MA air mass flow. Above a capacity ratio of 0.995, and where NTU*(1 - ratio) >= 700,
# EnergyPlus uses NTU/(1 + NTU).
_CA = "(_MA*_CPS)"
_CMIN = f"min({_CA}, _MCW)"
_CR = f"({_CMIN}/max({_CA}, _MCW))"
_NTU = f"(_UA*_CPS/_CPA/{_CMIN})"
_E = f"({_NTU}*(1 - {_CR}))"
_EFF = (f"if({_CR} <= 0.995, if({_E} >= 700, {_NTU}/(1 + {_NTU}), (1 - exp(-{_E}))/(1 - {_CR}*exp(-{_E}))), "
        f"{_NTU}/(1 + {_NTU}))")
register("ep_tower_q_ua", ["_UA", "_MCW", "_MA", "_CPS", "_CPA", "_Twin", "_Twb"],
         f"{_EFF}*{_CMIN}*(_Twin - _Twb)", "W", SRC + " calculateSimpleTowerOutletTemp (Qactual of one pass)")
register("ep_tower_tout", ["_Twin", "_Q", "_MCW"], "_Twin - max(_Q/ep_W, 0)*ep_W/_MCW", "K",
         SRC + " calculateSimpleTowerOutletTemp (a negative Qactual leaves the inlet temperature)")
# fan control given the stage outlet temperatures (_Toff free convection, _Ton fan on; _T1 / _T2 low / high speed)
register("ep_tower_ss_tout", ["_Toff", "_Ton", "_Tset"], "if(_Toff > _Tset, if(_Ton <= _Tset, _Tset, _Ton), _Toff)",
         "K", SRC + " calculateSingleSpeedTower (FanCycling control, one cell)")
register("ep_tower_ss_power", ["_Toff", "_Ton", "_Tset", "_Pfan"],
         "if(_Toff > _Tset, if(_Ton <= _Tset, (_Tset - _Toff)/(_Ton - _Toff)*_Pfan, _Pfan), 0*_Pfan)", "W",
         SRC + " calculateSingleSpeedTower (FanModeFrac * fan power)")
register("ep_tower_ts_tout", ["_Toff", "_T1", "_T2", "_Tset"],
         "if(_Toff > _Tset, if(_T1 <= _Tset, _Tset, if(_T2 <= _Tset, _Tset, _T2)), _Toff)", "K",
         SRC + " calculateTwoSpeedTower", note="high-speed UA > 0 assumed (EnergyPlus tests it in the second stage)")
register("ep_tower_ts_power", ["_Toff", "_T1", "_T2", "_Tset", "_Plow", "_Phigh"],
         "if(_Toff > _Tset, if(_T1 <= _Tset, (_Tset - _Toff)/(_T1 - _Toff)*_Plow, if(_T2 <= _Tset, "
         "(_Tset - _T1)/(_T2 - _T1)*_Phigh + (1 - (_Tset - _T1)/(_T2 - _T1))*_Plow, _Phigh)), 0*_Plow)", "W",
         SRC + " calculateTwoSpeedTower (FanPower)")

# ---------------------------------------------------------------------------------------------------- C. water use
# calculateWaterUsage. _MA: air mass flow through the tower = air flow ratio * design air flow * ep_rhoair(P, Tdb, W);
# _Win the inlet humidity ratio, _Wout the SATURATED exit humidity ratio (water_use_laws writes the chain that gives
# it); _RHOW the water density (the loop fluid's, at max(mean air temperature, 4 C) for the saturated exit and at the
# mean water temperature for the loss factor — a quantity of the brick).
register("ep_tower_evap_satexit", ["_MA", "_Win", "_Wout", "_RHOW"],
         "_MA*max(_Wout/(1 + _Wout) - _Win/(1 + _Win), 0)/_RHOW", "m^3/s",
         SRC + " calculateWaterUsage (EvapLoss::MoistTheory: specific humidities, a negative loss is zero)")
# the loss factor: EnergyPlus multiplies the input field (documented in percent per K) by the temperature drop and the
# water volume flow AS IT IS — no division by 100 anywhere in CondenserLoopTowers.cc (drift, beside it, is divided).
# _F is therefore the number EnergyPlus multiplies by, per K.
register("ep_tower_evap_lossfactor", ["_F", "_Twin", "_Tout", "_MW", "_RHOW"],
         "_F*max(_Twin - _Tout, 0*ep_K)*(_MW/_RHOW)", "m^3/s",
         SRC + " calculateWaterUsage (EvapLoss::UserFactor)")
register("ep_tower_drift", ["_Vdes", "_DF", "_AFR"], "_Vdes*_DF*_AFR", "m^3/s",
         SRC + " calculateWaterUsage (drift: design water flow * drift fraction * air flow ratio; _DF is the "
               "fraction = the percent field / 100)")
# blowdown by concentration ratio: evaporation/(ratio - 1) - drift for a ratio ABOVE 2; at 2 or below EnergyPlus's
# "protect divide by zero" branch gives evaporation - drift (the value of ratio 2); never negative
register("ep_tower_blowdown", ["_Evap", "_Drift", "_CR"],
         "if(_CR > 2, max(_Evap/(_CR - 1) - _Drift, 0*_Evap), max(_Evap - _Drift, 0*_Evap))", "m^3/s",
         SRC + " calculateWaterUsage (Blowdown::Concentration)")


def water_use_laws(mode="SaturatedExit", standard_pressure=True):
    """The laws of a tower's water use as a chain of definitions (names are the brick's to keep or rename):
    given MA (air mass flow, kg/s), Twb, Tdb (K), P (Pa), Win (inlet humidity ratio), Q (heat rejected, W), RHOW
    (kg/m^3), Vdes (design water flow, m^3/s), DF (drift fraction), AFR (air flow ratio), CR (concentration ratio);
    for the loss factor also F (per K), Twin, Tout (K), MW (kg/s).
    -> (quantities to add, laws). SaturatedExit: the exit air is saturated at the enthalpy the heat gives it; its
    saturation temperature is EnergyPlus's PsyTsatFnHPb — at standard pressure its own fits (ep_tsat_h_std), elsewhere
    the implicit law hsat(Tsat, P) == h_out (standard_pressure=False: `search` 0..80 C)."""
    q = {"Evap": {"role": "derived", "unit": "m^3/s"}, "Drift": {"role": "derived", "unit": "m^3/s"},
         "Blowdown": {"role": "derived", "unit": "m^3/s"}, "Makeup": {"role": "derived", "unit": "m^3/s"}}
    src = SRC + " calculateWaterUsage"
    laws = []
    if mode == "SaturatedExit":
        q.update({"h_out": {"role": "derived", "unit": "J/kg"}, "Wout": {"role": "derived", "unit": ""},
                  "Tsat_out": {"role": "derived", "unit": "K"}})
        laws.append({"zfl": "h_out == ep_hsat(Twb, P) + Q/MA", "source": src + ": exit air enthalpy"})
        if standard_pressure:
            laws.append({"zfl": "Tsat_out == ep_tsat_h_std(h_out)", "source": "PsyTsatFnHPb at standard pressure"})
        else:
            q["Tsat_out"]["search"] = ["273.15", "353.15"]
            # an implicit law reads given quantities only: the exit enthalpy is written out in it (Q, MA given)
            laws.append({"zfl": "ep_h(Tsat_out, ep_w_tdbtwbpb(Tsat_out, Tsat_out, P)) == ep_hsat(Twb, P) + Q/MA",
                         "source": "PsyTsatFnHPb off standard pressure: the root EnergyPlus iterates to"})
        laws.append({"zfl": "Wout == ep_w_tdbh(Tsat_out, h_out)", "source": src + ": saturated exit humidity ratio"})
        laws.append({"zfl": "Evap == ep_tower_evap_satexit(MA, Win, Wout, RHOW)", "source": src + ": MoistTheory"})
    elif mode == "LossFactor":
        laws.append({"zfl": "Evap == ep_tower_evap_lossfactor(F, Twin, Tout, MW, RHOW)", "source": src + ": UserFactor"})
    else:
        raise ValueError(f"evaporation mode {mode!r}: SaturatedExit or LossFactor")
    laws += [{"zfl": "Drift == ep_tower_drift(Vdes, DF, AFR)", "source": src + ": drift"},
             {"zfl": "Blowdown == ep_tower_blowdown(Evap, Drift, CR)", "source": src + ": blowdown by concentration"},
             {"zfl": "Makeup == Evap + Drift + Blowdown", "source": src + ": makeup"}]
    return q, laws
