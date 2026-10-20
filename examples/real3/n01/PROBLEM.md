# n01 problem: worst-case offset of a Wheatstone bridge built from discrete resistors

## Source
- Article "How to Stay Out of Deep Water when Designing with Bridge Sensors", Analog Dialogue (Analog Devices), vol. 48 no. 1, 2014.
  Read through the republication at
  https://www.eenewseurope.com/en/how-to-stay-out-of-trouble-when-designing-with-bridge-sensors/
  (2014-06-19, titled "How to stay out of trouble when designing with bridge sensors").
  The original is https://www.analog.com/en/analog-dialogue/articles/how-to-stay-out-of-deep-water.html
  (my fetch of it timed out; I did not read the original page, only the republication). Author: not confirmed by me.
- Equation 1 of the article is an image in the republication; I could not read it. A search-engine summary gave it as
  VOS = +-(TOL x VEX)/100 with TOL in percent. I did NOT see the equation itself; I check it by hand instead.

## The problem, in my words
A bridge of four discrete resistors, one pair per divider arm, is excited by VEX. Ideally the output is zero, but
only if the four are exactly equal. The article asks: how large can the unloaded differential output (the offset)
be when each of the four elements has a given tolerance?

Numbers in the source: every one of the four elements has a tolerance of 0.1 %; the excitation is 5 V.
No resistor value is given. No detector or load is given (the offset is the unloaded output).

## PUBLISHED ANSWER
The offset can reach 5 mV (that is TOL x VEX = 0.1 % x 5 V, worst case, unloaded). It goes on to say that
with an in-amp gain of 400 this is +-2 V at the output, i.e. more than 80 % of a rail-to-rail 5 V swing
(this last part is arithmetic on the 5 mV and is not about the bridge).
Claim: an upper bound that is reached, not an estimate: a reached maximum.

## What I had to assume (the source left it open)
1. Nominal resistance of the four elements: 10 kohm (the formula does not depend on it; I also ran 1 kohm).
2. A network brick needs a branch current, so the unloaded output voltage is turned into the current through a
   detector resistor Rm between the two mid-points: I5 = (offset)/(Rm + about R). Rm = 1 Gohm (assumed, "almost
   unloaded"); I also ran Rm = 10 Mohm. Rm is exact (no tolerance), added by me.
3. Tolerance reading: each element independently anywhere in +-0.1 % of nominal (the source says "for each one of
   the individual elements").
4. The excitation 5 V is exact (the source gives no tolerance for it).
