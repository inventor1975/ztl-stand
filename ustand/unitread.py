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
    "pound": "lb", "pounds": "lb", "lb": "lb", "lbs": "lb", "lbf": "lbf", "psf": "psf", "plf": "plf", "pcf": "pcf", "ksf": "ksf", "klf": "klf", "mph": "mph", "psi": "psi",
    "psia": "psi", "kip": "kip", "kips": "kip", "ksi": "ksi",
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
# the same, with a PLAIN space never joining groups of three (thin and narrow no-break spaces are typed on purpose)
NUM_PLAIN = NUM.replace("|\u2009|\u202f| )", "|\u2009|\u202f)")
NUM_RE_PLAIN = re.compile(rf"(?<![\w.])({NUM_PLAIN})(?![\d])")
assert NUM_PLAIN != NUM


def _numbers(text):
    """the number matches of a text. A PLAIN SPACE between groups of three is a way of writing thousands ("3 250") AND
    the gap between two cells of a table printed as text; it is read as grouping (and said in the note) unless the
    text itself says otherwise (2026-11-15, MEASURED: a table row printed as text, "... PIN-10 250 12.5 ... 1,480", was read as
    10250 - a number that stands nowhere in the document - and went on as a quoted value):
    - the text writes its thousands with a COMMA somewhere: then a plain space in it separates two numbers;
    - the first group is the number of a designation ("PIN-10", "M-12", "RB08-4"): glued by a hyphen to a letter
      or a digit before it, it is the end of a name, not the head of a number."""
    comma = re.search(r"(?<![\d.,])\d{1,3}(?:,\d{3})+(?![\d,])", text) is not None
    if comma:
        return list(NUM_RE_PLAIN.finditer(text))
    out, pos = [], 0
    while True:
        m = NUM_RE.search(text, pos)
        if m is None:
            return out
        raw, st = m.group(1), m.start(1)
        if " " in raw and st >= 2 and text[st - 1] in "-\u2013" and text[st - 2].isalnum():
            m = NUM_RE_PLAIN.search(text, st)             # the designation's own number alone; the next starts after it
        out.append(m)
        pos = m.end(1)


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


# "IN" THE WORD, NOT THE INCH (2026-11-15, MEASURED: "at most 4 in total" was read as 4 inches, "1.5 in plan"
# as 1.5 inches - a length where the document states a count and a ratio). After a number, "in" followed by one of
# these words is the preposition: the number has no unit there. An inch before a noun or a measure word stays an
# inch ("3 in insulation", "6 in thick", "6 in below").
IN_AS_WORD = frozenset("""the a an all total each every any this that these those both which its their his her our plan number turn series
parallel place lieu case cases addition accordance general particular service use operation question order phase phases zone zones
front between excess full effect contact line aggregate compliance conformance elevation section detail table figure clause schedule
appendix part parts one two three four five six ten either neither some most many few such no not""".split())


def _unit_from_words(t):
    """the longest recognised unit at the start of t -> (units.py string, chars consumed, note)"""
    t0 = t
    low = t.lower()
    m_in = re.match(r"in\s+([A-Za-z]+)", t)
    if m_in and m_in.group(1).lower() in IN_AS_WORD:
        return None, 0, f"'in' before {m_in.group(1)!r} is the word, not inches"
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


# FEET AND INCHES WRITTEN TOGETHER (2026-11-13, MEASURED on a drawing note: 3'-6" was read as "3 ft" and "-6 in" - the
# dash of the notation taken for a minus sign, and a model that needed the height wrote "3 ft minus (-6 in)"). The
# dash between feet and inches is a separator. ONE length: feet + inches/12, in ft. Only the two unambiguous forms:
# the marks (3'-6", 3' 6", 5'-10 1/2") and the words joined by a dash (3 ft-6 in); "12 ft 6 in" with a plain space
# stays two numbers, because "30 ft 6 in deep" is two quantities as often as one.
_INCH = r"(\d+(?:\.\d+)?)(?:[ -](\d+)/(\d+))?"
FTIN_RE = re.compile(
    rf"(?<![\w.'\u2032-])(\d+)\s*(?:['\u2032]\s*[-\u2013]?\s*{_INCH}\s*(?:\"|\u2033|'')"
    rf"|(?:ft|feet|foot)\s*[-\u2013]\s*{_INCH}\s*(?:in\b\.?|inch(?:es)?\b|\"))", re.I)


def _feet_inches(text):
    out = []
    for m in FTIN_RE.finditer(text):
        g = m.groups()
        inch, num, den = (g[1], g[2], g[3]) if g[1] is not None else (g[4], g[5], g[6])
        try:
            v = F(g[0]) + (F(inch) + (F(int(num), int(den)) if num else 0)) / 12
        except (ValueError, ZeroDivisionError):
            continue
        out.append(Mention(v, "ft", "ft", m.start(), m.end(),
                           f"feet and inches written together: {m.group(0).strip()!r} read as {v} ft"))
    return out


