# HVAC plant models in the stand — ported from EnergyPlus (design in words, 2026-11-12)

The curator's word (2026-11-12): "if it goes into the stand, then in full — not only the hackathon task". So this is a
DOMAIN of the stand, like structures or conduction: the models a plant designer uses, each one usable in any brick, each
one checked against its source's own tests, each one proved by ZTL like every other law.

## Source and licence

EnergyPlus v26.2.0 (github.com/NREL/EnergyPlus, tag v26.2.0, released 2026-09-30), the files under
ext-data/energyplus/v26.2.0 (src/EnergyPlus: Psychrometrics, CurveManager, CondenserLoopTowers, ChillerElectricEIR,
ChillerReformulatedEIR, General; tst/EnergyPlus/unit: the same; datasets/PerfCurves.idf, Chillers.idf). Its licence is a
BSD-3-style licence with a fourth clause on the name: a port keeps the copyright notice (ustand/hvac/NOTICE-EnergyPlus.txt,
quoted in each module's header) and refers to "EnergyPlus version 26.2.0" — never implying endorsement. NOT the copy that
a PLE dev task carries: that copy is benchmark data (HF terms: no redistribution).

## How a model enters a brick: library functions

A law may call a LIBRARY FUNCTION, e.g. `Pw == ep_psat(T)` (prefix `ep_` — never a quantity name). The brick compiler
EXPANDS the call into its ZFL expression before anything else reads the law, exactly like a define, with the arguments
substituted in parentheses. So:
- ZTL proves the expanded law as it proves any law — sound ranges, exact refutation points; nothing new in the judge;
- the unit check sees the expansion: each template divides its inputs by built-in unit constants (`__K1` = 1 K,
  `__Pa1` = 1 Pa, ...) so that exp and ln read pure numbers, and multiplies the result by its unit;
- branches of a piecewise formula (EnergyPlus's `if (Tkel < 273.16) ... else ...`) are the stand's `if(...)`;
- one template per function is the ONLY definition: the Python evaluation used by the tests reads the same template
  (no second hand-written copy to drift).
Iterative EnergyPlus functions (wet bulb from dry bulb and humidity ratio, saturation temperature from pressure) are
NOT templates: they are the inverse of an explicit one, written as an IMPLICIT law (a derived quantity with `search`),
which the stand already proves (zimplicit's root-exclusion certificate). The library documents the pairing.

## Layers (each done and verified before the next)

1. **Psychrometrics** (Psychrometrics.hh/.cc): saturation pressure (Hyland-Wexler over ice and water), humidity ratio from
   dew point / wet bulb / relative humidity, enthalpy, specific heat, latent heat, density, specific volume, relative
   humidity, dry bulb from enthalpy; the iterative ones as implicit pairs.
2. **Performance curves** (CurveManager): every curve type EnergyPlus defines that a plant uses — linear, quadratic,
   cubic, quartic, biquadratic, bicubic, triquadratic, quadratic-linear, cubic-linear, exponent, ... — with the input
   CLAMPING to the stated limits and the output limits (min/max), as EnergyPlus evaluates them.
3. **Cooling towers** (CondenserLoopTowers): the variable-speed approach correlations (CoolTools, YorkCalc and the
   user-defined coefficient form) with their validity limits and the wet-bulb clamping, fan power vs air-flow ratio,
   evaporation (the saturated-exit and the loss-factor formulations), drift, blowdown by cycles of concentration;
   single- and two-speed towers (UA by the effectiveness-NTU model) and the Merkel variable-speed tower as the next step
   within the layer.
4. **Chillers** (ChillerElectricEIR, ChillerReformulatedEIR): capacity f(T), EIR f(T), EIR f(PLR), the reformulated
   form on the leaving condenser temperature, minimum unloading, condenser heat.
5. What layers 3-4 need besides: water properties at the needed accuracy, fans, pumps.

## Status (2026-11-12): layers 1-4 done; what each does NOT hold

Layers 1 and 2: ustand/hvac/psychro.py, curves.py (tests/test_hvac.py). Layers 3 and 4: ustand/hvac/towers.py,
chillers.py (tests/test_hvac_plant.py; the functions and example bricks are in BRICKS.md 7i).

**Layer 3, cooling towers — ported** (each against the C++ transcribed by hand in the test):
- the approach correlations of CoolingTower:VariableSpeed, CoolToolsCrossFlow and YorkCalc with their built-in
  coefficients (read back from CondenserLoopTowers.cc by the test), capped as the operating tower caps them, and raw;
  the user-defined coefficient objects CoolingTowerPerformance:CoolTools / :YorkCalc as curve types read from IDF;
- what EnergyPlus solves, as implicit laws: the range at a fixed fan speed, the air flow ratio that meets the
  setpoint, the calibration of the water flow ratio at sizing;
- the control sequence of calculateVariableSpeedTower (full speed / free convection / cycling at the minimum air
  flow / modulating): outlet temperature, cycling ratio, air flow ratio, fan power (the cube law or a fan curve);
- the UA tower of CoolingTower:SingleSpeed / :TwoSpeed (calculateSimpleTowerOutletTemp, effectiveness-NTU): one pass
  as a template, the fixed point of its iteration as an implicit law; the fan cycling of both towers;
- water use: evaporation by the saturated-exit method and by the loss factor, drift, blowdown by concentration
  ratio, makeup (a scheduled blowdown is a given quantity in `Makeup == Evap + Drift + Blowdown`).

EnergyPlus's capping, as found in the code (checkModelBounds): the inlet wet bulb is clamped to the model's limits
before every evaluation; the water flow ratio is clamped for the CoolTools models ONLY (for YorkCalc it only warns,
on the liquid-to-gas ratio); the range and the approach are compared with their limits for a warning and the capped
values are never used; the air flow ratio is not clamped, the solver keeps it in [minimum, 1]. The setpoint's
approach is formed from the UNCAPPED wet bulb while the model reads the capped one.

**Layer 3 — NOT ported**: multi-cell staging; the fluid-bypass control of the single-speed tower; basin heater;
fault models; sizing (UA from nominal capacity, autosized flows) other than the variable-speed calibration; the
control sequence of CoolingTower:VariableSpeed:Merkel (its tower is the UA tower with UA multiplied by three
curves, which a brick writes with `curve(...)`; the load-following sequence around it is not written); the water
properties of the loop (density, specific heat: FluidProperties is not among the ported files — they are quantities
of the brick, so no EnergyPlus test that depends on them at 1e-3 is reproduced).

**Layer 4, chillers — ported**: Chiller:Electric:EIR (available capacity, the evaporator load and its cuts, part
load ratio, cycling below the minimum part load ratio, the minimum unloading ratio and false loading, power,
condenser heat, condenser outlet temperature, the condenser-flow limits, the evaporatively-cooled condenser's water
use) and Chiller:Electric:ReformulatedEIR (all three curves on the LEAVING condenser temperature — an implicit law);
`chiller_from_idf` builds the curves, quantities and laws of a brick from an IDF chiller object (every chiller of
datasets/Chillers.idf: 162 EIR, 161 reformulated).

**Layer 4 — NOT ported**: the evaporator flow modes and the plant's flow lock (the laws take the load the
evaporator is asked for and the leaving water at its setpoint); heat recovery; thermosiphon; faults; sizing and
the rated-performance (IPLV) report; the Lift form of the reformulated EIRFPLR; the reformulated chiller's
fallbacks when its root is not bracketed by the curve limits (EnergyPlus then substitutes twice from the mean of
its two end results — MEASURED on a sweep of the dataset: 87 of 483 operating points end that way; a brick there
has no root in `search` and is OPEN). Two constants are outside the ported files and are arguments:
HVAC::SmallLoad (1 W from memory of DataHVACGlobals.hh — to confirm) and Constant::InitConvTemp (5.05 C —
confirmed by EnergyPlus's own test value at 1e-9).

**Verified** (tests/test_hvac_plant.py; the numbers are printed by the test as MEASURED lines):
templates = the C++ by hand to 3e-14 (approach, 6000 points inside and outside the limits), 4e-13 (UA tower pass),
3e-12 (water use), 8e-15 (EIR chillers, 972 points over the whole dataset); EnergyPlus's iterates against the roots
of the implicit laws: tower outlet within 7e-5 K, air flow ratio 3e-5 (400 points, cube law and a fan power curve), the UA tower's outlet within 4e-4 K (its
iteration's own stopping error), the reformulated chiller's leaving condenser temperature within 6e-5 K.
EnergyPlus's own unit-test values reproduced at their tolerances: tower outlet 26.9537 C, FanCyclingRatio 0.5424,
outlet 30.0 C at the solved air flow, 40 - 22.2222 C beyond the model's range (CondenserLoopTowers.unit.cc);
condenser flow 2.31460814 kg/s, evaporative water use 6.22019725e-06 m3/s, power 20987 W, the condenser-flow
fractions (ChillerElectricEIR.unit.cc). NOT reproduced, and why: the sizing tests (UA 7389.232 W/K, air flows,
nominal capacities: they need the water tables and the sizing routines), the input-default and report-table tests
(no such objects here), the basin-heater test, the Merkel test, IPLV 2.03 (StandardRatings), the thermosiphon
tests.

**In the stand** (fifteen bricks, nine EARNED and six REFUTED with the refuting point recomputed by the
transcription; seconds MEASURED on this machine, six at a time): a CoolTools tower's outlet over a wet-bulb range
against a condenser limit (36 s), the air flow ratio that meets a setpoint and its fan power (24 s), the control
sequences as explicit laws (under 1 s), makeup water by the saturated-exit chain (280 s EARNED, under 1 s REFUTED)
and by the loss factor, a UA tower's outlet proved within 0.02 K of EnergyPlus's own iterate (240 s), an EIR
chiller's power over a load and condenser-temperature box (4 s), a reformulated chiller's power with its leaving
condenser temperature implicit (146 s EARNED, 18 s REFUTED).

**A gap of the stand found here** (not of the port): the UA tower with every given exact could not be REFUTED.
Four runs (641..728 s each) with a bound the proved range lies wholly past — `Tout <= 302.35 K`, `Tout <= 301.4 K`, `X <= 304.6 K`,
a window below the value — ended OPEN: "proved within [302.4, 302.4] K, which reaches past the bound, yet no
corner violates it". The range is PROVED to be on the wrong side, and the verdict is still OPEN, because the
refutation wants a corner witness and none is found for this long implicit law. The shorter implicit laws (tower
range, air flow ratio, the reformulated chiller) are refuted normally.

**Found in EnergyPlus while porting** (each read in the code, the first two also measured by the test):
- datasets/PerfCurves.idf states the built-in YorkCalc model as a user-defined object with a maximum wet bulb of
  26.6667 C; the code's built-in YorkCalc uses 29.4444 C. Above 26.6667 C the "same" model gives different
  approaches.
- The evaporation LOSS FACTOR (documented in percent per K) is multiplied as entered — nothing divides it by 100,
  while the drift percent beside it is divided. With the field's default 0.2 the "evaporation" of a 5.5 K range
  is 1.1 times the whole water flow.
- checkModelBounds computes capped values of the range and of the approach and never uses them; the water flow
  ratio is capped for CoolTools only.
- In calculateVariableSpeedTower the outlet at full fan is compared with the setpoint by `>` and then by `<`: at
  exact equality neither branch runs and the tower reports the INLET temperature with zero fan power.
- At full speed the fan power is the design power itself, not design power times the fan curve at 1.
- Blowdown: a concentration ratio of 2 or less is treated as 2 ("protect divide by zero" at `> 2.0`).
- The UA tower's effectiveness switches to NTU/(1 + NTU) (the equal-capacity limit) above a capacity ratio of
  0.995 — a small jump in the outlet temperature across that line.
- The EIR chiller reads CAPFT at the leaving-water SETPOINT and EIRFT at the actual leaving temperature; the
  cycling ratio is taken from the part load ratio BEFORE the minimum unloading ratio is applied.
- The reformulated chiller replaces a reference COP of zero or less by 5.5, silently.
- The reformulated chiller solves its leaving condenser temperature only when the results at the two curve limits
  fall strictly inside them; otherwise it substitutes twice — on our sweep of the dataset that was 87 of 483 points.

## Verification, per function

- EnergyPlus's own unit tests (tst/EnergyPlus/unit/*.unit.cc): every reference value they assert becomes a stand check
  at their tolerance.
- Where a test is missing, the function's REFERENCES in the source (ASHRAE Fundamentals values the comments cite) or a
  sweep against the C++ formula re-evaluated in double precision (the port must agree to rounding).
- A PLANTED error per layer (a changed coefficient, a lost branch, a lost clamp) must turn a check RED.
- What "proved" means here, said in every output's `rests_on`: the EnergyPlus correlation is the model; ZTL proves what
  the correlation gives over the input box, not that the correlation is physics (ASHRAE's 0.3 % on Hyland-Wexler stays
  the correlation's own error).

## Not in scope of v1

Running EnergyPlus itself; whole-building loads; controls and time stepping (the brick's modes and stocks carry
operating points); refrigerant properties.
