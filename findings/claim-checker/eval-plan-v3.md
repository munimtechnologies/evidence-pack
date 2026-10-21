# Claim-provenance checker v1: evaluation plan (LOCAL DRAFT v3, run 142, 2026-10-21)

**Status: draft, not a pre-registration yet.** It becomes one only when committed publicly (evidence-pack `findings/`) BEFORE any checker code runs on a held-out set. Under the current hold posture nothing is committed or queued. No checker code exists yet. Written by AI agents (Claude, claude-opus-5-5) in MV2's name; no human has reviewed it. Supersedes draft v2 (20261021T042443Z-medicine/ahrq-checker-eval-prereg-v2.md), which superseded v1 (20261021T002117Z-medicine/ahrq-checker-eval-prereg-v1.md); both are kept for the record. Licence when published: CC BY 4.0.

Purpose: the AHRQ Clinical Evidence Synthesis Transformation Challenge (Phase 1 due 2027-03-12) scores "quality, reproducibility, and provenance" (15 points), which the rules describe as including "error detection" and "independent reproduction". The proposed feature is a checker that flags silent claim-provenance problems in an evidence document. This plan fixes in advance how its first version will be judged, so the AHRQ narrative can report an honest, pre-specified result.

## 0. Amendment notes

### 0.1 v1 -> v2 (2026-10-21, run 140, before any checker code exists)
All changes come from inspecting the **development set**, not any held-out set (none exists yet). Sources: the blind second labelling (20261021T022123Z-medicine/seed-set-second-labels-blind.md; input kappa 0.78, gate passed) and the input adjudication (20261021T032436Z-medicine/seed-set-input-adjudication.md, plus S44/S80 settled in run 140).
1. **Two-field labelling rule** (section 2): each seed row gets an Input label judged from the package version the problem was found in, and, separately, a v1-coverage label. v1 had mixed the two.
2. **Counts corrected:** v1 said "35 of 79 catchable (R)". Adjudicated: **Input R = 37 of 79** (+S35, +S36, +S75, -S48). **Covered by v1 modules as written = 34 of 79** (S48 drops out of R2; S35, S36 and S75 are R but no v1 module catches them).
3. **Three modules added before code freeze:** R1b, R2b, R5b (section 3), each with H-A mutation operators (section 4). Coverage becomes 37 of 79 (47%). H-A grows from 64 to 88 planted mutations (8 per module x 11 modules).
4. **Pass rules rescaled** to 88 items (P1, P2); the thresholds themselves are unchanged (recall >= 0.80; >= 5 of 8 per module).
5. **Prior art redone and recorded** (section 1): sciwrite-lint (arXiv 2604.08501). Novelty claim (b) narrowed; sciwrite-lint named as an optional comparison (section 5).
6. S80 and S81 (found in run 137) added to the development set; headline figures stay on the 79 rows the second labelling covered.

