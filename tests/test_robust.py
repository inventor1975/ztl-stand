"""Stand: the stand never answers with a traceback.

The blind test of 2026-10-10 met eight tracebacks in twelve bricks; a fuzz of every example then
found ~25 more. Each is now a BRICK ERROR with its place named, or a verdict. Two parts:
  1. the named cases from the blind test and the fuzz, each with the answer it must get;
  2. a seeded fuzz over every example brick: no exception escapes `run`, and no STAND ERROR (the
     stand's own bug) appears. A brick slower than 20 s is counted apart — that is the speed gap,
     not a crash.

Run: python3 -m tests.test_robust   -> ROBUST GREEN
"""
import copy
import glob
import json
import random
import signal

from ustand import stand as S
from ustand import mode as _MODE   # the stand's tests run in DEV mode: the independent checker on every design
_MODE.DEV[0] = True

ok = fail = 0


def check(name, cond, why=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  OK   {name}")
    else:
        fail += 1; print(f"  FAIL {name} — {why}")


base = json.load(open("examples/divider-1pct-req-1pct.json"))


def case(name, edit, want="BRICK ERROR", contains=""):
    b = copy.deepcopy(base)
    edit(b)
    r = S.run(b, conflicts=False)
    check(f"{name}: {want}", r["verdict"] == want and contains in str(r.get("why", "")), json.dumps(r)[:200])


print("1. named cases")
case("an unknown unit (furlong)", lambda b: b["quantities"]["Vin"].__setitem__("unit", "furlong"), contains="not known")
case("an unclosed parenthesis in a unit (parentheses themselves are read since 2026-10-10)",
     lambda b: b["quantities"]["Vin"].__setitem__("unit", "J/(kg*K"), contains="not closed")
case("a ground with / and ( (read as a unit by ZTL before)",
     lambda b: b["quantities"]["Vin"].__setitem__("ground", "datasheet p.3 (rev/2)"), want="EARNED")
case("a derived quantity as a requirement bound",
     lambda b: b["requirements"].append({"quantity": "Vout", "op": "<=", "value": "I", "why": "x"}), contains="derived quantity")
case("a law written twice", lambda b: b["laws"].append(dict(b["laws"][0])), contains="repeats")
case("an unreadable law", lambda b: b["laws"].append({"zfl": "Vout == (I*", "source": "x"}), contains="not a readable")
case("an unknown name in a law", lambda b: b["laws"].append({"zfl": "Vout == Q*2", "source": "x"}), contains="'Q'")
case("an infinite constant", lambda b: b["laws"].__setitem__(0, {"zfl": "Vin - Vout == I*R1.R*1e999", "source": "x"}),
     contains="finite")
case("a string where an object belongs", lambda b: b.__setitem__("catalog", "resistors"), contains="catalog")
case("a range turned around", lambda b: b["quantities"]["Vin"].update({"range": ["6", "4"]}), contains="low end above")
b2 = json.load(open("examples/power-16thW-only.json"))
b2["laws"].append({"zfl": "Ptot == P1 + P2", "source": "sum"})
b2["quantities"]["Ptot"] = {"role": "derived", "unit": "W"}
r = S.run(b2, conflicts=False)
check("a chain of definitions (Ptot == P1 + P2, P1 == I*I*R1): a definition of definitions, judged (G14, 2026-10-10)",
      r["verdict"] in ("EARNED", "REFUTED", "OPEN"), str(r)[:200])
b2b = json.loads(json.dumps(b2)); b2b["laws"][-1] = {"zfl": "Ptot - P1 == P2", "source": "the same, not explicit"}
r = S.run(b2b, conflicts=False)
check("a defined quantity inside a law NOT of the form X == ... (Ptot - P1 == P2): BRICK ERROR, said why",
      r["verdict"] == "BRICK ERROR" and ("used in a linear law" in r["why"] or "must define" in r["why"]), str(r)[:200])
b3 = copy.deepcopy(base)
b3["quantities"]["P"] = {"role": "derived", "unit": "W"}
b3["laws"] += [{"zfl": "P == I*I*R1.R", "source": "a"}, {"zfl": "P == Vout*Vout/R2.R", "source": "b"}]
r = S.run(b3, conflicts=False)
check("one quantity defined by two nonlinear laws: BRICK ERROR (the second used to replace the first silently)",
      r["verdict"] == "BRICK ERROR" and "two nonlinear laws" in r["why"], str(r)[:200])
r = S.run("examples/blind/b10_modes_crashes.json")
check("the blind test's modes brick that crashed (a denominator spanning zero in a mode): I2 x 7, optimal",
      r["verdict"] == "EARNED" and r["design"]["CNT"]["N"]["nominal"] == "7" and r["objective"]["optimal"], str(r)[:200])

print("2. seeded fuzz over every example")
files = sorted(glob.glob("examples/*.json") + glob.glob("examples/tasks/*.json") + glob.glob("examples/blind/b*.json"))
bases = [json.load(open(f)) for f in files]
JUNK = ["(kg", "mol", "", "m/s/(", "xyz", "kg*", "^2", "C/W)", "1/0"]
VALS = ["0", "-1", "abc", ["1"], {"range": ["2", "1"]}, None, "1/0", {"value": "x"}, {"range": ["1"]}, 7, "1e999"]


def paths(o, p=()):
    if isinstance(o, dict):
        for k, v in o.items():
            yield p + (k,)
            yield from paths(v, p + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield p + (i,)
            yield from paths(v, p + (i,))


def setp(o, p, v):
    for k in p[:-1]:
        o = o[k]
    o[p[-1]] = v


def delp(o, p):
    for k in p[:-1]:
        o = o[k]
    del o[p[-1]]


def mutate(b, rng):
    b = copy.deepcopy(b)
    for _ in range(rng.randint(1, 3)):
        p = rng.choice(list(paths(b)))
        k = rng.random()
        try:
            if (k < 0.25 and p[-1] == "unit") or k < 0.1:
                setp(b, p, rng.choice(JUNK))
            elif k < 0.45:
                setp(b, p, copy.deepcopy(rng.choice(VALS)))
            elif k < 0.6:
                delp(b, p)
            elif k < 0.75 and isinstance(b.get("laws"), list) and b["laws"]:
                b["laws"].append({"zfl": rng.choice(["x == y*y", "a = b", "1 == 2", "Q == Q*Q + 1"]), "source": "fuzz (a/b)"})
            elif k < 0.85:
                setp(b, p, "datasheet p.3 (rev/2) [x]")
            else:
                setp(b, p, {"range": ["5", "5"]})
        except Exception:
            pass
    return b


class Slow(BaseException):
    pass


FIRED = [False]


def alarm(*a):
    # mpmath's interval comparison wraps its conversion in a bare `except:` and turns ANY exception into
    # NotImplemented — this alarm too, which then surfaced as "TypeError: '<' not supported between ivmpf and int",
    # a false STAND ERROR (2026-10-12, measured: the same mutants alone never fail). A run the alarm hit is slow.
    FIRED[0] = True
    raise Slow()


signal.signal(signal.SIGALRM, alarm)
rng = random.Random(2026)
N = 150
crashes, stand_errors, slow, counts = [], [], 0, {}
for i in range(N):
    bi = rng.randrange(len(bases))
    b = mutate(bases[bi], rng)
    FIRED[0] = False
    signal.alarm(20)
    try:
        r = S.run(b, conflicts=False)
        if FIRED[0]:
            raise Slow()
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        if r["verdict"] == "STAND ERROR":
            stand_errors.append((files[bi], r["why"][:160]))
    except Slow:
        slow += 1
    except Exception as e:                       # noqa: BLE001
        crashes.append((files[bi], f"{type(e).__name__}: {e}"[:160]))
    finally:
        signal.alarm(0)
check(f"{N} mutated bricks from {len(files)} examples ({counts}, {slow} slower than 20 s): no traceback",
      not crashes, str(crashes[:3]))
check("and no STAND ERROR (the stand's own bug)", not stand_errors, str(stand_errors[:3]))

# COMPONENTS (2026-10-12): a seeded fuzz over the system bricks, also inside an inlined component — no STAND ERROR
import os as _os
_here = _os.getcwd()
_os.chdir("examples/components")
try:
    _vals = [None, 1, "x", [], {}, {"a": 1}, ["1"], -1, "1e999", ["5", "1"], {"assume": ["1"]}]
    _errs, _n = [], 0
    for _fname in ("phone-charging-system.json", "phone-charging-hierarchy.json", "phone-charging-choose.json",
                   "phone-charging-tune.json", "bridge-two-sensors.json"):
        _base = json.load(open(_fname))
        for _seed in range(100):
            _rnd = random.Random(_seed)

            def _mut(d, depth=0):
                if isinstance(d, dict) and d:
                    k = _rnd.choice(list(d))
                    if _rnd.random() < 0.5 or depth > 4:
                        d[k] = _rnd.choice(_vals)
                    else:
                        _mut(d[k], depth + 1)
                elif isinstance(d, list) and d:
                    i = _rnd.randrange(len(d))
                    if _rnd.random() < 0.5:
                        d[i] = _rnd.choice(_vals)
                    else:
                        _mut(d[i], depth + 1)
            _x = copy.deepcopy(_base)
            _k = _rnd.choice(list(_x["components"]))
            if _rnd.random() < 0.5 and "file" in _x["components"][_k]:
                _x["components"][_k] = {"brick": json.load(open(_x["components"][_k]["file"]))}
                _mut(_x["components"][_k]["brick"])
            else:
                _mut(_x)
            _r = S.run(_x, conflicts=False)
            _n += 1
            if _r["verdict"] == "STAND ERROR":
                _errs.append(_r["why"][-80:])
finally:
    _os.chdir(_here)
check(f"components fuzz: {_n} mutated system bricks (inside components too): no STAND ERROR", not _errs, _errs[:3])

print(f"robust: {ok} ok, {fail} failed")
print("ROBUST GREEN" if fail == 0 else "ROBUST RED")
