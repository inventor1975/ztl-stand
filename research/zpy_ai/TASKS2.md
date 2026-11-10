# Six business rules with partly unverified inputs

Write ONE Python file `solutions.py` with the six functions below. Each takes `inputs`, a dict:

    inputs[name] = {"value": <bool or number or None>, "status": "verified" | "claimed" | "unknown"}

`verified` means checked. `claimed` means someone said so and nobody checked — it is only on record and must not be
acted on. `unknown` means nobody knows (`value` is `None`).

**The policy everywhere:** act only on what is verified. If the right outcome could still change depending on what the
unverified inputs really are, return `"needs_check"`; but do not ask for a check that could not change the outcome.
Each function returns its positive outcome, its negative outcome, or `"needs_check"`.

1. `approve_purchase(inputs)` -> `"approve"` / `"reject"` / `"needs_check"`.
   Premium customers may spend up to 5000 per purchase; everyone else up to 1000. A purchase flagged for fraud is never
   approved. Inputs: `premium`, `fraud_flag` (bools), `amount` (number).

2. `route_order(inputs)` -> `"approve"` / `"hold"` / `"needs_check"`.
   Orders over 100 need the manager's sign-off; orders of 100 or less need the clerk's sign-off.
   Inputs: `amount` (number), `manager_ok`, `clerk_ok` (bools).

3. `open_gate(inputs)` -> `"open"` / `"keep_closed"` / `"needs_check"`.
   The gate opens for a valid badge that is not revoked. It also opens in an emergency when a guard is present, and
   for a valid badge when a guard is present (a guard can vouch even for a revoked badge).
   Inputs: `badge_valid`, `revoked`, `emergency`, `guard_present` (bools).

4. `deploy(inputs)` -> `"deploy"` / `"block"` / `"needs_check"`.
   Deploy only if the tests pass. During a freeze only hotfixes may deploy. Any hotfix needs a security review.
   Inputs: `tests_pass`, `freeze`, `hotfix`, `security_review` (bools).

5. `fire_alarm(inputs)` -> `"alarm"` / `"quiet"` / `"needs_check"`.
   Normally the alarm follows the smoke detector. While the smoke detector is in test mode, the alarm follows the heat
   sensor instead. Inputs: `test_mode`, `smoke`, `heat` (bools).

6. `dispense(inputs)` -> `"give"` / `"withhold"` / `"needs_check"`.
   Never give to a patient with an allergy. A prescription is required. Patients of 40 kg or more may receive up to
   500 mg; lighter patients up to 250 mg. Inputs: `allergy`, `prescription` (bools), `weight_kg`, `dose_mg` (numbers).

Every input listed is always present. No other files: just `solutions.py`.
