"""SPICE NETLIST -> a stand brick (2026-10-15, the curator's "да"): what an engineer's CAD already writes.

Every schematic tool (KiCad, Altium, OrCAD, ...) exports a SPICE netlist to simulate; it holds the topology and the
nominal values. The tolerances live in the BOM (or a `tol=` on the element line); the requirements are a short list.
This module turns the three into an ordinary brick — Kirchhoff's current law at every node (modified nodal analysis),
the sources' equations — and the stand judges it as any brick (large systems by ZTL's zlin).

    python3 -m ustand.spice circuit.cir --bom bom.csv --req "V(out) within 2.4 2.6" --req "I(R5) <= 1m"
            [--dev] [--emit brick.json]
    python3 -m ustand.spice circuit.cir --bom bom.csv --range "V(out)"      the PROVED range (each end attained)

THE NETLIST (DC, linear — version 1):
    R<name> n+ n- value [tol=1%]          a resistor
    V<name> n+ n- [DC] value              a voltage source (its current, I(V<name>), flows from n+ through it to n-)
    I<name> n+ n- [DC] value              a current source (from n+ through it to n-)
    E<name> n+ n- nc+ nc- gain            voltage-controlled voltage source (an op-amp's open loop: a large gain)
    G<name> n+ n- nc+ nc- gm              voltage-controlled current source
    F<name> n+ n- Vsense gain             current-controlled current source
    H<name> n+ n- Vsense r                current-controlled voltage source
    L<name> n+ n- value                   at DC a short (0 V, its current an unknown)
    C<name> n+ n- value                   at DC open (ignored)
    .param name=value, `{name}` as a value; numbers with SPICE suffixes (f p n u m k meg g t; 10k, 4.7u, 1meg) and
    the RKM code (4k7, 2R2); node 0 (or gnd) is the ground; the FIRST line is the title (as in every SPICE); `*` comments,
    `+` continues a line; .title/.end/.op skipped.
Anything else (D, Q, M, X subcircuits, .model, AC/TRAN) is REFUSED aloud — never silently dropped.

THE BOM (CSV): a reference column (Reference / Designator / Ref / RefDes; "R1, R2" or "R1-R3" in one row), a value
column (checked against the netlist: a mismatch is an error), a tolerance column ("1%", "±5 %", "0.1%", "50ppm"). A
tolerance with no unit is refused: 0.5 may be 0.5 % or 50 %.

REQUIREMENTS: V(node) | V(a,b) | I(R1) (from its n+ to n-) | I(V1) | P(R1) (its power, a nonlinear expression),
then  `within lo hi`, `<= x` or `>= x`, numbers with SPICE suffixes.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from fractions import Fraction as F

from . import bricks as B

_SUFFIX = {"f": F(1, 10**15), "p": F(1, 10**12), "n": F(1, 10**9), "u": F(1, 10**6), "m": F(1, 1000),
           "k": F(1000), "meg": F(10**6), "g": F(10**9), "t": F(10**12), "mil": F(254, 10**7)}
_NUM = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)(meg|mil|[fpnumkgt])?[a-z]*$", re.I)
_RKM = re.compile(r"^(\d+)([RrKkMmUuNnPp])(\d+)$")
_RKM_SCALE = {"R": F(1), "r": F(1), "K": F(1000), "k": F(1000), "M": F(10**6), "m": F(1, 1000), "U": F(1, 10**6),
              "u": F(1, 10**6), "N": F(1, 10**9), "n": F(1, 10**9), "P": F(1, 10**12), "p": F(1, 10**12)}


class SpiceError(B.BrickError):
    pass


def number(text, params=None):
    """A SPICE number, exactly: 10k, 4.7u, 1meg, 1e3, 2.2K, 10kohm, 4k7 (RKM), {name} (a .param)."""
    t = str(text).strip()
    if t.startswith("{") and t.endswith("}"):
        name = t[1:-1].strip()
        if params is None or name.lower() not in params:
            raise SpiceError(f"{t}: no .param of that name (version 1 reads a name, not an expression)")
        return params[name.lower()]
    if re.match(r"^[+-]?\d+/\d+$", t):
        return F(t)                         # an exact fraction (a bound the stand itself proved, 2026-10-15)
    m = _RKM.match(t)
    if m:
        # the RKM code of BOMs and schematics (IEC 60062): the letter is the decimal point and the scale; here the
        # case matters — M mega, m milli (4M7 = 4.7 Mohm, 4m7 = 4.7 m)
        whole, letter, frac = m.groups()
        return F(f"{whole}.{frac}") * _RKM_SCALE[letter]
    m = _NUM.match(t)
    if not m:
        raise SpiceError(f"{t!r} is not a SPICE number")
    v = F(m.group(1))
    if m.group(2):
        v *= _SUFFIX[m.group(2).lower()]
    return v


def _name(s):
    out = re.sub(r"[^A-Za-z0-9_]", "_", s)
    return out if re.match(r"[A-Za-z_]", out) else "n_" + out


def read_netlist(text):
    """-> (elements, params): elements [(kind, name, nodes, args, tol)] in order."""
    lines, cur = [], ""
    # the FIRST line of a SPICE file is its title, always (as every SPICE reads it) — a guess by its look took a title
    # "R-2R ladder ..." for a resistor (2026-10-15)
    for raw in text.splitlines()[1:]:
        line = raw.split(";", 1)[0].rstrip()
        if not line.strip() or line.lstrip().startswith("*"):
            continue
        if line.lstrip().startswith("+"):
            cur += " " + line.lstrip()[1:]
            continue
        if cur:
            lines.append(cur)
        cur = line.strip()
    if cur:
        lines.append(cur)
    params, elems, models = {}, [], {}
    first = True
    for line in lines:
        tok = line.split()
        head = tok[0].lower()
        if head.startswith("."):
            if head == ".param":
                for a in re.findall(r"(\w+)\s*=\s*([^\s]+)", line[len(tok[0]):]):
                    params[a[0].lower()] = number(a[1], params)
            elif head in (".end", ".op", ".title", ".ends", ".options", ".option", ".include", ".lib", ".control",
                          ".endc", ".save", ".probe"):
                if head in (".include", ".lib"):
                    raise SpiceError(f"{head}: an included file is not read (version 1) — paste the netlist whole")
            elif head == ".model":
                m = re.match(r"^\.model\s+(\S+)\s+([A-Za-z]+)\s*\(?(.*?)\)?\s*$", line, re.I)
                if not m:
                    raise SpiceError(f"{line!r}: a .model card is .model NAME TYPE(param=value ...)")
                mp = {}
                for k_, v_ in re.findall(r"(\w+)\s*=\s*([^\s)]+)", m.group(3)):
                    mp[k_.lower()] = v_
                models[m.group(1).lower()] = (m.group(2).upper(), mp)
            elif head in (".tran", ".ac", ".dc", ".noise", ".tf", ".meas", ".measure", ".step", ".temp"):
                pass                        # an analysis card: the stand judges DC only (said in the docs)
            else:
                raise SpiceError(f"{tok[0]}: not read (version 1)")
            first = False
            continue
        first = False
        kind = head[0]
        tol = None
        rest = []
        for t in tok[1:]:
            m = re.match(r"^tol\s*=\s*(.+)$", t, re.I)
            if m:
                tol = tolerance(m.group(1))
            else:
                rest.append(t)
        if kind in "rlc":
            if len(rest) < 3:
                raise SpiceError(f"{tok[0]}: needs two nodes and a value")
            elems.append((kind, tok[0], rest[:2], [number(rest[2], params)], tol))
        elif kind in "vi":
            vals = [t for t in rest[2:] if t.lower() != "dc"]
            if not vals:
                raise SpiceError(f"{tok[0]}: no DC value")
            if any(t.lower().startswith(("ac", "sin", "pulse", "pwl", "exp", "sffm")) for t in vals[1:]):
                vals = vals[:1]             # the AC / transient part is not DC: the DC value alone
            elems.append((kind, tok[0], rest[:2], [number(vals[0], params)], tol))
        elif kind in "eg":
            if len(rest) < 5:
                raise SpiceError(f"{tok[0]}: needs n+ n- nc+ nc- and a gain")
            elems.append((kind, tok[0], rest[:4], [number(rest[4], params)], tol))
        elif kind in "fh":
            if len(rest) < 4:
                raise SpiceError(f"{tok[0]}: needs n+ n- a sensing V source and a gain")
            elems.append((kind, tok[0], rest[:2] + [rest[2]], [number(rest[3], params)], tol))
        elif kind == "d":
            if len(rest) < 3:
                raise SpiceError(f"{tok[0]}: a diode is D<name> anode cathode model")
            elems.append(("d", tok[0], rest[:2], [rest[2].lower()], tol))
        elif kind == "q":
            if len(rest) < 4:
                raise SpiceError(f"{tok[0]}: a transistor is Q<name> collector base emitter model")
            elems.append(("q", tok[0], rest[:3], [rest[3].lower()], tol))
        else:
            raise SpiceError(f"{tok[0]}: a {kind.upper()} element is not read (R V I E G F H L C, and D Q by "
                             "operating regions)")
    # the devices' models, read now that every card is in
    for i, (kind, ename, nds, args, tol) in enumerate(elems):
        if kind in "dq":
            mname = args[0]
            if mname not in models:
                raise SpiceError(f"{ename}: no .model {mname}")
            mtype, mp = models[mname]
            if kind == "d" and mtype != "D" or kind == "q" and mtype not in ("NPN", "PNP"):
                raise SpiceError(f"{ename}: .model {mname} is {mtype}, not a {'diode (D)' if kind == 'd' else 'NPN/PNP'}")
            need = ("vfwd",) if kind == "d" else ("bf", "vbe", "vcesat")
            miss = [k_ for k_ in need if k_ not in mp]
            if miss:
                raise SpiceError(f"{ename}: .model {mname} lacks {', '.join(miss)} — the region model needs them "
                                 "(Vfwd and Ron as LTspice's piecewise diode; BF, Vbe, Vcesat for a transistor); "
                                 "nothing is assumed")
            vals = {k_: number(v_, params) for k_, v_ in mp.items() if k_ in ("vfwd", "ron", "bf", "vbe", "vcesat")}
            tols = {k_[:-3]: tolerance(v_) for k_, v_ in mp.items() if k_.endswith("tol") and k_[:-3] in vals}
            elems[i] = (kind, ename, nds, [mname, mtype, vals, tols], tol)
    return elems, params


def tolerance(text):
    """'1%', '±5 %', '0.1%', '50ppm' -> a fraction; a bare number is refused (0.5: 0.5 % or 50 %?)."""
    t = str(text).strip().replace("±", "").replace("+/-", "").replace(" ", "")
    if t.endswith("%"):
        return F(t[:-1]) / 100
    if t.lower().endswith("ppm"):
        return F(t[:-3]) / 10**6
    raise SpiceError(f"tolerance {text!r}: write its unit (%, ppm) — a bare number is ambiguous")


def read_bom(path):
    """-> {reference: (value or None, tolerance or None)}."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.reader(fh, dialect))
    if not rows:
        raise SpiceError(f"{path}: an empty BOM")
    head = [h.strip().lower() for h in rows[0]]

    def col(*names):
        return next((i for i, h in enumerate(head) if h in names), None)
    ci = col("reference", "references", "designator", "designators", "ref", "refdes", "ref des", "part")
    cv = col("value", "val", "comment")
    ct = col("tolerance", "tol", "tol.")
    if ci is None:
        raise SpiceError(f"{path}: no reference column (Reference / Designator / Ref / RefDes)")
    out = {}
    for r in rows[1:]:
        if ci >= len(r) or not r[ci].strip():
            continue
        refs = []
        for part in re.split(r"[,\s]+", r[ci].strip()):
            m = re.match(r"^([A-Za-z]+)(\d+)-\1?(\d+)$", part)
            if m:
                refs += [f"{m.group(1)}{i}" for i in range(int(m.group(2)), int(m.group(3)) + 1)]
            elif part:
                refs.append(part)
        val = r[cv].strip() if cv is not None and cv < len(r) and r[cv].strip() else None
        tol = tolerance(r[ct]) if ct is not None and ct < len(r) and r[ct].strip() else None
        for ref in refs:
            out[ref.upper()] = (val, tol)
    return out


