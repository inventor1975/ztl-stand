# -*- coding: utf-8 -*-
"""ustand.unitread: numbers and units read from document text by code, converted exactly (2026-11-12). Run:
PYTHONPATH=. python3 tests/test_unitread.py"""
import sys
from fractions import Fraction as F
sys.path.insert(0, ".")
from ustand import unitread as R, units as U   # noqa: E402

CHECKS, FAILS = 0, []


def check(c, what):
    global CHECKS
    CHECKS += 1
    if not c:
        FAILS.append(what)
        print("FAIL:", what)


def one(text, to, near=None):
    return R.read(text, to, near)[0]


# what documents write -> the stand's units, exactly
check(one("The design flow is 1,250 gpm.", "gpm") == 1250, "1,250 gpm")
check(one("design flow 1,250 gpm", "m^3/s") == 1250 * U.parse("gpm")[0], "gpm to m^3/s exactly")
check(one("Energy charge $0.0812/kWh.", "USD/kWh") == F("0.0812"), "$0.0812/kWh")
check(one("demand charge $14.25 per kW-month", "USD/(kW*month)") == F("14.25"), "$14.25 per kW-month")
check(one("demand charge $14.25 per kW-month", "USD/(kW*year)") == F("14.25") * 12, "per month x 12 per year")
check(one("8.12 cents/kWh", "USD/kWh") == F("0.0812"), "cents per kWh are hundredths of a dollar")
check(one("design wet bulb 78 °F", "K") == (78 + F("459.67")) * F(5, 9), "78 °F to K by the offset")
check(one("design wet bulb 78 °F", "degC") == (78 - 32) * F(5, 9), "78 °F to °C")
check(one("a range of 10 °F", "dF") == 10 and one("a range of 10 °F", "dC") == F(50, 9),
      "an °F read into a DIFFERENCE unit is a difference (no offset)")
check(one("motor 15 hp", "kW") == 15 * U.parse("hp")[0] / 1000, "hp to kW")
check(one("efficiency 93.6 percent", "") == F("0.936") and one("3.0 % real", "%") == 3, "percent")
check(one("allocation of 12,500 kgal per year", "gal/day") == F(12500 * 1000 * 86400, 31557600),
      "kgal per year to gal per day (the Julian year)")
check(one("load 900 tons of refrigeration", "kW") == 900 * U.parse("TR")[0] / 1000, "tons of refrigeration")
check(one("investment $1.2 million", "USD") == 1200000 and one("$85k", "USD") == 85000, "$1.2 million, $85k")
check(one("20 mA at 24 V", "A") == F(1, 50) and one("20 mA at 24 V", "V") == 24, "mA and V, picked by dimension")
check(one("roof load 30 psf", "Pa") == 30 * U.parse("lbf/ft^2")[0], "psf")
check(one("every 3 months", "year") == F(1, 4), "3 months = 1/4 year")
check(one("-4 °C", "K") == F(26915, 100) and one("−4 °C", "K") == F(26915, 100), "a minus sign, ASCII or U+2212")
# refused, never guessed
for t, to, why in (("load 900 tons", "kW", "a bare ton"), ("pressure 25 psig", "Pa", "gauge pressure"),
                   ("flow 1250", "gpm", "no unit written"), ("85 °F and 95 °F", "degF", "two candidates")):
    try:
        R.read(t, to)
        check(False, f"refused: {why}")
    except ValueError as e:
        check(True, f"refused: {why} ({str(e)[:60]})")
check(one("85 °F and 95 °F", "degF", near="95") == 95, "two candidates, the one named by `near`")
check(one("supply 85 °F, return 95 °F", "degF", near="return") == 95, "two candidates, the one after a word")
m = R.mentions("Table 3 250 gpm")[0]
check(m.value == 3250 and "plain space" in m.note, "a space-grouped number is read AND said (a trap: 'Table 3 250')")
try:
    R.convert(5, "gpm", "kW")
    check(False, "a dimension mismatch is refused")
except U.UnitError:
    check(True, "a dimension mismatch is refused")
# near = the number AS WRITTEN, with its unit too (2026-11-12, PLE M6: near="3.0%" matched nothing)
T2 = "the computed rate was 2.2% in 2031, under the policy minimum of 3.0%."
check(one(T2, "%", "3.0%") == 3 and one(T2, "%", "3.0") == 3 and one(T2, "%", "3.0 %") == 3
      and one(T2, "%", "2.2%") == F(11, 5) and one(T2, "%", "minimum of") == 3,
      "near as written: 3.0%, 3.0, 3.0 %, 2.2%, or the words before it")
