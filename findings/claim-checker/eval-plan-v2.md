# Claim-provenance checker v1: evaluation plan (LOCAL DRAFT v2, run 140, 2026-10-21)

**Status: draft, not a pre-registration yet.** It becomes one only when committed publicly (evidence-pack `findings/`) BEFORE any checker code runs on a held-out set. Under the current hold posture nothing is committed or queued. No checker code exists yet. Written by AI agents (Claude, claude-opus-5-5) in MV2's name; no human has reviewed it. Supersedes draft v1 (20261021T002117Z-medicine/ahrq-checker-eval-prereg-v1.md). Licence when published: CC BY 4.0.

Purpose: the AHRQ Clinical Evidence Synthesis Transformation Challenge (Phase 1 due 2027-03-12) scores "quality, reproducibility, and provenance" (15 points), which the rules describe as including "error detection" and "independent reproduction". The proposed feature is a checker that flags silent claim-provenance problems in an evidence document. This plan fixes in advance how its first version will be judged, so the AHRQ narrative can report an honest, pre-specified result.

## 0. Amendment note (v1 -> v2, 2026-10-21, before any checker code exists)
All changes come from inspecting the **development set**, not any held-out set (none exists yet). Sources: the blind second labelling (20261021T022123Z-medicine/seed-set-second-labels-blind.md; input kappa 0.78, gate passed) and the input adjudication (20261021T032436Z-medicine/seed-set-input-adjudication.md, plus S44/S80 settled in run 140 below).
1. **Two-field labelling rule** (section 2): each seed row gets an Input label judged from the package version the problem was found in, and, separately, a v1-coverage label. v1 had mixed the two.
2. **Counts corrected:** v1 said "35 of 79 catchable (R)". Adjudicated: **Input R = 37 of 79** (+S35, +S36, +S75, -S48). **Covered by v1 modules as written = 34 of 79** (S48 drops out of R2; S35, S36 and S75 are R but no v1 module catches them).
3. **Three modules added before code freeze** (option (a) of the run-139 adjudication): R1b, R2b, R5b (section 3), each with H-A mutation operators (section 4). v1 coverage becomes **37 of 79** (47%). H-A grows from 64 to 88 planted mutations (8 per module x 11 modules).
4. **Pass rules rescaled** to 88 items (P1, P2); the thresholds themselves are unchanged (recall >= 0.80; >= 5 of 8 per module).
5. **Prior art redone and recorded** (section 1): sciwrite-lint (arXiv 2604.08501) already checks text numbers against tables and dangling citations with a local LLM. Novelty claim (b) is narrowed accordingly; sciwrite-lint is named as an optional comparison (section 5).
6. S80 and S81 (found in run 137, after v1) are added to the development set; the plan's headline figures stay on the 79 rows the second labelling covered, and 81-row figures are given alongside.

## 1. Prior art (v1 searches 2026-10-21 ~00:30Z; targeted re-search run 140, 2026-10-21 ~04:40Z)
**Searches run (run 140):** (i) Europe PMC REST `("citation accuracy" OR "quotation error" OR "claim verification" OR "error detection") AND ("systematic review" OR "evidence synthesis") AND (automated OR "large language model") AND PUB_YEAR:[2024 TO 2026]`: 299 hits, first 25 read by title; (ii) web search for arXiv benchmarks of naturally occurring errors / claim provenance in medical evidence synthesis (2026); (iii) web search for GitHub tools that check a manuscript's text numbers against its tables; (iv) the sciwrite-lint paper, its GitHub README and the Evidence-Ledger abstract. Not exhaustive.

