# -*- coding: utf-8 -*-
"""Physics blind round 1 — the predictions, made from CASES.md only, BEFORE SEALED/outcomes.md is opened.

Two kinds, said per number:
  ZTL  — a closed-form law over the stated input ranges; the range [lo, hi] is computed exactly (corners — each law
         here is monotone in each input over its range, said per case) and then PROVED as Lean theorems by
         tools/zbound2lean.py (q >= lo' and q <= hi', lo' / hi' the range widened by 1e-6 relative);
  NUM  — special functions / field integrals / tide arguments ZTL's kernel lacks (Bessel, Biot–Savart): computed here
         with scipy / mpmath over the input range — Logic1's numerics, NOT a ZTL conclusion.

Run:  python3 research/physics/predict.py   (writes research/physics/PREDICTIONS.md)
"""
import itertools
import math
import os
import sys
from fractions import Fraction as F

import numpy as np
from scipy import integrate, special

HERE = os.path.dirname(os.path.abspath(__file__))
ZTL = os.path.normpath(os.path.join(HERE, "..", "..", "..", "ZTL"))
sys.path.insert(0, os.path.join(ZTL, "tools")); sys.path.insert(0, ZTL)
import zbound2lean as ZB      # noqa: E402

OUT = []
THEOREMS = []


def say(s=""):
    print(s); OUT.append(s)


def corners(f, ranges):
    vals = [f(*c) for c in itertools.product(*ranges)]
    return min(vals), max(vals)


def prove(name, sheet, expr, lo, hi):
    """Lean: expr >= lo·(1 − 1e-6) and expr <= hi·(1 + 1e-6) over the sheet's box (lo, hi > 0 here)."""
    lo_c = F(lo).limit_denominator(10**9) * F(999999, 1000000)
    hi_c = F(hi).limit_denominator(10**9) * F(1000001, 1000000)
    st = ZB.bound_to_lean([], [], sheet, expr, [(">=", str(lo_c)), ("<=", str(hi_c))], name)
    THEOREMS.append((name, st["status"]))
    return st["status"]


def rng(v, u):
    return (v - u, v + u)


# ---------------------------------------------------------------------------------------------------------------
def case1():
    say("## 1. Open–closed tube resonances — ZTL")
    # humid air: c = (331.4 + 0.6 t)·(1 + 0.16·x_v), x_v = RH·p_sat(t)/p, p_sat by Magnus (hPa) — x_v over the stated
    # ranges t 18.7..19.7, RH 0.60..0.70 is 0.0128..0.0161 (computed below); c increases with t and x_v, f_n
    # decreases with L and a: corners exact.
    def psat(t):
        return 6.1094 * math.exp(17.625 * t / (t + 243.04))
    xv = [rh * psat(t) / 1013.25 for t in (18.7, 19.7) for rh in (0.60, 0.70)]
    xlo, xhi = min(xv), max(xv)
    say(f"- humid-air mole fraction of water x_v in [{xlo:.4f}, {xhi:.4f}] (Magnus); c = (331.4 + 0.6 t)(1 + 0.16 x_v)")
    T = (18.7, 19.7); X = (xlo, xhi); L = (1.497, 1.499); A = (0.0180, 0.0190)
    c = lambda t, x: (331.4 + 0.6 * t) * (1 + 0.16 * x)
    clo, chi = corners(c, (T, X))
    say(f"- speed of sound c in [{clo:.2f}, {chi:.2f}] m/s")
    sheet = f"t=[18.7,19.7] credit, x=[{xlo:.6f},{xhi:.6f}] credit, L=[1.497,1.499] credit, a=[0.018,0.019] credit"
    for n in (1, 10, 19):
        f = lambda t, x, l, a, n=n: (2 * n - 1) * c(t, x) / (4 * (l + 0.6133 * a))
        lo, hi = corners(f, (T, X, L, A))
        st = prove(f"ZPhys1f{n}", sheet, f"({2*n-1})*(331.4 + 0.6*t)*(1 + 0.16*x)/(4*(L + 0.6133*a))", lo, hi)
        say(f"- f_{n} in [{lo:.3f}, {hi:.3f}] Hz  (Lean: {st})")
    s = lambda t, x, l, a: c(t, x) / (4 * (l + 0.6133 * a))
    lo, hi = corners(s, (T, X, L, A))
    st = prove("ZPhys1slope", sheet, "(331.4 + 0.6*t)*(1 + 0.16*x)/(4*(L + 0.6133*a))", lo, hi)
    say(f"- slope c/(4L') in [{lo:.4f}, {hi:.4f}] Hz; a straight line through the origin in (2n−1)  (Lean: {st})")
    say(f"- the measured peaks are consistent with these laws iff the c they imply lies in [{clo:.2f}, {chi:.2f}] m/s")


