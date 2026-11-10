# CAD/FEA level 1 — a mesh's own proof (2026-11-10)

`ustand/cadmesh.py` (OBJ / STL, own reader, integer arithmetic; tests/test_cadmesh.py 16 checks). On SimJEB bracket
148 (MIT, CC0/ODC-BY; the CAD from GrabCAD, non-commercial — the files are NOT in this repo, they live in
Projects/ext-data/simjeb): closed, oriented, genus 12, no self-intersection among 7662 candidate pairs, volume
130190.585221618 mm^3 = the dataset's number, area 44242.2567912664 mm^2 (a bracket), in 2.4 s. The volume of the
dataset's own tetrahedral mesh (640197 tets, exact): 130190.58558612 — the two meshes agree to 3e-9.

**A premise conflict inside the dataset.** The metadata's mass is volume x 4.47e-6 kg/mm^3 for ALL 381 brackets
(min = max = 4.47e-6 to 1e-15); the FEA deck of bracket 148 carries MAT1 density 4.43e-9 t/mm^3 (= 4.43e-6 kg/mm^3).
Two densities for one material in one dataset, 0.9 % apart. Not claimed to be an error (Ti-6Al-4V is quoted at
several values); claimed: the two premises differ, and a mass requirement within 1 % would turn on which is read.

## All 381 SimJEB brackets (2026-11-10 00:55, research/cad/simjeb_level1.py; results simjeb_level1_results.jsonl)

1 min 31 s on 16 cores (median 2.9 s a part, max 36.6 s). Against the dataset's own metadata:

| | result |
|---|---|
| read, closed, oriented | 381 / 381 |
| vertex and face counts | = metadata, 381 / 381 |
| volume | = metadata to 4.7e-16 relative (the float's last digit), 381 / 381 |
| surface area | the metadata's number inside our proved bracket, 381 / 381 |
| **self-intersecting surface** | **3: brackets 432, 473, 551** (3 / 4 / 1 crossing face pairs, each confirmed by an independent float test) — their volume is NOT proved (the divergence formula assumes no self-intersection), the dataset's volume for them is the formula's number, not the solid's |
| **genus** | **15 differ** — every one a MULTI-COMPONENT mesh (2 to 87 separate bodies); the metadata's genus = (2 - chi)/2 for one component, so it is off by (c - 1) and goes NEGATIVE for five of them (e.g. bracket 233: 87 bodies, metadata genus -80 — impossible for a surface); ours (2c - chi)/2 |
| more than one body | 15 brackets (5 with 2, one with 87) — for a structural part a disconnected body carries no load unless it is constrained on its own: a question for the FEA, not answered here |

**Update 02:57 (the source scout, research/cad/SOURCES-stress.md):** the SimJEB paper (ar5iv full text, as read by
the scout — to be re-checked against the PDF before any public use) gives Ti-6Al-4V density 4.47e-3 g/mm^3, the
same as the metadata; the 4.43 is the FEA deck's MAT1 card (bracket 148, read by us directly). So the split is
paper + metadata (4.47) against the deck that produced the simulations (4.43).

**A fourth data defect (14:58):** SimJEB's published FEA archive holds bracket 293's deck as an EMPTY file
(`293.fem`, 0 bytes, dated 2021-04-24, inside SimJEB_fea_(fem) as distributed), while the metadata reports results for
it (483 403 tets, max vertical displacement 1.470 mm). The only empty deck of the 381; our run says so instead of
crashing (tetfea.read_deck: "no GRID / CTETRA cards").