### 0.2 v2 -> v3 (2026-10-21, runs 141-142, before any checker code exists)
All changes again come from the development set: a by-hand run of R2b and R5b on the registry blocks of the two base packages (run 141: 20261021T060514Z-medicine/package5-r2b-r5b-check.md; run 142: section 0.3 below). No held-out set exists.
1. **R2b registry scoping** (run 141): when the count sentence names a registry, only that registry's ID pattern is counted; out-of-scope IDs are reported separately. Reason: in package 5 v26 E.2, "11 records" (ClinicalTrials.gov) sits in a block that also holds ChiCTR2500107918, so v2's R2b would report 10 vs 11 (gap 1) when the true gap is 2, and 12 vs 11 (a false flag) once the gap is fixed.
2. **R2b sentence scope and registry gate** (run 142, new): the run-141 fix kept "the block runs from the count sentence to the next heading". That is still wrong. On the clean texts it would compare "Three other hits" (package 4 v18 E.5, 3 IDs) with 5 IDs and "Two other placebo-controlled trials" (package 5 E.2, 2 IDs) with 7 (v26) or 9 (v27) IDs: at least two false flags on unmutated lines in every H-A run. Counts in sentences about PubMed or Europe PMC ("35 records", "20 hits", "0 records") would also be compared with registry IDs unless a gate says which counts are registry counts. Section 3 now defines both.
3. **R5b clause level** (run 141), **with item rules** (run 142): v2's bullet-level R5b misses a trial described in a clause inside a bullet that carries other IDs (the S82 case). A naive clause split (on every ";", comma and "and") would false-flag descriptive phrases in package 4 v18 E.5 ("a pharmacokinetic and safety study, not an efficacy trial"; "larger efficacy trials"). Section 3 now says which clauses are items.
4. **H-A operator added for R5b:** strip the ID from one enumerated clause in a sentence or bullet that keeps other IDs.
5. **H-A base texts** must have every Input-R seed problem fixed (section 4). Otherwise S82 sits on an unmutated line of package 5 v26 and the corrected R2b flags it in every H-A run. Base texts are therefore package 4 v19 (with the pending i4 edit) and package 5 v27 (with the S82 ID edit), or newer, with file hashes recorded.
6. **Seed row S82** added (development only): package 5 v26 E.2, two of the 11 ClinicalTrials.gov search records described without IDs ("a topical iontophoresis trial", "an ultrasound-therapy study"; they are NCT07395895 and NCT07738692). Class J; Input R; v1 coverage: v3 R2b and v3 R5b. v2's R2b as written also fires on it, but with the wrong gap (1 instead of 2), and v2's R5b misses it. Headline figures stay on the 79 rows; 82-row figures are given alongside.
7. **Pass rules unchanged.** Still 11 modules x 8 = 88 planted mutations; P1 needs at least 71 of 88 (0.807); with true recall 0.85 the Wilson 95% CI half-width is about +/-0.075 (1.96 x sqrt(0.85 x 0.15 / 88) = 0.0746). P2 is still at least 5 of 8 per module.

### 0.3 Run-142 worked example (by hand, both base packages; no code)
- Count-pattern hits (`(\d+|one..twelve)` + up to 3 words + `records|trials|hits|studies`, case-insensitive): **23 in package 5 v26, 14 in package 4 v18.**
- With the v3 gate (section 3, R2b), only these pass into R2b; all others are literature counts, PubMed/Europe PMC search counts, or a heading ("E.5 Registered clinical studies"):
  - P5 line 163 "11 records" (names ClinicalTrials.gov; "accounted for below"): 9 in-scope NCT IDs in the scope, 1 out-of-scope (ChiCTR2500107918). **Flag, gap 2 (true: S82).**
  - P5 line 172 "Two other placebo-controlled trials ...: PIKASO (NCT06096259 ...) and NCT06328426": 2 vs 2, no flag.
  - P5 line 173 "The remaining three records are ...": 1 ID (NCT04767841) vs 3. **Flag, gap 2 (true: S82).**
  - P5 reference 39 "(11 records)" (names ClinicalTrials.gov; 9 NCT IDs in the same entry). **Flag, gap 2 (true: S82; the pending ref-39 edit fixes it).**
  - P4 line 160 "Three other hits have no drinking outcome: NCT05014087 ...; NCT00188045 ...; NCT00226109 ...": 3 vs 3, no flag.
  - P4 line 160 "each gave the same 2 trials, NCT06004830 and NCT05807139" (names ICTRP: all patterns): 2 vs 2, no flag.
- R5b (v3 items): P5 line 173 gives 3 items, 2 without an ID (**2 flags, true: S82**). P5 line 173 "Other registered trials:" label gives 4 items, all with IDs; P5 line 172 ("...: PIKASO (NCT06096259 ...) and NCT06328426") gives 2, both with IDs; P5 line 163 gives no items (the pieces after the count start with "the" or have no design noun). P4 line 160 "Three other hits ...:" gives 3 items, all with IDs; "the same 2 trials, NCT06004830 and NCT05807139" has no "are"/":" list, so only R2b checks it. No other enumerated registry items in either package. Negated or definite mentions ("no other AUD treatment trial", "no randomized efficacy trial", "the study", "an efficacy trial" inside an apposition with no count or label) are not items.
- **Expected v3 result on the H-A base texts (P4 v19, P5 v27): 0 R2b and 0 R5b flags.** This is a prediction made before code; if the frozen code flags either base text on a registry line, that is a false positive under P3 and is reported as such.
- Limit: this is one hand pass by the same model family that wrote the rule; regex hits were checked by line, not every sentence of both packages was re-read.

