"""Six business rules over partly unverified inputs, decided with zpy (ZTL layer).

Only verified inputs are earned facts; claimed ones are credit (read as Z), unknown ones are unknown.
Each rule is a claim for the positive outcome; decide() with if_stable="classical" walks every completion
of the unverified facts, so "needs_check" is returned exactly when the outcome could still change.
"""
import zpy
from zpy import fact, credit, unknown, decide


def _atom(inputs, key, pred, name):
    """A boolean fact `name` = pred(value of inputs[key]), grounded as the input is."""
    i = inputs[key]
    st = i["status"]
    if st == "verified":
        return fact(name, bool(pred(i["value"])), by="verified input " + key)
    if st == "claimed" and i["value"] is not None:
        return credit(name, bool(pred(i["value"])), source="claimed input " + key)
    return unknown(name)


def _b(inputs, key):
    return _atom(inputs, key, lambda v: v, key)


def _run(claim, yes, no):
    return decide(claim, earned=yes, refuted=no, otherwise="needs_check", if_stable="classical")


def approve_purchase(inputs):
    p, fraud = _b(inputs, "premium"), _b(inputs, "fraud_flag")
    a5 = _atom(inputs, "amount", lambda v: v <= 5000, "amt_le_5000")
    a1 = _atom(inputs, "amount", lambda v: v <= 1000, "amt_le_1000")
    ok = ~fraud & ((p & a5) | (~p & a1))
    return str(_run(ok, "approve", "reject"))


def route_order(inputs):
    m, c = _b(inputs, "manager_ok"), _b(inputs, "clerk_ok")
    big = _atom(inputs, "amount", lambda v: v > 100, "big")
    ok = (big & m) | (~big & c)
    return str(_run(ok, "approve", "hold"))


def open_gate(inputs):
    v, r = _b(inputs, "badge_valid"), _b(inputs, "revoked")
    e, g = _b(inputs, "emergency"), _b(inputs, "guard_present")
    ok = (v & ~r) | (e & g) | (v & g)
    return str(_run(ok, "open", "keep_closed"))


def deploy(inputs):
    t, fr = _b(inputs, "tests_pass"), _b(inputs, "freeze")
    h, s = _b(inputs, "hotfix"), _b(inputs, "security_review")
    ok = t & (~fr | h) & (~h | s)
    return str(_run(ok, "deploy", "block"))


def fire_alarm(inputs):
    tm, sm, ht = _b(inputs, "test_mode"), _b(inputs, "smoke"), _b(inputs, "heat")
    on = (~tm & sm) | (tm & ht)
    return str(_run(on, "alarm", "quiet"))


def dispense(inputs):
    al, rx = _b(inputs, "allergy"), _b(inputs, "prescription")
    heavy = _atom(inputs, "weight_kg", lambda v: v >= 40, "heavy")
    d5 = _atom(inputs, "dose_mg", lambda v: v <= 500, "dose_le_500")
    d2 = _atom(inputs, "dose_mg", lambda v: v <= 250, "dose_le_250")
    ok = ~al & rx & ((heavy & d5) | (~heavy & d2))
    return str(_run(ok, "give", "withhold"))