def case2():
    say("## 2. Binary-pulsar orbital decay — NUM (closed forms over the corners in Python; NOT proved in Lean)")
    Tsun = 4.925490947e-6
    Pb = 0.09851259274 * 86400
    e = 0.106322
    # ω̇ = 3 (Pb/2π)^(-5/3) (T M)^(2/3) / (1-e²)  ->  M = [ω̇ (1-e²)/3 · (Pb/2π)^(5/3)]^(3/2) / T
    def mass_total(wdot_deg_yr, e):
        w = wdot_deg_yr * math.pi / 180 / (365.25 * 86400)
        return (w * (1 - e * e) / 3 * (Pb / (2 * math.pi)) ** (5 / 3)) ** 1.5 / Tsun
    # γ = e (Pb/2π)^(1/3) T^(2/3) M^(-4/3) m_c (M + m_c)   ->  m_c (M + m_c) = G
    def mc_of(M, gam_ms, e):
        G = gam_ms * 1e-3 / (e * (Pb / (2 * math.pi)) ** (1 / 3) * Tsun ** (2 / 3) * M ** (-4 / 3))
        return (-M + math.sqrt(M * M + 4 * G)) / 2
    def pdot_gw(M, mc, e):
        mp = M - mc
        fe = (1 + 73 * e * e / 24 + 37 * e ** 4 / 96) * (1 - e * e) ** (-3.5)
        return -(192 * math.pi / 5) * (Pb / (2 * math.pi)) ** (-5 / 3) * fe * Tsun ** (5 / 3) * mp * mc / M ** (1 / 3)
    vals = []
    mas = 1e-3 / 3600 * math.pi / 180 / (365.25 * 86400)       # mas/yr -> rad/s
    kpc = 3.0857e19
    for wd in (17.5859 - 0.0007, 17.5859 + 0.0007):
        for g in (0.445 - 0.011, 0.445 + 0.011):
            for ee in (e - 0.000011, e + 0.000011):
                M = mass_total(wd, ee); mc = mc_of(M, g, ee)
                for ma in (-2.0, -1.0):
                    for md in (-7.0, -5.2):
                        for d in (1.3 * 0.7, 2.0 * 1.3):
                            mu2 = (ma * mas) ** 2 + (md * mas) ** 2
                            shk = Pb * mu2 * d * kpc / 2.998e8 / Pb   # Ṗ_b^Shk = P_b μ² d / c ; as Ṗ_b (s/s): μ² d / c · P_b / P_b
                            shk = mu2 * d * kpc / 2.998e8 * Pb / Pb
                            vals.append((pdot_gw(M, mc, ee), Pb * mu2 * d * kpc / 2.998e8 / Pb * 1.0, M, mc))
    # Ṗ_b^Shk as a dimensionless rate: (Ṗ_b/P_b)_Shk = μ² d / c, so Ṗ_b^Shk = P_b μ² d / c (s/s when P_b in s)
    gw = [v[0] for v in vals]
    shk = [Pb * ((ma * mas) ** 2 + (md * mas) ** 2) * d * kpc / 2.998e8
           for ma in (-2.0, -1.0) for md in (-7.0, -5.2) for d in (0.91, 2.6)]
    Ms = [v[2] for v in vals]; mcs = [v[3] for v in vals]
    say(f"- total mass M in [{min(Ms):.5f}, {max(Ms):.5f}] M☉ (from ω̇); companion m_c in [{min(mcs):.4f}, {max(mcs):.4f}] M☉ (from γ)")
    say(f"- Ṗ_b(GW) in [{min(gw):.4e}, {max(gw):.4e}] s/s; Ṗ_b(Shklovskii) in [{min(shk):.3e}, {max(shk):.3e}] s/s")
    lo, hi = min(gw) + min(shk), max(gw) + max(shk)
    say(f"- PREDICTED observed Ṗ_b in [{lo:.4e}, {hi:.4e}] s/s (GW + Shklovskii; Galactic term neglected as the case says)")
    say("  (the range is dominated by γ's ±2.5 % through m_c, and by the distance's factor ~3 in the kinematic term)")