try:
    one(T2, "%", "4%")
    check(False, "a near that is not in the text is refused")
except ValueError:
    check(True, "a near that is not in the text is refused")
check(R.near_number("120,000 USD") == (120000, "USD") and R.near_number("floor of") is None,
      "near_number: a number with its unit, or None for words")
# US structural units (2026-11-12): written as the documents write them, exact, and usable as a quantity's own unit
check(U.parse("psf") == U.parse("lbf/ft^2") and U.parse("plf") == U.parse("lbf/ft") and U.parse("pcf") == U.parse("lbf/ft^3")
      and U.parse("kip")[0] == 1000 * U.parse("lbf")[0] and U.parse("ksf")[0] == 1000 * U.parse("psf")[0]
      and U.parse("klf")[0] == 1000 * U.parse("plf")[0] and U.parse("mph")[0] == U.parse("mi/h")[0],
      "psf, plf, pcf (unit weight), kip, ksf, klf, mph are exact and are the stand's own units")
check(one("The roof live load is 20 psf.", "psf") == 20 and one("diaphragm shear 450 plf", "lbf/ft") == 450
      and one("a force of 85 kips", "lbf") == 85000 and one("snow density 18.2 pcf", "pcf") == F("18.2")
      and one("basic wind speed 115 mph", "mph") == 115, "20 psf, 450 plf, 85 kips, 18.2 pcf, 115 mph read from text")
try:
    U.parse("kkip")
    check(False, "a prefix on kip is refused")
except Exception:
    check(True, "a prefix on kip is refused")
# FEET AND INCHES WRITTEN TOGETHER (2026-11-13: 3'-6" had been read as "3 ft" and "-6 in")
pairs = lambda t: [(m.value, m.unit) for m in R.mentions(t)]      # noqa: E731
check(pairs("parapet height 3'-6\" above the deck") == [(F(7, 2), "ft")], "3'-6\" is ONE length, 7/2 ft: the dash is a separator, not a minus")
check(pairs("3 ft-6 in") == [(F(7, 2), "ft")] and pairs("3' 6\"") == [(F(7, 2), "ft")], "the words joined by a dash, and the marks with a space, read the same")
check(pairs("5'-10 1/2\"") == [(F(47, 8), "ft")], "inches with a fraction: 5'-10 1/2\" is 47/8 ft")
check(pairs("joists at 6'-0\" on centre, 30'-0\" span") == [(F(6), "ft"), (F(30), "ft")], "two such lengths in one sentence stay two")
check(pairs("height 12 ft 6 in") == [(F(12), "ft"), (F(6), "in")], "PLANTED a plain space between the words is NOT joined (30 ft 6 in deep is two quantities as often as one)")
check(pairs("at -6 in below") == [(F(-6), "in")] and pairs("a 30' bay") == [(F(30), "ft")], "a real minus and a lone foot mark are read as before")
check(R.near_match(R.mentions("height 3'-6\" min")[0], "3'-6\"", "height 3'-6\" min") and "read as 7/2 ft" in R.mentions("height 3'-6\" min")[0].note,
      "such a length is found by `near` as it is written, and the note says how it was read")
check(pairs("offset 1.5 (ft)") == [(F(3, 2), "ft")] and pairs("12 (in)") == [(F(12), "in")], "a unit in brackets right after the number")
check(pairs("factor 2 (maximum)") == [(F(2), None)], "PLANTED brackets that hold a word, not a unit, give no unit")
# A UNIT PER COUNTED ITEM IN A HEADER (2026-11-14: a column "(<unit> per <item>)" could not be read)
check(R.unit_in("Capacity C (lb per bolt)")[0] == "lb" and "per bolt" in R.unit_in("lb per bolt")[1],
      "a header's 'lb per bolt' is lb, and the note says the item is counted, not a unit")
check(R.unit_in("Cost ($ per panel)")[0] == "USD" and R.unit_in("W per rack")[0] == "W" and R.unit_in("Price, $ each")[0] == "USD",
      "$ per panel, W per rack, $ each: the unit of one item")
check(R.unit_in("lb per ft")[0] == "(lb)/(ft)" and R.unit_in("$ per kWh")[0] == "USD/(kWh)" and R.unit_in("Force (kip per in)")[0] == "(kip)/(in)",
      "PLANTED a real unit after 'per' stays a rate, never an item")
check(R.unit_in("Load (lb per ton)")[0] is None and R.unit_in("Rate (USD per linear foot)")[0] is None,
      "PLANTED a refused word (a bare ton) is not an item, and two words after 'per' are not read")
if FAILS:
    print(f"UNITREAD RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"UNITREAD GREEN ({CHECKS} checks)")
