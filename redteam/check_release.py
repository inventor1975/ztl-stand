"""FINDING 1 (redteam, 2026-11-02): frame3d's geometric stiffness ignores END RELEASES.

frame3d.energy_system gives a released member end its own rotation unknown ("IR", k, end) — the ELASTIC stiffness uses
it. But every geometric form (_form3: stability_lower's G, Q, B and the axial-load split; second_order_disp's K_G and
continuum correction) and every end-moment / end-slope row (_glob3) is built from the NODE's rotation DOFs, so for a
released member the geometric stiffness acts on the node's rotation, not the member's: the member is treated, for
buckling and P-delta, as if it were rigidly connected. Where the node's rotation is restrained (stiff connections,
supports), the member's buckling load is overstated up to 4x (pinned-pinned -> clamped-clamped).

    PYTHONPATH=. python3 redteam/check_release.py

Independent reference: redteam/ref_hinged.py (a straight member, Hermite elements, hinges as free end rotations,
numpy), Euler's closed forms, and EN 1993-1-1 6.3.1 computed by hand below."""
import json
import math
import os
import sys
from fractions import Fraction as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref_hinged as RH  # noqa: E402
from ustand import frame3d as F3  # noqa: E402

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "decks")
E, I, A = 210e9, 8e-5, 0.01
EI = E * I
out = {}

# (a) column fixed at the base, HINGED at its top (RELEASE J), top node held laterally and rotationally
t = open(os.path.join(D, "rel-column-fixed-pinned.txt")).read()
lo = float(F3.stability_lower(t, "0")["lam_low"])
true = RH.buckling(EI, 4.0, ("fixed", "pin")) / 1e7
out["a_fixed_pinned_column"] = {"deck": "redteam/decks/rel-column-fixed-pinned.txt", "proved_lam_low": lo,
                                "true_lam_cr": true, "closed_form": 20.1907 * EI / 16 / 1e7,
                                "clamped_clamped_for_comparison": 4 * math.pi ** 2 * EI / 16 / 1e7,
                                "false_by_factor": lo / true}

# (b) a pin-ended strut (RELEASE at both ends), L = 12 m, P = 1.3 MN (130 MPa): EN 6.3.1 EARNED, yet it buckles
t = open(os.path.join(D, "rel-strut-12m.txt")).read()
lo = float(F3.stability_lower(t, "0")["lam_low"])
P = 1.3e6
Pcr = RH.buckling(EI, 12.0, ("pin", "pin"))
jb = F3.judge_buckling(t, "0", 235e6, "b", "b")
fy, a_b = 235e6, 0.34
lb = math.sqrt(A * fy / Pcr)
ph = 0.5 * (1 + a_b * (lb - 0.2) + lb * lb)
chi = 1 / (ph + math.sqrt(ph * ph - lb * lb))
out["b_pinned_strut_12m"] = {"deck": "redteam/decks/rel-strut-12m.txt", "proved_alpha_cr_low": lo,
                             "true_alpha_cr": Pcr / P, "euler": math.pi ** 2 * EI / 144 / P,
                             "false_by_factor": lo / (Pcr / P),
                             "stand_EN_6_3_1": {"verdict": jb["verdict"], "utilisation_max": jb["utilisation_max"]},
                             "hand_EN_6_3_1_with_true_Ncr": {"lambda_bar": lb, "chi_curve_b": chi,
                                                             "N_b_Rd": chi * A * fy, "N_Ed": P,
                                                             "utilisation": P / (chi * A * fy)}}

# (c) a STABLE pinned strut (true alpha_cr = 2) with a lateral load at mid-span: the second-order displacement's proved
#     upper end is below the true value
t = open(os.path.join(D, "rel-strut-second-order.txt")).read()
r = F3.second_order_disp(t, "0", ["U(2,Y)"])["BASE"]["U(2,Y)"]
plo, phi_ = float(F(r[0])), float(F(r[1]))
Pc = float(F([ln for ln in t.splitlines() if ln.startswith("F, 3, FX")][0].split(",")[3].strip())) * -1
x, v = RH.second_order(EI, 12.0, ("pin", "pin"), Pc, [(6, 5000)], n=400)
x2, v2 = RH.second_order(EI, 12.0, ("pin", "pin"), Pc, [(6, 5000)], n=800)
k = math.sqrt(Pc / EI)
closed = 5000 / (2 * Pc * k) * (math.tan(k * 6) - k * 6)        # pin-pin beam-column, central point load
out["c_second_order_disp"] = {"deck": "redteam/decks/rel-strut-second-order.txt", "proved": [plo, phi_],
                              "reference_n400": float(v[len(v) // 2]), "reference_n800": float(v2[len(v2) // 2]),
                              "closed_form": closed, "upper_end_below_truth_by": closed / phi_ - 1}
print(json.dumps(out, indent=1, default=str))
