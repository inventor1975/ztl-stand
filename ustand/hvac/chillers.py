# -*- coding: utf-8 -*-
"""Layer 4: CHILLERS, ported from EnergyPlus 26.2.0 src/EnergyPlus/ChillerElectricEIR.cc (ElectricEIRChillerSpecs::
calculate) and ChillerReformulatedEIR.cc (ReformulatedEIRChillerSpecs::calculate / control) (DESIGN-HVAC.md).

The three performance curves come through layer 2 (`curve(NAME, ...)`); these templates are what EnergyPlus does
AROUND them, in its order:
    CapFT   = max(curve CAPFT(leaving chilled-water SETPOINT, condenser temperature), 0)
    Avail   = RefCap * CapFT                                             ep_chiller_avail
    Qevap   = min(|load|, Avail * MaxPLR)  [and the low-temperature limit]  ep_chiller_qevap, ep_chiller_qevap_lim
    PLR0    = max(0, min(Qevap/Avail, MaxPLR))        (0 when Avail = 0)
    FRAC    = min(1, PLR0/MinPLR) below MinPLR, else 1 (cycling)          ep_chiller_frac   — from PLR0, BEFORE:
    PLR     = max(PLR0, MinUnloadRatio)                                   ep_chiller_plr
    Qfalse  = Avail*PLR*FRAC - Qevap, zero below SmallLoad (hot-gas bypass) ep_chiller_falseload
    Power   = (Avail/COP) * max(EIRFPLR, 0) * max(EIRFT, 0) * FRAC         ep_chiller_power
    Qcond   = Power * (fraction to the condenser) + Qevap + Qfalse         ep_chiller_qcond
    Tcond,out = Qcond / mcond / cp + Tcond,in                              ep_chiller_tcondout
Chiller:Electric:EIR reads CAPFT and EIRFT at the ENTERING condenser temperature and EIRFPLR at PLR.
Chiller:Electric:ReformulatedEIR reads all three at the LEAVING condenser temperature (EIRFPLR is a function of
(leaving condenser temperature, PLR)), which depends on Qcond: EnergyPlus solves
    Tco == Tci + Qcond(Tco)/(mcond*cp)                 — an IMPLICIT law, Tco searched between the lowest minimum and
the highest maximum that the three curves state for it (General::SolveRoot, |residual| < 1e-4 K). Its reference COP
of zero or less is replaced by 5.5 (ep_chiller_cop_reform).
The chilled water leaves AT its setpoint in these laws (the load is what the flow and the setpoint ask for):
EnergyPlus reads CAPFT at the setpoint and EIRFT at the actual leaving temperature — the same number here.

chiller_from_idf(text, name) reads a Chiller:Electric:EIR or :ReformulatedEIR object and its three curves from an
IDF text (datasets/Chillers.idf) and returns the curves, quantities and laws of a brick.

NOT ported, said: the evaporator flow modes (constant / leaving-setpoint-modulated flow resolution, the plant's
flow lock and its mass-flow tolerances); heat recovery; the thermosiphon; the fault models; sizing; the
Lift form of the reformulated EIRFPLR; the reformulated chiller's fallbacks when the root is not bracketed
(it then substitutes twice from the mean of the two end results, or evaluates at the entering temperature);
the 1e-4 K sliver of the low-temperature limit (DataPlant::DeltaTempTol). Two constants live outside the ported
files and are therefore ARGUMENTS: HVAC::SmallLoad and Constant::InitConvTemp.
"""
from __future__ import annotations

import re

from . import register

SRC = "EnergyPlus 26.2.0, src/EnergyPlus/ChillerElectricEIR.cc ElectricEIRChillerSpecs::calculate"
SRC_R = "EnergyPlus 26.2.0, src/EnergyPlus/ChillerReformulatedEIR.cc ReformulatedEIRChillerSpecs::calculate"

register("ep_chiller_avail", ["_RefCap", "_CapFT"], "_RefCap*max(_CapFT, 0)", "W",
         SRC + " (AvailChillerCap; a negative curve value is zero)")
register("ep_chiller_qevap", ["_Load", "_Avail", "_MaxPLR"], "min(_Load, _Avail*_MaxPLR)", "W",
         SRC + " (QEvaporator = |MyLoad|, cut at AvailChillerCap * MaxPartLoadRat)")