def case3():
    say("## 3. Spring with emptying mass — ZTL")
    k = (22.4, 22.6)
    ms = (56, 58); ph = (226, 228); eb = (55, 57); fb = (669, 671)
    for D, a in (("11.60", (0.01456, 0.01464)), ("19.55", (0.05554, 0.05590))):
        T0 = corners(lambda k_, s, p, b: 2 * math.pi * math.sqrt((p + b + s / 3) / 1000 / k_), (k, ms, ph, fb))
        T1 = corners(lambda k_, s, p, b: 2 * math.pi * math.sqrt((p + b + s / 3) / 1000 / k_), (k, ms, ph, eb))
        dur = corners(lambda f_, e_, a_: (f_ - e_) / 1000 / a_, (fb, eb, a))
        slope = corners(lambda k_, a_: -4 * math.pi ** 2 * a_ / k_, (k, a))
        sheet = f"k=[22.4,22.6] credit, al=[{a[0]},{a[1]}] credit"
        st = prove(f"ZPhys3s{D.replace('.', '_')}", sheet, "4*pi*pi*al/k", -slope[1], -slope[0])
        say(f"- outlet {D} mm: T initial in [{T0[0]:.4f}, {T0[1]:.4f}] s, final in [{T1[0]:.4f}, {T1[1]:.4f}] s, "
            f"discharge {dur[0]:.2f}–{dur[1]:.2f} s, d(T²)/dt in [{slope[0]:.5f}, {slope[1]:.5f}] s²/s (Lean |slope|: {st})")
    say("- T² linear in t (WKB, slowly varying mass); α from the slope equals the balance α exactly, by the same law")


def case4():
    say("## 4. AC resistance of steel rods at 50 Hz — NUM (complex Bessel; outside ZTL)")
    r0 = 6.0e-3; w = 2 * math.pi * 50; mu0 = 4e-7 * math.pi
    def ratio(rho, mur):
        d = math.sqrt(2 * rho / (w * mu0 * mur))
        kk = (1 - 1j) / d
        z = (kk * r0 / 2) * special.jv(0, kk * r0) / special.jv(1, kk * r0)
        return abs(z), math.degrees(np.angle(z))
    rs = [ratio(rho, mu) for rho in (0.73e-6 * 0.95, 0.73e-6 * 1.05) for mu in (1.0, 1.02)]
    say(f"- stainless 304: |Z|/R_DC in [{min(r[0] for r in rs):.6f}, {max(r[0] for r in rs):.6f}], phase "
        f"{min(r[1] for r in rs):.3f}–{max(r[1] for r in rs):.3f}°; |Z| ≈ 5.19 mΩ (R_DC measured)")
    rho_s = (0.16e-6, 0.20e-6)
    grid = [(rho, mu, *ratio(rho, mu)) for rho in rho_s for mu in (100, 200, 500, 1000, 2000)]
    for rho, mu, q, ph in grid:
        say(f"  S235JR ρ={rho*1e6:.2f} µΩm μr={mu}: |Z|/R_DC = {q:.3f}, phase {ph:.1f}°, |Z| = {q*1.39:.3f} mΩ")
    qs = [g[2] for g in grid]
    say(f"- S235JR over μr 100–2000 and ρ 0.16–0.20: ratio in [{min(qs):.3f}, {max(qs):.3f}] (|Z| {min(qs)*1.39:.2f}–{max(qs)*1.39:.2f} mΩ); "
        f"a measured ratio implies μr through this monotone curve (at ρ fixed by R_DC: ρ = R_DC·π r0²/l = {1.39e-3*math.pi*r0**2/0.8*1e6:.4f} µΩm)")
    rho_m = 1.39e-3 * math.pi * r0 ** 2 / 0.8
    say("  at the measured R_DC's ρ: " + "; ".join(f"μr={mu}: {ratio(rho_m, mu)[0]:.3f}" for mu in (100, 300, 500, 1000, 2000)))