_UNIT = {"r": "ohm", "l": "H", "c": "F", "v": "V", "i": "A", "e": "", "g": "A/V", "f": "", "h": "ohm"}


REGIONS = {"d": ("on", "off"), "q": ("active", "saturation", "cutoff")}


def devices(netlist_text):
    """{name: kind} of the region devices (D, Q) in the netlist."""
    return {e[1]: e[0] for e in read_netlist(netlist_text)[0] if e[0] in "dq"}


def to_brick(netlist_text, bom=None, requirements=(), regions=None, nominal=False):
    """The brick: quantities (element values, toleranced from the BOM), laws (KCL + sources), requirements.
    regions {device: region} — each D/Q stamped by its piecewise-linear model in that region; its REGION CONDITIONS
    are the brick's "margins" (each derived M == ... must be >= 0), returned in brick["_margins"].
    nominal: every tolerance dropped (a point — for choosing the regions)."""
    elems, _params = read_netlist(netlist_text)
    regions = regions or {}
    if not elems:
        raise SpiceError("no elements in the netlist")
    bom = bom or {}
    gnd = {"0", "gnd", "GND", "ground"}
    nodes = []
    for kind, _n, nds, _a, _t in elems:
        for nd in (nds if kind not in "fh" else nds[:2]):
            if nd not in gnd and nd not in nodes:
                nodes.append(nd)
    vname = {nd: "V_" + _name(nd) for nd in nodes}
    V = lambda nd: "0" if nd in gnd else vname[nd]
    qs, laws, kcl = {}, [], {nd: [] for nd in nodes}
    grounded = {}                       # node -> (its grounded V source's current, +1 when it leaves the node)
    names = {}
    mism = []
    for kind, ename, nds, args, tol in elems:
        q = _name(ename)
        if q in names:
            raise SpiceError(f"{ename}: two elements with one name")
        names[q] = ename
        if kind == "c":
            continue
        if kind in "dq":
            continue                        # stamped below, by region
        val = args[0]
        b_val, b_tol = bom.get(ename.upper(), (None, None))
        if b_val is not None:
            try:
                bv = number(b_val)
                if bv != val:
                    mism.append(f"{ename}: netlist {val}, BOM {b_val}")
            except SpiceError:
                pass                        # a BOM value that is a part name, not a number: not compared
        t = b_tol if b_tol is not None else tol
        if kind in "rviegfh":
            qq = {"role": "given", "value": str(val), "unit": _UNIT[kind]}
            if t:
                qq["tolerance"] = str(t)
            qs[q] = qq
        if kind == "r":
            a, b = nds
            cur = f"(({V(a)}) - ({V(b)}))/{q}"
            if a not in gnd:
                kcl[a].append(cur)
            if b not in gnd:
                kcl[b].append(f"-({cur})")
        elif kind == "i":
            a, b = nds
            if a not in gnd:
                kcl[a].append(q)
            if b not in gnd:
                kcl[b].append(f"-{q}")
        elif kind == "g":
            a, b, c, d = nds
            cur = f"{q}*(({V(c)}) - ({V(d)}))"
            if a not in gnd:
                kcl[a].append(cur)
            if b not in gnd:
                kcl[b].append(f"-({cur})")
        elif kind in "vlhe":
            a, b = nds[:2]
            iq = "I_" + q
            qs[iq] = {"role": "derived", "unit": "A"}
            if a not in gnd:
                kcl[a].append(iq)
            if b not in gnd:
                kcl[b].append(f"-{iq}")
            if kind == "v" and (a in gnd) != (b in gnd):
                # a GROUNDED source: its node's voltage is an explicit definition, and its current is defined by its
                # node's KCL (below) — two unknowns fewer in the core system (2026-10-15: a CE stage went 6 -> 4,
                # back under the checker's Cramer cap in --dev)
                nd_, sg_ = (a, "") if b in gnd else (b, "-")
                laws.append({"zfl": f"{V(nd_)} == {sg_}{q}", "source": f"{ename}: a grounded voltage source"})
                grounded[nd_] = (iq, 1 if b in gnd else -1)
            elif kind == "v":
                laws.append({"zfl": f"({V(a)}) - ({V(b)}) == {q}", "source": f"{ename}: a voltage source"})
            elif kind == "l":
                laws.append({"zfl": f"({V(a)}) - ({V(b)}) == 0", "source": f"{ename}: an inductor, a short at DC"})
            elif kind == "e":
                c, d = nds[2:4]
                laws.append({"zfl": f"({V(a)}) - ({V(b)}) == {q}*(({V(c)}) - ({V(d)}))", "source": f"{ename}: VCVS"})
        if kind == "f":
            a, b, sense = nds
            cur = f"{q}*I_{_name(sense)}"
            if a not in gnd:
                kcl[a].append(cur)
            if b not in gnd:
                kcl[b].append(f"-({cur})")
    margins = []
    for kind, ename, nds, args, tol in elems:
        if kind not in "dq":
            continue
        q = _name(ename)
        reg = regions.get(ename) or regions.get(ename.upper())
        if reg not in REGIONS[kind]:
            raise SpiceError(f"{ename}: its region must be one of {', '.join(REGIONS[kind])} (got {reg!r})")
        _mname, mtype, vals, mtols = args
        b_val, b_tol = bom.get(ename.upper(), (None, None))
        main_p = "vfwd" if kind == "d" else "bf"            # the BOM's tolerance is the main parameter's
        for k_, v_ in vals.items():
            t_ = (b_tol if (k_ == main_p and b_tol is not None) else mtols.get(k_, tol if k_ == main_p else None))
            qq = {"role": "given", "value": str(v_), "unit": {"vfwd": "V", "ron": "ohm", "bf": "", "vbe": "V",
                                                                "vcesat": "V"}[k_]}
            if t_ and not nominal:
                qq["tolerance"] = str(t_)
            qs[f"{q}_{k_}"] = qq

        def margin(expr, unit, why, q=q):
            mq = f"M_{q}_{len(margins)}"
            qs[mq] = {"role": "derived", "unit": unit}
            laws.append({"zfl": f"{mq} == {expr}", "source": f"{ename} region condition: {why}"})
            margins.append({"quantity": mq, "op": ">=", "value": "0", "unit": unit,
                            "why": f"{ename} in region {reg}: {why}"})

        def into(nd, cur):                     # the device draws `cur` from node nd
            if nd not in gnd:
                kcl[nd].append(f"({cur})")
        if kind == "d":
            a, k = nds
            if reg == "on":
                iq = f"I_{q}"
                qs[iq] = {"role": "derived", "unit": "A"}
                ron = f" + {q}_ron*{iq}" if "ron" in vals and vals["ron"] != 0 else ""
                laws.append({"zfl": f"({V(a)}) - ({V(k)}) == {q}_vfwd{ron}", "source": f"{ename}: a diode, on"})
                into(a, iq)
                into(k, f"-{iq}")
                margin(iq, "A", "its current >= 0")
            else:
                margin(f"{q}_vfwd - (({V(a)}) - ({V(k)}))", "V", "its voltage <= Vfwd")
        else:
            c, bn, e = nds
            sgn = 1 if mtype == "NPN" else -1
            jb = (f"({V(bn)}) - ({V(e)})" if sgn > 0 else f"({V(e)}) - ({V(bn)})")
            jc = (f"({V(c)}) - ({V(e)})" if sgn > 0 else f"({V(e)}) - ({V(c)})")
            ib, ic = f"I_{q}b", f"I_{q}c"
            if reg == "cutoff":
                margin(f"{q}_vbe - ({jb})", "V", "its base-emitter voltage <= Vbe (off)")
            else:
                qs[ib] = {"role": "derived", "unit": "A"}
                laws.append({"zfl": f"{jb} == {q}_vbe", "source": f"{ename}: base-emitter junction, on"})
                if reg == "active":
                    icx = f"{q}_bf*{ib}"
                    margin(ib, "A", "its base current >= 0")
                    margin(f"{jc} - {q}_vcesat", "V", "Vce >= Vcesat (not saturated)")
                else:
                    qs[ic] = {"role": "derived", "unit": "A"}
                    laws.append({"zfl": f"{jc} == {q}_vcesat", "source": f"{ename}: saturated"})
                    icx = ic
                    margin(ib, "A", "its base current >= 0")
                    margin(ic, "A", "its collector current >= 0")
                    margin(f"{q}_bf*{ib} - {ic}", "A", "Ic <= BF*Ib (saturated, not active)")
                # NPN draws Ib at b and Ic at c, returns both at e; PNP the other way
                into(bn, f"{sgn}*{ib}")
                into(c, f"{sgn}*{icx}")
                into(e, f"-{sgn}*({ib} + {icx})")
    for kind, ename, nds, _a, _t in elems:
        if kind == "h":
            a, b, sense = nds
            laws.append({"zfl": f"({V(a)}) - ({V(b)}) == {_name(ename)}*I_{_name(sense)}", "source": f"{ename}: CCVS"})
        if kind in "fh" and "I_" + _name(nds[2]) not in qs:
            raise SpiceError(f"{ename}: senses {nds[2]}, which is not a voltage source of the netlist")
    if mism:
        raise SpiceError("the BOM and the netlist disagree: " + "; ".join(mism))
    for nd in nodes:
        terms = kcl[nd]
        if not terms:
            raise SpiceError(f"node {nd}: nothing conducts at it (only capacitors, or devices in an off region) — "
                             "at DC it floats (no unique voltage)")
        qs[vname[nd]] = {"role": "derived", "unit": "V"}
        g_ = grounded.get(nd)
        own = (g_[0] if g_[1] > 0 else f"-{g_[0]}") if g_ else None
        if g_ and terms.count(own) == 1 and len(terms) > 1:
            rest = [t_ for t_ in terms if t_ != own]
            # KCL solved for the grounded source's current: an explicit definition
            laws.append({"zfl": f"{g_[0]} == {'-' if g_[1] > 0 else ''}({' + '.join(rest)})",
                         "source": f"KCL at node {nd} (the current of its grounded source)"})
        else:
            laws.append({"zfl": " + ".join(terms) + " == 0", "source": f"KCL at node {nd}"})
    reqs = []
    for i, rtext in enumerate(requirements):
        reqs.append(_requirement(rtext, i, qs, laws, V, gnd, names, elems))
    if nominal:
        for qq in qs.values():
            qq.pop("tolerance", None)
    brick = {"stand": "ztl-stand/1", "why": "imported from a SPICE netlist (ustand/spice.py)", "quantities": qs,
             "laws": laws, "requirements": reqs, "_margins": margins,
             "_regions": {e[1]: (regions.get(e[1]) or regions.get(e[1].upper())) for e in elems if e[0] in "dq"}}
    return brick


