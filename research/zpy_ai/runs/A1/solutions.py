"""Three-valued (Kleene) decision functions; claimed == unknown."""

T, F, U = True, False, None


def _v(inputs, name):
    d = inputs[name]
    if d.get("status") == "verified" and d.get("value") is not None:
        return d["value"]
    return U


def _b(inputs, name):
    x = _v(inputs, name)
    return U if x is U else bool(x)


def _not(a):
    return U if a is U else (not a)


def _and(*xs):
    if any(x is F for x in xs):
        return F
    return U if any(x is U for x in xs) else T


def _or(*xs):
    if any(x is T for x in xs):
        return T
    return U if any(x is U for x in xs) else F


def _cmp(a, b, f):
    if a is U or b is U:
        return U
    return bool(f(a, b))


def _out(c, pos, neg):
    return pos if c is T else neg if c is F else "needs_check"


def approve_payment(inputs):
    c = _and(_cmp(_v(inputs, "amount"), 1000, lambda a, b: a <= b),
             _or(_b(inputs, "account_verified"), _b(inputs, "manager_ok")),
             _not(_b(inputs, "fraud_flag")))
    return _out(c, "approve", "reject")


def open_door(inputs):
    c = _and(_b(inputs, "badge_valid"),
             _or(_b(inputs, "in_schedule"), _b(inputs, "escort_present")),
             _not(_b(inputs, "revoked")))
    return _out(c, "open", "keep_closed")


def allow_deploy(inputs):
    c = _and(_b(inputs, "tests_pass"), _b(inputs, "review_approved"),
             _or(_not(_b(inputs, "freeze_active")), _b(inputs, "hotfix")))
    return _out(c, "deploy", "block")


def machine_action(inputs):
    c = _or(_cmp(_v(inputs, "temp"), 90, lambda a, b: a > b),
            _cmp(_v(inputs, "pressure"), 5, lambda a, b: a > b),
            _and(_b(inputs, "vibration_alarm"), _not(_b(inputs, "maintenance_mode"))))
    return _out(c, "shutdown", "run")


def approve_loan(inputs):
    c = _and(_cmp(_v(inputs, "income"), _v(inputs, "payment"),
                  lambda a, b: a >= 3 * b),
             _not(_b(inputs, "default_history")),
             _or(_b(inputs, "collateral"), _b(inputs, "guarantor")))
    return _out(c, "approve", "decline")


def give_medication(inputs):
    c = _and(_not(_b(inputs, "allergy")),
             _cmp(_v(inputs, "dose"), _v(inputs, "max_dose"), lambda a, b: a <= b),
             _or(_b(inputs, "prescription"), _b(inputs, "emergency")))
    return _out(c, "give", "withhold")
