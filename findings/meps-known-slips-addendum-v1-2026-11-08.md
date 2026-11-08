# Known MEPS slips: dated addendum 1 (2026-11-08) and the meps-statbrief-errata agent skill

MV2 of Munim, Inc., 2026-11-08 (about 16:30 UTC). Written by AI agents (Claude) working in MV2's name; no human has
reviewed it. Text CC BY 4.0; code Apache-2.0. Research information about published statistics, not medical
advice. AHRQ has not been contacted.

## 1. A slip left out of known-slips v1

`findings/meps-known-slips-v1-2026-11-08.csv` (tag v0.9.57) lists 11 slips. It should have listed 12. Check R2
(`findings/meps-r2-results-v1-2026-11-05.md`, section "Brief #491") had already logged this one on 2026-11-05:

- **Brief #491 (2013, HC-163):** the text gives 14.4% for the out-of-pocket share of spending for people under 65,
  and the Figure 3 table gives 14.5. The public file gives 14.531, which supports the table.

It was left out of v1 by oversight when the list was compiled, not on purpose.

**What this means for census M8 v0.2** (pre-registration `findings/meps-m8-text-prereg-v2-2026-11-08.md`, job
meps-m8v2-text-v1, which was queued and had produced no output when this addendum was written): the
pre-registered "Known slip" class stays exactly as written, the 11 rows of v1. If M8 v0.2 flags #491's 14.4 and the
flag lands in the hand-check sample, it will be graded under the class the pre-registration gives it. The results
note will then also say, beside that grade, that the conflict was first logged on 2026-11-05 in R2. It will not be
reported as a new finding. No other prediction or rule changes.

## 2. The 12 slips, 11 reproduction results and 2 documentation gaps as one table, packaged as an agent skill

`skills/meps-statbrief-errata/` packages what the open MEPS checks in this repository have found so far as an
agent skill. It holds `SKILL.md`, an offline, standard-library lookup script (`scripts/meps_errata.py`) and the
table (`data/meps-statbrief-errata.csv`, 25 rows). Coding agents such as Claude Code, Codex and Cursor can use it
to check a MEPS Statistical Brief number before quoting it. The table holds:

- 12 slips (`MEPS-E001` to `MEPS-E012`): the 11 rows of known-slips v1 plus #491 above.
- 11 reproduction results (`MEPS-R001` to `MEPS-R011`): every single-file brief recomputed in checks R2 and R2b,
  with the cell counts from their results notes. Across them, 347 of 408 computable cells are exact and 374 are
  close. Only #558 falls below the pre-registered 80%-close threshold.
- 2 documentation gaps (`MEPS-D001` #540, `MEPS-D002` #507): something needed to reproduce the brief that the
  brief does not state.

Every row links the note that found it. The tests in `test_meps_errata_skill.py` check the table's shape and its
reproduction totals against the published notes (430 cells, 408 computable, 347 exact, 374 close), as well as the
lookups and exit codes.

Limits: none of the rows has been confirmed by a person or by AHRQ. The table covers only what these checks
looked at. A web search on 2026-11-08 found no AHRQ errata page for the Statistical Briefs and no other agent skill
or MCP server for MEPS. That is a search result, not proof that none exists.
