# -*- coding: utf-8 -*-
"""Layer 1: PSYCHROMETRICS, ported from EnergyPlus 26.2.0 src/EnergyPlus/Psychrometrics.hh / .cc (DESIGN-HVAC.md).

Each function is one template (see ustand/hvac/__init__.py). Arguments: _T, _Tdp, _Twb absolute temperatures (K);
_W humidity ratio (kg water / kg dry air, a pure number); _P barometric pressure (Pa); _RH relative humidity (0..1);
_H enthalpy (J/kg). EnergyPlus's own guards are kept where they change a value (max(w, 1e-5), the clamps); its
WARNINGS are not (the stand states the domain instead). Not ported, said: the saturation-pressure CACHE of
PsyPsatFnTemp (EnergyPlus evaluates the formula at the temperature with its mantissa truncated to a grid — a relative
change below ~1e-7); the IF97 variant (compiled only with EP_IF97); PsyWFnTdpPb's walk-down when Psat(Tdp) >= Pb.
Iterative EnergyPlus functions (PsyTwbFnTdbWPb, PsyTsatFnPb, PsyTsatFnHPb, PsyTdpFnWPb) are IMPLICIT laws over these:
e.g. the wet bulb Twb of (T, W, P) is the derived quantity with `search` fixed by W == ep_w_tdbtwbpb(T, Twb, P).
"""
from . import register

SRC = "EnergyPlus 26.2.0, src/EnergyPlus/Psychrometrics"
TK = "(_T/ep_K)"                  # absolute temperature, a pure number (K)
TC = "(_T/ep_K - 273.15)"         # Celsius, as EnergyPlus writes T (Constant::Kelvin = 273.15)

# PsyPsatFnTemp (raw): Hyland-Wexler, ASHRAE Fundamentals 2005 ch. 6 eq. 5 (ice, below the triple point 273.16 K) and
# eq. 6 (water); clamped outside 173.15..473.15 K to the values EnergyPlus returns there
_ICE = ("exp(-5674.5359/Tk + 6.3925247 + Tk*(-0.9677843e-2 + Tk*(0.62215701e-6 + Tk*(0.20747825e-8 + "
        "(-0.9484024e-12)*Tk))) + 4.1635019*ln(Tk))")
_WATER = "exp(-5800.2206/Tk + 1.3914993 + Tk*(-0.048640239 + Tk*(0.41764768e-4 + Tk*(-0.14452093e-7))) + 6.5459673*ln(Tk))"
register("ep_psat", ["_T"],
         ("if(Tk < 173.15, 0.001405102123874164, if(Tk < 273.16, " + _ICE + ", if(Tk <= 473.15, " + _WATER +
          ", 1555073.745636215)))*ep_Pa").replace("Tk", TK),
         "Pa", SRC + ".cc PsyPsatFnTemp (raw)")

register("ep_hfg", ["_W", "_T"], f"((2500940 + 1858.95*max({TC}, 0)) - 4180*max({TC}, 0))*ep_J_kg", "J/kg",
         SRC + ".hh PsyHfgAirFnWTdb (w unused, as in EnergyPlus)")
register("ep_hg", ["_W", "_T"], f"(2500940 + 1858.95*{TC})*ep_J_kg", "J/kg", SRC + ".hh PsyHgAirFnWTdb")
register("ep_h", ["_T", "_W"], f"(1.00484e3*{TC} + max(_W, 1.0e-5)*(2.50094e6 + 1.85895e3*{TC}))*ep_J_kg", "J/kg",
         SRC + ".hh PsyHFnTdbW")
register("ep_cpair", ["_W"], "(1.00484e3 + max(_W, 1.0e-5)*1.85895e3)*ep_J_kgK", "J/(kg*K)", SRC + ".hh PsyCpAirFnW")
register("ep_tdb_hw", ["_H", "_W"],
         "((_H/ep_J_kg - 2.50094e6*max(_W, 1.0e-5))/(1.00484e3 + 1.85895e3*max(_W, 1.0e-5)) + 273.15)*ep_K", "K",
         SRC + ".hh PsyTdbFnHW (the result in K)")