## 1. Prior art (v1 searches 2026-10-21 ~00:30Z; targeted re-search run 140, 2026-10-21 ~04:40Z; not redone for v3)
**Searches run (run 140):** (i) Europe PMC REST `("citation accuracy" OR "quotation error" OR "claim verification" OR "error detection") AND ("systematic review" OR "evidence synthesis") AND (automated OR "large language model") AND PUB_YEAR:[2024 TO 2026]`: 299 hits, first 25 read by title; (ii) web search for arXiv benchmarks of naturally occurring errors / claim provenance in medical evidence synthesis (2026); (iii) web search for GitHub tools that check a manuscript's text numbers against its tables; (iv) the sciwrite-lint paper, its GitHub README and the Evidence-Ledger abstract. Not exhaustive. Redo before the public commit if more than ~4 weeks have passed.

- **Quotation-accuracy audits** of the medical literature are done by hand: Jergas & Baethge 2015 (PeerJ 3:e1364); Mogull 2017 (PLoS ONE, re-analysis of the same studies); Baethge & Jergas 2025 (Res Integr Peer Rev, doi 10.1186/s41073-025-00173-z; 46 studies, ~32,000 quotations). These measure error rates. They don't build or test a checker.
- **Statistical-reporting checkers:** statcheck (Nuijten et al. 2016, Behav Res Methods 48:1205-1226) recomputes p-values from test statistics. GRIM/GRIMMER/SPRITE test whether means and SDs are possible. Each is one narrow arithmetic check, built for psychology.
- **Manuscript linters:** **sciwrite-lint** (Samsonau 2026, arXiv 2604.08501; github.com/authentic-research-partners/sciwrite-lint, MIT) checks reference existence and metadata, claim support, dangling citations and cross-references (deterministic), and, with a local 8B LLM on a 16 GB+ GPU, numbers in text vs tables, arithmetic and percentages, sample-size tracking, abstract-body alignment and p-value interpretation. It was evaluated on 30 arXiv/bioRxiv papers **with injected errors**. Its markdown mode needs pandoc `[@key]` citations, not numeric `[1]` ones. LLM "skills" do similar passes: labarba/sciwrite (pass 5, numerical and citation integrity) and aipoch's "Consistency Checker Across Manuscript" (sample-size drift, conclusions vs results).
- **Claim-evidence traceability:** Evidence-Ledger Adjudication (Chen, Yu, Wang; arXiv 2607.26512, 2026-07-29) routes unsupported claims back to the author; evaluated on 2,335 rows from AVeriTeC, CLIMATE-FEVER and SciFact (existing fact-checking sets, not errors in real drafts). It lists SemanticCite, FactReview and Peerispect as related. Valsci (Edelman 2025, BMC Bioinformatics, PMID 40437377) verifies claims against literature in batch.
- **LLM error-detection benchmarks:** FLAWS (arXiv 2511.21843; 713 paper-error pairs, errors inserted by an LLM), PaperAudit-Bench (arXiv 2601.19916), the TMLR 2026 contradiction benchmark (arXiv 2610.11087; reports systems "perform worse on real mistakes than on our benchmark"), MedErrBench (arXiv 2602.05692; planted errors in clinical notes), MedProbeBench (arXiv 2604.18418; claim support in AI-written guidelines, not natural errors).
- **Systematic-review automation:** otto-SR (medRxiv 2025.06.13.25329541) evaluates extraction accuracy, not claim provenance in the written synthesis.
- **What still looks new (not confirmed exhaustively):** (a) a labelled set of *naturally occurring* silent problems in drug-evidence summaries, each tagged with the input needed to catch it (the package alone, a cited table, a registry, a search, or an index). Every evaluation above uses injected errors or existing fact-check sets. (b) **Narrowed:** text-vs-table and citation-list checks are NOT new (sciwrite-lint). What we found nowhere is binding prose to **the job files that produced the numbers** (R7), to **plan-file status** (R6), to **the submission deadline** (R4), and to **registry-ID completeness** (R2b/R5b); and doing it deterministically on CPU, with no LLM. (c) an evaluation that pairs planted errors with natural ones and estimates the problems both methods missed (capture-recapture). The narrative must cite sciwrite-lint and claim only (a), the narrowed (b) and (c).

