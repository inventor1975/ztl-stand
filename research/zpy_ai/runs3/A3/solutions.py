from itertools import product

NC = "needs_check"


def _decide(inputs, rule, num_candidates):
    """Enumerate every possible value of unverified inputs; verified ones are fixed.
    If all completions give the same outcome return it, else needs_check."""
    names = list(inputs)
    options = []
    for n in names:
        d = inputs[n]
        if d.get("status") == "verified":
            options.append([d["value"]])
        elif n in num_candidates:
            options.append(num_candidates[n])
        else:
            options.append([True, False])
    outcomes = {rule(**dict(zip(names, combo))) for combo in product(*options)}
    return outcomes.pop() if len(outcomes) == 1 else NC


def approve_purchase(inputs):
    def rule(premium, fraud_flag, amount, gold):
        if fraud_flag:
            return "reject"
        return "approve" if amount <= (20000 if gold else 5000 if premium else 1000) else "reject"
    return _decide(inputs, rule, {"amount": [0, 1000, 1001, 5000, 5001, 20000, 20001, 10**9]})


def route_order(inputs):
    def rule(amount, manager_ok, clerk_ok, director_ok):
        if amount > 10000:
            ok = manager_ok and director_ok
        else:
            ok = manager_ok if amount > 100 else clerk_ok
        return "approve" if ok else "hold"
    return _decide(inputs, rule, {"amount": [0, 100, 100.01, 101, 10000, 10000.01, 10001, 10**9]})


def open_gate(inputs):
    def rule(badge_valid, revoked, emergency, guard_present, lockdown):
        badge_ok = (badge_valid and not revoked) or (badge_valid and guard_present)
        ok = (emergency and guard_present) or (badge_ok and not lockdown)
        return "open" if ok else "keep_closed"
    return _decide(inputs, rule, {})


def deploy(inputs):
    def rule(tests_pass, freeze, hotfix, security_review, ci_green):
        ok = ci_green and tests_pass and (hotfix or not freeze) and (security_review or not hotfix)
        return "deploy" if ok else "block"
    return _decide(inputs, rule, {})


def fire_alarm(inputs):
    def rule(test_mode, smoke, heat, manual_pull):
        return "alarm" if manual_pull or (heat if test_mode else smoke) else "quiet"
    return _decide(inputs, rule, {})


def dispense(inputs):
    def rule(allergy, prescription, weight_kg, dose_mg, doctor_override):
        if allergy or not prescription:
            return "withhold"
        lim = 500 if weight_kg >= 40 else 250
        if doctor_override:
            lim = max(lim, 750)
        return "give" if dose_mg <= lim else "withhold"
    return _decide(inputs, rule, {"weight_kg": [0, 39.9, 40, 200],
                                  "dose_mg": [0, 250, 250.1, 500, 500.1, 750, 750.1, 10**6]})