register("ep_rhov_tdbwpb", ["_T", "_W", "_P"],
         f"(max(_W, 1.0e-5)*(_P/ep_Pa)/(461.52*{TK}*(max(_W, 1.0e-5) + 0.62198)))*ep_kg_m3", "kg/m^3",
         SRC + ".hh PsyRhovFnTdbWPb")
register("ep_v", ["_T", "_W", "_P"],
         f"(1.59473e2*(1 + 1.6078*max(_W, 1.0e-5))*(1.8*{TC} + 492)/(_P/ep_Pa))*ep_m3_kg", "m^3/kg",
         SRC + ".hh PsyVFnTdbWPb", note="EnergyPlus returns 0.83 for a negative volume (outside any physical "
         "domain); not ported")
register("ep_w_tdbh", ["_T", "_H"],
         f"if((_H/ep_J_kg - 1.00484e3*{TC})/(2.50094e6 + 1.85895e3*{TC}) < 0, 1.0e-5, "
         f"(_H/ep_J_kg - 1.00484e3*{TC})/(2.50094e6 + 1.85895e3*{TC}))", "", SRC + ".hh PsyWFnTdbH")
register("ep_rhov_tdbrh", ["_T", "_RH"], f"(ep_psat(_T)/ep_Pa*_RH/(461.52*{TK}))*ep_kg_m3", "kg/m^3",
         SRC + ".hh PsyRhovFnTdbRh")
_U = "(max(_W, 1.0e-5)/(0.62198*(ep_psat(_T)/ep_Pa)/(_P/ep_Pa - ep_psat(_T)/ep_Pa)))"
_RHV = f"({_U}/(1 - (1 - {_U})*((ep_psat(_T)/ep_Pa)/(_P/ep_Pa))))"
register("ep_rh_tdbwpb", ["_T", "_W", "_P"], f"if({_RHV} < 0, 0.01, if({_RHV} > 1, 1, {_RHV}))", "",
         SRC + ".hh PsyRhFnTdbWPb (outside 0..1 clamped to [0.01, 1], as EnergyPlus)")
register("ep_w_tdppb", ["_Tdp", "_P"], "(ep_psat(_Tdp)/ep_Pa)*0.62198/(_P/ep_Pa - ep_psat(_Tdp)/ep_Pa)", "",
         SRC + ".hh PsyWFnTdpPb", note="domain Psat(Tdp) < Pb; EnergyPlus's walk-down above it is not ported")
_WRH = "((_RH*ep_psat(_T)/ep_Pa)*0.62198/max(_P/ep_Pa - _RH*ep_psat(_T)/ep_Pa, 1000))"
register("ep_w_tdbrhpb", ["_T", "_RH", "_P"], f"if({_WRH} < 1.0e-5, 1.0e-5, {_WRH})", "", SRC + ".hh PsyWFnTdbRhPb")
# PsyWFnTdbTwbPb: the wet bulb clamped to the dry bulb; a negative result falls back to PsyWFnTdbRhPb(T, 0.0001, P)
_TWB = "min(_Twb, _T)"
_TWBC = f"({_TWB}/ep_K - 273.15)"
_WET = f"(0.62198*(ep_psat({_TWB})/ep_Pa)/(_P/ep_Pa - ep_psat({_TWB})/ep_Pa))"
_WW = f"(((2501.0 - 2.381*{_TWBC})*{_WET} - ({TC} - {_TWBC}))/(2501.0 + 1.805*{TC} - 4.186*{_TWBC}))"
register("ep_w_tdbtwbpb", ["_T", "_Twb", "_P"], f"if({_WW} < 0, ep_w_tdbrhpb(_T, 0.0001, _P), {_WW})", "",
         SRC + ".hh PsyWFnTdbTwbPb")
register("ep_h_tdbrhpb", ["_T", "_RH", "_P"], "ep_h(_T, ep_w_tdbrhpb(_T, _RH, _P))", "J/kg", SRC + ".hh PsyHFnTdbRhPb")

