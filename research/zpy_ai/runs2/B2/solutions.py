"""Six business rules over zpy. Only verified inputs are acted on; unverified ones are enumerated
over every value they could really have, and the verdict of each completion is zpy's (all facts earned)."""
import itertools
import zpy


def _cands(ts):
    out = {0, 1e9, -1}
    for t in ts:
        out |= {t, t + 0.5, t - 0.5}
    return sorted(out)


def _solve(inputs, bools, nums, formula, pos, neg):
    """bools: names; nums: {name: thresholds}; formula(c) -> Claim built from facts c[name] (bools and
    derived comparisons are made by the rule itself via c['_v'])."""
    axes = []
    for n in bools + list(nums):
        x = inputs[n]
        if x["status"] == "verified":
            axes.append([x["value"]])
        elif n in nums:
            axes.append(_cands(nums[n]))
        else:
            axes.append([True, False])
    outcomes = set()
    for combo in itertools.product(*axes):
        v = dict(zip(bools + list(nums), combo))
        claim = formula(v)
        outcomes.add(zpy.decide(claim, earned=pos, refuted=neg, otherwise="needs_check"))
        if len(outcomes) > 1:
            return "needs_check"
    out = outcomes.pop()
    return out


def _f(name, value):
    return zpy.fact(name, bool(value), by="verified")


def approve_purchase(inputs):
    def formula(v):
        prem, fraud = _f("premium", v["premium"]), _f("fraud_flag", v["fraud_flag"])
        le5, le1 = _f("le5000", v["amount"] <= 5000), _f("le1000", v["amount"] <= 1000)
        return ~fraud & ((prem & le5) | (~prem & le1))
    return _solve(inputs, ["premium", "fraud_flag"], {"amount": [1000, 5000]}, formula, "approve", "reject")


def route_order(inputs):
    def formula(v):
        big, m, c = _f("over100", v["amount"] > 100), _f("manager_ok", v["manager_ok"]), _f("clerk_ok", v["clerk_ok"])
        return (big & m) | (~big & c)
    return _solve(inputs, ["manager_ok", "clerk_ok"], {"amount": [100]}, formula, "approve", "hold")


def open_gate(inputs):
    def formula(v):
        b, r, e, g = (_f(n, v[n]) for n in ("badge_valid", "revoked", "emergency", "guard_present"))
        return (b & ~r) | (e & g) | (b & g)
    return _solve(inputs, ["badge_valid", "revoked", "emergency", "guard_present"], {}, formula, "open", "keep_closed")


def deploy(inputs):
    def formula(v):
        t, f, h, s = (_f(n, v[n]) for n in ("tests_pass", "freeze", "hotfix", "security_review"))
        return t & (~f | h) & (~h | s)
    return _solve(inputs, ["tests_pass", "freeze", "hotfix", "security_review"], {}, formula, "deploy", "block")


def fire_alarm(inputs):
    def formula(v):
        t, s, h = (_f(n, v[n]) for n in ("test_mode", "smoke", "heat"))
        return (~t & s) | (t & h)
    return _solve(inputs, ["test_mode", "smoke", "heat"], {}, formula, "alarm", "quiet")


def dispense(inputs):
    def formula(v):
        a, p = _f("allergy", v["allergy"]), _f("prescription", v["prescription"])
        heavy = _f("w40", v["weight_kg"] >= 40)
        d500, d250 = _f("d500", v["dose_mg"] <= 500), _f("d250", v["dose_mg"] <= 250)
        return ~a & p & ((heavy & d500) | (~heavy & d250))
    return _solve(inputs, ["allergy", "prescription"], {"weight_kg": [40], "dose_mg": [250, 500]},
                  formula, "give", "withhold")
