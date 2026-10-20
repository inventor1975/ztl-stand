# r05 PROBLEM: pump operating point and brake power for a pipe system (BYU lecture example)

## Source
- Course notes: "Lecture 30 notes" (Pumps), Chemical Engineering 374 Fluid Mechanics, Brigham Young University,
  slide 12 "Example". Instructor not named on the slides (course page under ~mjm82).
  URL: https://www.et.byu.edu/~mjm82/che374/Fall2024/LectureNotes/Lecture_30_notes.pdf
  (the same example is in the Fall 2016 notes, same numbers).
- Freely readable PDF. The slide carries handwritten additions (fluid properties, the head equation).

## The problem in my words
A pump lifts a liquid from a suction tank at 1 atm, elevation 0, to a tank at 6 atm, elevation 10 m, through
a single straight pipe 200 m long, 0.1 m inside diameter, roughness 0.045 mm (no fittings or minor losses shown
on the diagram). The pump's head-versus-velocity curve is Hp = 200 m - v^2 (v = mean pipe velocity in m/s, the
coefficient 1 s^2/m is printed). Pump efficiency 90 %. Find the flow rate and the brake power.
Handwritten: rho = 1000 kg/m^3, mu = 0.798e-3 kg/(m s) (water at about 30 C),
Hreq = dP/(rho g) + dZ + friction term (Darcy-Weisbach).

Numbers used: P1 = 101325 Pa, P2 = 607950 Pa, dZ = 10 m, L = 200 m, D = 0.1 m, eps = 0.045 mm,
rho = 1000, mu = 0.000798 Pa s, pump H0 = 200 m, c = 1 s^2/m, eta = 0.9, g = 9.80665 m/s^2.

## PUBLISHED ANSWER (slide 12)
- Operating point where required head meets pump head: H_op = 149.149 m, v_op = 7.131 m/s.
- Volumetric flow printed as 0.055 m^3/s.
- bhp = rho g H Q / eta = 89.35 kW.
- The plot also prints Hreq at v = 0: 61.662 m and at v = 10 m/s: 232.223 m.
It claims the operating point (v, H) and the flow and power listed above. It gives no tolerance; each number is
to the digits printed.

## What the source left open (my assumptions)
- Friction-factor correlation not named. Inferred: Haaland. Check: Haaland at v = 10 m/s (Re = 1.253e6,
  eps/D = 4.5e-4) gives f = 0.016726, which makes Hreq(10) = 232.223 m exactly as printed; Colebrook gives
  0.016753 and Swamee-Jain 0.016840, neither matches. The v = 0 value 61.662 fixes g = 9.80665.
- No minor losses (none drawn). Velocity is the mean pipe velocity, the pump curve uses the same 0.1 m pipe.
- The brick has NO uncertain quantities in its faithful form (the source is a point calculation). A second
  variant (brick_tol.json) ADDS uncertainty that is mine, not the source's: mu for 20..40 C water
  (0.653..1.002 mPa s), D +-1 %, eps 0.03..0.06 mm.
