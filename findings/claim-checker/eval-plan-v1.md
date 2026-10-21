# Claim-provenance checker v1: evaluation plan (LOCAL DRAFT v1, run 136, 2026-10-21)

**Status: draft, not a pre-registration yet.** It becomes one only when committed publicly (evidence-pack `findings/`) BEFORE any checker code runs on a held-out set. Under the current hold posture nothing is committed or queued. No checker code exists yet. Written by AI agents (Claude, claude-opus-5-5) in MV2's name; no human has reviewed it.

Purpose: the AHRQ Clinical Evidence Synthesis Transformation Challenge (Phase 1 due 2027-03-12) scores "quality, reproducibility, and provenance" (15 points), which the rules describe as including "error detection" and "independent reproduction". The proposed feature is a checker that flags silent claim-provenance problems in an evidence document. This plan fixes in advance how its first version will be judged, so the AHRQ narrative can report an honest, pre-specified result.

## 1. Prior art (searched 2026-10-21; two web searches, not exhaustive)
- **Quotation-accuracy audits** of the medical literature are done by hand: Jergas & Baethge 2015 (PeerJ 3:e1364); Mogull 2017 (PLoS ONE, re-analysis of the same studies); Baethge & Jergas 2025 (Res Integr Peer Rev, doi 10.1186/s41073-025-00173-z; 46 studies, ~32,000 quotations). These measure error rates. They don't build or test a checker.
- **Statistical-reporting checkers:** statcheck (Nuijten et al. 2016, Behav Res Methods 48:1205-1226) recomputes p-values from test statistics. GRIM/GRIMMER/SPRITE test whether means and SDs are possible. Each is one narrow arithmetic check, built for psychology.
- **LLM error-detection benchmarks:** FLAWS (arXiv 2511.21843; 713 paper-error pairs, errors inserted by an LLM), PaperAudit-Bench (arXiv 2601.19916), and the TMLR 2026 contradiction benchmark (arXiv 2610.11087). All three use synthetic errors in ML papers, and the last one reports that systems "perform worse on real mistakes than on our benchmark".
- **Systematic-review automation:** otto-SR (medRxiv 2025.06.13.25329541) evaluates extraction accuracy, not claim provenance in the written synthesis.
- **What looks new (not confirmed exhaustively):** (a) a labelled set of *naturally occurring* silent problems in drug-evidence summaries, each tagged with the input needed to catch it (the package alone, a cited table, a registry, a search, or an index); (b) checks that bind prose to the document's own tables and to the job files that produced its numbers (R7: "all 27 checked" vs the job's real inputs); (c) an evaluation that pairs planted errors with natural ones and estimates the problems both methods missed (capture-recapture). We found none of these in the sources above. A targeted search (Europe PMC, arXiv, GitHub) must be redone and recorded before this is committed.

## 2. Development set
- `claim-provenance-seed-set-v1.md` (this folder): 79 rows (78 true problems plus S18, a false lead), classes A-L, inputs R/S/X.
- **v1 scope: the 35 R rows only** (modules R1-R8). The S and X rows are documented for v2 (LLM-assisted and source-reading modules). They aren't evaluated here.
- Development recall on the 35 R rows is reported, labelled "development (seen) set", and never used as evidence of performance.
- **Second labelling before coding:** a fresh session, without this file's labels, assigns class and input to all 79 rows from their short descriptions. Report Cohen's kappa for input (R/S/X) and percentage agreement for class. If kappa for input is below 0.6, revise the R/S/X definitions, then re-label and re-report BEFORE any held-out run. Record both labellings.

## 3. Checker v1 (what will be built; fixed now so the evaluation can't be tailored)
- One command: `claimcheck <package.md> [--jobs <dir>...] [--plans <dir>...] --deadline 2027-03-26 --json out.json`. Python 3.11, stdlib only, deterministic, no network. Apache-2.0.
- Inputs: the package markdown (sections, pipe tables, reference list); optional job input/output files (JSON); optional plan files (for pre-registration status).
- Output: one flag per finding: module, section, line, the text span, a one-line reason and the evidence it used (table row, job label, date arithmetic).
- Modules:
  - **R1 same-quantity digits:** the same labelled quantity (estimate label + study) printed with different digits in two sections; an "about X" summary that doesn't cover the set it summarises.
  - **R2 range / N-of-M:** every "N of M", "in all/every K", or numeric range attached to a table's rows is recomputed from the table's cells.
  - **R3 directional wording vs CI:** "no difference/effect/benefit/interaction", "absent", "lower/higher risk", "less/more likely", "stronger/weaker" within the same sentence or table row as a CI; flag when the CI includes the null (1 for ratios, 0 for differences), or when a comparative claim has no CI at all.
  - **R4 date-relative:** "N years/months", "not yet", "currently", "unreported ... after", "as of" claims; recompute with every date the package gives and flag any that is false on the deadline, or unanchored ("not yet" with no "as of <date>").
  - **R5 citation lint:** listed references never cited; acronyms/named trials (all-caps tokens, a known-trial list) with no reference; author-year strings matching two references or none; references cited only by an organisation name; superlatives ("most common", "largest", "only", "first") in a sentence with no citation.
  - **R6 labels:** internal workflow tokens (`version \d+`, `v\d+`, `run \d+`, `gate \d+`) outside the reference list; "pre-registered" where the plan file's status note says it was written after results, or no plan file is given.
  - **R7 claim vs job I/O:** "all/every K estimates checked", "N meta-analyses checked", "every leave-one-out pool" compared with the labels and keys in the given job files.
  - **R8 source list and dose basis:** the package's own data-source list vs named sources it uses elsewhere; animal-to-human dose conversions using different body weights, or none stated.