register("ep_chiller_qevap_lim", ["_Load", "_Avail", "_MaxPLR", "_ME", "_CP", "_Tin", "_Tlow"],
         "min(min(_Load, _ME*_CP*max(_Tin - _Tlow, 0*ep_K)), _Avail*_MaxPLR)", "W",
         SRC + " (the same with the leaving chilled-water lower temperature limit: the evaporator cannot cool "
               "below it)")
_P0 = "if(_Avail/ep_W > 0, max(0, min(_Q/_Avail, _MaxPLR)), 0)"
register("ep_chiller_plr", ["_Q", "_Avail", "_MinUnl", "_MaxPLR"],
         "if(_Avail/ep_W > 0, max(max(0, min(_Q/_Avail, _MaxPLR)), _MinUnl), 0)", "",
         SRC + " (ChillerPartLoadRatio: never below the minimum unloading ratio while capacity is available)")
register("ep_chiller_frac", ["_Q", "_Avail", "_MinPLR", "_MaxPLR"],
         f"if({_P0} < _MinPLR, min(1, ({_P0})/_MinPLR), 1)", "",
         SRC + " (ChillerCyclingRatio FRAC, from the part load ratio BEFORE the minimum unloading ratio is applied)")
_FL = "(_Avail*_PLR*_FRAC - _Q)"
register("ep_chiller_falseload", ["_Q", "_Avail", "_PLR", "_FRAC", "_Small"],
         f"if({_FL} < _Small, 0*_Small, {_FL})", "W",
         SRC + " (ChillerFalseLoadRate; _Small = HVAC::SmallLoad, defined outside the ported files)")
register("ep_chiller_power", ["_Avail", "_COP", "_EIRFT", "_EIRFPLR", "_FRAC"],
         "(_Avail/_COP)*max(_EIRFPLR, 0)*max(_EIRFT, 0)*_FRAC", "W", SRC + " (Power; negative curve values are zero)")
register("ep_chiller_qcond", ["_Power", "_Fcond", "_Q", "_False"], "_Power*_Fcond + _Q + _False", "W",
         SRC + " (QCondenser)")
register("ep_chiller_tcondout", ["_QC", "_MC", "_CP", "_Tci"], "_QC/_MC/_CP + _Tci", "K", SRC + " (CondOutletTemp)")
register("ep_chiller_condflow", ["_M", "_Mmax", "_MinRatio"], "max(min(_M, _Mmax), _MinRatio*_Mmax)", "kg/s",
         SRC + " (condenser flow after the control: not above the maximum, not below the minimum flow fraction; "
               "the branch pump's own minimum is not ported)")
register("ep_chiller_cop_reform", ["_COP"], "if(_COP <= 0, 5.5, _COP)", "",
         SRC_R + " (ReferenceCOP <= 0 is replaced by 5.5)")
# evaporatively-cooled condenser: the air leaves saturated at the wet bulb; water use over RhoH2O(_Tconv),
# _Tconv = Constant::InitConvTemp (defined outside the ported files)
register("ep_chiller_evapcond_water", ["_MC", "_Win", "_Twb", "_P", "_Tconv"],
         "(ep_w_tdbtwbpb(_Twb, _Twb, _P) - _Win)*_MC/ep_rho_h2o(_Tconv)", "m^3/s",
         SRC + " (EvapWaterConsumpRate of an EvaporativelyCooled condenser)")


# ------------------------------------------------------------------------------------------------- from an IDF
def _sub(text, mapping):
    pat = "|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True))
    return re.sub(rf"(?<![\w.])({pat})(?![\w])", lambda m: f"({mapping[m.group(1)]})", text)


