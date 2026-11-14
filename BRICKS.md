# How to write bricks (ztl-stand/1)

This is a reference for whoever writes the next JSON, including a future me with
no memory of today.

One JSON file holds the whole question: the world, the choices, the laws, the requirements, the factory catalog.
Run it with `python3 -m ustand.stand file.json`. Worked examples are in `examples/` and `examples/tasks/`.
With many designs add `--jobs N` (since 2026-10-11): the designs are judged ahead by N worker processes, in the
same order; the verdict and the output are the same, only faster (each worker needs its own memory). Since
2026-10-13 it also speeds up the search over NONLINEAR continuous amounts (workers compute its next steps ahead).
Two modes (since 2026-10-11): by default the verdicts are ZTL's (the workhorse); `--dev` adds the independent
checker on every design and every certificate — for new kinds of problems and small trials. The output's
`checked_by` says which.

## The skeleton

```json
{
  "stand": "ztl-stand/1",
  "quantities":   { "...": {} },
  "slots":        { "...": {} },
  "define":       { "...": "..." },
  "laws":         [ {"zfl": "...", "source": "..."} ],
  "requirements": [ {"quantity": "...", "op": "...", "value": "..."} ],
  "objective":    {"minimize": "..."},
  "catalog":      { "...": {} }
}
```

`define` and `objective` are optional; everything else is required. With nothing to choose, write
`"slots": {}` and `"catalog": {}` — a check of one fixed design (real round 2: s01, s03).

## 1. quantities — what the world gives, and what follows

```json
"Vin":  {"role": "given",   "value": "5",  "unit": "V", "ground": "psu"},
"P":    {"role": "given",   "value": "20", "tolerance": "0.1", "unit": "W"},
"Ta":   {"role": "given",   "range": ["20", "45"], "unit": "degC"},
"Vout": {"role": "derived", "unit": "V"}
```

