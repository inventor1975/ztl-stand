import zpy
from zpy import fact, unknown, decide


def _ok(inputs, name):
    return inputs[name]["status"] == "verified"


def _b(inputs, name):
    """A boolean input as a claim: earned only if verified; claimed/unknown stay unknown."""
    if _ok(inputs, name):
        return fact(name, bool(inputs[name]["value"]), by="verified")
    return unknown(name)


def _out(claim, pos, neg):
    return decide(claim, earned=pos, refuted=neg, otherwise="needs_check")


def _num(inputs, name, atom, test, *others):
    names = (name,) + others
    if all(_ok(inputs, n) for n in names):
        return fact(atom, bool(test(*[inputs[n]["value"] for n in names])), by="verified")
    return unknown(atom)


def approve_payment(inputs):
    small = _num(inputs, "amount", "small", lambda a: a <= 1000)
    c = small & (_b(inputs, "account_verified") | _b(inputs, "manager_ok")) & ~_b(inputs, "fraud_flag")
    return _out(c, "approve", "reject")


def open_door(inputs):
    c = _b(inputs, "badge_valid") & (_b(inputs, "in_schedule") | _b(inputs, "escort_present")) & ~_b(inputs, "revoked")
    return _out(c, "open", "keep_closed")


def allow_deploy(inputs):
    c = _b(inputs, "tests_pass") & _b(inputs, "review_approved") & (~_b(inputs, "freeze_active") | _b(inputs, "hotfix"))
    return _out(c, "deploy", "block")


def machine_action(inputs):
    hot = _num(inputs, "temp", "hot", lambda t: t > 90)
    high = _num(inputs, "pressure", "high", lambda p: p > 5)
    c = hot | high | (_b(inputs, "vibration_alarm") & ~_b(inputs, "maintenance_mode"))
    return _out(c, "shutdown", "run")


def approve_loan(inputs):
    afford = _num(inputs, "income", "afford", lambda i, p: i >= 3 * p, "payment")
    c = afford & ~_b(inputs, "default_history") & (_b(inputs, "collateral") | _b(inputs, "guarantor"))
    return _out(c, "approve", "decline")


def give_medication(inputs):
    dose_ok = _num(inputs, "dose", "dose_ok", lambda d, m: d <= m, "max_dose")
    c = ~_b(inputs, "allergy") & dose_ok & (_b(inputs, "prescription") | _b(inputs, "emergency"))
    return _out(c, "give", "withhold")