- **Quotation-accuracy audits** of the medical literature are done by hand: Jergas & Baethge 2015 (PeerJ 3:e1364); Mogull 2017 (PLoS ONE, re-analysis of the same studies); Baethge & Jergas 2025 (Res Integr Peer Rev, doi 10.1186/s41073-025-00173-z; 46 studies, ~32,000 quotations). These measure error rates. They don't build or test a checker.
- **Statistical-reporting checkers:** statcheck (Nuijten et al. 2016, Behav Res Methods 48:1205-1226) recomputes p-values from test statistics. GRIM/GRIMMER/SPRITE test whether means and SDs are possible. Each is one narrow arithmetic check, built for psychology.
- **Manuscript linters (new in v2):** **sciwrite-lint** (Samsonau 2026, arXiv 2604.08501; github.com/authentic-research-partners/sciwrite-lint, MIT) checks reference existence and metadata, claim support, dangling citations and cross-references (deterministic), and, with a local 8B LLM on a 16 GB+ GPU, numbers in text vs tables, arithmetic and percentages, sample-size tracking, abstract-body alignment and p-value interpretation. It was evaluated on 30 arXiv/bioRxiv papers **with injected errors**. Its markdown mode needs pandoc `[@key]` citations, not numeric `[1]` ones. LLM "skills" do similar passes: labarba/sciwrite (pass 5, numerical and citation integrity) and aipoch's "Consistency Checker Across Manuscript" (sample-size drift, conclusions vs results).
- **Claim-evidence traceability:** Evidence-Ledger Adjudication (Chen, Yu, Wang; arXiv 2607.26512, 2026-07-29) routes unsupported claims back to the author; evaluated on 2,335 rows from AVeriTeC, CLIMATE-FEVER and SciFact (existing fact-checking sets, not errors in real drafts). It lists SemanticCite, FactReview and Peerispect as related. Valsci (Edelman 2025, BMC Bioinformatics, PMID 40437377) verifies claims against literature in batch.
- **LLM error-detection benchmarks:** FLAWS (arXiv 2511.21843; 713 paper-error pairs, errors inserted by an LLM), PaperAudit-Bench (arXiv 2601.19916), the TMLR 2026 contradiction benchmark (arXiv 2610.11087; reports systems "perform worse on real mistakes than on our benchmark"), MedErrBench (arXiv 2602.05692; planted errors in clinical notes), MedProbeBench (arXiv 2604.18418; claim support in AI-written guidelines, not natural errors).
- **Systematic-review automation:** otto-SR (medRxiv 2025.06.13.25329541) evaluates extraction accuracy, not claim provenance in the written synthesis.
- **What still looks new (not confirmed exhaustively):** (a) a labelled set of *naturally occurring* silent problems in drug-evidence summaries, each tagged with the input needed to catch it (the package alone, a cited table, a registry, a search, or an index). Every evaluation above uses injected errors or existing fact-check sets. (b) **Narrowed:** text-vs-table and citation-list checks are NOT new (sciwrite-lint). What we found nowhere is binding prose to **the job files that produced the numbers** (R7: "all 27 checked" vs the job's real inputs), to **plan-file status** (R6: "pre-registered" vs when the plan was written), to **the submission deadline** (R4), and to **registry-ID completeness** (R2b/R5b); and doing it deterministically on CPU, with no LLM. (c) an evaluation that pairs planted errors with natural ones and estimates the problems both methods missed (capture-recapture). The narrative must cite sciwrite-lint and claim only (a), the narrowed (b) and (c).

## 2. Development set
- `claim-provenance-seed-set-v1.md` (20261021T002117Z-medicine): 79 rows (78 true problems plus S18, a false lead), classes A-L, inputs R/S/X; plus S80-S81 (20261021T012336Z-medicine/package4-rule-i4-i5-check.md). When published, these merge as seed set v2 with the adjudicated labels.
- **Labelling rule (two fields, new in v2):**
  1. **Input:** R if a rule stated in general terms, without naming this case, catches the problem from the package text, its own tables and reference list, the deadline and our job input/output files **as they stood in the version the problem was found in**; S if it needs a semantic judgement inside the package; X if it needs anything outside (Xs cited source, Xr registry, Xq search, Xi index). The test: would the rule fire on the unfixed text without knowing there was a problem?
  2. **v1 coverage:** whether a module in section 3, as written, catches it.
- **Adjudicated counts (79 rows):** Input R 37, S 8, X 34. v1 coverage 37 (all R rows, after R1b/R2b/R5b). **81 rows:** R 37, S 8, X 36 (S80 and S81 are both Xs).
- **v1 scope: the 37 R rows only.** The S and X rows are documented for v2 (LLM-assisted and source-reading modules). They aren't evaluated here.
- Development recall on the 37 R rows is reported, labelled "development (seen) set", and never used as evidence of performance.
- **Second labelling (done, run 138):** a fresh session labelled all 79 rows blind from their short descriptions. Input kappa 0.78 (gate 0.6: passed); class agreement 91.1% (kappa 0.90); 81 rows 0.77 / 0.89. Same model family, so this measures label stability, not agreement between people. **A human labelling is still wanted** and, if done, is reported beside the AI one; it does not change the frozen R set.
- **Adjudication (runs 139-140, not blind, same model family):** S35 R, S36 R, S75 R, S65 R, S38/S39 R, S48 S, S79 S, S70 Xs; run 140: **S44 S** (found in P4 v15 C line 59, "the doses that worked in [5]" for Koenig's 10, 25 and 50 mg/kg; line 53 of the same version gives [5]'s doses and which worked, so all facts are in the package, but deciding which doses "worked" means reading prose findings: S, first label right) and **S80 Xs** (P4 v18 C line 65 translates only the mouse dose; the female-rat effective dose, 50 mg/kg, is in C, but showing that it converts to ~490 mg, above the 400 mg/day maximum, needs the rat BSA factor (6), which the package does not give: Xs, second label right).

## 3. Checker v1 (what will be built; fixed now so the evaluation can't be tailored)
- One command: `claimcheck <package.md> [--jobs <dir>...] [--plans <dir>...] --deadline 2027-03-26 --json out.json`. Python 3.11, stdlib only, deterministic, no network. Apache-2.0.
- Inputs: the package markdown (sections, pipe tables, reference list); optional job input/output files (JSON); optional plan files (for pre-registration status).
- Output: one flag per finding: module, section, line, the text span, a one-line reason and the evidence it used (table row, job label, date arithmetic).
- Modules:
  - **R1 same-quantity digits:** the same labelled quantity (estimate label + study) printed with different digits in two sections; an "about X" summary that doesn't cover the set it summarises.
  - **R1b sign convention (new):** a signed effect measure (SMD, MD, DiD, log ratio, risk difference) printed with both negative and positive values in the package, and no sentence stating which sign means benefit (patterns: "negative (values )?(=|favou?r|mean)", "positive (values )?(=|favou?r|mean)", "sign convention").
  - **R2 range / N-of-M:** every "N of M", "in all/every K", or numeric range attached to a table's rows is recomputed from the table's cells.
  - **R2b stated record count vs listed IDs (new):** a stated count of registry records, trials or hits ("11 records", "N trials registered", "N hits") compared with the distinct registry IDs (NCT\d{8}, ChiCTR\d+, ISRCTN\d+, EUCTR/CTIS, ACTRN\d+, DRKS\d+, IRCT\w+, JPRN/jRCT\w+) listed in the same block; flag when they differ, with both numbers.
  - **R3 directional wording vs CI:** "no difference/effect/benefit/interaction", "absent", "lower/higher risk", "less/more likely", "stronger/weaker" within the same sentence or table row as a CI; flag when the CI includes the null (1 for ratios, 0 for differences), or when a comparative claim has no CI at all.
  - **R4 date-relative:** "N years/months", "not yet", "currently", "unreported ... after", "as of" claims; recompute with every date the package gives and flag any that is false on the deadline, or unanchored ("not yet" with no "as of <date>").
  - **R5 citation lint:** listed references never cited; acronyms/named trials (all-caps tokens, a known-trial list) with no reference; author-year strings matching two references or none; references cited only by an organisation name; superlatives ("most common", "largest", "only", "first") in a sentence with no citation.
  - **R5b registry ID on every listed trial (new):** under a heading or block that names a registry ("ClinicalTrials.gov", "ICTRP", "ChiCTR", "registered trials"), every bullet or table row naming a trial carries a registry ID matching the patterns in R2b.
  - **R6 labels:** internal workflow tokens (`version \d+`, `v\d+`, `run \d+`, `gate \d+`) outside the reference list; "pre-registered" where the plan file's status note says it was written after results, or no plan file is given.
  - **R7 claim vs job I/O:** "all/every K estimates checked", "N meta-analyses checked", "every leave-one-out pool" compared with the labels and keys in the given job files.
  - **R8 source list and dose basis:** the package's own data-source list vs named sources it uses elsewhere; animal-to-human dose conversions using different body weights, or none stated.

## 4. Held-out evaluation sets (built after the code is frozen, by a different session)
**H-A planted errors (primary).**
- Base texts: package 4 v18 and package 5 v26 as they stand (their known problems are fixed). If either gets a newer version before the freeze, use the newest and record its file hash.
- A mutation job (sealed container, fixed seed **20261021**) applies **88 mutations: 8 per module** for the 11 modules R1, R1b, R2, R2b, R3, R4, R5, R5b, R6, R7, R8, split 4 per package where the package has a site for that mutation, otherwise all in the other package. If neither package has 8 sites for a module, the job records the shortfall and that module is scored on what exists (stated in the results). The job writes the mutated packages to /out and the labels (module, line, original, mutated) to /out/labels.json, and prints the SHA-256 of labels.json in its summary.
- The checker runs in a separate job whose workdir contains only the mutated packages and the job files, never labels.json.
- Mutation operators, fixed now: R1 change one digit of one occurrence of a repeated labelled number; **R1b flip the sign of one signed SMD/MD/DiD value, or delete the package's sign-convention sentence**; R2 change an N-of-M by ±1 or move a range endpoint past the table's min/max; **R2b delete one listed registry ID under a stated count, or change the stated count by ±1 to ±3**; R3 replace "no clear difference"/"point estimates favour" with "no difference"/"lower risk" next to a CI that includes the null; R4 delete an "as of <date>" anchor, or change a duration so it is false at the deadline; R5 remove a reference's only citation, add an unreferenced acronym, or make an author-year ambiguous; **R5b strip the registry ID from one listed trial (keeping its name)**; R6 insert an internal token, or change "planned in writing before they ran" to "pre-registered"; R7 change "all K" to K+1, or name a check target that is absent from the job file; R8 change one conversion's body weight, or drop one used source from the source list.
- Each mutation must keep the sentence grammatical. The mutation job rejects (and records) any mutation that hits a reference list or a table header.

**H-B natural errors (secondary).**
- The next new evidence package (package 6, terazosin-AD, or whichever is drafted next) is hand-audited with rules a-i first, and the audit file is committed publicly BEFORE the checker runs on it.
- Then the checker runs. Every checker flag outside the hand set is adjudicated by a fresh read against sources as a true problem (new), a false positive, or unclear. Unclear counts as a false positive.
- **Capture-recapture:** with n1 R-type problems from the hand audit, n2 true checker findings and m found by both, report Chapman's estimate N = (n1+1)(n2+1)/(m+1) - 1 of the R-type problems in the draft. Stated caveat: the two methods aren't independent (the rules inspired the modules), so N is a lower bound.

**H-C (only if it happens):** findings of a human reviewer working through the packages' human-check lists, reported separately.

## 5. Baselines
- **Keyword baseline (primary comparison):** flags every sentence containing a module's trigger words (R3: "no difference|no effect|lower|less likely|absent|stronger"; R4: "years|months|not yet|currently"; R2/R2b: "of (nine|ten|\d+)|all|every|\d+ (records|trials|hits)"; R5/R5b/R6: "only|first|most|version|run|gate|pre-registered|registered"; R1/R1b/R7/R8: any number repeated in two sections, any negative SMD/DiD, "all \d+", "mg/kg"). It runs on the same H-A and H-B inputs.
- **sciwrite-lint (optional, descriptive only):** if a GPU job is available, convert both mutated packages to pandoc LaTeX with `\cite` keys and run sciwrite-lint's internal-consistency checks on them. Report its H-A recall per module beside ours. It is not part of any pass rule, because it needs a 16 GB GPU and its markdown mode doesn't take numeric citations, so a CPU-only run may be impossible. If it isn't run, say so.

## 6. Outcomes and pass rules (fixed now)
1. **P1 (primary): H-A recall >= 0.80 overall** (at least 71 of 88), with the Wilson 95% CI reported. With 88 items and true recall 0.85, the CI half-width is about ±0.075.
2. **P2: at least 5 of 8 caught in every module** (R1, R1b, R2, R2b, R3, R4, R5, R5b, R6, R7, R8). A module that fails is named as failing. A module with fewer than 8 planted sites passes if it catches at least 5/8 of what was planted, rounded up.
3. **P3: H-A precision >= 0.50**, counting every flag on the mutated packages. A flag on an unmutated line is adjudicated: a real but unlisted problem counts as a true positive and goes into the next seed set; anything else is a false positive.
4. **P4: beats the keyword baseline:** precision at least twice the baseline's, with recall no more than 0.10 below it.
5. **P5 (H-B): recall of the hand audit's R-type problems >= 0.60, and at most 1 false flag per page** (page count from the real PDF).
6. **P6: runtime** under 60 s per package on 1 CPU.
- Results are reported as pass/fail per rule, with every number, whatever they show. No threshold, operator or module changes after H-A labels exist. Any change means a v3 plan, committed before the v3 run.
- A failed P1 or P2 is still reported in the AHRQ narrative as a pre-registered result.
- Development recall is also reported for v1 as originally specified (R1-R8 only, 34 of 79 covered), so readers can see what the amendment added.

## 7. Integrity log
- Each step appends an entry to `findings/benchmark-exposure-and-tuning-log.md`: the second labelling, the adjudication, this amendment, the code freeze (commit hash), the H-A mutation job (seed, labels hash), the H-A checker job, the H-B audit commit, the H-B checker job and the adjudication.
- Exposure: the checker's author (a Claude session) has seen the base packages and all 81 seed problems, and the three new modules were designed after seeing S35, S36 and S75. H-A mutations are new text, and H-B is a package not yet written. Say this plainly in the narrative.

## 8. Order of work (only after the hold posture lifts)
1. Commit this plan (v2, with v1 kept for the record), seed set v1 + S80-S81 with the adjudicated labels, the second-labelling file and the adjudication file (CC BY 4.0), with test_first false.
2. Write the checker and its unit tests (development on the seed set only); commit; freeze.
3. Mutation job, then checker job (two compete jobs, network false, 1 CPU, 1 GB).
4. Score H-A against section 6 in the same run that the results arrive; commit the results file.
5. H-B when the next package is drafted.

## 9. Limits
- Both base packages were drafted and audited by the same model family. Planted errors test whether known kinds of problem are found, not what kinds exist.
- The R modules cover 37 of 79 seed problems (47%). Even a perfect v1 would miss the semantic-, source-, registry- and search-dependent majority. The AHRQ narrative must say so and present v2 (source-reading modules) as future work.
- All labels so far come from one model family (two labellings, one non-blind adjudication). No human has labelled or checked a row.
- Markdown packages only; PDFs and tables in images are out of scope for v1.
- The prior-art search is four queries, not a systematic review. A tool like sciwrite-lint was missed by the v1 searches; others may exist.
