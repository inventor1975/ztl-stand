# Six decision functions with partly unverified inputs

Write ONE Python file `solutions.py` with the six functions below. Each takes `inputs`, a dict:

    inputs[name] = {"value": <bool or number or None>, "status": "verified" | "claimed" | "unknown"}

- `verified` — checked; the value is reliable.
- `claimed` — someone said so, nobody checked. **A claimed value must not be relied on** for the decision: treat it
  exactly like an unknown one (the value is given only for the record).
- `unknown` — nobody knows; `value` is `None`.

Every function returns exactly one of THREE strings: the positive outcome, the negative outcome, or `"needs_check"`.

**The rule for all six:** return the positive outcome only if the condition holds **whatever** the claimed/unknown
inputs turn out to be; the negative outcome only if it fails **whatever** they turn out to be; otherwise
`"needs_check"`. (Unknown booleans may turn out True or False; unknown numbers may turn out any number.)

1. `approve_payment(inputs)` -> `"approve"` / `"reject"` / `"needs_check"`.
   Condition: `amount <= 1000` AND (`account_verified` OR `manager_ok`) AND NOT `fraud_flag`.
   Inputs: `amount` (number), `account_verified`, `manager_ok`, `fraud_flag` (bools).

2. `open_door(inputs)` -> `"open"` / `"keep_closed"` / `"needs_check"`.
   Condition: `badge_valid` AND (`in_schedule` OR `escort_present`) AND NOT `revoked`.

3. `allow_deploy(inputs)` -> `"deploy"` / `"block"` / `"needs_check"`.
   Condition: `tests_pass` AND `review_approved` AND (NOT `freeze_active` OR `hotfix`).

4. `machine_action(inputs)` -> `"shutdown"` / `"run"` / `"needs_check"`.
   Condition for shutdown: `temp > 90` OR `pressure > 5` OR (`vibration_alarm` AND NOT `maintenance_mode`).
   Inputs: `temp`, `pressure` (numbers), `vibration_alarm`, `maintenance_mode` (bools).

5. `approve_loan(inputs)` -> `"approve"` / `"decline"` / `"needs_check"`.
   Condition: `income >= 3 * payment` AND NOT `default_history` AND (`collateral` OR `guarantor`).
   Inputs: `income`, `payment` (numbers), `default_history`, `collateral`, `guarantor` (bools).

6. `give_medication(inputs)` -> `"give"` / `"withhold"` / `"needs_check"`.
   Condition: NOT `allergy` AND `dose <= max_dose` AND (`prescription` OR `emergency`).
   Inputs: `dose`, `max_dose` (numbers), `allergy`, `prescription`, `emergency` (bools).

Every input name listed is always present in `inputs`. No other files, no tests to write: just `solutions.py`.