def _requirement(text, i, qs, laws, V, gnd, names, elems):
    m = re.match(r"^\s*([VIP])\(\s*([^,\)\s]+)\s*(?:,\s*([^\)\s]+)\s*)?\)\s*(within|<=|>=)\s*(\S+)(?:\s+(\S+))?\s*$", text, re.I)
    if not m:
        raise SpiceError(f"requirement {text!r}: write V(node) | V(a,b) | I(R1) | I(V1) | P(R1), then within lo hi, "
                         "<= x or >= x")
    what, a, b, op, x, y = m.groups()
    what = what.upper()
    el = {e[1].upper(): e for e in elems}
    if what == "V":
        for nd in (a, b):
            if nd is not None and nd not in gnd:
                try:
                    V(nd)
                except KeyError:
                    raise SpiceError(f"requirement {text!r}: no node {nd} in the netlist")
        if b is None:
            q, unit = V(a), "V"
        else:
            q = f"Vd_{_name(a)}_{_name(b)}"
            qs[q] = {"role": "derived", "unit": "V"}
            laws.append({"zfl": f"{q} == ({V(a)}) - ({V(b)})", "source": f"V({a},{b})"})
            unit = "V"
    else:
        e = el.get(a.upper())
        if e is None:
            raise SpiceError(f"requirement {text!r}: no element {a}")
        kind, ename, nds = e[0], e[1], e[2]
        if what == "I":
            if kind in "vlhe":
                q = "I_" + _name(ename)
            elif kind == "r":
                q = "Ir_" + _name(ename)
                qs[q] = {"role": "derived", "unit": "A"}
                laws.append({"zfl": f"{q} == (({V(nds[0])}) - ({V(nds[1])}))/{_name(ename)}", "source": f"I({ename})"})
            else:
                raise SpiceError(f"requirement {text!r}: I() of a {kind.upper()} element is not read (version 1)")
            unit = "A"
        else:
            if kind != "r":
                raise SpiceError(f"requirement {text!r}: P() reads a resistor (version 1)")
            q = "P_" + _name(ename)
            qs[q] = {"role": "derived", "unit": "W"}
            laws.append({"zfl": f"{q} == (({V(nds[0])}) - ({V(nds[1])}))*(({V(nds[0])}) - ({V(nds[1])}))/{_name(ename)}",
                         "source": f"P({ename})"})
            unit = "W"
    if op.lower() == "within":
        if y is None:
            raise SpiceError(f"requirement {text!r}: within needs two bounds")
        value = [str(number(x)), str(number(y))]
    else:
        value = str(number(x))
    return {"quantity": q, "op": op.lower(), "value": value, "unit": unit, "why": text.strip()}


