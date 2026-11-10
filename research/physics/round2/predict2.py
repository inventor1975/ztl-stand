# -*- coding: utf-8 -*-
"""Physics blind round 2 — predictions from CASES.md only, BEFORE SEALED/outcomes.md is opened (2026-11-09).

ZTL = the range computed over the input corners (each law monotone in each input over its range unless said), then
       both ends JUDGED by ZTL's numeric floor (znumjudge: q >= lo and q <= hi over the inputs' box, EARNED needed) and,
       where the law is closed-form XE, proved in Lean (tools/zbound2lean.py).
NUM = Logic1's numerics (root-solving of transcendental modal equations, Planck band integrals, a slope's standard
       error from specifications) — not a ZTL conclusion.
MODEL = Logic1's judgement beyond the stated laws (a thick-plate correction, a current-efficiency direction), said.
"""
import itertools
import math
import os
import sys
from fractions import Fraction as F

import numpy as np
from scipy import integrate, optimize, special

HERE = os.path.dirname(os.path.abspath(__file__))
ZTL = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "ZTL"))
sys.path.insert(0, os.path.join(ZTL, "tools")); sys.path.insert(0, ZTL)
import znumjudge as ZJ        # noqa: E402
import zbound2lean as ZB      # noqa: E402

OUT = []


def say(s=""):
    print(s); OUT.append(s)


def corners(f, ranges):
    v = [f(*c) for c in itertools.product(*ranges)]
    return min(v), max(v)


def ztl_judge(expr, sheet, lo, hi):
    """Both ends judged by ZTL's floor; returns 'EARNED both' or what failed."""
    qs = ZJ.parse_quantities(sheet)[0]
    lo, hi = lo * (1 - 1e-6), hi * (1 + 1e-6)          # the same 1e-6 widening as the Lean bounds (float corners)
    a = ZJ.judge_sheet_claim(f"{expr} >= {lo!r}", dict(qs), {})["disposition"]
    b = ZJ.judge_sheet_claim(f"{expr} <= {hi!r}", dict(qs), {})["disposition"]
    return "EARNED both" if a == b == "EARNED" else f"lo {a}, hi {b}"


def lean(name, sheet, expr, lo, hi):
    lo_c = F(lo).limit_denominator(10 ** 9) * F(999999, 1000000)
    hi_c = F(hi).limit_denominator(10 ** 9) * F(1000001, 1000000)
    return ZB.bound_to_lean([], [], sheet.replace(" earned", " credit"), expr,
                            [(">=", str(lo_c)), ("<=", str(hi_c))], name)["status"]


def case1():
    say("## 1. Free-edge discs, f(2,0) — ZTL (thin plate, the stated law) + MODEL (Mindlin thickness correction)")
    discs = {"A": ("Al", 25.05, 3.181, 2679), "B": ("Al", 48.00, 6.581, 2725), "C": ("Al", 68.00, 3.163, 2712),
             "D": ("Al", 68.00, 6.579, 2709), "E": ("Ag", 51.17, 0.818, 10140)}
    for k, (mat, d, t, rho) in discs.items():
        E = (68e9, 70e9) if mat == "Al" else (76e9, 83e9)
        nu = (0.33, 0.35) if mat == "Al" else (0.37, 0.37)
        lam2 = (5.196, 5.26) if mat == "Al" else (5.128, 5.128)
        drho = 0.005 if mat == "Al" else 0.007
        def f(l2, e, n, dd, tt, r):
            a = dd / 2e3; tm = tt / 1e3
            return l2 / (2 * math.pi * a * a) * tm * math.sqrt(e / (r * (1 - n * n))) / math.sqrt(12)
        lo, hi = corners(f, (lam2, E, nu, (d - 0.1, d + 0.1), (t - 0.01, t + 0.01), (rho * (1 - drho), rho * (1 + drho))))
        sheet = (f"l2=[{lam2[0]},{lam2[1]}] earned, E=[{E[0]:.0f},{E[1]:.0f}] earned, nu=[{nu[0]},{nu[1]}] earned, "
                 f"dd=[{(d-0.1)/1e3},{(d+0.1)/1e3}] earned, tt=[{(t-0.01)/1e3},{(t+0.01)/1e3}] earned, "
                 f"r=[{rho*(1-drho)},{rho*(1+drho)}] earned")
        expr = "l2/(2*pi*(dd/2)*(dd/2))*tt*sqrt(E/(r*(1 - nu*nu)))/sqrt(12)"
        j = ztl_judge(expr, sheet, lo * 0.9999, hi * 1.0001)
        # MODEL: Mindlin first-order factor 1/sqrt(1 + (k t)^2/12 · (1 + 2/(kappa (1 − nu)))), k a = sqrt(lam2),
        # kappa = pi²/12; the factor's own uncertainty taken as ±50 % of its deviation from 1
        ka = math.sqrt(sum(lam2) / 2); kt = ka * t / (d / 2); nm = sum(nu) / 2
        g = 1 / math.sqrt(1 + kt * kt / 12 * (1 + 2 / ((math.pi ** 2 / 12) * (1 - nm))))
        clo, chi = lo * (1 - 1.5 * (1 - g)), hi * (1 - 0.5 * (1 - g))
        say(f"- disc {k} ({mat}, t/a {t/(d/2):.3f}): thin plate f in [{lo:.1f}, {hi:.1f}] Hz (ZTL judge: {j}); "
            f"MODEL thick-plate factor {g:.3f} -> [{clo:.1f}, {chi:.1f}] Hz")


