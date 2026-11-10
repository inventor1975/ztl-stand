import itertools

_NUM = {
    "amount": [0, 100, 100.5, 101, 1000, 1000.5, 1001, 5000, 5000.5, 5001, 10**9],
    "weight_kg": [0, 39, 39.5, 40, 41, 10**6],
    "dose_mg": [0, 250, 250.5, 251, 500, 500.5, 501, 10**9],
}


def _decide(inputs, rule, pos, neg):
    names = list(inputs)
    domains = []
    for n in names:
        d = inputs[n]
        if d["status"] == "verified":
            domains.append([d["value"]])
        elif n in _NUM:
            domains.append(_NUM[n])
        else:
            domains.append([True, False])
    outs = set()
    for combo in itertools.product(*domains):
        outs.add(bool(rule(**dict(zip(names, combo)))))
        if len(outs) > 1:
            return "needs_check"
    return pos if outs.pop() else neg


def approve_purchase(inputs):
    return _decide(inputs, lambda premium, fraud_flag, amount:
                   (not fraud_flag) and amount <= (5000 if premium else 1000),
                   "approve", "reject")


def route_order(inputs):
    return _decide(inputs, lambda amount, manager_ok, clerk_ok:
                   manager_ok if amount > 100 else clerk_ok,
                   "approve", "hold")


def open_gate(inputs):
    return _decide(inputs, lambda badge_valid, revoked, emergency, guard_present:
                   (badge_valid and not revoked) or (emergency and guard_present)
                   or (badge_valid and guard_present),
                   "open", "keep_closed")


def deploy(inputs):
    return _decide(inputs, lambda tests_pass, freeze, hotfix, security_review:
                   tests_pass and (hotfix or not freeze)
                   and (security_review or not hotfix),
                   "deploy", "block")


def fire_alarm(inputs):
    return _decide(inputs, lambda test_mode, smoke, heat:
                   heat if test_mode else smoke,
                   "alarm", "quiet")


def dispense(inputs):
    return _decide(inputs, lambda allergy, prescription, weight_kg, dose_mg:
                   (not allergy) and prescription
                   and dose_mg <= (500 if weight_kg >= 40 else 250),
                   "give", "withhold")
