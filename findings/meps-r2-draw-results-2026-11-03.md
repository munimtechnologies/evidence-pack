# Check R2: the random draw of five MEPS Statistical Briefs (result)

MV2 of Munim, Inc., 2026-11-03. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Pre-registration: `findings/meps-r2-prereg-v1-2026-11-02.md`. Code: `meps/r2_draw.py` 0.1.0 (tag v0.9.37). Job
`meps-r2-draw-v2`, 2026-11-02 12:23-12:26 UTC, exit 0. Output: `findings/meps-r2-draw-v1/r2-draw.json`. Text CC
BY 4.0. Research information about published statistics, not medical advice. AHRQ has not been contacted.

## Validity

- **Timing:** the pre-registration (commit 0702a28) and the draw code (commit b18bf97) were committed at
  06:24:21Z and 06:24:28Z on 2026-11-02 (repository commit feed). The beacon pulse they name is stamped 10:00:00Z
  that day, so the seed did not exist when the draw was fixed.
- **Eligible set:** the job recomputed exactly the 11 briefs listed in the pre-registration (#491, 493, 496, 497,
  506, 507, 521, 533, 540, 554, 558). The draw is valid.
- **Seed:** NIST Randomness Beacon 2.0, chain 2, pulse 2009978, timeStamp 2026-11-02T10:00:00.000Z. outputValue
  begins 15F9E90C6AD2924D, so the seed is 1583552983538504269.
- The first attempt (`meps-r2-draw-v1`) was stopped from outside (SIGTERM, exit 143) while it waited for the
  pulse. It was re-filed unchanged as v2. The v1 output in the job log is the unit-test fixture, not a draw.

## The five briefs, in draw order

1. **#506** (HC-181, 2015)
2. **#540** (HC-216, 2019)
3. **#521** (HC-192, 2016)
4. **#507** (HC-181, 2015)
5. **#491** (HC-163, 2013)

Three are editions of one annual series on the concentration of health care spending. They share a method, which
the specification notes as a limit. As pre-registered, no brief is replaced for being hard.

## Next

The specification for #506, #521 and #540 is `findings/meps-r2-spec-conc-v1-2026-11-03.md`, fixed before their
files are downloaded. Under it, 10 of #540's 40 cells (treated conditions) are not computable from the one file
it names. #507 and #491 get their own specifications before any job reads their files.
