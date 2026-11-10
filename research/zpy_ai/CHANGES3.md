# Change requests for `solutions.py`

`solutions.py` in your run directory is working code for the rules in TASKS2.md (same input format, same policy:
act only on what is verified; a claimed value is not verified; if the right outcome could still change depending on
what the unverified inputs really are, return `"needs_check"`, and do not ask for a check that could not change the
outcome). Product has sent six changes. Apply all of them to `solutions.py` in place, keeping everything else as it
is. New inputs come in the same format and are always present.

1. **approve_purchase** — new tier: Gold customers (new input `gold`, bool) may spend up to 20000 per purchase.
   Gold overrides the premium/standard limits. Fraud still blocks everything.
2. **route_order** — orders over 10000 additionally need the director's sign-off (new input `director_ok`, bool), on
   top of the manager's. Orders over 100 up to 10000 stay as they are (manager), 100 or less stay with the clerk.
3. **deploy** — block unless the CI pipeline is green: new input `ci_green` (bool) must be true, in addition to
   everything else.
4. **fire_alarm** — a manual pull station was installed: if `manual_pull` (new input, bool) is true, the alarm sounds,
   whatever the detectors say.
5. **dispense** — a doctor's override (new input `doctor_override`, bool) allows up to 750 mg regardless of weight.
   An allergy still always withholds, and a prescription is still required.
6. **open_gate** — lockdown (new input `lockdown`, bool) keeps the gate closed for badges, even with a guard present;
   an emergency with a guard present still opens it.
