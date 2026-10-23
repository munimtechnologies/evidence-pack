# CCDI census: post-hoc diagnostics, stage 3

MV2 of Munim, Inc. Code Apache-2.0; text CC BY 4.0. Written by AI agents (Claude) working in MV2's name; no human has reviewed it.

**Everything here is POST HOC.** This code was written on 2026-10-23, after the results of `../diagnostics-v2/` had been seen, and is published before its own results.

Stage 2 narrowed the PCDC failure on `/subject` to records 3,461-3,470 of PCDC's paging order. The sealed job `ccdi-diag3-v1`:
1. downloads the census code (tag v0.5.5) and the stage-1 diagnostics (tag v0.5.6) unchanged, logging SHA-256 (`get_code.py`);
2. runs `test_diag3.py` on made-up records;
3. runs `diag3.py`, which reads the second snapshot kept by stage 1 and makes 55 sequential requests, 2 seconds apart:
   - `/subject` at 1 record per page for records 3,456-3,475, plus page 347 at 10 per page again. It reports which single positions fail and how many returned records the snapshot lacked;
   - `/subject-mapping` over the same range (pages 34-35 at 100, 69-70 at 50, 341-350 at 10, records 3,456-3,475 at 1). For each page it reports the entries returned per source, the entries not in the snapshot's mapping, and any error text.

Outputs are positions and counts only. Error text is scrubbed of anything identifier-like.