def mentions(text):
    out = _feet_inches(text)
    taken = [(m.start, m.end) for m in out]
    for m in _numbers(text):
        if any(a <= m.start(1) < b for a, b in taken):
            continue                                      # a part of a feet-and-inches length already read whole
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
            else:
                # the unit in brackets right after the number - "1.5 (ft)" - when the brackets hold a unit and
                # nothing else (2026-11-13, MEASURED: a criteria clause writes its offsets so)
                pm = re.match(r"[ \t]*\(([^()\n]{1,14})\)", rest)
                if pm:
                    u2, n2, note2 = _unit_from_words(pm.group(1).strip())
                    if u2 is not None and n2 == len(pm.group(1).strip()):
                        unit, unit_text, note = u2, pm.group(1).strip(), note2
                        end += pm.end()
        if " " in raw.strip("-\u2212"):
            note = (note + "; " if note else "") + f"digits grouped by a plain space: {raw!r} read as {v}"
        out.append(Mention(v, unit_text.strip(), unit, start, end, note))
    return sorted(out, key=lambda x: x.start)


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


def near_number(near):
    """`near` as the number AS WRITTEN — "3.0", "3.0%", "120,000 USD" -> (value, unit or None); None when `near` is
    a word, not one number. (2026-11-12, PLE M6: near="3.0%" — exactly what the model is told to give — was taken
    for a word and matched nothing; the discount rate was refused with the % in the text.)"""
    s = str(near).strip()
    try:
        return _num(s), None
    except (ValueError, ZeroDivisionError):
        pass
    ms = mentions(s)
    if len(ms) == 1 and not re.search(r"[A-Za-z]", s[:ms[0].start]):
        return ms[0].value, ms[0].unit
    return None


def near_match(m, near, text=""):
    """does the mention `m` (of `text`) match `near` — the number as written (value, and unit if written), or a word
    the mention follows within 40 characters?"""
    nn = near_number(near)
    if nn is not None:
        v, u = nn
        return m.value == v and (u is None or m.unit == u)
    return str(near).lower() in text.lower()[max(0, m.start - 40):m.start]


def read(text, to, near=None):
    """-> (value in `to`, the Mention) — the ONE mention convertible to `to` (and matching `near`, if given: the number
    as written, or a word the mention follows within 40 characters). Raises ValueError, naming the candidates, when
    there is none or more than one: never a guess."""
    ms = [m for m in mentions(text) if m.unit is not None and dims_match(m.unit, to)]
    if near is not None:
        ms = [m for m in ms if near_match(m, near, text)]
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


def unit_in(text):
    """The unit a column HEADER or a label names, with no number beside it: "Flow (gpm)", "Price, $", "Energy
    [kWh/yr]", "UPV* factor" (none). -> (units.py string or None, note). The last parenthesised / bracketed group
    is tried first, then the text after the last comma, then the whole text."""
    cands = re.findall(r"[(\[]([^()\[\]]+)[)\]]", text)[::-1]
    if "," in text:
        cands.append(text.rsplit(",", 1)[1])
    cands.append(text)
    notes = []
    for c in cands:
        c = c.strip().strip(".:;")
        if not c:
            continue
        low = c.lower()
        if low in CUR_PREFIX:
            return CUR_PREFIX[low], ""
        if low.startswith(("$/", "$ per ", "usd/", "usd per ")):
            u2, n2, note = _unit_from_words(re.sub(r"^(\$|usd)\s*(/|per)\s*", "", c, flags=re.I))
            if u2 is not None:
                return f"USD/({u2})", note
            if _per_item(re.sub(r"^(\$|usd)\s*", "", c, flags=re.I)):
                return "USD", _per_item(re.sub(r"^(\$|usd)\s*", "", c, flags=re.I)) + ": counted items, not a unit"
        u, n, note = _unit_from_words(c)
        if u is not None and n == len(c):
            return u, note
        if u is not None and _per_item(c[n:]):
            return u, note or f"{_per_item(c[n:])}: counted items, not a unit"
        if note:
            notes.append(note)
    return None, "; ".join(notes) or "no unit named"


def _per_item(rest):
    """`rest` is "per <one word>" (or "/ <one word>", "each") and the word is NOT a unit: a counted item ("lb per
    bolt", "$ per panel", "W per rack") -> the word; else None. Running text already reads "40 lb per bolt"
    as a force; a column header saying the same was refused (MEASURED 2026-11-14: a table's "(<unit> per <item>)"
    column could not be read, and with the whole header row quoted the unit of ANOTHER column was taken). A word the
    reader refuses (a bare "ton") or knows as a unit is never an item."""
    m = re.fullmatch(r"\s*(?:(?:/|\bper\b)\s*([A-Za-z]{3,})|\beach\b)\s*", rest, flags=re.I)
    if not m:
        return None
    w = m.group(1)
    if w is None:
        return "each"
    if w.lower() in WORDS or w.lower() in REFUSED:
        return None
    try:
        U.parse(w)
        return None
    except U.UnitError:
        return "per " + w