def chiller_spec_from_idf(text, name):
    """the Chiller:Electric:EIR / :ReformulatedEIR object called `name` and its three curves, from an IDF text"""
    from . import curves as CV
    objs = CV.idf_objects(text)
    hit = [(c, f) for c, f in objs if c.lower() in ("chiller:electric:eir", "chiller:electric:reformulatedeir")
           and f and f[0].lower() == name.lower()]
    if not hit:
        raise ValueError(f"no Chiller:Electric:EIR or :ReformulatedEIR called {name!r} in the IDF text")
    cls, f = hit[0]
    reform = cls.lower().endswith("reformulatedeir")
    f = f + [""] * 40
    spec = {"name": f[0], "type": "ReformulatedEIR" if reform else "EIR", "RefCap": f[1], "COP": f[2],
            "Tref_chw": f[3], "Tref_cond": f[4], "Vchw_ref": f[5], "Vcond_ref": f[6]}
    if reform:
        kind = f[9] or "LeavingCondenserWaterTemperature"
        if kind.lower() != "leavingcondenserwatertemperature":
            raise ValueError(f"{name}: EIRFPLR curve type {kind!r} — only LeavingCondenserWaterTemperature is ported")
        cnames = {"CAPFT": f[7], "EIRFT": f[8], "EIRFPLR": f[10]}
        spec.update({"MinPLR": f[11], "MaxPLR": f[12], "OptPLR": f[13], "MinUnl": f[14], "Fcond": f[19] or "1.0",
                     "Tlow": f[20], "condenser": "WaterCooled"})
    else:
        cnames = {"CAPFT": f[7], "EIRFT": f[8], "EIRFPLR": f[9]}
        spec.update({"MinPLR": f[10], "MaxPLR": f[11], "OptPLR": f[12], "MinUnl": f[13],
                     "condenser": f[18] or "WaterCooled", "FanPowerRatio": f[19], "Fcond": f[20] or "1.0",
                     "Tlow": f[21]})
    for k in ("COP", "MinPLR", "MaxPLR", "MinUnl"):
        try:
            float(spec[k])
        except ValueError:
            raise ValueError(f"{name}: {k} is {spec[k]!r} — not a number")
    try:
        float(spec["RefCap"])
    except ValueError:
        spec["RefCap"] = None          # 'Autosize' (the dataset's generic DOE-2 chillers): the brick states RefCap
    curves = {}
    byname = {}
    for c, fl in objs:
        if c.lower().startswith("curve:") and fl:
            byname.setdefault(fl[0].lower(), (c, fl))
    for role, cn in cnames.items():
        if cn.lower() not in byname:
            raise ValueError(f"{name}: its {role} curve {cn!r} is not in the IDF text")
        _, cs = CV.curve_from_idf(*byname[cn.lower()])
        n = CV.TYPES[cs["type"]][0]
        want = {"CAPFT": 2, "EIRFT": 2, "EIRFPLR": 2 if reform else 1}[role]
        if n != want:
            raise ValueError(f"{name}: its {role} curve {cn!r} has {n} inputs, not {want}")
        # what EnergyPlus feeds each curve: temperatures in deg C, the part load ratio a pure number
        cs["inputs"] = {"CAPFT": ["degC", "degC"], "EIRFT": ["degC", "degC"],
                        "EIRFPLR": ["degC", ""] if reform else [""]}[role]
        cs["idf_name"] = cn
        curves[role] = cs
    spec["curves"] = curves
    return spec