- **given**: fixed by the world. Write it in one of three ways:
  - `value` alone — exact;
  - `value` with `tolerance` — relative, ±10% is `"0.1"`. The tolerance may NAME a given dimensionless quantity
    (since 2026-10-12): `"R1": {"role": "given", "value": "1000", "tolerance": "tol", "unit": "ohm"}` with
    `"tol": {"role": "given", "value": "0.001"}` — the box is value * (1 +- t) for the worst t in tol's box, so one
    tolerance can be shared and `find` can search it ("the largest tolerance that still works", real round 3, n01);
  - `range` — absolute, both ends.

  The stand must hold for every value inside the tolerance or range ("for all"). `ground` names who vouches for an
  exact value (it becomes ZTL's earned ground). Different givens vary INDEPENDENTLY: every combination inside their
  boxes is covered. A value shared by several parts is ONE quantity used in several laws (real round 3, s09).
- **derived**: follows from the laws. Every derived quantity must be determined by the laws.
- There is no "choose" role: choices are **slots** (section 2).
- Numbers are strings, read as exact fractions: `"0.01"` is 1/100, `"1/3"` is 1/3, `"76.8/1000000"` is 0.0000768.
- Never write floats with a binary meaning such as `0.1` as a number. Always use strings.

## 2. slots and catalog — what the designer may pick

```json
"slots": {"R1": {"from": ["res_1pct_quarterW", "res_0.1pct_quarterW"]}},
"catalog": {
  "res_1pct_quarterW": {
    "series": "E24", "decades": [1000, 10000], "ground": "datasheet",
    "fields": {"R": {"series": true, "tolerance": "0.01", "unit": "ohm"},
               "P": {"value": "0.25", "unit": "W"}}
  }
}
```

- A **slot** is a place in the design. It names the catalogs it may take an **item** from.
- An **item** has **fields**. Putting an item in slot `R1` creates one quantity per field: `R1.R`, `R1.P`. Use them
  in laws, requirements and the objective.
- There are three ways to write a catalog:
  - **E-series**: `"series": "E24"` (also `"E3"`, `"E6"`, `"E12"`, `"E48"`, `"E96"`, `"E192"`), plus `"decades"`.
    - The decade multiplies the series value read as 1.0 … 9.x: with decade 1000 the E24 row runs 1000, 1100, …, 9100
      and the E96 row 1000, 1020, …, 9760. E48/E96/E192 follow IEC 60063 (E192 with its 9.20).
    - The decades are in the FIELD's unit: with `"unit": "kohm"`, decades `[10, 100]` give 10.0 … 976 kohm (s10).
    - Exactly one field carries `"series": true`. The other fields take their `value` (or `range`) as given.
  - **Listed items**:

    ```json
    "items": [{"R": {"value": "5", "tolerance": "0.1"}, "price": "1", "grade": "fine"}, ...],
    "fields": {"R": {"unit": "C/W"}, "price": {"unit": "USD"}}
    ```

    - A field is either a plain value, `{"value", "tolerance"}`, or `{"range": [lo, hi]}`.
    - A non-numeric field ("grade") is a **label**: it is shown in the output but is not a quantity. A name that
      LOOKS like a number ("6309" for a bearing) is read as a number — and then needs a unit like any number
      (`"name": {"unit": ""}`); write it as text ("6309 bearing") if it is only a name.
    - Units of listed items go in the catalog's `fields` block.
  - **Integers**: `"integers": {"field": "N", "from": "1", "to": "12", "unit": ""}`.
- The stand tries every combination of items across all slots, so the count is the product of the catalog sizes.

### where and computed — the design space and per-design values (since 2026-10-10)

```json
"where":    ["STR.NP <= 2*INV.inputs", "SYS.name == \"phosphate\" or VA.N <= Vmax"],
"computed": {"spi": "ceil(STR.NP / INV.inputs)", "Acs": {"value": "D.w*D.h", "unit": "m^2"}}
```

- `where`: conditions on EXACT values; a combination of items that fails one is not a design at all (the output
  says `excluded_by_where`). Use it for compatibility ("no more strings than inputs"), per-item windows ("this
  system only with these volumes") and pre-filters that make a large catalog small. Since 2026-10-11 it may use
  `exp`, `ln`, `log10`, `sqrt` (a pre-filter by physics, e.g. an NTC's resistance at a temperature): their values
  are held as exact-fraction intervals, and a comparison they do not decide (two sides equal to ~55 digits, like
  `log10(1000) == 3`) is a BRICK ERROR, never a guess. `computed` stays exact: no exp/ln there.
- `computed`: a value per design from EXACT values, then used like a given quantity in laws, requirements, the
  objective and `where`. Declare its unit (`{"value", "unit"}`); a plain string means dimensionless.
- Both read: given quantities without tolerance, catalog fields without tolerance, labels (compare with `==` /
  `!=`), other computed values. Operators: `+ - * /`, comparisons, `and or not`, and `ceil floor abs min max`.
- Names are read in SI, like laws. A bare number beside a quantity with a unit (`VA.N <= 30` with N in mL) is a
  BRICK ERROR — 30 would be read as 30 m^3; write the bound as a given quantity with its unit. `ceil`/`floor` need a
  dimensionless argument (round a ratio).
- They define the design space; they state nothing about physics, so nothing in them is judged.

### Continuous choices — any amount in a range (since 2026-10-10)

```json
"slots":   {"MZ": {"from": ["maize"]}, "SB": {"from": ["soy"]}},
"catalog": {"maize": {"continuous": {"field": "x", "from": "45", "to": "70", "unit": ""}},
            "soy":   {"continuous": {"field": "x", "from": "0",  "to": "40", "unit": ""}}}
```

- A continuous slot takes any amount in its range. When the objective and every requirement's quantity are AFFINE in
  the amounts (coefficients may be toleranced givens), the stand finds the cheapest mix of the ROBUST problem (every
  requirement for every value of the box) with an LP solver, judges that mix like any design, and asks ZTL to PROVE
  that no mix in the box costs less than a bound L (weak LP duality; ZTL derives every coefficient from the laws
  itself and checks the affinity). The output: the mix, its cost, `lower_bound` and `gap`.
- A batch that must sum to a total is a requirement `within [total, total]` on a derived sum — kept an exact equality.
- **No mix exists** is PROVED, not just reported: when the robust LP finds no mix, a phase-1 LP's multipliers go to ZTL
  (`zlp.infeasible`, Farkas — the box-maximum of the weighted requirement margins is below zero) and that combination
  is REFUTED (`combinations_proved_without_mix`). Without the proof it stays OPEN, as before.
- **With modes** (since 2026-10-10): every mode's requirements, each over that mode's own box of data, go into ONE LP;
  the mix is judged in every mode (`per_mode`), the bound and the Farkas proof cover every mode's box.
- **One datum in several coefficients** (since 2026-10-12, blind test 5 c11: one spot rate in three coefficients).
  The robust LP above takes each coefficient's worst case APART and may find no mix although one exists. The stand
  then reads the requirements at finitely many DATA POINTS (scenario cuts): the LP over them is a relaxation of the
  robust problem. Its mix is judged over the WHOLE box like any design; a failing point and each row's hardest point
  at that mix are added, and again (up to 40 rounds). An EARNED mix: the relaxation's multipliers give ZTL the lower
  bound (`zlp.lower_bound` at those points) — it holds for every mix, since the relaxation asks less. An infeasible
  relaxation: Farkas at those points proves no mix. `lower_bound_is` names the points and rounds. A mix that touches
  a bound exactly is judged again a hair inside (the LP's margin x100, x10^4, x10^5); the `gap` shows what that cost.
  MEASURED: c11 on its TRUE box (four quarterly spot rates as ranges, not 625 point modes) — EARNED 52.9093 kEUR,
  L 52.9092, two strike choices proved without a mix, 4 min 54 s.
- **Amounts NOT affine** (since 2026-10-12, J3, the curator's "да": a purge inside a ratio, a surcharge under a
  log10, a mass in an exponent). Per discrete combination: a local solver (outside, untrusted) finds the cheapest mix
  over the requirements read at data points (the same scenario loop); the stand judges that mix over the WHOLE box;
  then ZTL checks a split of the AMOUNTS' box (`zmin`, Lean `ZMin.min_sound`): every piece either "the objective is
  >= L here" or "requirement i fails here at ONE point of its data". The output names it in `lower_bound_is`
  ("zmin: ... split in N pieces"). Every piece failing: that combination has NO mix (REFUTED when all have none).
  A combination proved not to beat the cheapest mix found so far is not searched (its bound still checked).
  Without a bound the mix stays EARNED, `lower_bound` null. Equalities must still be affine (a batch total).
  MEASURED: blind c01 with the PCM mass continuous — EARNED VIP-40, 6.3667 kg, 109.384 EUR, 12 insulations in 36 s
  (11 proved without a mix; the author's 0.01 kg grid: 273 s); blind c05 with the surcharge continuous — EARNED A,
  0.9 / 1.1 m, h 0.1762 m, 149 647 EUR, L 149 646, 300 combinations in 7 min (228 without a mix; the author's
  grid 0.18 m, 150 075 EUR). **Laws that are a linear SYSTEM** (since 2026-10-12, c06: ten concentration laws
  with the purge fraction in their coefficients): the search reads the stand's own solution, while what ZTL reads
  is the KERNEL's own (zcertify.solve_system, Cramer, on the connected part of the system the requirement leans
  on; up to 6 unknowns). c06 with p continuous and the modules pinned: EARNED p = 1/92, 137 804 EUR/yr, the bound
  proved within 0.41 EUR, 3.4 s — the author's own hand optimum, where the stand had only his grid.
- A requirement bound may name EXACT values of the combination (a part's own limit, `DEV.Tc`; since 2026-10-12): read
  per combination. A bound naming a toleranced quantity, a derived one or an amount is refused.
- Version 1: amounts >= 0; every derived quantity defined explicitly (`X == ...`); numeric requirement bounds;
  a nominal objective. Discrete slots may sit beside continuous ones (one LP per discrete combination).

## 3. define — names for expressions of given and catalog quantities

```json
"define": {"R1T": "R1.R*(1 + R1.a*(T - 25))"}
```

Each define is expanded in place, in parentheses, inside the laws and the objective.

**Use it for anything that depends ONLY on given or catalog quantities.** Do not declare such a thing as a derived
quantity.
- A derived quantity is an unknown. Multiplying an unknown by another unknown (`I*R1T`) leaves the linear class.
- A define keeps it a coefficient, so the system stays linear and ZTL solves it exactly. Task t5 shows this.

## 4. laws — one equality each, ZFL syntax

```json
{"zfl": "Vin - Vout == I*R1.R", "source": "Ohm's law"}
```

- Each law is exactly one equality, `lhs == rhs`, using `+ - * /`, numbers, names and `slot.field`.
- Always give `source`: it is the law's ground.
- **The linear class**, which ZTL solves exactly:
  - every law is linear in the derived quantities;
  - given and catalog quantities may multiply them.
  - Example: `Vout == I*R2.R` is linear in I and Vout.
  - **Many coupled linear unknowns** (since 2026-10-15): up to 6 the stand solves the system symbolically; above
    that a requirement is proved by a certificate over the whole box — searched outside, checked exactly by ZTL's
    kernel module `zlin.py` (enclosure of the interval system, read per tolerance; monotone tolerances pinned at
    their ends; an exact solve at the corner). Measured on a ladder: 20 unknowns / 41 tolerances — the exact worst
    case in 0.6 s; 50 / 101 in 5 s (bench/CAPACITY.md). What the requirement may read:
    - one unknown (`u19 >= 0.001`), or a LINEAR expression of them through a definition (`dV == u18 - u19`,
      `I == (u18 - u19)/R19`): the expression joins the system as one more unknown — certified exactly;
    - a NONLINEAR expression (`P == u19*u19/G19`): each unknown it reads first gets a range proved by zlin, and the
      expression is certified by ZTL over those ranges as boxes — sound, but wider than the truth (the unknowns' tie
      to the tolerances is lost); when that is too wide the requirement stays OPEN and says so.
    Wide tolerances on EVERY part (since 2026-10-15 evening): a quantity that enters the system "by one layer" (a
    resistor, a conductance, a source in series — the kernel PROVES it by an exact identity, never assumes it) has
    its sign read by three factors and may be branched on its two ends (its extremes lie on them). Measured, the exact
    worst case: every part +-10 % on 5 unknowns 0.1 s, 10 unknowns ~70 s; every part +-5 % on 10 unknowns 0.2 s, on 20
    ~10 s. A quantity that does not enter by one layer keeps the first-order rule.
    `--dev` beyond its 16-tolerance corner wall: the checker re-checks zlin's certificate with its own code
    (`checker.check_linear_certificate`); a requirement without a re-checked certificate stays OPEN, said.
- **A nonlinear definition** is allowed only in the form `X == expression`, where X is one derived quantity and the
  expression may multiply derived quantities. Example: `P1 == I*I*R1.R`.
  - ZTL bounds it by its own interval reading, one definition at a time ("ZTL, interval reading of the definition");
    only where ZTL cannot read it does the stand bound it itself, and `how` then says "outside ZTL".
- **A derived quantity equal to a product or quotient of toleranced quantities** (`tau == R.R*C.C`) is read the
  same way ("ZTL, outer range" or "ZTL, interval reading").
- A nonlinear law that defines nothing (`Vout*I == I*I`) is refused.
- **Chains of definitions are fine.** A law `X == expression` whose expression is nonlinear, holds a function, or
  uses another definition is itself a definition (`Ptot == P1 + P2` with `P1 == I*I*R1`;
  `Dveff == Dv - g0*tb` with `Dv == Isp*g0*ln(m0/mf)`). A defined quantity inside a law that is NOT of the form
  `X == ...` (`Ptot - P1 == P2`) is a BRICK ERROR: rewrite it as `X == ...`.
- Each law once: a law written twice is a BRICK ERROR (it made the system look over-determined).
- **A law's domain**: `{"zfl": "TN == gw + L100/(mu - lam)", "valid": "mu > lam", ...}`. The condition becomes a
  requirement (a quantity `valid_<i>` = left side minus right side, required `> 0`), so a design whose box leaves the
  region where the formula holds is REFUTED with "laws[i] holds only where ...". Without it the stand computes the
  formula wherever it is defined — an M/M/1 latency with mu < lambda came out negative and a nonsense design was
  EARNED (t16b keeps that as a warning).
- `op` may also be the strict `<` or `>` (a value exactly on the bound fails). Strict bounds are decided by the
  readings and corners; certificates prove only `<=` and `>=`.
- **Functions** (since 2026-10-10): `exp ln log10 atan tan sin cos sqrt` (one argument; `sin cos` since 2026-10-13), `pow min max` (two); `a**b` is
  `pow(a, b)`.
  - ZTL reads each as a proved bracket of fractions, about 1e-14 wide or narrower.
  - The independent checker reads it with mpmath's interval arithmetic, a different implementation.
  - A transcendental function needs a dimensionless argument. `exp` of a time is a BRICK ERROR: divide by a time
    constant first.
  - `x^n` and `x**n` are `pow(x, n)` (since 2026-10-11). `abs(x)` is the branch `if(x > 0, x, -x)` — everything
    below about branches holds for it.
  - `pow(x, n)` with a constant `n` (integer or not: `pow(H, 1.5)`) carries x's unit to that power; an exponent that
    is not a constant needs a dimensionless x. For a negative power write a quotient: `K/pow(R, 1.033)` (s10).
  - `tan` is read on |x| <= 1.5 only; `ln` and `log10` need a positive argument. `sin` and `cos` take any
    argument in radians — an angle in `deg` is converted (its unit is a pure number pi/180).
  - A law with a function must have the form `X == expression` — or be an implicit law (below).
  - **Branches** (since 2026-10-10): `if(A > B, a, b)` — `a` where the comparison holds, `b` elsewhere; `<`, `<=`,
    `>`, `>=` only. Where the comparison is decided over the whole box (or a piece of it) only that branch is read;
    where it is not, the value is the hull of both — sound, may be wide. Both branches need the same unit. A jump
    between the branches is never mistaken for a monotone function (its derivative is not read across the switch).
    Example: `Pall == if(x > 1, Sy/(2*x), Sy*(1 - x/2))*A/n` (Euler or Johnson).
  - **Tables** (since 2026-10-11): `table(x, x0, y0, x1, y1, ...)` — linear between the knots, the end value held
    beyond them (say so in `why` if the source extrapolates instead). At least two knots; numeric x-knots must
    increase. The y-values may be numbers, given quantities or `slot.field`s (a pad's friction per temperature).
    It compiles to the same `if` chain you would type, so everything above about branches holds. Knots are numbers
    read in SI next to `x`: with a dimensional `x`, divide it by a unit given (`table(T/Tu, ...)`, `Tu = 1 K`).
    A maximum AT an inner knot that equals the bound exactly stays OPEN (the box is cut at the knot but the
    pieces still touch it); a hair of margin decides it.
    Example: `mu == table(Tf/Tu, 100, PAD.m100, 300, PAD.m300, 450, PAD.m450)`.
    The y values carry their units: a given quantity or a field with a unit — a bare number is dimensionless
    (real round 2, s06).
  - `sin`, `cos` and inverse trigonometry other than `atan` do not exist yet.
  - With a function, a value at a point is an interval. A requirement is violated there only when ALL of the
    interval is past the bound (a witness is certain, never a rounding).

### Implicit laws — an operating point where two curves meet (since 2026-10-10, G6)

```json
"Q": {"role": "derived", "unit": "m^3/h", "search": ["0.5", "70"]},
...
{"zfl": "PUMP.H0 - PUMP.a*Q*Q == dz + (FSJ*L/D + SK)*V*V/(2*G)", "source": "pump curve = system curve"}
```

- Give the quantity a `"search": [low, high]` range (in its own unit). Its law is the ONE law in which it appears
  that does not define another quantity; Q may sit on both sides and inside functions (here the friction factor
  `FSJ` is Swamee–Jain at the flow itself, through `define`).
- Other laws may use Q freely: `P == RHO*G*Q*H/PUMP.eta`, `dT == P/(rho*cp*Q)`.
- What it means: every root of the law inside `search`, for every value of the box. The stand SEARCHES a
  root-exclusion certificate; ZTL CHECKS it (ZTL `zimplicit.py`: every excluded piece by its own reading, uniqueness
  by dg/dQ, and, when the root is monotone in every parameter, the two extreme corners bracketed by an exact sign
  change — then the range is tight). The checker finds its OWN enclosure with its own derivative and arithmetic
  and confirms ZTL's ends independently.
- More than one root in `search` (x² = p on [-3, 3]): the range holds every branch, and a requirement must hold on
  all of them. Narrow `search` to the physical branch if you mean one.
- No root in `search` for a design: that design is OPEN, with the reason. Widen `search` if it is too narrow.
- **The root must be BUILT** (since 2026-11-12/13; ZTL keeps the operational register). "The Q such that the law
  holds" is a definite description: it denotes only a satisfier that exists, and existence is earned. ZTL's kernel
  proves an ENCLOSURE of the roots in `search`; that a root is there is a second fact, with two possible grounds:
  - OPERATIONAL — per part of a partition of the box, a bracket where the law keeps strictly opposite signs at the two
    ends over the whole part AND its slope in Q keeps one strict sign (bounded away from zero). This is the rule ZTL
    proves in Lean with zero axioms (`ZRootPar.par_root`, `tree_root`): the root is built, and is the only one in the
    bracket. `--prove` gives that theorem for an EARNED verdict. Without it the rule is read twice, by two
    implementations: ZTL's kernel checks a brought cover of the box (`zimplicit.check_exists`, ZTL after 2026-11-13),
    and the stand's checker builds the root by its own route. Either one that builds it earns the fact, and the
    note under `how` says which did. The kernel reads no slope through `min` / `max` (the HVAC curves), and it
    reads each occurrence of Q on its own, so a wide bracket around zero can defeat it; there the checker's route
    stands alone, and the note says so. With an older ZTL (no `check_exists`) the checker's route alone is used.
  - FORMAL — the sign change with the law only continuous between (the classical intermediate value theorem): "a root
    exists", with no object built. Said in the output, and NOT enough for a verdict.
  The marks go to ZTL's JUDGE as the claim "(a root in the window & every root there in its range) | (a root outside
  the window)", and the stand prints the judge's disposition: built -> EARNED; not built -> OPEN, with what is to be
  verified named. So a law that JUMPS across zero, a pole with a sign change, a root that only touches zero or has a
  zero slope, and a `search` some values of the box have no root in are OPEN — never EARNED around a root that is not
  there, and never REFUTED "at a point" that has none. With several roots (x² = p) one of them is built and the range
  holds every one: the claim is "a root exists, and every root is in range", not "the root".
- Inside a certificate (an extreme inside the box), Q enters as one variable over its proved range: the pump's
  power `rho*g*Q*(H0 - a*Q^2)/eta` peaks INSIDE Q's range and is still proved.
- Version 1 limits, each a BRICK ERROR: an implicit law may use only given and catalog quantities besides Q (put
  other expressions in through `define`); one implicit law per quantity; `search` only on a derived quantity, low
  below high; a quantity with an explicit law `Q == ...` takes no `search`.
- Speed: the checker reads every corner of the box, and each corner solves the implicit law. Nine toleranced
  quantities (the pump, the pi bracket included) take about 20 s per design.

## 5. units — always write them

- Every quantity and every field should have a `unit`. Then every law's dimensions are checked, and a mismatch is a
  `BRICK ERROR` (adding watts to degrees, for example).
- If any unit is missing, the output says `units: not checked: …`.
- **Prefixes scale values to SI**:
  - prefixes: `p n u m c k M G`;
  - units: `V A ohm W F H Hz s m g K C J N Pa ppm % h min day week month quarter year L mol t Ah Wh bar rpm dB dBA
    rad deg Gy Sv VA var in ft yd mi lb lbf kip psi ksi psf ksf plf klf pcf mph oz ozf gal gpm cfm daN BTU BTUH MBH TR therm hp dC dF degR` (absolute
    `degC` / `degF`: see temperatures below), and the
    currencies `USD EUR GBP ILS RUB JPY CHF CNY`. Each currency is its own dimension: adding USD to EUR is a unit
    error, and an exchange rate is a quantity (`EUR/USD`). A currency takes `k` and `M` only: `kEUR`, `MUSD`;
  - `Gy` and `Sv` are J/kg, `VA` and `var` are W: the check cannot tell absorbed from equivalent dose, nor apparent
    or reactive from active power — the names are for the reader. `deg` is pi/180 to 40 significant digits
    (pi is irrational; the relative error is below 1e-40). A number may stand in a unit: `kWh/100km`, `1000L`.
    `rpm` is a revolution per minute (1/60 s^-1); `oz` the avoirdupois ounce (1/16 lb), `ozf` its force, `gal`
    the US liquid gallon (231 in^3), `gpm` a gallon per minute — all exact by definition.
  - `in ft lb lbf psi ksi` (since 2026-10-12, real round 3) are exact by definition: 0.0254 m, 0.3048 m,
    0.45359237 kg, that pound under 9.80665 m/s^2, lbf/in^2 (6894.757... Pa), 1000 psi. Not there: **dBm** (a
    logarithm — write levels in dB and judge differences, as a link budget does). Absolute temperatures in
    **degF / degC**: see the bullet on temperatures below (since 2026-11-12).
  - `year` (or `yr`) is the **Julian year, 365.25 days**. A life counted as 365 x 24 = 8760 hours a year is not
    that: write it in hours (`262800 h` for 30 such years), or the 0.07 % difference decides a tight bound;
  - **one reckoning for calendar time** (since 2026-11-12): `month` (`mo`) is the BILLING month, exactly 1/12 of that
    year (30.4375 days) — never a calendar month of 28-31 days; `quarter` (`qtr`) is 1/4 of it; `week` (`wk`) 7 days.
    So a charge per month times a year is exactly twelve charges;
  - **two ways of writing** a unit are read (since 2026-11-12): a HYPHEN between two names is a product that binds
    tighter than `/` — `USD/kW-month` is USD per (kW x month), `N-m` is N*m (`m^-2` stays a power); the word `per`
    between spaces — `USD per kWh` is `USD/(kWh)`, `per kWh` is `1/kWh`;
  - **US structural units, exact** (since 2026-11-12): `kip` (1000 lbf), `psf` (lbf/ft^2), `ksf`, `plf` (lbf/ft),
    `klf`, `pcf` — the UNIT WEIGHT lbf/ft^3 of load standards (a mass density is `lb/ft^3`) — `mph`, `mi`, `yd`.
    No prefix on any of them.
  - **US energy units, exact by definition** (since 2026-11-12): `BTU` (`Btu`, the International Table BTU,
    1055.05585262 J; `kBTU`, `MBTU` = 10^6 BTU), `BTUH` (BTU/h), `MBH` (1000 BTU/h), `TR` the ton of refrigeration
    (12 000 BTU/h), `therm` (100 000 BTU), `hp` (550 ft*lbf/s), `cfm` (ft^3/min), and `kgal` / `Mgal`. Plain `ton` is
    refused (it is also the short ton of 2000 lb; `t` is the metric tonne);
  - combined with `*`, `/`, powers and parentheses: `C/W`, `1/C`, `m*s^-2`, `J/(kg*K)`, `m^3/h`, `cm^4`. A power
    may be a fraction — `m^2.5/s`, `m^(1/2)/s` (a weir's coefficient) — on an unscaled unit (`km^0.5` is refused:
    write it in SI). `pow(H, 1.5)` and `sqrt(H)` of a length are then half powers, checked like any other.

  So `"unit": "nF"` with value 39 means 39e-9 F. Results come back in the quantity's own unit.
- **Pitfall (hit on 2026-10-09).** A bare number inside a law is in SI base units.
  - Writing `50` for a 50 mm length makes it 50 metres.
  - Put dimensioned constants in as given quantities with a unit: `"Hn": {"role": "given", "value": "50", "unit": "mm"}`.
  - Dimensionless numbers such as `2`, `1` and `25` in `(T - 25)` are fine. A number in a sum takes its partner's unit.
  - A conversion factor typed into a law (`Q*1000` to turn m^3 into L) is a bare number, so the unit check cannot
    see it (blind test 4: a `*1000` with the unit L passed silently). Never convert inside a law: give each quantity
    its own unit and let the stand scale it.
- **Write temperatures in `degC` (or `degF`, `K`) and differences in `dC` (`dF`).** The old unit `C` is a temperature
  DIFFERENCE with no offset — 20 `C` is read as 20 K. It stays for old bricks made of sums and differences only; a
  brick that calls the HVAC library (`ep_...`, `curve`) with a quantity in `C` is refused (2026-11-12: 20 `C` given
  to `ep_psat` was EARNED at 0.0014 Pa — the formula at 20 K).
- **Absolute temperatures: `degC` and `degF`** (since 2026-11-12, `ustand/temperature.py`). A quantity or a catalog
  field written in `degC` or `degF` is converted to K EXACTLY before the stand reads the brick
  (K = C + 273.15, K = (F + 459.67) x 5/9); the output keeps the stand's values in K (labelled K) and adds
  `in_written_scales` — the guaranteed range, the violating point and the value there back in the written scale, and
  the overshoot as a difference. Differences and rates use `dC` (1 K) and `dF` (5/9 K); `degR` is the Rankine.
  ```json
  "Twb": {"role": "given", "range": ["75", "78"], "unit": "degF"},
  "A":   {"role": "given", "value": "7", "unit": "dF"},
  "CWS": {"role": "derived", "unit": "degF"}          // CWS == Twb + A; CWS <= 85 (deg F)
  ```
  Refused, each with its reason, because each would be a silent wrong answer: `degC`/`degF` inside a compound unit
  (`degF/h` — write `dF/h`); a relative `tolerance` on an absolute temperature (+-1 % of 78 F is not +-1 % of
  298.7 K — write a range); a NUMBER added to an absolute temperature in a law, a define or a bound (`Twb + 7`: the
  7 would be 7 K — write the difference as a given quantity in `dF`); the legacy `C` beside `degC`/`degF` in one
  brick. Version 1 translates plain bricks (with catalog, modes and find); components, stocks and networks stay
  in K.

### Correlated tolerances (one value shared by several parts)

- **Since ZTL ca17ad4, ONE shared quantity is handled exactly by the judge** (t7 is EARNED as written). The problem
  remains with TWO or more shared quantities: ZTL refuses, and the verdict is OPEN.
- **When a shared quantity is a common factor, factor it out.** Solve for the scaled unknown (v = E·u, with `G*v == F`
  where K = E·G). Then bring the unscaled one back in ONE row (`E*uy == vy`). Only do this for the unknowns a
  requirement needs, because each extra row adds rank (t7b).

### Built-in constants

`pi`, `g0` (standard gravity, 9.80665 m/s^2), `R_gas` (8.314462618 J/(mol*K)) and `c0` (299792458 m/s) may be
used in any law, define, objective or bound without declaring them. The stand adds them as given quantities, unless
the brick declares a quantity of that name itself (then the brick's own wins).
- `pi` is a rational bracket 1e-15 wide, because the stand computes in exact fractions.
- `g0`, `R_gas` and `c0` are exact by the definition of the SI.

**One of a unit, by name (since 2026-11-13).** `one_ft`, `one_psf`, `one_in`, `one_K` — `one_` and a unit name —
is exactly 1 of that unit, added the same way when a text names it. It is for the EMPIRICAL formulas of codes and
standards: `h = a L^(1/3) (p + b)^(1/4) - c`, "with L in ft and p in psf", is a rule about numbers, not a
balanced equality, and the stand refuses it as written (a length to the power 1/3 is not a length). Say which number
is meant: `(L/one_ft)**(1/3)` is the pure number of L in feet; multiply by `one_ft` to give the result its unit:

    "h == one_ft*(k*(L/one_ft)**(1/3)*((p + p10)/one_psf)**(1/4) - c)"

with `k`, `c` pure numbers and `p10` a pressure. A name `one_x` where `x` is not a unit is not a constant.

### Things that are allowed (asked in the blind test)

- A define may use earlier defines.
- A law or define may divide by a toleranced quantity, as long as the divisor's range keeps away from zero.
- "Nominal" for a range is its midpoint. The nominal point is only a shortcut; the verdict is over the whole box.
- `designs_count` counts every verdict. When more than 200 designs were judged, the list keeps EARNED first, then
  OPEN, then REFUTED (`designs_not_listed` says how many were cut).
- `objective.ties`: other designs with exactly the same objective as the reported one (not all judged — use
  `"report": "all"` to see which of them pass).
- An OPEN design in `designs` says why: which requirement, the range proved for it, and what kept it open (no
  certificate decided an extreme that may lie inside the box; a strict bound, which certificates do not prove; the
  checker could not evaluate; an implicit law without a root; a definition that could not be bounded).
- In `how`, "outer range" means a sound range that may be wider than the truth. It is enough to EARN; it never
  refutes on its own.

## 6. requirements

```json
{"quantity": "Vout", "op": "within", "value": ["2.475", "2.525"], "why": "2.5 V ±1%"},
{"quantity": "P1",   "op": "<=",     "value": "R1.P"},
{"quantity": "I",    "op": ">=",     "value": "0.024"}
```

- `op` is `within`, `<=` or `>=`. The quantity must be derived.
- Numbers are in the quantity's own unit.
- A bound is a number, a GIVEN quantity, or a `slot.field`. A DERIVED quantity as a bound is a BRICK ERROR:
  write the difference as its own derived quantity (`margin == L/300 - delta`) and bound that by 0.
- A bound may be a quantity name (`R1.P`):
  - for proof, its least favourable end is used;
  - at a witness point, its value there.
- A bound may be an EXPRESSION of numbers, given quantities and `slot.field`s: `"L/300"`, `"15*g0"`,
  `"savings - LOAN.fee"`. Its names are in SI, as in a law, and its dimension must be the quantity's (checked). For
  proof it is taken at its least favourable end over the box; at a witness point, its exact value there.
  - An expression with no names, such as `"2.5*99/100"`, is a number in the quantity's own unit.
  - A bound that reads a toleranced quantity which also moves the bounded quantity loses their correlation. A
    ratiometric window `Vout within [Vin*0.49, Vin*0.51]` comes out OPEN. Write the ratio as its own quantity
    instead (`Vout == k*Vin`, `k within [0.49, 0.51]`), and ZTL keeps the correlation exactly.
- Several requirements may read the same quantity (a floor and a ceiling, or two reasons): the stand applies all of
  them together. (Before 2026-10-11 only the last one counted in one step of the proof — a false EARNED in one
  order; no delivered brick of the four blind tests was affected, re-run.)
- Always give `why`.

## 7. objective (optional)

```json
"objective": {"minimize": "HS.price + PAD.price", "why": "cheapest parts that hold Tj"}
```

- Designs are tried from the lowest objective, evaluated at nominal values. The first EARNED one is therefore the
  cheapest.
- The output says `optimal: true` only if every cheaper design was REFUTED.
- If a cheaper one was undecided, the output says so: "optimal only among the decided ones".
- A nominal objective may name DERIVED quantities (since 2026-10-10): they are read at the NOMINAL point (every
  toleranced value at its nominal: the value, or the middle of a range) by the checker's exact solution of the laws.
  With modes it reads the brick's own values, not a mode's. `"unit": "EUR/MWh"` shows the value in that unit (it
  is unit-checked against the expression).
- `nominal(X)` in `computed` (and `where`): X at its nominal value, for given and catalog quantities with a
  tolerance or a range (a derived one belongs in the objective). A `where` condition on a field WITH a tolerance
  must read it through `nominal(...)` — the design space is chosen by nominal values (real round 3, s10).

**Worst case** (since 2026-10-10, G11): `"objective": {"minimize": "Tot", "case": "worst"}` — the objective may then
name derived quantities, and the stand minimizes its WORST over the box (every allowed down payment, rate, tolerance):

- every design is judged; for each EARNED one the output lists `objective_worst`: `proved_at_most` (an upper bound
  from the readings — sound, may be loose) and `reached_at_least` (its largest value at the checker's corners —
  the worst case is at least that);
- the design with the smallest proved bound is reported, with `value` = that bound;
- `optimal: true` only when its bound is at or below the corner value of every other earned design and nothing is
  OPEN; otherwise the note names the designs whose worst case may still be lower (a loose bound is never called
  optimal: t20's synthetic twin in tests shows one);
- not yet with modes (BRICK ERROR).

### An optional part (since 2026-10-11)

`"slots": {"HS": {"from": ["sinks"], "optional": true}}` — the design may leave the slot empty. The stand adds a
catalog `HS_none` with one item `none`: every numeric field 0 (price 0, conductance 0), every label `none`. Write
the laws so that 0 means "absent": `Tj == Ta + P/(Gbare + HS.G)` with a conductance G, not `P*HS.R` with a
resistance (an absent sink is not a zero resistance).

## 7a. find (optional) — the limiting value (since 2026-10-12)

```json
"Rsa":  {"role": "given", "value": "0", "unit": "C/W"},
"find": {"largest": "Rsa", "from": "0", "to": "20", "precision": "0.001"}
```

- Asks "the largest (or `smallest`) value of a GIVEN quantity that still works". The stand judges RANGES, not
  points: it runs the brick with the quantity over [from, a] (for `smallest`: [a, to]) — EARNED only when EVERY
  value in it works — and bisects on a. No monotonicity is assumed: "works on the whole range" is monotone by
  construction.
- The quantity's own value/tolerance/range is replaced by the search: give it a placeholder `value` (and its
  unit). For `largest` every tried range starts at `from`; for `smallest` every one ends at `to`. For a symmetric
  +-x, search the magnitude x and write the quantity as x times a given `s` in `[-1, 1]` (real round 2, s03).
- `precision` is in the quantity's unit (default: a thousandth of the search range); the tried values sit on the
  grid from + k * precision, so `proved` is a GRID value: an exact limit 563.143 with precision 0.01 is reported as
  proved 563.14 or 563.15 (whichever side holds), with `beyond` one step further (real round 3, s08).
- Several limits in one brick (since 2026-10-12): `"find": [ {...}, {...} ]` — each searched on its own, the
  output's `finds` lists each answer, the verdict is the weakest of theirs. An item may carry its own
  `"requirements": [...]`, which replace the brick's for that search (real round 2, s05: the HOT and COLD trip
  limits, each with its own requirement — `examples/tasks/t30-ntc-trip-limits-find-list.json`).
  - The list's EARNED means every limit was FOUND (each bracket proved), not that any published value holds: read
    each item's `proved` against the source (s08).
  - Two items may search the same quantity (s10). Scenarios with DIFFERENT data (another part, another set-up):
    give each scenario its own quantities and laws, and each item its own requirements on them (n02, s08). The
    brick's top-level `requirements` must still name one valid requirement.
- The answer: `proved` (every value from `from` up to it works, EARNED), `beyond` and `beyond_is`: REFUTED (a
  concrete failing point lies in the range up to `beyond`, see `at_beyond`) or OPEN (undecided — the limit lies
  between, not proved). `at_proved` is the full output there (the design, its guaranteed ranges). `tries` lists
  every range judged.
- If the whole search range works, `proved` is its far end and `proved_means` says to widen it. If even the shared
  end alone fails, the verdict is REFUTED. With slots, "works" means some design works on the whole range.
- Version 1: one quantity. With modes (since 2026-10-12) every tried range is judged in every mode; a mode that
  overrides the searched given itself is refused. Each try is a full run: a slow brick times ~15 tries.

## 7c. network (optional) — branch currents of a resistor/conductance network (since 2026-10-12)

```json
"quantities": {"V":  {"role": "given", "range": ["9", "11"], "unit": "V"},
               "R1": {"role": "given", "value": "1000", "tolerance": "0.01", "unit": "ohm"}, "...": {}},
"network": {"branches": {"b1": {"from": "a", "to": "n1", "R": "R1"},
                         "b5": {"from": "n1", "to": "n2", "G": "G5"}},
            "source":   {"from": "a", "to": "gnd", "V": "V"}},
"requirements": [{"quantity": "I(b5)", "op": "within", "value": ["-0.2", "0.2"], "unit": "mA"}]
```

- Any scalar network: electrical resistors, thermal conductances (V a temperature difference, I a heat flow),
  diffusion grids. Each branch has exactly one of `R` (resistance) or `G` (conductance): a given quantity's name
  (value, tolerance or range — any value in its box) or a number string. One source holds node `from` at V and node
  `to` at 0. Nodes are named by the branches; every node must reach a source node.
- Requirements (ops `<=`, `>=`, `within`):
  - `I(<branch>)` — a branch current, positive from the branch's `from` to its `to`;
  - `V(<node>)` — a node's potential above the reference (plus `at`, below) and `V(<node>, <node>)` — the
    difference of two nodes' potentials (since 2026-10-12, network v2: real round 3 asked a bridge's offset
    VOLTAGE and a junction TEMPERATURE).
- **A current source** (since 2026-10-12, network v2): `"source": {"into": "j", "from": "amb", "I": "P", "at":
  "Ta"}` injects I into node `into` and draws it from `from`, the reference — a dissipated power into a thermal
  network, whose node potentials are temperatures. `at` (optional, for either kind of source) is the reference's
  own potential: `V(j)` is then Ta + the rise. The voltage source is `{"from", "to", "V"}`, the reference is `to`.
- Units: every branch one kind; with a voltage source the current's unit = the source's x a conductance, with a
  current source a potential's unit = the source's / a conductance (W / (W/K) = K); `at` has the potential's unit.
- A tolerance may name a given quantity (section 1), so `find` can search "the largest tolerance that still works".
- **Network + laws** (since 2026-10-12, version 1, one way): a brick with `network` may carry `laws`; a branch's
  `R`/`G`, the source's `V`/`I` or `at` may then be a DERIVED quantity (`P == ID*ID*RDS`). The laws are judged first
  — each derived input's range is PROVED (by ZTL, as in any brick) and becomes its box (`inputs_from_laws` in the
  output); then the network certificate. `find` may search a given of the laws (the largest drain current:
  `examples/tasks/t33-mosfet-network-with-laws.json`). Not in v1: a feedback (a law reading the network's outputs —
  that is an implicit law), and requirements on ordinary quantities beside the network's. When two inputs rest on
  one toleranced given, `correlation_note` says so: each box is proved, the link between them is not kept — the
  bounds hold, maybe wider.
- THE VERDICT is the network certificate's: a search (floating point, trusted for nothing) brings a certificate
  per side of each current; `ustand/znet.py` checks it EXACTLY (residuals, an eigenvalue bound, energy enclosures,
  sign pinning, box splits) and gives the proved range `proved_range`. EARNED when it lies inside the requirement.
  REFUTED needs a failing point PROVED: the search's best corner, its current enclosed exactly by certificates on
  that one point (`its_violating_point`, `value_there`). Otherwise OPEN. `found_inside` is the range the search
  reached at corners — how tight the proof is.
- znet.py is in the stand, not in public ZTL. Its mathematics is in `lean/ZNet.lean` (zero axioms): the eigenvalue
  bound, the residual-to-energy chain, the branch form, the energy enclosure over the box, pinning, rounds and cuts
  are proved, the pair target's effective resistance too; the rational roots are checked at run time; Kirchhoff's
  law and the derivative-sign formulas are the named premises.
- `--dev` also solves EVERY corner exactly in fractions (up to 2^10 corners; a current is monotone in each
  conductance, so its extremes are at corners) and checks they lie in the proved range.
- When the rounds pin every branch, the box is a point and its value is solved EXACTLY in fractions (networks up
  to 60 free nodes): a requirement met with equality is EARNED, not left OPEN by the certificate's rounding (the
  bridge's worst offset is exactly TOL x VEX = 5 mV: `examples/tasks/t32-bridge-offset-voltage.json`).
- One source; no slots, laws or modes in a network brick (`find` works on it). Measured: 20 x 20 grid, 760
  branches at +-5 %, 26 s (voltage source, a branch current) and 23 s (current source, a node temperature); the
  proved range within 0.01 % of the found one. Examples: `t29` (bridge currents), `t31` (a MOSFET's thermal
  network: junction temperature, sink heat flow), `t32` (a bridge's offset voltage).

## 7f. From a SPICE netlist (since 2026-10-15) — what the engineer's CAD already writes

No brick to write by hand: the schematic tool's SPICE netlist (topology and nominal values), the BOM (tolerances) and a
short list of requirements.

    python3 -m ustand.spice circuit.cir --bom bom.csv --req "V(out) within 4.7 5.4" --req "P(Rload) <= 0.3" \
            [--dev] [--emit brick.json]

- The netlist (DC, linear, version 1): R, V, I, E (VCVS — an op-amp as a large open-loop gain), G (VCCS), F (CCCS), H
  (CCVS), L (a short at DC), C (open at DC); `.param` and `{name}`; SPICE suffixes (10k, 4.7u, 1meg — and 1M is MILLI,
  as in SPICE) and the RKM code (4k7, 2R2); node 0 or gnd. A diode, a transistor, a subcircuit, `.model`, `.include`:
  refused aloud — never dropped silently (diodes and transistors: by operating region, below).
- The BOM (CSV, `,` `;` or tab): a reference column (Reference / Designator / Ref / RefDes; "R1, R2" and "R1-R3" in one
  row), a value column (checked against the netlist — a mismatch is a BRICK ERROR), a tolerance column ("1%", "±5 %",
  "50ppm"). A tolerance with no unit is refused (0.5 could be 0.5 % or 50 %). Or `tol=1%` on the element's line.
- Requirements: `V(node)`, `V(a,b)`, `I(R1)` (from its first node to its second), `I(V1)`, `P(R1)`; then
  `within lo hi`, `<= x`, `>= x`.
- The brick is Kirchhoff's current law at every node plus each source's equation (modified nodal analysis); the
  stand then judges it as any brick — many nodes by zlin, a power (nonlinear) through the nodes' proved ranges.
- Examples (examples/spice): a divider, a non-inverting op-amp, a Wheatstone bridge, an LM317-like regulator, a
  12-node ladder — each with its answer by hand in tests/test_stand.py.
- DIODES AND TRANSISTORS, by operating region (since 2026-10-15): `D1 a k dm` with `.model dm D(Vfwd=0.7 Ron=10)`
  (LTspice's piecewise-linear diode), `Q1 c b e qm` with `.model qm NPN(BF=100 Vbe=0.65 Vcesat=0.2)` (or PNP). The
  BOM's tolerance is the main parameter's (Vfwd, BF); `VbeTol=5%` etc. on the model for the others. A missing
  parameter is refused — nothing is assumed. Regions: D on/off, Q active/saturation/cutoff; given by `--region
  Q1=active`, or found: every combination solved at the nominal point, the consistent ones kept. Then, for each:
  stage 1 PROVES its region conditions over the whole tolerance box (the diode's current >= 0, Vce >= Vcesat, ...),
  stage 2 judges the requirements. A device that LEAVES its region somewhere in the box is said as such, with the
  point (OPEN — the model changes there), never as the requirement's failure. Proved: an operating point in those
  regions exists at every point of the box; NOT proved: that it is the only one (a latch has two).

## 7g. From an ANSYS truss deck (since 2026-10-16) — a plane truss, every bar's modulus toleranced

    python3 -m ustand.truss deck.txt --tol 0.5% --range "U(42,X)"           the PROVED range of a displacement
    python3 -m ustand.truss deck.txt --tol 0.5% --req "U(42,Y) >= -811"     a requirement

- The deck: the subset of ANSYS's own input files the interval-FEM benchmarks use — `N, id, x, y`, `E, i, j` (LINK1 /
  LINK180 bars), `MP, EX, 1, value`, `R, 1, area`, `F, node, FX|FY, value`, `D, node, UX|UY, 0`; `/PREP7`, `ET`,
  `MAT 1`, `REAL 1`, `!` comments read and skipped. Anything else — a second material, a prescribed nonzero
  displacement, another element type, an unknown command — is refused aloud. A bar whose length is irrational is
  refused (its stiffness would not be exact).
- `--tol t`: every bar's modulus anywhere in E (1 +- t), independently. (The benchmarks' "1 % uncertainty" is
  E in [0.995, 1.005] E: `--tol 0.5%`.)
- Each bar enters the equilibrium as E_i (A/L) c c^T — rank one in its own parameter, as a resistor's conductance — so
  the certificates are zlin's, with the signs of d U / d E_i proved by its step 6 (three factors, each enclosed).
- Large or ill-conditioned systems: the stand rescales the unknowns and the equations (powers of two — an exact change
  of variables; certify._scaling) when the kernel's plain contraction is >= 0.9. MEASURED on R. Muhanna's IFEM
  Benchmark 2 (a 20-floor cantilever, 101 moduli at +-0.5 %, 81 unknowns, 2^101 vertices): corner D's UX in
  [18117.870011, 18299.962368] and UY in [-810.857866, -802.508648], each end attained AND proved (exact), ~8.5 min
  per displacement. Unscaled the plain contraction was 3.2 and nothing was proved in an hour. Benchmark 1 (a 10 x 10
  truss, 420 moduli, 230 unknowns): UX in [22.022936346773, 22.272341101043], UY in [-10.325510056061,
  -10.192083141099], every end exact, ~55 min per displacement (2026-10-16).
- Examples (examples/truss): the benchmark's cantilever at 12 and 20 floors (bench/hard-tasks/mkcant.py).

## 7j. assembly (optional) — a structure inside the brick: bars, springs and shear panels (since 2026-11-14)

A plane linear elastic model stated element by element — the model an engineer draws for a roof or floor diaphragm:
chords and collectors as axial bars, the deck as rectangular shear panels, the braced frames as springs to ground.
Its stiffnesses and loads NAME the brick's quantities; its results are quantities of the brick. The stand solves the
structure for EVERY design (and every mode), so the catalogue search, the objective and the modes work through a
structure whose parts act on one another: "choose the deck of each zone so that the diaphragm holds, cheapest".

```json
"quantities": {"P":  {"role": "given", "value": "40", "unit": "kN"},
               "kc": {"role": "given", "value": "1000000000", "unit": "kN/m"}},
"slots":   {"ZA": {"from": ["decks"]}, "ZB": {"from": ["decks"]}},
"assembly": {
  "length_unit": "m",
  "nodes": {"a0": [0, 0], "a1": [4, 0], "a2": [8, 0], "t0": [0, 2], "t1": [4, 2], "t2": [8, 2]},
  "fixed": [["a0", "X"], ["a0", "Y"], ["a1", "X"], ["a1", "Y"], ["a2", "X"], ["a2", "Y"],
            ["t0", "Y"], ["t1", "Y"], ["t2", "Y"]],
  "elements": [{"id": "pA", "type": "panel", "nodes": ["a0", "a1", "t1", "t0"], "g": "ZA.G"},
               {"id": "pB", "type": "panel", "nodes": ["a1", "a2", "t2", "t1"], "g": "ZB.G"},
               {"id": "c1", "type": "bar", "a": "t0", "b": "t1", "k": "kc"},
               {"id": "c2", "type": "bar", "a": "t1", "b": "t2", "k": "kc"}],
  "loads": [["t1", "X", "P"]],
  "outputs": {"qA": {"flow": "pA", "unit": "kN/m"}, "qB": {"flow": "pB", "unit": "kN/m"}}
},
"requirements": [{"quantity": "qA", "op": "<=", "value": "ZA.cap", "why": "capacity, zone A"},
                 {"quantity": "qB", "op": "<=", "value": "ZB.cap", "why": "capacity, zone B"}],
"objective": {"minimize": "ZA.price + ZB.price"}
```

- `nodes`: name → `[x, y]`, numbers in `length_unit`. `fixed`: `[node, "X" | "Y"]` supports.
- `elements` — `bar`: axial stiffness `k` = EA/L between nodes `a` and `b` (its direction must be exact: a rational
  length — on a grid it always is). `spring`: a `node`'s `dir` (X or Y) to ground, stiffness `k`. `panel`: the corners
  of a rectangle along the axes, in the order bottom-left, bottom-right, top-right, top-left; `g` is the shear
  stiffness G' in force per length — the panel carries a constant shear flow q = G' × (its shear strain).
- A stiffness (`k`, `g`) and a load are EXPRESSIONS of the brick's quantities, written as strings: a given, a field of
  the item a slot holds (`ZA.G`), a computed value, arithmetic of them (`EA/L`). Their units are checked: a stiffness
  is a force per length, a load a force. A bare number is refused — name a quantity that has the unit.
- `outputs`: name → one of `{"u": [node, "X"|"Y"]}` (a displacement), `{"force": element}` (a bar's tension or the
  force in a spring), `{"flow": panel}` (a panel's shear flow), each with its `unit`. Every output is a quantity of
  the brick under that name: use it in laws, in the objective, and directly in a requirement.
- **Modes** are load cases: a mode overrides the given loads, the structure is solved in each, the design must hold
  in all. A mode cannot override an output.
- The mathematics is ZTL's (`zenergy`, Lean `ZEnergy.lean`): the stand only states the elements. Up to 120 unknowns
  the result is EXACT (a fraction); above, it is a PROVED RANGE of the one true value, about 1e-24 wide.
- **A refutation that leans on such a range must hold over the whole of it.** A tolerance is a set of states the world
  may take: one failing point refutes the design. A result of the structure above the exact size is ONE value known
  only to lie in a range; an end of that range may not be a state at all. So a design is REFUTED through such a
  result only when, at the witness's values of the real data, the requirement fails for every value of the range
  (the stand's own judge earns the opposite with half the overshoot to spare). Otherwise the design is OPEN — "the
  range does not separate the value from the bound" — and, being undecided, it counts against `optimal` like any
  open design. MEASURED: a limit set inside a design's proved range — that design OPEN, the next one EARNED,
  `optimal: false` ("1 cheaper design(s) undecided"); with the rule switched off the same brick refuted it and called
  the dearer design optimal.
- Version 1: every stiffness and load is EXACT per design — a quantity with a tolerance or a range, or a derived one,
  is refused by name (so `find` cannot search a load of the structure yet); no continuous amounts beside the section;
  the group pruning of large catalogues is off, each design is solved (about 0.1–0.2 s at 126–442 unknowns).
- A model that is a mechanism (no support; a displacement nothing holds) is refused with what is loose, never solved.
- It proves the statics of the model as stated — not that the model is the structure.
- From Python, without a brick: `ustand.assembly.solve(spec)` with numbers in place of the names (a range
  `[low, high]` is that element's own tolerance there) returns each output's `nominal`, `lo`, `hi`.
- Tests: `tests/test_assembly_brick.py` (the section: selection, coupling, modes, the refutation rule),
  `tests/test_assembly.py` (the solver's door).

## 7d. components (optional) — a system of devices, each proved once (since 2026-10-12)

The curator's example: a 230 V socket, a 5 V adapter, a phone's charging board, a battery — four devices, each
complex inside, each described by a CONTRACT and judged once. Files in `examples/components/`.

A **component** is an ordinary brick with an interface:

```json
"interface": {"inputs":  {"Vin": {"assume": ["200", "250"], "bands": ["200", "230", "250"]}},
              "outputs": ["Vout"]}
```

- `inputs` are given quantities of that brick; `assume` is the range the component is proved for, in the
  quantity's unit. `bands` (optional) cut it into pieces, each proved on its own: the contract becomes a table
  "input band → output range", which keeps much of what one range loses.
- `outputs` are derived quantities; for each band the stand proves their ranges (the GUARANTEE), and the
  component's own requirements (its ratings) must be EARNED in that band. A band that fails has no guarantee.

A **system** names components and wires them:

```json
"components": {"AD": {"file": "adapter-5v.json"}, "CH": {"file": "charging-board.json"},
               "BT": {"brick": { ... }}},
"connect":    {"AD.Vin": "Vmains", "CH.Vin": "AD.Vout", "BT.Vchg": "CH.Vchg"},
"laws":       [{"zfl": "Vend == BT.Vcell"}]
```

- An input is fed by a system GIVEN or by an upstream component's output. Files are read relative to the system
  brick's own file.
- The range ARRIVING at an input must lie inside its `assume`, else the system is **OPEN**: the contract does not
  cover it. An arriving range is an enclosure, so leaving `assume` is not a refutation.
- The bands the arriving range touches are used; an output's range is the hull of their guarantees.
- The system's laws, requirements and objective may name an output as `BT.Vcell`; it becomes a given range
  `BT_Vcell`. The output lists `components`: per component, what arrived, from where, the bands used and the
  outputs.
- **EARNED is sound; REFUTED is not available.** If the system fails at a point of the components' ranges, that
  point may be one no component can produce (the ranges enclose). The answer is then OPEN, with where it failed.
  Finer bands, or the chain as one flat brick, decide it.
- **Recursion:** a system with an `interface` is itself a component (`power-supply.json` = adapter + board, used
  under `phone-charging-hierarchy.json`). Each contract is judged once per (brick, band), cached by content.
- **Choosing a component** (since 2026-10-12): `"AD": {"choose": [{"label": "cheap", "file": "adapter-5v-cheap.json",
  "fields": {"price": {"value": "1.5", "unit": "EUR"}}}, ...]}`. A candidate's `fields` are exact numbers the
  system names as `AD.price` (in the objective, laws, requirements). Every combination of candidates is judged —
  cheapest first when the objective reads only such numbers, stopping at the first EARNED. `optimal` is true only
  when nothing cheaper is left OPEN: a system cannot refute, so a cheaper candidate that is not earned stays
  undecided, and the output lists it with its reason (`combinations`). A candidate's malformed brick is a BRICK
  ERROR for the whole system, not a skipped design — unless that combination stopped earlier (its input left an
  assume), where the error is not reached. Example: `phone-charging-choose.json` — the +-10 % adapter leaves the
  board's assume, the standard one (3 EUR) wins, optimal false. A choice inside a component that is itself a
  system is refused: its contract must be ONE device's.
- **Tuning a component's parameters** (since 2026-10-12, the curator's "да", v1 discrete): a component's brick may
  have its OWN slots — `adapter-divider.json` picks its feedback resistor R1 from a catalog, with the part's price
  as its objective. Each design of those slots becomes one candidate device (pinned: a contract is one device's —
  left free, the slot would pick another part in every band), and the brick's objective read at that design is its
  field `cost`, which the system names as `AD.cost`. Then the choice above runs: `phone-charging-tune.json` —
  2k7 and 3k3 (cheapest) put Vout outside the board's assume, 3k0 1 % wins at 0.012 EUR, the 0.1 % part is never
  needed. Not yet: a CONTINUOUS parameter inside a component (v2).
- **`find` over a system** works (`phone-charging-find.json`: the widest mains the chain earns is 250 V, the
  adapter's assume; 250.1 V is OPEN, never a false "cannot").
- **Refused (version 1):** a component that contains itself; a feedback between siblings (an input fed, through
  the connections, by its own component's output); an input left unconnected.
- **Tight contracts** (since 2026-10-12, real round 4): a band's output ranges and affine remainders are no longer
  the stand's outer reading of the law (a name appearing twice, R1 in `Vr*(R1+R2)/R1`, did not cancel). The stand
  reads the values the component ATTAINS at its box's corners and middle (exactly), then PROVES each end just
  past them as an ordinary requirement — widening the margin if not proved, never past the outer reading. Round 4's
  k01 divider (one wide band, all 12 grade pairs OPEN) is now EARNED on the flat brick's answer; k02's amplifier +
  ADC system is within 0.2 mV of the flat range (it was twice as wide). Up to 10 toleranced quantities per
  component are read at every corner; above that, the outer reading as before.
- A band is used when it OVERLAPS the arriving range; one sharing only an edge is not (round 4: it added a band
  and lost the affine form).
- **Affine contracts** (since 2026-10-12, the curator's "да"): for an output of the same dimension as its inputs,
  each band also proves `out = k * in + e` — the slope k chosen by the stand (two point runs), the remainder e's
  range PROVED (any k keeps it true). When the range arriving at every input lies in ONE band, the system gets the
  output as a law `S1_Vo == k * source + S1_Vo_e`, so it stays tied to its source: `bridge-two-sensors.json` — two
  ratiometric sensors on one 5 V +-5 % supply, their difference proved within +-3.1 mV (the supply cancels); with
  `"contracts": "ranges"` (ranges only) the same system is OPEN. Several bands touched, or other dimensions: the
  range, as before. Sources and inputs in different units are converted through SI (`kV` into `V`); different
  dimensions are refused.
- **`"bands": "arriving"`** (since 2026-10-12, round 4): instead of cut points, judge the contract on the range that
  ARRIVES at the input — the tightest (the charger: the system equals the flat brick exactly), at the price of a new
  judgement for every new arriving range (cached by content). Use cut points when one component serves many systems.
- **A chosen part's fields** reach the system as `COMPONENT.slot.field` (`AD.R1.price`, `AD.R1.R`); a toleranced
  one becomes its own toleranced given there (sound; not tied to the component's inside). A name a component does
  not have is refused, said plainly.
- **The price, said plainly:** between components only RANGES travel (unless an affine contract applies). Two outputs of one component, or two
  components fed by one source, are independent ranges in the system — a flat brick would keep that
  correlation. MEASURED on the charger: flat brick Vend ∈ [4.152, 4.238] V, the system [4.144, 4.246] V (the
  battery's bands are wider than what arrives).

## 7h. stocks — a system of stocks and flows under a shared random driver (since 2026-11-03)

A DIFFERENT kind of brick, for "how likely is it to run short within N days": a battery and a water tank fed by one
weather, a store fed by uncertain deliveries. Mark it `"kind": "stocks"`; it has no quantities/laws. The answer is
P_fail — the probability of at least one counted failure within `days` steps — PROVED from both sides.

```json
{"stand": "ztl-stand/1", "kind": "stocks",
 "driver": {"start": "sun", "p": {"sun":   {"sun": ["0.6", "0.8"], "cloud": ["0.2", "0.4"]},
                                  "cloud": {"sun": ["0.3", "0.5"], "cloud": ["0.5", "0.7"]}}},
 "stocks": {"battery": {"capacity": "2000", "start": "2000", "unit": "100"},
            "tank":    {"capacity": "4",    "start": "4",    "unit": "0.5"}},
 "steps": [{"add": "battery", "amount": {"sun": ["1700", "1900"], "cloud": ["400", "600"]}, "why": "solar, Wh/day"},
           {"take": "battery", "amount": ["400", "400"], "fail": "power", "why": "vaccine fridge first"},
           {"take": "battery", "amount": ["600", "600"], "then": [{"add": "tank", "amount": ["2", "2"]}],
            "why": "the pump runs only on what is left, and then fills the tank"},
           {"take": "tank", "amount": ["1.5", "1.5"], "fail": "water", "why": "the clinic's daily water"}],
 "days": 30,
 "requirements": [{"quantity": "P_fail", "op": "<=", "value": "0.01", "why": "at most 1 % chance of a bad day"}]}
```

- **driver**: the shared random factor as a Markov chain — its states, the start, and for EVERY state the
  probabilities of the next state as ranges `[lo, hi]` (a row must admit a distribution: sum of lo <= 1 <= sum of hi).
  One step = one day (or the step the person names). A known climate gives the ranges; say where they come from.
- **stocks**: each with `capacity`, `start` and a `unit`. EVERY amount, capacity and start of that stock must be a
  whole number of its unit (choose the unit that divides them all: 100 Wh, 0.5 m³). Fewer, larger units are faster;
  the product of (capacity/unit + 1) over the stocks times the driver's states must stay under 200 000.
- **steps**, applied in order every step AFTER the driver has moved: `add` (an inflow, capped at the capacity;
  its amount may depend on the driver's state, a dict by state), `take` with `fail` (MUST: if the stock cannot pay,
  that is a failure with this name), `take` without `fail` (MAY: only if the stock can pay, and then its `then`
  steps run — a pump that runs on the leftover). Order is priority: the fridge before the pump.
- Every `amount` is a range `[lo, hi]`; the stand lets an adversary pick ANY grid value in it anew each step (the
  bound holds for fixed and for varying data alike — and does not assume that less is always worse).
- `fail_on`: optional list of the failure names that count (default: all).
- **requirements**: on `P_fail` only (`<=`, `<`, `>=`, `>`, `within`). EARNED: every system in the ranges meets it;
  REFUTED: the proved range lies outside; OPEN: it straddles (narrow the ranges or use smaller units).
- Model only what the person describes; a failure the person did not ask about is not a step. Do not split one
  device into two stocks.

## 7i. HVAC models: library functions and performance curves (since 2026-11-12, ported from EnergyPlus 26.2.0)

DESIGN-HVAC.md has the plan and the sources. Two devices, both expanded into ordinary laws before the stand reads the
brick — ZTL proves the expansion like any law.

**Library functions** `ep_<name>(...)`, arguments and results in SI (temperatures in K, pressure in Pa, humidity ratio
as a pure number, enthalpy in J/kg):

| function | is | EnergyPlus |
|---|---|---|
| `ep_psat(T)` | saturation pressure (Hyland-Wexler, ice below 273.16 K) | PsyPsatFnTemp |
| `ep_h(T, W)`, `ep_h_tdbrhpb(T, RH, P)` | enthalpy of moist air | PsyHFnTdbW, PsyHFnTdbRhPb |
| `ep_cpair(W)`, `ep_hfg(W, T)`, `ep_hg(W, T)` | specific heat, latent heat, vapour enthalpy | PsyCpAirFnW, PsyHfgAirFnWTdb, PsyHgAirFnWTdb |
| `ep_tdb_hw(H, W)`, `ep_w_tdbh(T, H)` | dry bulb from enthalpy; humidity ratio from enthalpy | PsyTdbFnHW, PsyWFnTdbH |
| `ep_w_tdppb(Tdp, P)`, `ep_w_tdbrhpb(T, RH, P)`, `ep_w_tdbtwbpb(T, Twb, P)` | humidity ratio from dew point, RH, wet bulb | PsyWFnTdpPb, PsyWFnTdbRhPb, PsyWFnTdbTwbPb |
| `ep_rh_tdbwpb(T, W, P)`, `ep_rhov_tdbwpb`, `ep_rhov_tdbrh`, `ep_v(T, W, P)` | RH, vapour density, specific volume | PsyRhFnTdbWPb, PsyRhov*, PsyVFnTdbWPb |
| `ep_tsat_h_std(H)` | saturation temperature from enthalpy at standard pressure (its own fits) | PsyTsatFnHPb |
| `ep_w_twb_newW(T, Twb, P)` | the relation PsyTwbFnTdbWPb solves (with its ice branch) | PsyTwbFnTdbWPb |

An ITERATIVE EnergyPlus function is an implicit law: the wet bulb of (T, W, P) is the derived `Twb` with
`"search": [lo, hi]` and the law `W == ep_w_twb_newW(T, Twb, P)`. Note: in EnergyPlus itself the wet-bulb solver and
PsyWFnTdbTwbPb use DIFFERENT coefficients, so `ep_w_tdbtwbpb` is not the inverse of the wet-bulb solve.

**Performance curves** by name, in a `"curves"` block, called as `curve(NAME, x, y, ...)`:

```json
"curves": {"CAPFT": {"type": "Curve:Biquadratic", "coeffs": ["0.257896", "0.0389016", "-0.00021708", "0.0468684",
                                                             "-0.00094284", "-0.00034344"],
                     "x_min": "5", "x_max": "10", "y_min": "24", "y_max": "35", "inputs": ["degC", "degC"]}},
"laws": [{"zfl": "Cap == Cap_ref*curve(CAPFT, Tchw, Tcond)", "source": "capacity f(T)"}]
```

- Every input is clamped to its limits first and the output to `out_min` / `out_max`, as EnergyPlus's Curve::value.
- `inputs`: `"degC"` for a temperature (the argument, in K in the stand, enters the curve in deg C as EnergyPlus feeds
  it) or `""` for a pure number; limits are in those units, as an IDF writes them.
- Types: Linear, Quadratic, Cubic, Quartic, Exponent, Sigmoid, RectangularHyperbola1/2, ExponentialDecay,
  DoubleExponentialDecay, Biquadratic, QuadraticLinear, CubicLinear, Bicubic, FanPressureRise, ChillerPartLoadWithLift,
  Triquadratic, QuadLinear, QuintLinear. Refused aloud: ExponentialSkewNormal (erf), Table:Lookup.
- From an IDF: `ustand.hvac.curves.curves_from_idf(text)` gives the specs by name (all 976 curves of EnergyPlus's
  datasets read).
- `inputs` may also be `"dC"` (a temperature DIFFERENCE: K = deltaC, no offset) and `"output": "dC"` gives the
  result in K — used by the tower types below.

### Cooling towers (since 2026-11-12; EnergyPlus CondenserLoopTowers.cc — ustand/hvac/towers.py)

Temperatures in K, ranges and approaches in K (differences), flow ratios pure numbers, powers W, flows kg/s or m^3/s.

| function | is | EnergyPlus |
|---|---|---|
| `ep_tower_approach_cooltools(FRW, FRA, Twb, Tr)`, `ep_tower_approach_yorkcalc(...)` | approach (K) of a variable-speed tower from water flow ratio, air flow ratio, inlet wet bulb, range — built-in coefficients, CAPPED as the operating tower caps | calculateVariableSpeedApproach after checkModelBounds |
| `..._cooltools_raw`, `..._yorkcalc_raw` | the same without any capping (sizing, calibration) | calculateVariableSpeedApproach |
| `ep_tower_twbcap_cooltools(Twb)`, `ep_tower_twbcap_yorkcalc(Twb)` | the wet bulb clamped to the model's limits (-1..26.6667 C; -34.4..29.4444 C) | checkModelBounds |
| `ep_tower_vs_tout(Ton, Twin, Tset, FC)`, `ep_tower_vs_cycling(Ton, Tmin, Twin, Tset, FC)`, `ep_tower_vs_afr(..., AFRmin, AFRsol)`, `ep_tower_vs_power(Ton, Tmin, Twin, Tset, FC, FPRmin, FPRsol, Pdes)` | outlet temperature, fan cycling ratio, air flow ratio, fan power over the four regimes (full speed, fan off, cycling at the minimum air flow, modulating) | calculateVariableSpeedTower |
| `ep_tower_fpr_cube(FRA)` | fan power ratio FRA^3 — the default; with a fan curve write `curve(FAN, FRA)` in its place | calculateVariableSpeedTower |
| `ep_hsat(T, P)` | enthalpy of saturated air | PsyHFnTdbRhPb(T, 1, Pb) |
| `ep_tower_cpairside(Twb, X, P)`, `ep_tower_q_ua(UA, MCW, MA, CPS, CPA, Twin, Twb)`, `ep_tower_q_air(MA, Twb, X, P)`, `ep_tower_tout(Twin, Q, MCW)` | the UA (effectiveness-NTU) tower: air-side specific heat, heat of one pass, heat taken by the air, outlet water temperature | calculateSimpleTowerOutletTemp |
| `ep_tower_ss_tout / ss_power(Toff, Ton, Tset[, Pfan])`, `ep_tower_ts_tout / ts_power(Toff, T1, T2, Tset[, Plow, Phigh])` | single- and two-speed fan cycling between the stage outlet temperatures | calculateSingleSpeedTower, calculateTwoSpeedTower |
| `ep_tower_evap_satexit(MA, Win, Wout, RHOW)`, `ep_tower_evap_lossfactor(F, Twin, Tout, MW, RHOW)`, `ep_tower_drift(Vdes, DF, AFR)`, `ep_tower_blowdown(Evap, Drift, CR)` | water use (m^3/s): evaporation by the saturated-exit method and by the loss factor, drift, blowdown by concentration ratio | calculateWaterUsage |
| `ep_rhoair(P, T, W)`, `ep_rho_h2o(T)` | density of moist air; EnergyPlus's cubic for liquid water | PsyRhoAirFnPbTdbW, RhoH2O |

How EnergyPlus caps the inputs (found in the code, kept exactly): the wet bulb is clamped to the model's limits; the
water flow ratio to 0.75..1.25 for CoolTools ONLY (YorkCalc is not capped); the range and the approach are NOT
capped (only warned about); the air flow ratio is not capped (the search keeps it in [minimum, 1]).

What EnergyPlus ITERATES is an implicit law — one derived quantity with `search`:

```json
"quantities": {"Twb": {"role": "given", "range": ["288.15", "298.15"], "unit": "K", "ground": "wet bulb 15..25 C"},
               "Twin": {"role": "given", "value": "308.15", "unit": "K", "ground": "water in, 35 C"},
               "FRW": {"role": "given", "value": "1", "unit": "", "ground": "design flow"},
               "FRA": {"role": "given", "value": "1", "unit": "", "ground": "full fan"},
               "MaxRange": {"role": "given", "value": "11.1111", "unit": "K", "ground": "CoolTools model limit"},
               "Tr": {"role": "derived", "unit": "K", "search": ["0.001", "22.2222"]},
               "Tout": {"role": "derived", "unit": "K"}},
"laws": [{"zfl": "Twin == ep_tower_twbcap_cooltools(Twb) + ep_tower_approach_cooltools(FRW, FRA, Twb, Tr) + Tr",
          "source": "EnergyPlus calculateVariableTowerOutletTemp: the range it iterates to"},
         {"zfl": "Tout == Twin - min(Tr, MaxRange)", "source": "EnergyPlus calculateVariableTowerOutletTemp"}],
"requirements": [{"quantity": "Tout", "op": "<=", "value": "302.629", "why": "the chiller's entering condenser limit"}]
```

- The range at a FIXED fan speed (above): search `[0.001, max(the model's maximum range, 22.2222)]` K. No root there:
  EnergyPlus uses the maximum range and warns; the stand says OPEN.
- The air flow ratio that MEETS a setpoint: `Tset - Twb == ep_tower_approach_cooltools(FRW, FRA, Twb, Twin - Tset)`,
  `"FRA": {"role": "derived", "search": ["0.2", "1"]}` (from the minimum air flow ratio); then
  `Pfan == Pdes*ep_tower_fpr_cube(FRA)`. The requested approach uses the uncapped wet bulb, as EnergyPlus.
- The calibration at sizing: `Tapp_des == ep_tower_approach_cooltools_raw(FRW, FRA1, Twb_des, Tr_des)` with FRW
  searched from 0.5; the calibrated design flow is the design water flow / FRW.
- The control sequence, once the outlet at full fan `Ton` and at the minimum air flow `Tmin` are known:
  `Tout == ep_tower_vs_tout(Ton, Twin, Tset, FC)`, `Pfan == ep_tower_vs_power(Ton, Tmin, Twin, Tset, FC, FPRmin, FPRsol, Pdes)`.
- User coefficients: a curve of type `CoolingTowerPerformance:CoolTools` (35 coefficients) or `:YorkCalc` (27),
  called `curve(TWR, FRW, FRA, Twb, Tr)`; `curves_from_idf` reads the object with its limits
  (`"z_min"`/`"z_max"` the wet bulb, `"x_min"`/`"x_max"` the water flow ratio — CoolTools only).
- A UA tower (CoolingTower:SingleSpeed / :TwoSpeed): the exit air wet bulb `X` is the unknown,

  ```json
  "X": {"role": "derived", "unit": "K", "search": ["298.65", "308.15"]},
  {"zfl": "ep_tower_q_air(MA, Twb, X, P) == ep_tower_q_ua(UA, MCW, MA, ep_tower_cpairside(Twb, X, P), ep_cpair(W), Twin, Twb)",
   "source": "EnergyPlus calculateSimpleTowerOutletTemp: the fixed point of its iteration"},
  {"zfl": "Tout == ep_tower_tout(Twin, ep_tower_q_air(MA, Twb, X, P), MCW)", "source": "EnergyPlus calculateSimpleTowerOutletTemp"}
  ```

  with `MA` = air volume flow x `ep_rhoair(P, Tdb, W)` and `MCW` = water mass flow x its specific heat; search `X`
  from a little above the inlet wet bulb to the inlet water temperature. This law is long (the saturation pressure
  sits in it dozens of times): about 4 minutes per design with exact inputs (and with every input exact the stand can earn it but found no witness to REFUTE it — DESIGN-HVAC.md). EnergyPlus stops its iteration early;
  its outlet differs from the root by up to 4e-4 K (measured on 300 towers). A Merkel variable-speed tower is this
  tower with `UA*curve(UAWB, Twb_des - Twb)*curve(UAAF, FRA)*curve(UAWF, FRW)` in place of `UA` (the curve
  input of a wet-bulb difference is `"dC"`).
- Water use: `ustand.hvac.towers.water_use_laws("SaturatedExit")` (or `"LossFactor"`) returns the quantities and
  the laws of the chain — `h_out == ep_hsat(Twb, P) + Q/MA`, `Tsat_out == ep_tsat_h_std(h_out)`,
  `Wout == ep_w_tdbh(Tsat_out, h_out)`, `Evap == ep_tower_evap_satexit(MA, Win, Wout, RHOW)`,
  `Drift == ep_tower_drift(Vdes, DF, AFR)`, `Blowdown == ep_tower_blowdown(Evap, Drift, CR)`,
  `Makeup == Evap + Drift + Blowdown` — over the brick's `MA, Twb, P, Win, Q, RHOW, Vdes, DF, AFR, CR`.
  Two things EnergyPlus does that a reader would not guess: the loss factor `F` is multiplied AS ENTERED (the field
  is documented in percent per K, and nothing divides it by 100 — `DF`, the drift, is divided); a concentration
  ratio of 2 or less is treated as 2.
- The water's density and specific heat are the brick's quantities (EnergyPlus's fluid tables are not ported).

### Chillers (since 2026-11-12; EnergyPlus ChillerElectricEIR.cc, ChillerReformulatedEIR.cc — ustand/hvac/chillers.py)

| function | is |
|---|---|
| `ep_chiller_avail(RefCap, CapFT)` | available capacity, the curve value floored at 0 |
| `ep_chiller_qevap(Load, Avail, MaxPLR)`, `ep_chiller_qevap_lim(Load, Avail, MaxPLR, ME, CP, Tin, Tlow)` | evaporator heat: the load, cut at Avail x MaxPLR (and by the leaving-water lower limit) |
| `ep_chiller_plr(Q, Avail, MinUnl, MaxPLR)` | part load ratio, never below the minimum unloading ratio |
| `ep_chiller_frac(Q, Avail, MinPLR, MaxPLR)` | cycling ratio below the minimum part load ratio (taken BEFORE the unloading floor) |
| `ep_chiller_falseload(Q, Avail, PLR, FRAC, Small)` | false loading (hot-gas bypass), zero below `Small` (HVAC::SmallLoad) |
| `ep_chiller_power(Avail, COP, EIRFT, EIRFPLR, FRAC)` | compressor power, negative curve values floored at 0 |
| `ep_chiller_qcond(Power, Fcond, Q, False)`, `ep_chiller_tcondout(QC, MC, CP, Tci)` | condenser heat; condenser outlet temperature |
| `ep_chiller_condflow(M, Mmax, MinRatio)`, `ep_chiller_cop_reform(COP)`, `ep_chiller_evapcond_water(MC, Win, Twb, P, Tconv)` | condenser flow limits; the reformulated chiller's COP <= 0 -> 5.5; water use of an evaporatively-cooled condenser |

A chiller is built BY CODE from the IDF text that states it (name, reference capacity and COP, the three curves):

```python
from ustand.hvac import chillers
parts = chillers.chiller_from_idf(open("Chillers.idf", encoding="latin-1").read(),
                                  "ElectricEIRChiller McQuay WSC 471kW/5.89COP/Vanes")
brick = {"stand": "ztl-stand/1", "curves": parts["curves"],
         "quantities": dict(parts["quantities"],
                            Load={"role": "given", "range": ["200000", "450000"], "unit": "W", "ground": "cooling load"},
                            Tchw={"role": "given", "value": "281.15", "unit": "K", "ground": "leaving setpoint 8 C"},
                            Tcond={"role": "given", "range": ["295.15", "303.15"], "unit": "K", "ground": "22..30 C"}),
         "laws": parts["laws"],
         "requirements": [{"quantity": "Power", "op": "<=", "value": "79028", "why": "electrical budget"}]}
```

- The brick gives the operating quantities `Load` (W), `Tchw` (K, the leaving chilled-water setpoint) and, for
  Chiller:Electric:EIR, `Tcond` (K, the ENTERING condenser temperature); it gets `Avail, Qevap, PLR, FRAC, Qfalse,
  Power, Qcond`. `prefix="CH1_"` names every quantity and curve of one chiller apart from another's. An autosized
  reference capacity (the dataset's generic DOE-2 chillers) is the brick's to give as `RefCap`.
- Chiller:Electric:ReformulatedEIR reads its curves at the LEAVING condenser temperature, which depends on the
  condenser heat: the brick gives `Tcin` (K), `Mcond` (kg/s), `CpCond` (J/(kg*K)) and gets `Tco` as an implicit
  quantity, `Tco == ep_chiller_tcondout(Qcond(Tco), Mcond, CpCond, Tcin)`, searched between the curves' limits
  (2-3 minutes per design). Where the root lies outside those limits EnergyPlus does not solve it (it
  substitutes twice); the stand says OPEN.
- The laws take the load the evaporator is asked for and the water leaving at its setpoint; flow modes, heat
  recovery, the thermosiphon and sizing are not in them.

## 7b. modes (optional) — the design must hold in every one

```json
"modes": {
  "full load": {"quantities": {"P": {"value": "25", "tolerance": "0.1"}, "Ta": {"range": ["20", "45"]}},
                "requirements": [{"quantity": "Tj", "op": "<=", "value": "125", "why": "max junction"}]},
  "cold idle": {"quantities": {"P": {"value": "2", "tolerance": "0.1"}, "Ta": {"range": ["-10", "0"]}},
                "requirements": [{"quantity": "Tj", "op": ">=", "value": "-7", "why": "no ice at idle"}]}
}
```

- A mode **overrides given quantities** (`value`, `tolerance` or `range`) and **adds requirements**. The laws,
  defines and catalog are the same in every mode. Overriding a derived quantity is a BRICK ERROR.
- Top-level `requirements` apply in every mode, and may be empty when every requirement belongs to a mode.
- **EARNED** only when the design is EARNED in every mode. The output has `per_mode` (the guaranteed range and how,
  per mode). **REFUTED** names the `failing_mode` and its point, and `failing_modes` lists every mode the closest
  design fails in (each design's listing has its `failing_modes` too). **OPEN** if a design is undecided in some mode
  and none was earned.
- The objective works as before. `optimal` means every cheaper design was refuted in some mode.
- Each (design, mode) is judged by the same machinery as a plain brick, so everything in sections 1-7 holds per
  mode. `minimal_conflicts` runs across modes (since 2026-10-10): a mode's own requirement is listed as
  `[mode] ...`, the brick's apply in every mode (t11: only the pair full-load max + cold-idle min conflicts).
- A mode may also carry its own `define` (replacing the brick's of that name: `"Nact": "CNT.N - 1"` for one instance
  down) and its own `laws` (added to the brick's: a standby path). Requirements on a quantity a mode's law defines
  belong in that mode.

### Totals over the modes (since 2026-10-11)

Annual energy over flow bins, wear over wet and dry seasons: a sum of one quantity across the modes.

```json
"modes": {"low":  {"weight": "3000*hr", "quantities": {"Q": {"value": "0.03"}}},
          "high": {"weight": "2000*hr", "quantities": {"Q": {"value": "0.06"}}}},
"totals": {"Eyear": {"sum": "P", "unit": "MWh"}},
"requirements": [{"quantity": "Eyear", "op": "<=", "value": "150"}]
```

- Every mode needs a `weight`: a string — a number, or an expression of given quantities (`hr` above is a given
  `1 h`; a share of the year is a plain number). `Eyear` is the sum over the modes of `weight * sum`, with `sum`
  read in that mode. Mode names must be plain names (letters, digits, `_`).
- With `totals` the modes are judged as **ONE brick**: each derived quantity, and each given a mode overrides, gets
  a copy per mode, named `P_in_low` in the output. A given that no mode overrides is the **same value in every
  mode** — one physical part, one tolerance draw. (Without totals each mode is judged on its own, and such a given
  may take different values in different modes.) To let a given vary independently per mode, override it in
  every mode. A requirement of a mode goes on that mode's copies; a requirement on a total holds once.
- The objective may use totals, givens and catalog fields — not a derived quantity, which has one value per mode.

## 8. Reading the verdict

A bound MET EXACTLY counts as met: `Tj <= 175` with a worst case of exactly 175.000 is EARNED (a strict `<` is not).
With `"report": "all"` every EARNED design in `designs` carries its own `guaranteed` ranges.

| Verdict | Meaning | What comes with it |
|---|---|---|
| EARNED | a design meets every requirement for every value the tolerances allow | `design`, `guaranteed` ranges (in each quantity's unit), `how` each was bounded (ZTL exact / ZTL outer / ZTL certificate / outside ZTL), `rests_on` (the datasheet), `objective` |
| REFUTED | every design fails at a concrete point | `closest_design`, `its_violating_point`, `value_there`, `overshoot`, `reasons` |
| OPEN | some design could not be decided either way, and none was earned | how many |
| STAND FAULT | the judge and the independent checker disagree | which design. **Never ignore it** |
| BRICK ERROR | the JSON itself is wrong (units, roles, missing catalog, a wrong type, an unreadable number or law) | the reason, with the place (`quantities.Vin.unit`, `laws[2]`) |
| STAND ERROR | the stand itself failed on this brick — a bug in the stand, never a verdict about the design | the exception and where. Please report it |

The `reasons` block of a REFUTED verdict contains:
- `spread_over_tolerances` — the closest design's range;
- `window` — the requirement's width;
- `verdict_on_window` — set when the spread alone is wider than the window, so centring cannot help;
- `largest_contributors` — which toleranced quantity moves the result most.

A REFUTED verdict also carries `minimal_conflicts`:
- `sets` — the minimal sets of requirements that this catalog cannot satisfy together. No set contains another.
  Each set must be dropped or relaxed AS A WHOLE, and a requirement that appears in every set is the cheapest to
  change.
- `undecided_sets` — subsets the stand could not judge either way.
- How (since 2026-10-13): first ONE minimal set by deletion — each requirement dropped in turn while the rest stays
  refuted, n runs, any number of requirements; then subsets by size, smallest first, within a budget of subset runs
  (default 4 per requirement, at least 24; `"conflicts": N` or `"all"`; with `--jobs` the subsets of one size
  are judged by the workers). `complete` says whether every subset was judged;
  `subset_runs` how many runs it took. Every set listed is a minimal conflict; with `complete: false` there may be
  others.

### When the extreme lies inside the box

When the corners pass and the interval reading is too wide (power into a load peaks at RL = Rs), the stand searches a
certificate that splits the box into pieces, and ZTL checks it exactly. `how` then says "certificate checked exactly
(N pieces)", and the independent checker re-checks the same certificate with its own means. If the search finds a failing point inside, that point is the REFUTED witness. This works for a quantity
with an explicit law, and for one that depends on unknowns solved from a square linear system (up to 5 unknowns) (GAPS Z5, Z6). A certificate the checker cannot re-check earns nothing; it is listed in `certificates_unconfirmed`.

A quantity defined as a SUM (since 2026-10-12, the curator's "да"; c11: an annual result over four quarters) may be
proved term by term: each term over its own data, the bounds added (min of a sum >= sum of the mins — sound, maybe
wider when terms share a datum). It is tried FIRST when every term reads fewer data than the whole; then the whole
gets a small search budget (200 pieces: enough for a failing point near the top, not the hours a five-datum
certificate took). `how` says "a SUM proved term by term". A name FIXED at exactly 0 in a design (an option amount
of 0) is replaced by 0 before the search, in the whole and in each term: the value is unchanged, and a min/max it
multiplied no longer blocks the monotone pieces.

### Every design's outcome

- A requirement may name a **given** quantity or a catalog **field** directly (`"quantity": "FD.B"`, since 2026-10-11):
  the stand makes a derived `FD_B_req == FD.B` for it, shown under that name.
- `"conflicts"` at the top of the brick: `false` switches `minimal_conflicts` off; a number sets its budget of subset
  runs (default 4 per requirement, at least 24); `"all"` judges every subset (up to 2^n runs — with heavy designs far more than
  the verdict).
- The output lists `designs`: each design tried, in order, with its verdict.
  - A REFUTED design shows the requirement it `fails`, and `by_at_witness` how much at ITS WITNESS POINT (the point the stand
    found, not necessarily the worst one), and the `mode`, with modes.
  - An OPEN design shows why it was not decided.
- By default the stand stops at the first EARNED design (with an objective, the cheapest).
- Add `"report": "all"` to the brick to judge every design and answer "which ones pass".
- At most 200 designs are listed.
- A REFUTED names ONE failing requirement. With several requirements, `each_requirement` gives every one's OWN
  verdict on that design (the design pinned, that requirement alone): EARNED with its `guaranteed` range,
  REFUTED with its `overshoot`, or OPEN (since 2026-10-12; real round 2, s03 split its brick by hand for this).
- With `--dev` a REFUTED may show a different witness than work mode (both are failing points), and the checker
  may leave OPEN what work mode refutes — it confirms a refutation only with its own means (s02).

## 9. Before trusting a new JSON

1. Run it, and look at `units`. If it says "not checked", add the missing units.
2. Look at `how`. Every "outside ZTL" line is a place where the stand, not the judge, did the bounding. It is labelled
   and checked, but it is not ZTL's verdict.
3. If a result surprises you, open the witness point and recompute it by hand. It is exact rational arithmetic, so it
   must match.
4. Add the file to `tests/test_stand.py` with its expected verdict, so it stays true.
