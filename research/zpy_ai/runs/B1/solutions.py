import zpy


def _b(inputs, name):
    d = inputs[name]
    if d["status"] == "verified":
        return zpy.fact(name, bool(d["value"]), by="verified")
    return zpy.unknown(name)


def _cmp(inputs, atom, names, test):
    """Atom over numbers: decided only if every number is verified; else unknown."""
    if all(inputs[n]["status"] == "verified" for n in names):
        return zpy.fact(atom, bool(test(*[inputs[n]["value"] for n in names])), by="verified")
    return zpy.unknown(atom)


def _out(claim, pos, neg):
    return zpy.decide(claim, earned=pos, refuted=neg, otherwise="needs_check")


def approve_payment(inputs):
    c = (_cmp(inputs, "amount_ok", ["amount"], lambda a: a <= 1000)
         & (_b(inputs, "account_verified") | _b(inputs, "manager_ok"))
         & ~_b(inputs, "fraud_flag"))
    return _out(c, "approve", "reject")


def open_door(inputs):
    c = (_b(inputs, "badge_valid")
         & (_b(inputs, "in_schedule") | _b(inputs, "escort_present"))
         & ~_b(inputs, "revoked"))
    return _out(c, "open", "keep_closed")


def allow_deploy(inputs):
    c = (_b(inputs, "tests_pass") & _b(inputs, "review_approved")
         & (~_b(inputs, "freeze_active") | _b(inputs, "hotfix")))
    return _out(c, "deploy", "block")


def machine_action(inputs):
    c = (_cmp(inputs, "temp_hot", ["temp"], lambda t: t > 90)
         | _cmp(inputs, "pressure_high", ["pressure"], lambda p: p > 5)
         | (_b(inputs, "vibration_alarm") & ~_b(inputs, "maintenance_mode")))
    return _out(c, "shutdown", "run")


def approve_loan(inputs):
    c = (_cmp(inputs, "income_ok", ["income", "payment"], lambda i, p: i >= 3 * p)
         & ~_b(inputs, "default_history")
         & (_b(inputs, "collateral") | _b(inputs, "guarantor")))
    return _out(c, "approve", "decline")


def give_medication(inputs):
    c = (~_b(inputs, "allergy")
         & _cmp(inputs, "dose_ok", ["dose", "max_dose"], lambda d, m: d <= m)
         & (_b(inputs, "prescription") | _b(inputs, "emergency")))
    return _out(c, "give", "withhold")