MAX_COMBOS = 4096


def _run(brick, reqs):
    from . import stand as S
    b = {k: v for k, v in brick.items() if not k.startswith("_")}
    b["requirements"] = reqs
    keep, S._KEEP_EXACT[0] = S._KEEP_EXACT[0], True     # the values are read back exact (range_of), never "~..."
    try:
        return S.run(b, conflicts=False)
    finally:
        S._KEEP_EXACT[0] = keep


def judge(netlist_text, bom=None, requirements=(), regions=None):
    """With D/Q devices: the operating REGIONS first. Every combination of regions (or the ones given) is solved at
    the nominal point; the consistent ones (every region condition holds there) are kept. For each: stage 1 proves its
    region conditions over the WHOLE tolerance box (the margins >= 0 — then its piecewise-linear model is valid at
    every point), stage 2 judges the requirements in it. A region condition refuted at a point is said as such: the
    device LEAVES its region there (not the requirement's failure). Uniqueness of the operating point is not proved."""
    from . import checker as C
    import itertools
    devs = devices(netlist_text)
    if not devs:
        return _run(to_brick(netlist_text, bom, requirements), to_brick(netlist_text, bom, requirements)["requirements"])
    given = {k: v for k, v in (regions or {}).items()}
    for k in given:
        if k not in devs and k.upper() not in {d.upper() for d in devs}:
            raise SpiceError(f"--region {k}: no such device")
    free = [d for d in devs if d not in given and d.upper() not in {g.upper() for g in given}]
    n_combos = 1
    for d in free:
        n_combos *= len(REGIONS[devs[d]])
    if n_combos > MAX_COMBOS:
        raise SpiceError(f"{n_combos} combinations of regions: more than {MAX_COMBOS} — give some with --region")
    consistent, tried = [], 0
    for combo in itertools.product(*[REGIONS[devs[d]] for d in free]):
        rg = dict(given, **dict(zip(free, combo)))
        tried += 1
        try:
            bn = to_brick(netlist_text, bom, [], rg, nominal=True)
        except SpiceError:
            continue                        # these regions leave a node floating: not an operating point
        env = {n: B.num(q["value"]) for n, q in bn["quantities"].items() if q["role"] == "given"}
        unknowns = [n for n, q in bn["quantities"].items() if q["role"] == "derived"]
        try:
            vals = C.solve_at([l["zfl"] for l in bn["laws"]], env, unknowns)
        except (C.CheckError, ZeroDivisionError, KeyError):
            continue                        # singular in these regions (a floating node): not an operating point
        if all(vals[m["quantity"]] >= 0 for m in bn["_margins"]):
            consistent.append(rg)
    if not consistent:
        return {"verdict": "OPEN", "why": f"no combination of regions ({tried} tried) is consistent at the nominal "
                                         "point — the piecewise-linear models found no operating point"}
    points = []
    for rg in consistent:
        bk = to_brick(netlist_text, bom, requirements, rg)
        st1 = _run(bk, bk["_margins"]) if bk["_margins"] else {"verdict": "EARNED"}
        entry = {"regions": rg, "regions_hold": st1["verdict"]}
        if st1["verdict"] == "REFUTED":
            entry["leaves_its_region_at"] = st1.get("its_violating_point")
            entry["which"] = (st1.get("requirement") or {}).get("why") if isinstance(st1.get("requirement"), dict) \
                else st1.get("requirement")
        elif st1["verdict"] != "EARNED":
            entry["why"] = st1.get("why")
        else:
            st2 = _run(bk, bk["requirements"])
            entry["verdict"] = st2["verdict"]
            entry["result"] = {k: st2.get(k) for k in ("guaranteed", "its_violating_point", "value_there", "why",
                                                       "checked_by") if st2.get(k) is not None}
        points.append(entry)
    valid = [p_ for p_ in points if p_["regions_hold"] == "EARNED"]
    if len(points) == 1 and valid:
        verdict = valid[0]["verdict"]
        why = "the devices' regions hold over the whole box (proved), and the requirements were judged in them"
    elif valid and all(p_.get("verdict") == "EARNED" for p_ in points):
        verdict, why = "EARNED", f"{len(points)} operating points, each proved in its regions, each EARNED"
    elif any(p_.get("verdict") == "REFUTED" for p_ in valid):
        verdict, why = "REFUTED", "an operating point whose regions hold over the box fails a requirement"
    else:
        verdict = "OPEN"
        why = ("a device leaves its region inside the tolerance box (see leaves_its_region_at) — the model changes "
               "there, so nothing is claimed beyond it" if any(p_["regions_hold"] == "REFUTED" for p_ in points)
               else "the regions could not be proved over the box")
    return {"verdict": verdict, "why": why, "operating_points": points,
            "note": "regions by piecewise-linear device models (D: Vfwd + Ron; Q: Vbe, BF, Vcesat); an operating point "
                    "is proved to exist in its regions, its uniqueness is not"}