def chiller_parts(spec, prefix="", inline=True, small_load="1"):
    """The curves, quantities and laws of a brick for one chiller (from chiller_spec_from_idf).
    The brick supplies the OPERATING quantities, by these names (with `prefix`): Load (W, the cooling asked for),
    Tchw (K, the leaving chilled-water setpoint), and
      EIR:             Tcond (K, ENTERING condenser temperature);
      ReformulatedEIR: Tcin (K, entering condenser water), Mcond (kg/s), CpCond (J/(kg*K)).
    (and RefCap, W, when the IDF object leaves it to autosizing — the dataset's generic DOE-2 chillers).
    It gets, derived: Avail, Qevap, PLR, FRAC, Qfalse, Power, Qcond (and Tco, the implicit leaving condenser
    temperature, for the reformulated chiller).
    inline=True: every law is written over the given quantities alone (its inputs expanded in it), so ZTL reads each
    with all its dependencies; inline=False: a chain of definitions (shorter laws, wider ranges).
    small_load: HVAC::SmallLoad in W — the value is NOT in the ported files (1 W is what EnergyPlus's
    DataHVACGlobals.hh is remembered to hold; confirm it against that file)."""
    p = prefix
    reform = spec["type"] == "ReformulatedEIR"
    g = f"EnergyPlus datasets, {spec['name']}"
    q = {p + "RefCap": {"role": "given", "value": spec["RefCap"], "unit": "W", "ground": g},      # dropped below if autosized
         p + "COP": {"role": "given", "value": spec["COP"], "unit": "", "ground": g},
         p + "MinPLR": {"role": "given", "value": spec["MinPLR"], "unit": "", "ground": g},
         p + "MaxPLR": {"role": "given", "value": spec["MaxPLR"], "unit": "", "ground": g},
         p + "MinUnl": {"role": "given", "value": spec["MinUnl"], "unit": "", "ground": g},
         p + "Fcond": {"role": "given", "value": spec["Fcond"], "unit": "", "ground": g},
         p + "SmallLoad": {"role": "given", "value": str(small_load), "unit": "W",
                           "ground": "HVAC::SmallLoad (DataHVACGlobals.hh — outside the ported files)"}}
    if spec["RefCap"] is None:
        del q[p + "RefCap"]            # autosized in the IDF: the brick must give RefCap (W) itself
    curves = {p + k: {kk: vv for kk, vv in v.items() if kk != "idf_name"} for k, v in spec["curves"].items()}
    tc = p + ("Tco" if reform else "Tcond")
    cop = f"ep_chiller_cop_reform({p}COP)" if reform else f"{p}COP"
    e = {}
    e["Avail"] = f"ep_chiller_avail({p}RefCap, curve({p}CAPFT, {p}Tchw, {tc}))"
    e["Qevap"] = f"ep_chiller_qevap({p}Load, Avail, {p}MaxPLR)"
    e["PLR"] = f"ep_chiller_plr(Qevap, Avail, {p}MinUnl, {p}MaxPLR)"
    e["FRAC"] = f"ep_chiller_frac(Qevap, Avail, {p}MinPLR, {p}MaxPLR)"
    e["Qfalse"] = f"ep_chiller_falseload(Qevap, Avail, PLR, FRAC, {p}SmallLoad)"
    eirfplr = f"curve({p}EIRFPLR, {tc}, PLR)" if reform else f"curve({p}EIRFPLR, PLR)"
    e["Power"] = f"ep_chiller_power(Avail, {cop}, curve({p}EIRFT, {p}Tchw, {tc}), {eirfplr}, FRAC)"
    e["Qcond"] = f"ep_chiller_qcond(Power, {p}Fcond, Qevap, Qfalse)"
    order = ["Avail", "Qevap", "PLR", "FRAC", "Qfalse", "Power", "Qcond"]
    units = {"Avail": "W", "Qevap": "W", "PLR": "", "FRAC": "", "Qfalse": "W", "Power": "W", "Qcond": "W"}
    full = {}
    for k in order:                                # each expression over the given quantities (and Tco) alone
        full[k] = _sub(e[k], full) if full else e[k]
    src = (SRC_R if reform else SRC) + f"; {spec['name']}"
    laws = []
    for k in order:
        q[p + k] = {"role": "derived", "unit": units[k]}
        rhs = full[k] if inline or reform else _sub(e[k], {n: p + n for n in order})
        laws.append({"zfl": f"{p}{k} == {rhs}", "source": f"{src}: {k}"})
    if reform:
        lo = min(float(spec["curves"][c]["x_min" if c == "EIRFPLR" else "y_min"]) for c in spec["curves"])
        hi = max(float(spec["curves"][c]["x_max" if c == "EIRFPLR" else "y_max"]) for c in spec["curves"])
        q[tc] = {"role": "derived", "unit": "K", "search": [repr(round(lo + 273.15, 6)), repr(round(hi + 273.15, 6))]}
        laws.insert(0, {"zfl": f"{tc} == ep_chiller_tcondout({full['Qcond']}, {p}Mcond, {p}CpCond, {p}Tcin)",
                        "source": f"{SRC_R.replace('calculate', 'control')}: the leaving condenser temperature it "
                                  f"iterates to; {spec['name']}"})
    return {"curves": curves, "quantities": q, "laws": laws}


def chiller_from_idf(text, name, prefix="", inline=True, small_load="1"):
    """IDF text + the chiller's name -> {"curves", "quantities", "laws"} to merge into a brick (see chiller_parts)"""
    return chiller_parts(chiller_spec_from_idf(text, name), prefix=prefix, inline=inline, small_load=small_load)