def case5():
    say("## 5. Differential tidal rate shift between clock sites — NUM (outside ZTL)")
    fac = (1 + 0.298 - 0.608) * 9.81 / (2.998e8) ** 2      # ΔW = (1+k2−h2)·g·(V/g); Δν/ν = ΔW/c² per metre of V/g
    sites = {"PTB": (52.3, 10.46), "INRiM": (45.0, 7.64), "NPL": (51.4, -0.34)}
    semi = {"M2": 0.2423, "S2": 0.1128, "N2": 0.0464, "K2": 0.0307}
    diur = {"K1": 0.1416, "O1": 0.1005, "P1": 0.0468, "Q1": 0.0193}
    for a, b in (("INRiM", "PTB"), ("NPL", "PTB")):
        (pa, la), (pb, lb) = sites[a], sites[b]
        ra, rb = math.radians(pa), math.radians(pb); xa, xb = math.radians(la), math.radians(lb)
        s_amp = abs(math.cos(ra) ** 2 * np.exp(2j * xa) - math.cos(rb) ** 2 * np.exp(2j * xb))
        d_amp = abs(math.sin(2 * ra) * np.exp(1j * xa) - math.sin(2 * rb) * np.exp(1j * xb))
        line = ", ".join(f"{k} {H*s_amp*fac*1e18:.2f}" for k, H in semi.items()) + "; " + \
               ", ".join(f"{k} {H*d_amp*fac*1e18:.2f}" for k, H in diur.items())
        # worst-case peak-to-peak over a week: all constituents in phase (an upper bound), and the M2+S2+K1+O1 core
        upper = 2 * (sum(semi.values()) * s_amp + sum(diur.values()) * d_amp) * fac * 1e18
        say(f"- {a}–{b}: amplitudes (×1e-18) {line}; peak-to-peak bound (all in phase) {upper:.1f}×1e-18")
    sig = {"INRiM–PTB": 4.7e-16, "NPL–PTB": 3.8e-16}
    for k, s in sig.items():
        # white frequency noise over ~1 week at ~50 % uptime: σ(τ) at τ = 3e5 s, and a fit of a known waveform with
        # amplitude ~ few e-18: the scale-factor uncertainty ~ σ / (A_model · sqrt(N_eff)) — expressed directly:
        tau = 0.5 * 7 * 86400
        say(f"- {k}: noise averaged over a week ≈ {s/math.sqrt(tau)*1e18:.2f}×1e-18; a fitted scale factor A ≈ 1 with "
            f"uncertainty of order that noise over the model's amplitude (≈ 0.1–0.3, sharper on the larger baseline signal)")
    say("- expectation: A consistent with 1 (elastic-Earth model, ocean loading neglected — a few % effect)")


