# -*- coding: utf-8 -*-
"""READ A QUANTITY AS A DOCUMENT WRITES IT — the number and its unit, by code (2026-11-12, the curator: "the AI must
not do this; we resolve it ourselves, down to regular expressions").

    mentions(text)            -> [Mention(value, unit_text, unit, start, end, note)] — every number in the text, with
                                 the unit written after it (or before it, for $ and US$), read into a ztl-stand unit
                                 string (units.py) or None when no unit is written or the writing is not recognised
    convert(value, unit, to)  -> the value in the unit `to`, EXACTLY (Fractions); absolute temperatures by their
                                 offsets; an absolute scale read into a DIFFERENCE unit is converted as a difference
    read(text, to, near=None) -> (value in `to`, Mention) for the one mention that is convertible to `to`; `near`
                                 picks among several (the number as written, or a word just before it); refuses when
                                 the choice is ambiguous instead of guessing

What is recognised (all exact; the table below, case-insensitive where safe):
  numbers   1250  1,250  1 250 (thin and plain spaces between groups of three)  3.0  .5  1.2e3  -4  -4 (minus sign)
            followed optionally by a scale word: thousand, million, billion (and k / M only when glued to a currency:
            $1.2M, $85k)
  currency  $ US$ USD dollars, cents / ¢ (0.01 USD), EUR € euros
  units     every unit string units.py reads (kW, mA, kWh, gpm, psi, ...), and the words and symbols engineers write:
            percent / per cent / %, °F ° F deg F degrees F(ahrenheit) degF, °C, K kelvin, feet ft ', inches in. ",
            sq ft ft2 ft², gallons, gallons per minute, kilowatt(s), kilowatt-hour(s), horsepower, Btu/h Btuh MBH,
            tons (of refrigeration) TR, pounds lb lbs, psf, psig / psia (gauge pressure is REFUSED: it has an offset
            that the text does not state), hours hrs, years yrs, months, kgal, 1,000 gal (as kgal), cfm, rpm
  shapes    "<unit> per <unit>", "<unit>/<unit>", "$X/kWh", "X cents/kWh", "$X per kW-month", "X % per year"
Refused aloud (None with a note): psig, a bare "ton" / "tons" (refrigeration or mass — the context must say:
"tons of refrigeration", "TR"; a CONTEXT word may be given to read(); see ton_is), unknown words.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction as F

from . import units as U

# ---------------------------------------------------------------------------------------------------------------- words
# a written unit WORD -> a units.py token (lower-case keys; looked up after lower-casing, except the case-sensitive set)
WORDS = {
    "percent": "%", "per cent": "%", "pct": "%", "%": "%",
    "dollar": "USD", "dollars": "USD", "usd": "USD", "us$": "USD", "$": "USD",
    "cent": "USD/100", "cents": "USD/100", "¢": "USD/100",
    "euro": "EUR", "euros": "EUR", "eur": "EUR", "€": "EUR",
    "degf": "degF", "°f": "degF", "º f": "degF", "° f": "degF", "deg f": "degF", "deg. f": "degF", "degrees f": "degF",
    "degree f": "degF", "degrees fahrenheit": "degF", "degree fahrenheit": "degF", "fahrenheit": "degF", "°fwb": "degF",
    "°fdb": "degF", "°f wb": "degF", "°f db": "degF", "f wb": "degF", "f db": "degF", "°f wet-bulb": "degF",
    "degc": "degC", "°c": "degC", "° c": "degC", "deg c": "degC", "degrees c": "degC", "degrees celsius": "degC",
    "celsius": "degC", "kelvin": "K",
    "foot": "ft", "feet": "ft", "ft": "ft", "'": "ft", "inch": "in", "inches": "in", "in.": "in", '"': "in",
    "sq ft": "ft^2", "sq. ft.": "ft^2", "square feet": "ft^2", "ft2": "ft^2", "ft²": "ft^2", "sf": "ft^2",
    "gallon": "gal", "gallons": "gal", "gal": "gal", "kgal": "kgal", "mgal": "Mgal", "1,000 gal": "kgal",
    "1000 gal": "kgal", "thousand gallons": "kgal",
    "gallons per minute": "gpm", "gpm": "gpm", "cfm": "cfm", "rpm": "rpm",
    "watt": "W", "watts": "W", "kilowatt": "kW", "kilowatts": "kW", "megawatt": "MW", "megawatts": "MW",
    "kilowatt-hour": "kWh", "kilowatt-hours": "kWh", "kilowatt hour": "kWh", "kilowatt hours": "kWh", "kwh": "kWh",
    "mwh": "MWh", "kw": "kW", "mw": "MW",
    "horsepower": "hp", "hp": "hp", "bhp": "hp",
    "btu": "BTU", "btus": "BTU", "btu/h": "BTUH", "btu/hr": "BTUH", "btuh": "BTUH", "mbh": "MBH", "mbtu": "MBTU",
    "tons of refrigeration": "TR", "ton of refrigeration": "TR", "refrigeration tons": "TR", "tr": "TR",
    "pound": "lb", "pounds": "lb", "lb": "lb", "lbs": "lb", "lbf": "lbf", "psf": "lbf/ft^2", "psi": "psi",
    "psia": "psi", "kip": "1000*lbf", "kips": "1000*lbf", "ksi": "ksi",
    "hour": "h", "hours": "h", "hr": "h", "hrs": "h", "h": "h", "minute": "min", "minutes": "min", "min": "min",
    "second": "s", "seconds": "s", "sec": "s", "day": "day", "days": "day", "week": "week", "weeks": "week",
    "month": "month", "months": "month", "mo": "month", "quarter": "quarter", "quarters": "quarter",
    "year": "year", "years": "year", "yr": "year", "yrs": "year", "annum": "year",
    "kw-month": "kW*month", "kw-mo": "kW*month",
    "ampere": "A", "amperes": "A", "amp": "A", "amps": "A", "milliampere": "mA", "milliamperes": "mA",
    "volt": "V", "volts": "V", "kilovolt": "kV", "kilovolts": "kV", "ohm": "ohm", "ohms": "ohm", "Ω": "ohm",
    "meter": "m", "meters": "m", "metre": "m", "metres": "m", "millimeter": "mm", "millimeters": "mm",
    "kilogram": "kg", "kilograms": "kg", "liter": "L", "liters": "L", "litre": "L", "litres": "L",
    "pascal": "Pa", "kilopascal": "kPa", "megapascal": "MPa", "bar": "bar", "db": "dB", "dba": "dBA", "db(a)": "dBA",
}
REFUSED = {"psig": "gauge pressure: an offset to atmospheric that the text does not state — write psia, or the "
                   "atmosphere as a quantity",
           "ton": "a bare ton: refrigeration (TR) or mass (2000 lb) — the text must say which",
           "tons": "a bare ton: refrigeration (TR) or mass (2000 lb) — the text must say which"}
SCALE = {"thousand": F(1000), "million": F(10**6), "billion": F(10**9)}
CUR_PREFIX = {"$": "USD", "us$": "USD", "€": "EUR", "eur": "EUR", "usd": "USD"}

NUM = r"[-−]?(?:\d{1,3}(?:(?:,| | | )\d{3})+|\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?|[-−]?\.\d+"
NUM_RE = re.compile(rf"(?<![\w.])({NUM})(?![\d])")


@dataclass
class Mention:
    value: F                    # the number as written, scale words applied (in unit_text's unit)
    unit_text: str              # the unit as written ("" if none)
    unit: str | None            # the units.py string, or None (none written, or not recognised — see note)
    start: int
    end: int
    note: str = ""


def _num(s):
    return F(s.replace("−", "-").replace(",", "").replace(" ", "").replace(" ", "").replace(" ", ""))


def _unit_from_words(t):
    """the longest recognised unit at the start of t -> (units.py string, chars consumed, note)"""
    t0 = t
    low = t.lower()
    # "X per Y": read X, then "per" or "/", then Y
    best = None
    for k in sorted(WORDS, key=len, reverse=True):
        if low.startswith(k) and (len(k) == len(low) or not low[len(k)].isalnum() or not k[-1].isalnum()):
            best = (WORDS[k], len(k))
            break
    if best is None:
        m = re.match(r"([A-Za-z%][A-Za-z0-9^²³\-]*)", t0)
        if m:
            tok = m.group(1).replace("²", "^2").replace("³", "^3").rstrip("-")
            if tok.lower() in REFUSED:
                return None, len(m.group(1)), "refused: " + REFUSED[tok.lower()]
            try:
                U.parse(tok)
                best = (tok, len(m.group(1)))
            except U.UnitError:
                return None, 0, f"unit word {tok!r} not recognised"
        else:
            return None, 0, ""
    unit, n = best
    rest = t0[n:]
    m = re.match(r"\s*(?:/|\bper\b|\ba\b(?=\s+[A-Za-z]))\s*", rest, flags=re.I)
    if m:
        u2, n2, note2 = _unit_from_words(rest[m.end():])
        if u2 is not None:
            return f"({unit})/({u2})", n + m.end() + n2, note2
    return unit, n, ""


def mentions(text):
    out = []
    for m in NUM_RE.finditer(text):
        raw = m.group(1)
        try:
            v = _num(raw)
        except (ValueError, ZeroDivisionError):
            continue
        start, end = m.start(1), m.end(1)
        before = text[max(0, start - 4):start].lower()
        cur = next((CUR_PREFIX[k] for k in sorted(CUR_PREFIX, key=len, reverse=True) if before.rstrip().endswith(k)),
                   None)
        rest = text[end:]
        note, unit_text, unit = "", "", None
        # a scale word or a k / M glued to a currency
        sm = re.match(r"\s*(thousand|million|billion)\b", rest, flags=re.I)
        if sm:
            v *= SCALE[sm.group(1).lower()]
            end += sm.end()
            rest = text[end:]
        elif cur and re.match(r"[kKM]\b", rest):
            v *= 1000 if rest[0] in "kK" else 10**6
            end += 1
            rest = text[end:]
        ws = re.match(r"[ \t]*", rest).end()
        if cur:                                       # "$0.0812/kWh", "$14.25 per kW-month", "$1.2M"
            unit = cur
            um = re.match(r"\s*(?:/|\bper\b)\s*", rest, flags=re.I)
            if um:
                u2, n2, note = _unit_from_words(rest[um.end():])
                if u2 is not None:
                    unit, unit_text = f"{cur}/({u2})", rest[:um.end() + n2]
                    end += um.end() + n2
        else:
            u, n, note = _unit_from_words(rest[ws:]) if rest[ws:ws + 1] else (None, 0, "")
            if u is not None:
                unit, unit_text = u, rest[ws:ws + n]
                end += ws + n
        if " " in raw.strip("-\u2212"):
            note = (note + "; " if note else "") + f"digits grouped by a plain space: {raw!r} read as {v}"
        out.append(Mention(v, unit_text.strip(), unit, start, end, note))
    return out


_TEMP_ABS = {"degF": (F(5, 9), F(45967, 100)), "degC": (F(1), F(27315, 100))}
_TEMP_DIFF = {"degF": "dF", "degC": "dC"}


def convert(value, unit, to):
    """value in `unit` -> value in `to`, exactly. Absolute degF/degC to an absolute target (degF, degC, K) by the
    offsets; to a DIFFERENCE target (dF, dC) as a difference. Raises units.UnitError on a dimension mismatch."""
    value = F(value)
    if unit in _TEMP_ABS or to in _TEMP_ABS:
        if to in ("dF", "dC") and unit in _TEMP_DIFF:
            unit = _TEMP_DIFF[unit]
        elif unit in _TEMP_ABS or to in _TEMP_ABS:
            if unit in _TEMP_ABS:
                f, off = _TEMP_ABS[unit]
                k = (value + off) * f
            else:
                k = value * U.parse(unit)[0]
                if U.parse(unit)[1] != U.parse("K")[1]:
                    raise U.UnitError(f"{unit!r} is not a temperature")
            if to in _TEMP_ABS:
                f, off = _TEMP_ABS[to]
                return k / f - off
            fk, dk = U.parse(to)
            if dk != U.parse("K")[1]:
                raise U.UnitError(f"{to!r} is not a temperature")
            return k / fk
    fa, da = U.parse(unit)
    fb, db = U.parse(to)
    if da != db:
        raise U.UnitError(f"{unit!r} ({U.show(da)}) cannot become {to!r} ({U.show(db)})")
    return value * F(fa) / F(fb)


def dims_match(unit, to):
    try:
        convert(F(1), unit, to)
        return True
    except (U.UnitError, ZeroDivisionError):
        return False


def read(text, to, near=None):
    """-> (value in `to`, the Mention) — the ONE mention convertible to `to` (and matching `near`, if given: the number
    as written, or a word the mention follows within 40 characters). Raises ValueError, naming the candidates, when
    there is none or more than one: never a guess."""
    ms = [m for m in mentions(text) if m.unit is not None and dims_match(m.unit, to)]
    if near is not None:
        nv = None
        try:
            nv = _num(str(near))
        except (ValueError, ZeroDivisionError):
            pass
        if nv is not None:
            ms = [m for m in ms if m.value == nv or _num(text[m.start:m.start + len(str(near))] or "0") == nv]
        else:
            low = text.lower()
            ms = [m for m in ms if near.lower() in low[max(0, m.start - 40):m.start]]
    if not ms:
        all_ = mentions(text)
        raise ValueError(f"no number with a unit convertible to {to!r} in the text; numbers read: "
                         + "; ".join(f"{m.value} {m.unit or '(no unit' + (': ' + m.note if m.note else '') + ')'}"
                                     for m in all_[:8]))
    if len(ms) > 1:
        raise ValueError(f"{len(ms)} numbers convertible to {to!r}: " + "; ".join(f"{m.value} {m.unit_text or m.unit}"
                                                                                  for m in ms[:8]) +
                         " — say which (the number as written)")
    m = ms[0]
    return convert(m.value, m.unit, to), m
