"""Decision functions with partly unverified inputs (Kleene three-valued logic).

Each input variable occurs once per formula, so Kleene evaluation is exact.
Values: True, False, None (None = could be either).
"""


def _v(inputs, name):
    d = inputs[name]
    if d.get("status") == "verified" and d.get("value") is not None:
        return d["value"]
    return None


def _and(*xs):
    if any(x is False for x in xs):
        return False
    return None if any(x is None for x in xs) else True


def _or(*xs):
    if any(x is True for x in xs):
        return True
    return None if any(x is None for x in xs) else False


def _not(x):
    return None if x is None else (not x)


def _b(inputs, name):
    x = _v(inputs, name)
    return None if x is None else bool(x)


def _cmp(inputs, a, b, op):
    x, y = _v(inputs, a) if isinstance(a, str) else a, _v(inputs, b) if isinstance(b, str) else b
    if x is None or y is None:
        return None
    return op(x, y)


def _out(r, pos, neg):
    return pos if r is True else neg if r is False else "needs_check"


def approve_payment(inputs):
    r = _and(_cmp(inputs, "amount", 1000, lambda x, y: x <= y),
             _or(_b(inputs, "account_verified"), _b(inputs, "manager_ok")),
             _not(_b(inputs, "fraud_flag")))
    return _out(r, "approve", "reject")


def open_door(inputs):
    r = _and(_b(inputs, "badge_valid"),
             _or(_b(inputs, "in_schedule"), _b(inputs, "escort_present")),
             _not(_b(inputs, "revoked")))
    return _out(r, "open", "keep_closed")


def allow_deploy(inputs):
    r = _and(_b(inputs, "tests_pass"), _b(inputs, "review_approved"),
             _or(_not(_b(inputs, "freeze_active")), _b(inputs, "hotfix")))
    return _out(r, "deploy", "block")


def machine_action(inputs):
    r = _or(_cmp(inputs, "temp", 90, lambda x, y: x > y),
            _cmp(inputs, "pressure", 5, lambda x, y: x > y),
            _and(_b(inputs, "vibration_alarm"), _not(_b(inputs, "maintenance_mode"))))
    return _out(r, "shutdown", "run")


def approve_loan(inputs):
    income, payment = _v(inputs, "income"), _v(inputs, "payment")
    ratio = None if income is None or payment is None else income >= 3 * payment
    r = _and(ratio, _not(_b(inputs, "default_history")),
             _or(_b(inputs, "collateral"), _b(inputs, "guarantor")))
    return _out(r, "approve", "decline")


def give_medication(inputs):
    r = _and(_not(_b(inputs, "allergy")),
             _cmp(inputs, "dose", "max_dose", lambda x, y: x <= y),
             _or(_b(inputs, "prescription"), _b(inputs, "emergency")))
    return _out(r, "give", "withhold")