def case6():
    say("## 6. EMF along a rod in a Helmholtz field — NUM (outside ZTL)")
    mu0 = 4e-7 * math.pi; R = 0.105; N = 400; I = 0.030; f = 220; l = 0.075
    def Bz(rho):
        def loop(z):
            g = lambda th: (R * R - R * rho * math.cos(th)) / (rho * rho + R * R + z * z - 2 * R * rho * math.cos(th)) ** 1.5
            return mu0 * I * N / (4 * math.pi) * integrate.quad(g, 0, 2 * math.pi, limit=200)[0]
        return 2 * loop(R / 2)                         # both coils, the mid-plane at z = ±R/2 from each
    rr = np.linspace(0, 0.30, 601)
    bz = np.array([Bz(r) for r in rr])
    phi = np.concatenate([[0], integrate.cumulative_trapezoid(bz * 2 * math.pi * rr, rr)])
    def emf(y):
        def e_phi(r):
            return np.interp(r, rr, phi) / (2 * math.pi * r) if r > 0 else 0.0
        val = integrate.quad(lambda x: e_phi(math.hypot(x, y)) * (y / math.hypot(x, y)), -l, l, limit=200)[0]
        return 2 * math.pi * f * val                    # amplitude of dΦ/dt per unit I_rms -> RMS (I given as RMS)
    out = {y: emf(y / 100) * 1000 for y in (2, 5, 7, 9.8, 15, 25)}      # y = 0: zero by symmetry, not computed
    say("- ε_rms (mV): " + ", ".join(f"y={y} cm: {v:.4f}" for y, v in out.items()))
    ys = np.linspace(0.001, 0.30, 300); es = [emf(y) for y in ys]
    j = int(np.argmax(es)); say(f"- maximum ε ≈ {es[j]*1000:.4f} mV at y ≈ {ys[j]*100:.1f} cm; ε(0) = 0 by symmetry (E_φ ⟂ rod)")


def case7():
    say("## 7. Peas sedimenting in rapeseed oil — ZTL (Stokes × Haberman–Sayre, Oseen noted)")
    g = 9.81
    groups = [(11, 0.26, 0.85, 0.19, 6.00), (18, 0.24, 0.95, 0.18, 6.42), (20, 0.22, 0.84, 0.20, 7.00),
              (20, 0.24, 0.86, 0.18, 6.45), (27, 0.22, 0.82, 0.19, 6.61)]
    def Kp(q):
        return (1 - 0.75857 * q ** 5) / (1 - 2.1050 * q + 2.0865 * q ** 3 - 1.7068 * q ** 5 + 0.72603 * q ** 6)
    for i, (D, m, ro, V, d) in enumerate(groups, 1):
        def U(m_, ro_, V_, d_, mu_):
            return (m_ / 1000 - ro_ * V_ / 1000) * g / (3 * math.pi * mu_ * d_ / 1000 * Kp(d_ / D))
        lo, hi = corners(U, ((m - 0.01, m + 0.01), (ro - 0.03, ro + 0.03), (V - 0.01, V + 0.01), (d - 0.3, d + 0.3),
                             (0.0657, 0.0803)))
        nom = U(m, ro, V, d, 0.073)
        Re = 900 * nom * d / 1000 / 0.073
        # Oseen: F(1 + 3Re/16) with Re = ρ U d/μ — U solves U (1 + 3 ρ U d / (16 μ)) = U_stokes (a quadratic)
        def oseen(us, ro_, d_, mu_):
            k_ = 3 * ro_ * 1000 * d_ / 1000 / (16 * mu_)
            return (-1 + math.sqrt(1 + 4 * k_ * us)) / (2 * k_) if us > 0 else us
        Uo = oseen(nom, ro, d, 0.073)
        Re = ro * 1000 * nom * d / 1000 / 0.073
        say(f"- group {i} (D {D} mm): Stokes+wall U nominal {nom*100:.2f} cm/s, range [{max(lo,0)*100:.2f}, {hi*100:.2f}] cm/s; "
            f"Re ≈ {Re:.1f} — NOT small: with the Oseen factor U ≈ {Uo*100:.2f} cm/s (Oseen itself is rough above Re ~ 1)")
    say("- expected spread: the net weight m − ρV is a small difference of kitchen-scale numbers (±0.01 g of ~0.05 g),")
    say("  so the prediction itself spans a factor of several; measurements scattered over such a range are 'near'")


