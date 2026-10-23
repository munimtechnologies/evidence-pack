# CCDI census: post-hoc diagnostics, stage 2

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written by AI agents (Claude) working in MV2's name; no human has reviewed it.

**Everything here is POST HOC.** This code was written on 2026-10-23, after the results of `../diagnostics-v1/` had been seen. It follows up three things that stage 1 found (see `../diagnostics-v1/results.md`).

The sealed job `ccdi-diag2-v1`:
1. downloads the census code (tag v0.5.5) and the stage-1 diagnostics (tag v0.5.6) unchanged, logging SHA-256 (`get_code.py`);
2. runs `test_diag2.py` on made-up records;
3. runs `diag2.py` on the second snapshot that stage 1 kept, without a new crawl. It:
   - tries three looser rules on every Participant Index link that did not resolve: the target's alternate identifiers (unique matches only), the part after the last underscore, and the same name in another source. For each rule it reports whether the resulting pairs are new, how the linked records agree (the census tally), and the effect on the over-count;
   - lists which metadata keys each source fills. For pairs with ccdi-ecDNA on one side, it compares ages for every numeric key whose name contains "age";
   - re-requests the PCDC page that failed in both snapshots (`/subject` page 35 at 100 per page) at 50, 25 and 10 per page, with page 34 as a control. It counts the PCDC records the snapshot lacks.

Outputs are aggregates only. Identifiers are reduced to shapes such as `A{6}`, and a USI is shown as `<USI>`. A link segment is printed as text only when it looks like a program name (three capital letters) or a COG protocol number, both of which are public study labels.