def case2():
    say("## 2. Faraday's law, four cells in series — ZTL (+ Lean) + MODEL (current efficiency)")
    Fc = 96485.33212
    dI = 0.002 * 0.205 + 0.003
    for el, A in (("Fe", 55.845), ("Ni", 58.693), ("Cu", 63.546), ("Zn", 65.38)):
        lo, hi = corners(lambda I: A * I * 1800 / (2 * Fc), ((0.205 - dI, 0.205 + dI),))
        sheet = f"I=[{0.205-dI},{0.205+dI}] earned"
        expr = f"{A}*I*1800/(2*{Fc})"
        j = ztl_judge(expr, sheet, lo, hi)
        st = lean(f"ZPh2Far{el}", sheet, expr, lo, hi)
        say(f"- {el}: m in [{lo*1000:.2f}, {hi*1000:.2f}] mg (central {A*0.205*1800/(2*Fc)*1000:.2f}); "
            f"weighing ±1.4 mg (two weighings) on top; ZTL judge: {j}; Lean: {st}")
    say("- MODEL, said before opening: Cu at Faraday (~100 % efficiency from sulphate); Fe, Ni, Zn BELOW Faraday —")
    say("  hydrogen evolution at the cathode takes part of the charge (Zn and Fe most), so their masses fall short")


def case3():
    say("## 3. SiO2 micro-membranes — NUM (clamped tensioned plate: a J0/J1/I0/I1 root) and the membrane limit")
    rho = 2200.0
    for r_um in (10.3, 12.7, 15.8, 18.75, 20.3, 23.8):
        vals = []
        for sig in (320e6 * 0.7, 320e6 * 1.3):
            for t in (0.95e-6, 1.05e-6):
                for E in (70e9, 73e9):
                    for r in ((r_um - 0.3) * 1e-6, (r_um + 0.3) * 1e-6):
                        T = sig * t; D = E * t ** 3 / (12 * (1 - 0.17 ** 2)); m = rho * t
                        fm = 2.405 / (2 * math.pi * r) * math.sqrt(T / m)
                        def g(w):
                            s = math.sqrt(T * T + 4 * D * m * w * w)
                            k1 = math.sqrt((-T + s) / (2 * D)); k2 = math.sqrt((T + s) / (2 * D))
                            return k2 * special.j0(k1 * r) * special.i1(k2 * r) + k1 * special.j1(k1 * r) * special.i0(k2 * r)
                        w0 = 2 * math.pi * fm
                        ws = np.linspace(w0 * 0.9, w0 * 4, 4000); gs = [g(w) for w in ws]
                        root = next(optimize.brentq(g, ws[i], ws[i + 1]) for i in range(len(ws) - 1) if gs[i] * gs[i + 1] < 0)
                        vals.append((fm / 1e6, root / (2 * math.pi) / 1e6))
        mem = [v[0] for v in vals]; pl = [v[1] for v in vals]
        say(f"- r = {r_um} µm: membrane f in [{min(mem):.2f}, {max(mem):.2f}] MHz; tensioned clamped PLATE f in "
            f"[{min(pl):.2f}, {max(pl):.2f}] MHz (the plate is the stated full law; the bulge is not modelled)")


def case4():
    say("## 4. Time-of-flight slope — NUM (c/n_air; the OLS standard error from the specifications)")
    s = 299792458 / 1.00027
    L = np.array([0.35, 0.99, 1.88, 2.28, 3.43, 4.39, 5.14])
    sxx = float(((L - L.mean()) ** 2).sum()) / s ** 2
    for st_ns, sl in ((0.1, 0.02), (0.3, 0.03), (0.5, 0.04)):
        se = math.sqrt(sl ** 2 + (s * st_ns * 1e-9) ** 2) / math.sqrt(sxx)
        say(f"- per-point timing σ {st_ns} ns, path σ {sl*100:.0f} cm: slope SE ≈ {se:.3e} m/s ({se/s*100:.1f} %)")
    say(f"- PREDICTED slope s = c/n_air = {s:.6e} m/s; expected measured within ~2 SE of it, SE 1–4 % (σ_t 0.1–0.5 ns)")


