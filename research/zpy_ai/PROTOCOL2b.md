# zpy AI experiment — round 2b (written 2026-11-10, BEFORE the runs)

Round 2 (RESULTS2.md): both zpy runs routed around the layer to reach the classical reading the task asks for.
The curator's answer: «если IF STABLE, то только классический путь» — the path made LEGAL BUT NAMED:
zpy.decide(..., if_stable="classical" | "check") is required; the result carries .path ("ztl" / "classical" /
"check"); zpy_lint BYPASS flags a hand reading of an IF STABLE label.

Round 2b: arm B only, two new runs (B3, B4), the same TASKS2.md, the same sealed grade2.py (9d49a65), the same
prompt as round 2's B arm. zpy.py as the models read it: sha256 4e8cabf4a339a22a…

Finding would be: B code no longer routes around the layer (no BYPASS, no hand enumeration), classical-correct, and
its length against round 2's plain arm (65 lines).
