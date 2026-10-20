# s06 problem: LDO thermal worked example with stated tolerances (TC1264, SOT-223)

## Source
- Microchip TC1264 "800 mA Fixed-Output CMOS LDO with Shutdown", datasheet DS21375D (2010), section 5.2 "Power Dissipation" (the worked example next to Equations 5-1 and 5-2), Table 5-1, and section 1.0 DC characteristics.
- Read from a mirror: https://cdn.eicom.ru/media/PDF/8071246.pdf (a copy of DS21375D; the Microchip site itself returned 403 to my fetch tool).

## The problem in my words
A 2.7 V fixed-output LDO (SOT-223 package) is fed from a 3.3 V supply that is only good to +-10%. The regulated output is only good to +-0.5%, and the worst case for dissipation is the LOW output. The load is at most 275 mA. The die must stay at or below 125 C while the ambient is at its hottest, 95 C; the package junction-to-air resistance is 59 C/W. Question 1: what is the worst-case power in the regulator, and is it below what the package can shed? Question 2 (stated in the closing lines): what is the largest input voltage the same part can take under the same conditions?

Numbers given by the source:
- VIN max = 3.3 V * 1.10 = 3.63 V (written "3.3V +-10%")
- VOUT min = 2.7 V * 0.995 (written "2.7V +-0.5%")
- ILOAD max = 275 mA
- TJmax = 125 C, TAmax = 95 C, thetaJA = 59 C/W (Table 5-1: copper 100 sq mm top, 2500 backside; the table runs 45 to 59 C/W for other copper areas)
- Eq 5-1: PD = (VINmax - VOUTmin) * ILOADmax. Eq 5-2: PDmax = (TJmax - TAmax) / thetaJA.

## PUBLISHED ANSWER
- PD = 260 mW (the source's arithmetic: (3.3*1.1 - 2.7*0.995) * 275 mA).
- PDmax = (125 - 95)/59 = 508 mW.
- Claim: 260 mW is below 508 mW, so the design is acceptable thermally.
- Claim 2: substituting 508 mW back into Eq 5-1 gives a maximum allowable VIN of 4.6 V.

## Where the source is silent / what I assumed
- The example checks only the hot end (thermal). It does not check the low end of the input range against dropout, although its own supply (3.3 V -10% = 2.97 V) is close to 2.7 V + dropout. The datasheet gives a dropout table (Max column, VR >= 2.5 V): 30 mV at 0.1 mA, 160 at 100 mA, 480 at 300 mA, 800 at 500 mA, 1300 at 800 mA; and note 2: VIN >= VR + dropout is required. Supply current max 130 uA. I ADDED a second check from those numbers (extension, flagged in report.md).
- The 4.6 V of claim 2 is ambiguous: it reads as an absolute maximum VIN (the one used in Eq 5-1), not as a nominal with +10%. I read it as the absolute value.
- TA = 95 C is taken as the only ambient (the source gives only the maximum).
