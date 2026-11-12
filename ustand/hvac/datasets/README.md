# EnergyPlus datasets (unchanged copies)

`PerfCurves.idf` and `Chillers.idf` from EnergyPlus version 26.2.0 (github.com/NREL/EnergyPlus, tag v26.2.0,
`datasets/`), copied byte for byte; redistributed under the EnergyPlus licence (`../NOTICE-EnergyPlus.txt`).
EnergyPlus does not endorse this port. `tests/test_hvac.py` reads every curve here against `curves.py`.

sha256: PerfCurves.idf 92ed74036aa0..., Chillers.idf 6536996325fd... (`sha256sum` for the full value).

`../sources/CondenserLoopTowers.cc` — the same release's source file, unchanged: `tests/test_hvac_plant.py` reads the
CoolTools / YorkCalc coefficient sets from it by code and checks them against `towers.py`.