## 2. Development set
- `claim-provenance-seed-set-v1.md` (20261021T002117Z-medicine): 79 rows (78 true problems plus S18, a false lead), classes A-L, inputs R/S/X; plus S80-S81 (20261021T012336Z-medicine/package4-rule-i4-i5-check.md) and S82 (section 0.2 item 6). When published, these merge as seed set v2 with the adjudicated labels.
- **Labelling rule (two fields):**
  1. **Input:** R if a rule stated in general terms, without naming this case, catches the problem from the package text, its own tables and reference list, the deadline and our job input/output files **as they stood in the version the problem was found in**; S if it needs a semantic judgement inside the package; X if it needs anything outside (Xs cited source, Xr registry, Xq search, Xi index). The test: would the rule fire on the unfixed text without knowing there was a problem?
  2. **v1 coverage:** whether a module in section 3, as written, catches it.
- **Adjudicated counts (79 rows, headline):** Input R 37, S 8, X 34. v1 coverage 37 (all R rows). **81 rows:** R 37, S 8, X 36. **82 rows (with S82):** R 38, S 8, X 36; v1 coverage 38.
- **v1 scope: the R rows only.** The S and X rows are documented for v2 (LLM-assisted and source-reading modules). They aren't evaluated here.
- Development recall on the R rows is reported, labelled "development (seen) set", and never used as evidence of performance.
- **Second labelling (done, run 138):** a fresh session labelled all 79 rows blind from their short descriptions. Input kappa 0.78 (gate 0.6: passed); class agreement 91.1% (kappa 0.90); 81 rows 0.77 / 0.89. Same model family, so this measures label stability, not agreement between people. S82 was labelled once, not blind. **A human labelling is still wanted** and, if done, is reported beside the AI one; it does not change the frozen R set.
- **Adjudication (runs 139-140, not blind, same model family):** S35 R, S36 R, S75 R, S65 R, S38/S39 R, S48 S, S79 S, S70 Xs; S44 S; S80 Xs (reasons in v2 section 2).

## 3. Checker v1 (what will be built; fixed now so the evaluation can't be tailored)
- One command: `claimcheck <package.md> [--jobs <dir>...] [--plans <dir>...] --deadline 2027-03-26 --json out.json`. Python 3.11, stdlib only, deterministic, no network. Apache-2.0.
- Inputs: the package markdown (sections, pipe tables, reference list); optional job input/output files (JSON); optional plan files (for pre-registration status).
- Output: one flag per finding: module, section, line, the text span, a one-line reason and the evidence it used (table row, job label, date arithmetic).
- Shared definitions (v3):
  - **Registry ID patterns:** NCT\d{8}, ChiCTR\d+, ISRCTN\d+, EUCTR[\d-]+ / CTIS \d{4}-\d+-\d+-\d+, ACTRN\d+, DRKS\d+, IRCT\w+, JPRN-\w+ / jRCT\w+.
  - **Registry names** (each mapped to its pattern): ClinicalTrials.gov -> NCT; ChiCTR; ISRCTN; ANZCTR -> ACTRN; EU CTR / CTIS -> EUCTR/CTIS; DRKS; IRCT; jRCT / JPRN. "ICTRP", "WHO", "registry" or "registered" without one of these names means all patterns.
  - **Sentence:** split on ". " (and on line ends) where the next character is upper-case, "*" or "(", never inside parentheses or quotation marks. Headings and table header rows are not sentences.
  - **Count phrase:** a number (digits or one..twenty) followed within 3 words by records|trials|hits|studies|registrations.
