# k06 problem: head a lift-station pump must deliver over a range of wet-well level and force-main pressure

## Source
- Mark Ludwigson, P.E., "Centrifugal Pump Selection", PDH Academy course 431 (4 PDH), 46-page PDF,
  https://pdhacademy.com/wp-content/uploads/2023/06/431-Centrifugal-Pump-Selection.pdf
- The problem is "Example 3" (pages 29-31 of the PDF): a duplex lift station with submersible pumps.
  (Only the example is used. The PDF has seven examples; Examples 4-5 are nominal point calculations, Example 7 has a
  pump curve only as a picture.)

## The problem, in my words
A small sewage lift station pumps through a short run of fittings and 400 ft of 6 in ductile-iron pipe into an existing
force main. The wet-well level moves between elevation 4.0 ft and 6.0 ft. The pressure in the force main at the
tie-in moves between 9 and 13 psi; the tie-in pipe centreline is at elevation 12.0 ft. The pump must deliver the
peak-hour flow of 400 gpm. The task is to find the static head, and the total dynamic head (TDH) at 400 gpm, at the two
extreme operating conditions, so that a pump can be chosen (the pump chosen must give 400 gpm at the larger TDH).

Numbers used (all from the source):
- level EL 4.0 to 6.0 ft; tie-in pressure 9 to 13 psi; tie-in centreline EL 12.0 ft; 1 psi = 2.31 ft of head
- flow 400 gpm; pipe length 400 ft; pipe diameter 6 in
- minor losses by the K-method, sum of K = 7.37 (nine fittings: base elbow 0.50, 90 deg elbow 0.30, check valve 3.00,
  three gate valves 0.19 each, tee straight 0.60, wye straight 0.60, tee branch 1.80); head V^2/2g with g = 32.2 ft/s2
- friction by Hazen-Williams in the printed US form, HLf = (L/100) * 0.2083 * (100/C)^1.852 * q^1.852 / d^4.8655
  (q in gpm, d in inches, result in ft per the length used), C = 140 for ductile iron
  (the source lists C: 120 cast iron, 140 ductile iron, 150 PVC)

## PUBLISHED ANSWER
- lowest static head 26.8 ft (high level 6.0, low pressure 9 psi); highest static head 38.0 ft (level 4.0, 13 psi)
- minor losses 2.36 ft; pipe friction 4.82 ft (both at 400 gpm)
- TDH low = 34.0 ft; TDH high = 45.2 ft. The source says the 45.2 ft value is the one used to size the pump.
- It claims nothing more: no pump is chosen from a curve in this example, and no tolerance is put on C, K or the flow.

## What I had to assume (source left it open)
- The 6 in pipe is taken as exactly 6.0 in inside diameter for both velocity and friction (the source does the same).
- gpm to SI: US gallon 3.785411784 L exactly. The source uses 448.8 gpm per cfs (true 448.83); the effect on the minor
  loss is 0.0003 ft.
- The Hazen-Williams expression is not dimensionally consistent; in the brick q is divided by one gpm and d by one inch
  (given quantities) so the stand's unit check stays on, and the head is multiplied by one foot.
- The source has no pump curve in this example. "The pump" enters only as a required head Hp (a placeholder searched
  by `find`), so there is no catalog of pumps. I did not invent any.
- Uncertainty that is NOT in the source (only in variant A below, labelled): C anywhere in 120..150, the source's own
  list of materials, read as a range.
