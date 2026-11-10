"""Six business rules over partly unverified inputs, decided with zpy (act only on verified facts)."""
import zpy
from zpy import fact, credit, unknown, decide


def _atom(name, inputs, test=None):
    """A fact from an input: verified -> earned; claimed -> on credit (never acted on); else unknown.
    `test` turns a number into the bool the rule needs (e.g. amount <= 1000)."""
    i = inputs[name if test is None else test[0]]
    st, v = i["status"], i["value"]
    if test is not None:
        name, fn = test[1], test[2]
        if st == "verified":
            return fact(name, fn(v), by="verified")
        if st == "claimed":
            return credit(name, bool(v is not None and fn(v)), source="claimed")
        return unknown(name)
    if st == "verified":
        return fact(name, bool(v), by="verified")
    if st == "claimed":
        return credit(name, bool(v), source="claimed")
    return unknown(name)


def _num(inputs, key, atom, fn):
    return _atom(None, inputs, test=(key, atom, fn))


def _run(claim, yes, no):
    return decide(claim, earned=yes, refuted=no, otherwise="needs_check", if_stable="classical")


def approve_purchase(inputs):
    prem = _atom("premium", inputs)
    fraud = _atom("fraud_flag", inputs)
    le5000 = _num(inputs, "amount", "amount_le_5000", lambda a: a <= 5000)
    le1000 = _num(inputs, "amount", "amount_le_1000", lambda a: a <= 1000)
    gold = _atom("gold", inputs)
    le20000 = _num(inputs, "amount", "amount_le_20000", lambda a: a <= 20000)
    ok = ~fraud & ((gold & le20000) | (~gold & ((prem & le5000) | (~prem & le1000))))
    return str(_run(ok, "approve", "reject"))


def route_order(inputs):
    manager = _atom("manager_ok", inputs)
    clerk = _atom("clerk_ok", inputs)
    big = _num(inputs, "amount", "amount_over_100", lambda a: a > 100)
    director = _atom("director_ok", inputs)
    huge = _num(inputs, "amount", "amount_over_10000", lambda a: a > 10000)
    ok = (big & manager & (~huge | director)) | (~big & clerk)
    return str(_run(ok, "approve", "hold"))


def open_gate(inputs):
    valid = _atom("badge_valid", inputs)
    revoked = _atom("revoked", inputs)
    emer = _atom("emergency", inputs)
    guard = _atom("guard_present", inputs)
    lock = _atom("lockdown", inputs)
    ok = (emer & guard) | (~lock & ((valid & ~revoked) | (valid & guard)))
    return str(_run(ok, "open", "keep_closed"))


def deploy(inputs):
    tests = _atom("tests_pass", inputs)
    freeze = _atom("freeze", inputs)
    hot = _atom("hotfix", inputs)
    sec = _atom("security_review", inputs)
    ci = _atom("ci_green", inputs)
    ok = ci & tests & (~freeze | hot) & (~hot | sec)
    return str(_run(ok, "deploy", "block"))


def fire_alarm(inputs):
    test = _atom("test_mode", inputs)
    smoke = _atom("smoke", inputs)
    heat = _atom("heat", inputs)
    pull = _atom("manual_pull", inputs)
    ring = pull | (~test & smoke) | (test & heat)
    return str(_run(ring, "alarm", "quiet"))


def dispense(inputs):
    allergy = _atom("allergy", inputs)
    rx = _atom("prescription", inputs)
    heavy = _num(inputs, "weight_kg", "weight_ge_40", lambda w: w >= 40)
    d500 = _num(inputs, "dose_mg", "dose_le_500", lambda d: d <= 500)
    d250 = _num(inputs, "dose_mg", "dose_le_250", lambda d: d <= 250)
    doc = _atom("doctor_override", inputs)
    d750 = _num(inputs, "dose_mg", "dose_le_750", lambda d: d <= 750)
    ok = ~allergy & rx & ((heavy & d500) | (~heavy & d250) | (doc & d750))
    return str(_run(ok, "give", "withhold"))