- Modules:
  - **R1 same-quantity digits:** the same labelled quantity (estimate label + study) printed with different digits in two sections; an "about X" summary that doesn't cover the set it summarises.
  - **R1b sign convention:** a signed effect measure (SMD, MD, DiD, log ratio, risk difference) printed with both negative and positive values in the package, and no sentence stating which sign means benefit (patterns: "negative (values )?(=|favou?r|mean)", "positive (values )?(=|favou?r|mean)", "sign convention").
  - **R2 range / N-of-M:** every "N of M", "in all/every K", or numeric range attached to a table's rows is recomputed from the table's cells.
  - **R2b stated record count vs listed IDs (v3 definition):**
    - *Gate:* a sentence with a count phrase is checked only if it names a registry (list above) or contains at least one registry ID. Sentences that name only a bibliographic database (PubMed, Europe PMC, Embase, Crossref) and contain no registry ID are skipped. Reference-list entries are checked by the same rule.
    - *Scope:* the IDs in the count sentence itself; plus, if the sentence says "below", "as follows", "listed", "accounted for" or ends with ":", the lines after it up to the next heading or the next unindented paragraph that is not a bullet.
    - *Registry:* if the sentence names exactly one registry, only that registry's pattern is in scope; otherwise all patterns.
    - *Flag* when the stated count differs from the distinct in-scope IDs. Report the stated count, the in-scope distinct IDs, and the out-of-scope IDs separately. A count phrase preceded by "no", "none", "0" or "zero" is never flagged.
  - **R3 directional wording vs CI:** "no difference/effect/benefit/interaction", "absent", "lower/higher risk", "less/more likely", "stronger/weaker" within the same sentence or table row as a CI; flag when the CI includes the null (1 for ratios, 0 for differences), or when a comparative claim has no CI at all.
  - **R4 date-relative:** "N years/months", "not yet", "currently", "unreported ... after", "as of" claims; recompute with every date the package gives and flag any that is false on the deadline, or unanchored ("not yet" with no "as of <date>").
  - **R5 citation lint:** listed references never cited; acronyms/named trials (all-caps tokens, a known-trial list) with no reference; author-year strings matching two references or none; references cited only by an organisation name; superlatives ("most common", "largest", "only", "first") in a sentence with no citation.
  - **R5b registry ID on every enumerated trial (v3 definition):**
    - *Where:* (i) a sentence that passes the R2b gate and contains a count phrase; (ii) a bullet whose bold lead ends with ":" and contains "trial", "studies" or "records", under a heading or block that passes the R2b gate (e.g. "**Other registered trials:**").
    - *Items:* the text after the count phrase's verb ("are", ":") or after the bold lead, split at top level (never inside parentheses or quotation marks) on ";" , "," and a final " and ". Each piece with a trial-design noun (trial, study, record, registration) or a registry ID is an item.
    - *Not items:* pieces that begin with "the", "this", "that", "its" or a possessive (references to a trial already named), and pieces containing "no", "not", "none" or "without" before the noun.
    - *Flag* every item without a registry ID, with the sentence's count if it has one.
  - **R6 labels:** internal workflow tokens (`version \d+`, `v\d+`, `run \d+`, `gate \d+`) outside the reference list; "pre-registered" where the plan file's status note says it was written after results, or no plan file is given.
  - **R7 claim vs job I/O:** "all/every K estimates checked", "N meta-analyses checked", "every leave-one-out pool" compared with the labels and keys in the given job files.
  - **R8 source list and dose basis:** the package's own data-source list vs named sources it uses elsewhere; animal-to-human dose conversions using different body weights, or none stated.