def _witness_value(r):
    """The exact value a REFUTED run found at its point, from the stand's answer (or an operating point's)."""
    vt = r.get("value_there")
    if not vt:
        for p_ in r.get("operating_points") or []:
            vt = (p_.get("result") or {}).get("value_there")
            if vt:
                break
    if not isinstance(vt, dict) or not vt:
        return None
    return B.num(str(next(iter(vt.values()))).split(" ")[0])


SLACK = F(1, 10**9)


def range_of(netlist_text, bom, target, regions=None, steps=40, progress=None):
    """THE PROVED RANGE of one quantity (V(node) | V(a,b) | I(R) | I(V) | P(R)): each end by descent — a requirement
    the stand REFUTES gives an attained value at its point; that value is the next bound; when the stand EARNS it, the
    end is attained AND proved (exact). Where the descent does not close — an extreme inside the box (a load's
    maximum power), or a tight bound the certificate cannot reach exactly — the bound is moved past the best attained
    value by a relative 1e-9 and proved there: the end is then a BRACKET [attained, proved].
    -> {"min": {...}, "max": {...}} with "attained" (a value at a true point), "proved" (a bound EARNED over the box)."""
    return range_by(lambda op, bound: judge(netlist_text, bom, [f"{target} {op} {bound}"], regions), steps, progress)


