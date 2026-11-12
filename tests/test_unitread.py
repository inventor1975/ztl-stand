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
if FAILS:
    print(f"UNITREAD RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"UNITREAD GREEN ({CHECKS} checks)")