## 4. Held-out evaluation sets (built after the code is frozen, by a different session)
**H-A planted errors (primary).**
- **Base texts (v3):** the newest versions of package 4 and package 5 in which **every Input-R seed problem is fixed**: at least package 4 v19 (with the run-137 i4 edit) and package 5 v27 (with the S82 ID edit: NCT07395895 and NCT07738692 added to E.2 and reference 39). Record each file's SHA-256 in the integrity log before the mutation job runs. A checker flag on an unmutated line of a base text is scored under P3 like any other.
- A mutation job (sealed container, fixed seed **20261021**) applies **88 mutations: 8 per module** for the 11 modules R1, R1b, R2, R2b, R3, R4, R5, R5b, R6, R7, R8, split 4 per package where the package has a site for that mutation, otherwise all in the other package. If neither package has 8 sites for a module, the job records the shortfall and that module is scored on what exists (stated in the results). The job writes the mutated packages to /out and the labels (module, line, original, mutated) to /out/labels.json, and prints the SHA-256 of labels.json in its summary.
- The checker runs in a separate job whose workdir contains only the mutated packages and the job files, never labels.json.
- Mutation operators, fixed now: R1 change one digit of one occurrence of a repeated labelled number; R1b flip the sign of one signed SMD/MD/DiD value, or delete the package's sign-convention sentence; R2 change an N-of-M by +/-1 or move a range endpoint past the table's min/max; R2b delete one in-scope registry ID under a gated count, or change a gated stated count by +/-1 to +/-3; R3 replace "no clear difference"/"point estimates favour" with "no difference"/"lower risk" next to a CI that includes the null; R4 delete an "as of <date>" anchor, or change a duration so it is false at the deadline; R5 remove a reference's only citation, add an unreferenced acronym, or make an author-year ambiguous; R5b strip the registry ID from one listed trial (keeping its name), **or (v3) strip the ID from one enumerated clause in a sentence or bullet that keeps other IDs**; R6 insert an internal token, or change "planned in writing before they ran" to "pre-registered"; R7 change "all K" to K+1, or name a check target that is absent from the job file; R8 change one conversion's body weight, or drop one used source from the source list.
- Each mutation must keep the sentence grammatical. The mutation job rejects (and records) any mutation that hits a reference list or a table header. (R2b still *checks* reference entries; it just isn't *mutated* there.)

**H-B natural errors (secondary).**
- The next new evidence package (package 6, terazosin-AD, or whichever is drafted next) is hand-audited with rules a-i first, and the audit file is committed publicly BEFORE the checker runs on it.
- Then the checker runs. Every checker flag outside the hand set is adjudicated by a fresh read against sources as a true problem (new), a false positive, or unclear. Unclear counts as a false positive.
- **Capture-recapture:** with n1 R-type problems from the hand audit, n2 true checker findings and m found by both, report Chapman's estimate N = (n1+1)(n2+1)/(m+1) - 1 of the R-type problems in the draft. Stated caveat: the two methods aren't independent (the rules inspired the modules), so N is a lower bound.

**H-C (only if it happens):** findings of a human reviewer working through the packages' human-check lists, reported separately.

## 5. Baselines
- **Keyword baseline (primary comparison):** flags every sentence containing a module's trigger words (R3: "no difference|no effect|lower|less likely|absent|stronger"; R4: "years|months|not yet|currently"; R2/R2b: "of (nine|ten|\d+)|all|every|\d+ (records|trials|hits)"; R5/R5b/R6: "only|first|most|version|run|gate|pre-registered|registered"; R1/R1b/R7/R8: any number repeated in two sections, any negative SMD/DiD, "all \d+", "mg/kg"). It runs on the same H-A and H-B inputs. Unchanged in v3.
- **sciwrite-lint (optional, descriptive only):** if a GPU job is available, convert both mutated packages to pandoc LaTeX with `\cite` keys and run sciwrite-lint's internal-consistency checks on them. Report its H-A recall per module beside ours. It is not part of any pass rule. If it isn't run, say so.

## 6. Outcomes and pass rules (fixed; unchanged in v3)
1. **P1 (primary): H-A recall >= 0.80 overall** (at least 71 of 88), with the Wilson 95% CI reported. With 88 items and true recall 0.85, the CI half-width is about +/-0.075.
2. **P2: at least 5 of 8 caught in every module** (R1, R1b, R2, R2b, R3, R4, R5, R5b, R6, R7, R8). A module that fails is named as failing. A module with fewer than 8 planted sites passes if it catches at least 5/8 of what was planted, rounded up.
3. **P3: H-A precision >= 0.50**, counting every flag on the mutated packages. A flag on an unmutated line is adjudicated: a real but unlisted problem counts as a true positive and goes into the next seed set; anything else is a false positive.
4. **P4: beats the keyword baseline:** precision at least twice the baseline's, with recall no more than 0.10 below it.
5. **P5 (H-B): recall of the hand audit's R-type problems >= 0.60, and at most 1 false flag per page** (page count from the real PDF).
6. **P6: runtime** under 60 s per package on 1 CPU.
- Results are reported as pass/fail per rule, with every number, whatever they show. No threshold, operator or module changes after H-A labels exist. Any change means a v4 plan, committed before the v4 run.
- A failed P1 or P2 is still reported in the AHRQ narrative as a pre-registered result.
- Development recall is also reported for v1 as originally specified (R1-R8 only, 34 of 79 covered) and for the v2 definitions of R2b/R5b, so readers can see what each amendment added.
- **Secondary, descriptive (v3):** the run-142 prediction of 0 R2b and 0 R5b flags on the unmutated base texts (section 0.3) is reported as held or not.

## 7. Integrity log
- Each step appends an entry to `findings/benchmark-exposure-and-tuning-log.md`: the second labelling, the adjudication, the v2 amendment, the v3 amendment (with the run-141 and run-142 hand passes), the base-text hashes, the code freeze (commit hash), the H-A mutation job (seed, labels hash), the H-A checker job, the H-B audit commit, the H-B checker job and the adjudication.
- Exposure: the checker's author (a Claude session) has seen the base packages and all 82 seed problems; R1b, R2b and R5b were designed after seeing S35, S36, S75 and S82, and the v3 R2b/R5b definitions were tuned by hand against the registry blocks of the two base packages. H-A mutations are new text, and H-B is a package not yet written. Say this plainly in the narrative: the base packages are not a clean test of false-positive behaviour for R2b/R5b.

## 8. Order of work (only after the hold posture lifts)
1. Commit this plan (v3, with v1 and v2 kept for the record), seed set v2 (v1 + S80-S82 with the adjudicated labels), the second-labelling file and the adjudication file (CC BY 4.0), with test_first false.
2. Make package 4 v19 and package 5 v27 (pending edits plus trims); record hashes.
3. Write the checker and its unit tests (development on the seed set only); commit; freeze.
4. Mutation job, then checker job (two compete jobs, network false, 1 CPU, 1 GB).
5. Score H-A against section 6 in the same run that the results arrive; commit the results file.
6. H-B when the next package is drafted.

## 9. Limits
- Both base packages were drafted and audited by the same model family. Planted errors test whether known kinds of problem are found, not what kinds exist.
- The R modules cover 37 of 79 seed problems (47%; 38 of 82). Even a perfect v1 would miss the semantic-, source-, registry- and search-dependent majority. The AHRQ narrative must say so and present v2 (source-reading modules) as future work.
- All labels so far come from one model family (two labellings, one non-blind adjudication; S82 labelled once). No human has labelled or checked a row.
- Markdown packages only; PDFs and tables in images are out of scope for v1.
- The prior-art search is four queries, not a systematic review. Others like sciwrite-lint may exist.
- R2b and R5b are now defined in more detail than the other modules, because they were the ones worked by hand. The other modules may have similar scoping defects that only code will reveal; the plan forbids fixing them after H-A labels exist, so any found then are reported as failures.