def case8():
    say("## 8. Venus fringes through a two-hole mask — NUM (Bessel J1; outside ZTL)")
    asec = 4.848e-6
    for d in (6, 10, 14):
        vs = [abs(2 * special.j1(x) / x) for a in (12.0, 13.1) for lam in (450e-9, 550e-9, 650e-9)
              for x in (math.pi * d * 1e-3 * a * asec / lam,)]
        v550 = [abs(2 * special.j1(math.pi * d * 1e-3 * a * asec / 550e-9) / (math.pi * d * 1e-3 * a * asec / 550e-9))
                for a in (12.0, 13.1)]
        say(f"- d = {d} mm: V at 550 nm {min(v550):.3f}–{max(v550):.3f}; over 450–650 nm {min(vs):.3f}–{max(vs):.3f}")
    for a in (12.0, 13.1):
        say(f"- null baseline d_null = 1.22 λ/α: {1.22*550e-9/(a*asec)*1000:.1f} mm at α = {a}″ (λ 550 nm)")
    say("- expected: 6 mm clearly visible, 10 mm marginal (low contrast), 14 mm beyond the first null — absent/very faint;")
    say("  vanishing between 10 and 14 mm implies α = 1.22 λ / d in "
        f"[{1.22*550e-9/(14e-3)/asec:.1f}, {1.22*550e-9/(10e-3)/asec:.1f}]″ (λ 550 nm)")


def case9():
    say("## 9. Oil in a tank on a cart on a 2.4° ramp — ZTL")
    lo, hi = corners(lambda th: 9.81 * math.sin(math.radians(th)), ((2.3, 2.5),))
    st = prove("ZPhys9a", "th=[0.040142572795869574,0.04363323129985824] credit", "9.81*sin(th)", lo, hi)
    say(f"- frictionless a = g sin θ in [{lo:.4f}, {hi:.4f}] m/s² down the ramp (Lean: {st}); with rolling friction μ_r:")
    say("  down: a = g(sin θ − μ_r cos θ) < g sin θ; up and slowing: |a| = g(sin θ + μ_r cos θ) > g sin θ —")
    say("  the acceleration keeps its direction (down the ramp) at the turning point; its MAGNITUDE steps down there")
    dh = corners(lambda th: 46 * math.tan(math.radians(th)), ((2.3, 2.5),))
    say(f"- release from rest (frictionless): the surface turns from horizontal to parallel to the ramp — the edges move "
        f"by W tan θ in [{dh[0]:.2f}, {dh[1]:.2f}] cm relative to the tank base; with friction slightly less")
    say(f"- slope of v(t) = a: ≈ {lo:.3f}–{hi:.3f} m/s² frictionless, somewhat less going down with friction")


def case10():
    say("## 10. Calorimeter, Γ = c_w + c_Cu m_cup / M_w — ZTL")
    for Mw in (170, 200, 240):
        G = 4.18 + 0.385 * 110 / Mw
        st = prove(f"ZPhys10M{Mw}", f"M=[{Mw},{Mw}] credit", "4.18 + 0.385*110/M", G, G)
        say(f"- M_w = {Mw} g: Γ = {G:.4f} J/(g K) (Lean: {st})")
    lo, hi = 4.18 + 42.35 / 240, 4.18 + 42.35 / 170
    st = prove("ZPhys10range", "M=[170,240] credit", "4.18 + 0.385*110/M", lo, hi)
    say(f"- over 170–240 g: Γ in [{lo:.4f}, {hi:.4f}] (Lean: {st}); a common fit ≈ 4.39 — ABOVE c_w by ≈ 4–6 %")
    say("- heat losses (not in the laws) would push a measured slope higher still")


if __name__ == "__main__":
    say("# Physics blind round 1 — PREDICTIONS (from CASES.md only; frozen before SEALED/outcomes.md is opened)")
    say()
    for c in (case1, case2, case3, case4, case5, case6, case7, case8, case9, case10):
        try:
            c()
        except Exception as ex:
            say(f"  !! {c.__name__} failed: {type(ex).__name__}: {ex}")
        say()
    say("## Lean theorems")
    for n, s in THEOREMS:
        say(f"- {n}: {s}")
    open(os.path.join(HERE, "PREDICTIONS.md"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
