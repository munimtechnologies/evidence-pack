# CCDI census: post-hoc diagnostics (v1)

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written by AI agents (Claude) working in MV2's name; no human has reviewed it.

**Everything here is POST HOC.** This code was written on 2026-10-22, after the pre-registered census results (`../concordance-v1/results.md`) had been seen. Its job is to explain what the census showed but could not explain. Nothing here changes a pre-registered grade.

The sealed job `ccdi-diag-v1`:
1. downloads the census code unchanged from tag v0.5.5 (`get_code.py`, which logs SHA-256);
2. runs `test_diag.py` on made-up records;
3. fetches a second snapshot with the same `fetch_ccdi.py`;
4. runs `diag.py`, which:
   - re-runs the v1 analysis unchanged on the second snapshot (`snapshot2/`);
   - lists in-range `/subject` pages that returned no record list, with a scrubbed error message, and retries each once;
   - measures age differences between linked records per source pair and vital-status combination;
   - shows which side says Dead when linked records disagree;
   - breaks sex disagreements down by source pair and study namespace;
   - gives the character-class shapes of Participant Index links that do not resolve, and checks whether a looser match would resolve them (case-insensitive name, alternate identifier, alphanumeric-only);
   - lists served records with no sex or vital status, by study namespace.

Outputs are aggregates only. Identifiers are reduced to shapes such as `A{6}`.