def case5():
    say("## 5. Pre-tensioned silicone rod, phase velocity at 100 Hz — NUM (the tensioned Timoshenko quartic)")
    rho, r0, kap = 1070.0, 3.25e-3, 0.9
    table = {0.12: 0.019, 0.18: 0.068, 0.24: 0.107, 0.32: 0.156, 0.38: 0.206, 0.48: 0.275, 0.90: 0.696}
    for T in (0.12, 0.24, 0.48, 0.90):
        eps = table[T]
        out, strs = [], []
        for Tv in (T - 0.02, T + 0.02):
            for E in (59e3,):
                r = r0 / math.sqrt(1 + eps); A = math.pi * r * r; I = math.pi * r ** 4 / 4; G = E / 3
                w = 2 * math.pi * 100
                # [(T + kGA) k² − ρAω²][E I k² + kGA − ρIω²] − (kGA)² k² = 0 : quadratic in K = k²
                a2 = (Tv + kap * G * A) * E * I
                a1 = (Tv + kap * G * A) * (kap * G * A - rho * I * w * w) - rho * A * w * w * E * I - (kap * G * A) ** 2
                a0 = -rho * A * w * w * (kap * G * A - rho * I * w * w)
                Ks = [K for K in np.roots([a2, a1, a0]) if abs(K.imag) < 1e-9 and K.real > 0]
                c = w / math.sqrt(min(K.real for K in Ks))
                out.append(c); strs.append(math.sqrt(Tv / (rho * A)))
        say(f"- T = {T} N (ε {eps*100:.1f} %): string limit c0 in [{min(strs):.3f}, {max(strs):.3f}] m/s; "
            f"Timoshenko c(100 Hz) in [{min(out):.3f}, {max(out):.3f}] m/s (E = 59 kPa quasi-static: a dynamic modulus "
            f"would be higher and push c up)")


def case6():
    say("## 6. Silica WGM resonator — ZTL (+ Lean): FSR and Brillouin shift")
    c = 299792458.0
    ng = 1.4437 + 1.57607 * 0.0121
    lo, hi = corners(lambda D: c / (math.pi * ng * D) / 1e9, ((654e-6, 666e-6),))
    j = ztl_judge(f"299792458/(pi*{ng}*D)/1000000000", "D=[0.000654,0.000666] earned", lo, hi)
    st = lean("ZPh2FSR", "D=[0.000654,0.000666] earned", f"299792458/(pi*{ng}*D)/1000000000", lo, hi)
    say(f"- n_g = {ng:.5f}; FSR in [{lo:.3f}, {hi:.3f}] GHz (ZTL judge: {j}; Lean: {st})")
    lo, hi = corners(lambda V: 2 * 1.4437 * V / 1576.07e-9 / 1e9, ((5900, 5970),))
    j = ztl_judge("2*1.4437*V/0.00000157607/1000000000", "V=[5900,5970] earned", lo, hi)
    st = lean("ZPh2Bril", "V=[5900,5970] earned", "2*1.4437*V/0.00000157607/1000000000", lo, hi)
    say(f"- Brillouin shift in [{lo:.3f}, {hi:.3f}] GHz (bulk V_L; ZTL judge: {j}; Lean: {st})")


def case7():
    say("## 7. Overdamped RLC energy crossing — ZTL (+ Lean)")
    def tx(L, C, R, Ef, Es):
        a = R / (2 * L); w0 = 1 / math.sqrt(L * C); q = math.sqrt(a * a - w0 * w0)
        return math.log(Ef / Es) / (4 * q)
    def ex(L, C, R, Ef, Es):
        a = R / (2 * L); w0 = 1 / math.sqrt(L * C); q = math.sqrt(a * a - w0 * w0)
        ls = -a + q
        return Es * math.exp(2 * ls * tx(L, C, R, Ef, Es))
    rngs = ((43.2e-3, 45.6e-3), (446e-6, 462e-6), (26.9, 28.9), (1.993e-3 * 0.98, 1.993e-3 * 1.02), (0.220e-3 * 0.98, 0.220e-3 * 1.02))
    for extra in (0.0, 2.0):
        r2 = list(rngs); r2[2] = (26.9 + extra, 28.9 + extra)
        t = corners(tx, r2); e = corners(ex, r2)
        say(f"- extra contact resistance {extra} Ω: t_× in [{t[0]*1e3:.3f}, {t[1]*1e3:.3f}] ms; E_× in [{e[0]*1e6:.1f}, {e[1]*1e6:.1f}] µJ")
    sheet = "L=[0.0432,0.0456] earned, C=[0.000446,0.000462] earned, R=[26.9,28.9] earned, Ef=[0.00195314,0.00203286] earned, Es=[0.0002156,0.0002244] earned"
    expr = "ln(Ef/Es)/(4*sqrt((R/(2*L))*(R/(2*L)) - 1/(L*C)))"
    t = corners(tx, rngs)
    j = ztl_judge(expr, sheet, t[0] * 0.999, t[1] * 1.001)
    st = lean("ZPh2RLC", sheet, expr, t[0], t[1])
    say(f"- with the component R only: t_× in [{t[0]*1e3:.3f}, {t[1]*1e3:.3f}] ms (ZTL judge: {j}; Lean: {st})")
    say("- an unmeasured contact resistance (R larger) shortens t_× and lowers E_×: the measured values, if they differ,")
    say("  should sit on the SHORT/LOW side")