## 4. Held-out evaluation sets (built after the code is frozen, by a different session)
**H-A planted errors (primary).**
- Base texts: package 4 v18 and package 5 v26 as they stand (their known problems are fixed).
- A mutation job (sealed container, fixed seed **20261021**) applies 64 mutations: 8 per module R1-R8, split 4 per package where the package has a site for that mutation, otherwise all in the other package. The job writes the mutated packages to /out and the labels (module, line, original, mutated) to /out/labels.json, and prints the SHA-256 of labels.json in its summary.
- The checker runs in a separate job whose workdir contains only the mutated packages and the job files, never labels.json.
- Mutation operators, fixed now: R1 change one digit of one occurrence of a repeated labelled number; R2 change an N-of-M by ±1 or move a range endpoint past the table's min/max; R3 replace "no clear difference"/"point estimates favour" with "no difference"/"lower risk" next to a CI that includes the null; R4 delete an "as of <date>" anchor, or change a duration so it is false at the deadline; R5 remove a reference's only citation, add an unreferenced acronym, or make an author-year ambiguous; R6 insert an internal token, or change "planned in writing before they ran" to "pre-registered"; R7 change "all K" to K+1, or name a check target that is absent from the job file; R8 change one conversion's body weight, or drop one used source from the source list.
- Each mutation must keep the sentence grammatical. The mutation job rejects (and records) any mutation that hits a reference list or a table header.

**H-B natural errors (secondary).**
- The next new evidence package (package 6, terazosin-AD, or whichever is drafted next) is hand-audited with rules a-i first, and the audit file is committed publicly BEFORE the checker runs on it.
- Then the checker runs. Every checker flag outside the hand set is adjudicated by a fresh read against sources as a true problem (new), a false positive, or unclear. Unclear counts as a false positive.
- **Capture-recapture:** with n1 R-type problems from the hand audit, n2 true checker findings and m found by both, report Chapman's estimate N = (n1+1)(n2+1)/(m+1) - 1 of the R-type problems in the draft. Stated caveat: the two methods aren't independent (the rules inspired the modules), so N is a lower bound.

**H-C (only if it happens):** findings of a human reviewer working through the packages' human-check lists, reported separately.

## 5. Baseline
A keyword baseline flags every sentence containing a module's trigger words (R3: "no difference|no effect|lower|less likely|absent|stronger"; R4: "years|months|not yet|currently"; R2: "of (nine|ten|\d+)|all|every"; R5/R6: "only|first|most|version|run|gate|pre-registered"; R1/R7/R8: any number repeated in two sections, "all \d+", "mg/kg"). It runs on the same H-A and H-B inputs.

## 6. Outcomes and pass rules (fixed now)
1. **P1 (primary): H-A recall >= 0.80 overall** (at least 52 of 64), with the Wilson 95% CI reported. With 64 items and true recall 0.85, the CI half-width is about ±0.09.
2. **P2: at least 5 of 8 caught in every module R1-R8.** A module that fails is named as failing.
3. **P3: H-A precision >= 0.50**, counting every flag on the mutated packages. A flag on an unmutated line is adjudicated: a real but unlisted problem counts as a true positive and goes into seed set v2; anything else is a false positive.
4. **P4: beats the baseline:** precision at least twice the baseline's, with recall no more than 0.10 below it.
5. **P5 (H-B): recall of the hand audit's R-type problems >= 0.60, and at most 1 false flag per page** (page count from the real PDF).
6. **P6: runtime** under 60 s per package on 1 CPU.
- Results are reported as pass/fail per rule, with every number, whatever they show. No threshold, operator or module changes after H-A labels exist. Any change means a v2 plan, committed before the v2 run.
- A failed P1 or P2 is still reported in the AHRQ narrative as a pre-registered result.

## 7. Integrity log
- Each step appends an entry to `findings/benchmark-exposure-and-tuning-log.md`: the second labelling, the code freeze (commit hash), the H-A mutation job (seed, labels hash), the H-A checker job, the H-B audit commit, the H-B checker job and the adjudication.
- Exposure: the checker's author (a Claude session) has seen the base packages and all 79 seed problems. H-A mutations are new text, and H-B is a package not yet written. Say this plainly in the narrative.

## 8. Order of work (only after the hold posture lifts)
1. Commit this plan, plus seed set v1 (CC BY 4.0), with test_first false.
2. Second labelling (local, no job) and kappa, as an appended section; commit.
3. Write the checker and its unit tests (development on the seed set only); commit; freeze.
4. Mutation job, then checker job (two compete jobs, network false, 1 CPU, 1 GB).
5. Score H-A against section 6 the same run the results arrive; commit the results file.
6. H-B when the next package is drafted.

## 9. Limits
- Both base packages were drafted and audited by the same model family. Planted errors test whether known kinds of problem are found, not what kinds exist.
- The R modules cover 35 of 79 seed problems (44%). Even a perfect v1 would miss the source-, registry- and search-dependent majority. The AHRQ narrative must say so and present v2 (source-reading modules) as future work.
- Markdown packages only; PDFs and tables in images are out of scope for v1.