# PsyTsatFnHPb at STANDARD pressure (|Pb - 101330| <= 1 %): EnergyPlus's own piecewise polynomial fits in
# HH = H + 1.78637e4 (F6 = A0 + X(A1 + X(A2 + ...)), F7 the same / 1e10), the case k where CaseRange[k-1] < HH <= CaseRange[k],
# HH clamped to [-4.24e4, 4.5866e7]. Off standard pressure EnergyPlus iterates (secant) on
# ep_h(T, ep_w_tdbtwbpb(T, T, Pb)) = H from this start — in a brick that is an IMPLICIT law over those two.
def _f6(a):
    return f"({a[0]} + HH*({a[1]} + HH*({a[2]} + HH*({a[3]} + HH*({a[4]} + HH*({a[5]}))))))"


_CASES = [(-2.2138e4, ["-19.44", "8.53675e-4", "-5.12637e-9", "-9.85546e-14", "-1.00102e-18", "-4.2705e-24"]),
          (-6.7012e2, ["-1.94224e1", "8.5892e-4", "-4.50709e-9", "-6.19492e-14", "8.71734e-20", "8.73051e-24"]),
          (2.7297e4, ["-1.94224e1", "8.59061e-4", "-4.4875e-9", "-5.76696e-14", "7.72217e-19", "3.97894e-24"]),
          (7.5222e4, ["-2.01147e1", "9.04936e-4", "-6.83305e-9", "2.3261e-14", "7.27237e-20", "-6.31939e-25"]),
          (1.8379e5, ["-1.82124e1", "8.31683e-4", "-6.16461e-9", "3.06411e-14", "-8.60964e-20", "1.03003e-25"]),
          (4.7577e5, ["-1.29419", "3.88538e-4", "-1.30237e-9", "2.78254e-15", "-3.27225e-21", "1.60969e-27"]),
          (1.5445e6, ["2.39214e1", "1.27519e-4", "-1.52089e-10", "1.1043e-16", "-4.33919e-23", "7.05296e-30"]),
          (3.8353e6, ["4.88446e1", "3.85534e-5", "-1.78805e-11", "4.87224e-18", "-7.15283e-25", "4.36246e-32"])]
_F7 = ("((7.60565e11 + HH*(5.80534e4 + HH*(-7.36433e-3 + HH*(5.11531e-10 + HH*(-1.93619e-17 + HH*(3.70511e-25 + "
       "HH*(-2.77313e-33)))))))/1.0e10)")
_tsat = _F7
for hi, a in reversed(_CASES):
    _tsat = f"if(HH <= {hi}, {_f6(a)}, {_tsat})"
# the clamps: case 1 evaluates at max(HH, -4.24e4), case 9 at min(HH, 4.5866e7); a clamp on HH as a whole is the same
_HH = "min(max(_H/ep_J_kg + 1.78637e4, -4.24e4), 4.5866e7)"
register("ep_tsat_h_std", ["_H"], f"({_tsat.replace('HH', _HH)} + 273.15)*ep_K", "K",
         SRC + ".cc PsyTsatFnHPb (the standard-pressure fits; the result in K)",
         note="valid at |Pb - 101330 Pa| <= 1 % only, where EnergyPlus uses the fits alone")

# The relation EnergyPlus's PsyTwbFnTdbWPb SOLVES (it iterates WBT until W = newW): newW over liquid water for
# Twb >= 0 C, over ice below (ASHRAE Fundamentals 2009 ch. 1 eq. 33 / 35 — NOT the coefficients of PsyWFnTdbTwbPb).
# The wet bulb of (T, W, Pb) is the root Twb of W == ep_w_twb_newW(T, Twb, Pb): an implicit law. Not ported: the
# clamp WBT <= tBoil - 0.1 near boiling.
_WS = "(0.62198*(ep_psat(_Twb)/ep_Pa)/(_P/ep_Pa - ep_psat(_Twb)/ep_Pa))"
_TWC = "(_Twb/ep_K - 273.15)"
register("ep_w_twb_newW", ["_T", "_Twb", "_P"],
         f"if({_TWC} >= 0, ((2501.0 - 2.326*{_TWC})*{_WS} - 1.006*({TC} - {_TWC}))/(2501.0 + 1.86*{TC} - 4.186*{_TWC}), "
         f"((2830.0 - 0.24*{_TWC})*{_WS} - 1.006*({TC} - {_TWC}))/(2830.0 + 1.86*{TC} - 2.1*{_TWC}))", "",
         SRC + ".cc PsyTwbFnTdbWPb (the residual it iterates)")