def planck(lam, T):
    h, c, k = 6.62607015e-34, 2.99792458e8, 1.380649e-23
    return 2 * h * c * c / lam ** 5 / np.expm1(h * c / (lam * k * T))


def band_ratio(Tp, Ts, l1, l2):
    num = integrate.quad(lambda l: planck(l, Tp) * l, l1, l2)[0]
    den = integrate.quad(lambda l: planck(l, Ts) * l, l1, l2)[0]
    return num / den


def tb_from_depth(depth, rp, Ts, l1, l2):
    return optimize.brentq(lambda T: rp * rp * band_ratio(T, Ts, l1, l2) - depth, 50, 6000)


def eclipse(name, Ts, aR, rp, l1, l2, sysrange, Ag=0.0):
    say(f"### {name}")
    for f_, lab in ((2 / 3, "f = 2/3 (bare rock, no redistribution)"), (1 / 4, "f = 1/4 (full redistribution)")):
        vals = []
        for T in Ts:
            for a in aR:
                for r in rp:
                    for sysf in sysrange:
                        Td = T * math.sqrt(1 / a) * f_ ** 0.25
                        d = r * r * band_ratio(Td, T, l1, l2) / sysf + Ag * (r / a) ** 2
                        vals.append((d * 1e6, Td))
        dd = [v[0] for v in vals]; tdd = [v[1] for v in vals]
        say(f"- {lab}: T_day in [{min(tdd):.0f}, {max(tdd):.0f}] K; depth in [{min(dd):.1f}, {max(dd):.1f}] ppm")


def case8():
    say("## 8. 15 µm eclipse, M dwarf — NUM (Planck band integrals); the star's band flux ±10–25 % systematic")
    eclipse("F1500W 13.5–16.5 µm", (3489, 3591), (21.15, 22.35), (0.03105, 0.03141), 13.5e-6, 16.5e-6, (0.75, 1.0, 1.25))


def case9():
    say("## 9. MIRI LRS 5.06–10.55 µm, K dwarf — NUM; band flux ±5–15 %")
    eclipse("white light", (4775, 4925), (3.22, 3.45), (0.0159, 0.0163), 5.06e-6, 10.55e-6, (0.85, 1.0, 1.15))


def case10():
    say("## 10. TESS and WFC3 eclipses, 5.4 h K dwarf — NUM; a from Kepler III; band flux ±5–15 %")
    G, Msun, Rsun = 6.674e-11, 1.989e30, 6.957e8
    P = 0.22419577 * 86400
    aR = corners(lambda M, R: (G * M * Msun * P * P / (4 * math.pi ** 2)) ** (1 / 3) / (R * Rsun),
                 ((0.637, 0.682), (0.639, 0.663)))
    say(f"- a/R* from Kepler III in [{aR[0]:.3f}, {aR[1]:.3f}]")
    for band, l1, l2 in (("TESS 600–1000 nm", 0.6e-6, 1.0e-6), ("WFC3 G141 1.127–1.570 µm", 1.127e-6, 1.570e-6)):
        eclipse(band + ", A_g = 0", (4082, 4137), aR, (0.02102, 0.02166), l1, l2, (0.85, 1.0, 1.15))
        say(f"  reflected light with A_g = 0.1 adds {0.1*(0.02133/((aR[0]+aR[1])/2))**2*1e6:.1f} ppm")


if __name__ == "__main__":
    say("# Physics blind round 2 — PREDICTIONS (from CASES.md only; frozen before SEALED/outcomes.md is opened)")
    say()
    for c in (case1, case2, case3, case4, case5, case6, case7, case8, case9, case10):
        try:
            c()
        except Exception as ex:
            say(f"  !! {c.__name__} failed: {type(ex).__name__}: {ex}")
        say()
    open(os.path.join(HERE, "PREDICTIONS.md"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
