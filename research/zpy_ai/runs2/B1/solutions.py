import zpy


def _atom(inputs, key, name=None, pred=None):
    """A zpy claim for one input (or a predicate over a numeric input), grounded by its status."""
    name = name or key
    item = inputs[key]
    status, v = item["status"], item["value"]
    if status == "unknown" or v is None:
        return zpy.unknown(name)
    val = pred(v) if pred else bool(v)
    if status == "verified":
        return zpy.fact(name, val, by="verified")
    return zpy.credit(name, val, source="claimed")


def _judge(positive, pos, neg):
    d = positive.disposition
    if d in ("EARNED", "EARNED IF STABLE"):
        return pos
    if d in ("REFUTED", "REFUTED IF STABLE"):
        return neg
    return "needs_check"


def approve_purchase(inputs):
    prem = _atom(inputs, "premium")
    fraud = _atom(inputs, "fraud_flag")
    le5000 = _atom(inputs, "amount", "le5000", lambda a: a <= 5000)
    le1000 = _atom(inputs, "amount", "le1000", lambda a: a <= 1000)
    ok = ~fraud & ((prem & le5000) | (~prem & le1000))
    return _judge(ok, "approve", "reject")


def route_order(inputs):
    big = _atom(inputs, "amount", "big", lambda a: a > 100)
    mgr = _atom(inputs, "manager_ok")
    clk = _atom(inputs, "clerk_ok")
    ok = (big & mgr) | (~big & clk)
    return _judge(ok, "approve", "hold")


def open_gate(inputs):
    valid = _atom(inputs, "badge_valid")
    rev = _atom(inputs, "revoked")
    emer = _atom(inputs, "emergency")
    guard = _atom(inputs, "guard_present")
    ok = (valid & ~rev) | (emer & guard) | (valid & guard)
    return _judge(ok, "open", "keep_closed")


def deploy(inputs):
    tests = _atom(inputs, "tests_pass")
    freeze = _atom(inputs, "freeze")
    hot = _atom(inputs, "hotfix")
    sec = _atom(inputs, "security_review")
    ok = tests & (~freeze | hot) & (~hot | sec)
    return _judge(ok, "deploy", "block")


def fire_alarm(inputs):
    test = _atom(inputs, "test_mode")
    smoke = _atom(inputs, "smoke")
    heat = _atom(inputs, "heat")
    on = (~test & smoke) | (test & heat)
    return _judge(on, "alarm", "quiet")


def dispense(inputs):
    allergy = _atom(inputs, "allergy")
    rx = _atom(inputs, "prescription")
    heavy = _atom(inputs, "weight_kg", "heavy", lambda w: w >= 40)
    d500 = _atom(inputs, "dose_mg", "d500", lambda d: d <= 500)
    d250 = _atom(inputs, "dose_mg", "d250", lambda d: d <= 250)
    ok = ~allergy & rx & ((heavy & d500) | (~heavy & d250))
    return _judge(ok, "give", "withhold")