def _progress(side, e):
    """Each end to stderr AS SOON AS it is known: a run stopped by a time limit keeps what it proved (Muhanna's
    benchmark 1: four hours, nothing printed, 2026-10-16)."""
    print(json.dumps({side: {k: v for k, v in e.items() if k != "attained_at"}}, ensure_ascii=False),
          file=sys.stderr, flush=True)


def range_by(judge_one, steps=40, progress=None):
    """The descent of range_of for ANY importer: judge_one(op, bound) judges `target op bound` (op ">=" | "<=") and
    returns the stand's answer (a truss, ustand/truss.py, uses it as it is). progress(side, end): each run's state."""
    out = {}
    for side, op in (("min", ">="), ("max", "<=")):
        sgn = -1 if op == ">=" else 1                          # the bound moves outward by sgn
        bound = -sgn * F(10) ** 30                             # impossible: the stand answers with a point
        att, prv, runs, why, pt = None, None, 0, None, None
        for _ in range(steps):
            r = judge_one(op, bound)
            runs += 1
            if progress:
                progress(side, {"run": runs, "bound": float(bound), "verdict": r["verdict"]})
            if r["verdict"] == "EARNED":
                prv = bound
                break
            v = _witness_value(r) if r["verdict"] == "REFUTED" else None
            if v is not None and (att is None or (v - att) * sgn > 0):
                att = v
                pt = r.get("its_violating_point") or next(
                    (p_.get("result", {}).get("its_violating_point") for p_ in r.get("operating_points") or []
                     if (p_.get("result") or {}).get("its_violating_point")), None)
                # exact first; after 8 refutations (an interior extreme creeps up), past it by a slack that grows
                # tenfold each time (1e-9, 1e-8, ...): the bracket closes in a few runs, its width said
                slack = SLACK * 10 ** max(0, runs - 8)
                bound = v if runs < 8 else v + sgn * (abs(v) * slack + F(1, 10**15))
                continue
            if att is not None and bound == att:
                bound = att + sgn * (abs(att) * SLACK + F(1, 10**15))      # the exact bound not proved: just past
                continue
            why = r.get("why") or "no new point"
            break
        e = {"attained": str(att) if att is not None else None, "proved": str(prv) if prv is not None else None,
             "exact": att is not None and prv == att, "runs": runs, "attained_at": pt}
        if att is not None:
            e["attained_approx"] = float(att)
        if prv is not None:
            e["proved_approx"] = float(prv)
        if why and prv is None:
            e["why"] = why
        out[side] = e
        if progress:
            progress(side, e)
    return out


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    path = argv[0]
    reqs = [argv[i + 1] for i, a in enumerate(argv) if a == "--req"]
    ranges = [argv[i + 1] for i, a in enumerate(argv) if a == "--range"]
    regions = dict(argv[i + 1].split("=", 1) for i, a in enumerate(argv) if a == "--region")
    from . import mode as MODE
    MODE.DEV[0] = "--dev" in argv
    try:
        bom = read_bom(argv[argv.index("--bom") + 1]) if "--bom" in argv else None
        text = open(path, encoding="utf-8").read()
        if "--emit" in argv:
            br = to_brick(text, bom, reqs, regions or None) if not devices(text) or regions else to_brick(text, bom, reqs)
            json.dump({k: v for k, v in br.items() if not k.startswith("_")},
                      open(argv[argv.index("--emit") + 1], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        if ranges:
            out = {t_: range_of(text, bom, t_, regions or None, progress=_progress) for t_ in ranges}
            print(json.dumps(out, indent=1, ensure_ascii=False, default=str))
            return 0
        if not reqs:
            print(json.dumps({"verdict": "BRICK ERROR", "why": "no --req or --range: nothing to judge"}, indent=1))
            return 1
        out = judge(text, bom, reqs, regions or None)
    except (B.BrickError, OSError, ValueError, ZeroDivisionError) as e:      # every input fault said, never a traceback
        print(json.dumps({"verdict": "BRICK ERROR", "why": str(e)}, indent=1, ensure_ascii=False))
        return 1
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
