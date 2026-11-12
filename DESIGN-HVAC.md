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
