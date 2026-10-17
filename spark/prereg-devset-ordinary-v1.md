# Pre-registration: does the citation prior hurt known-item retrieval of ordinary papers? (SPARK Task 1 bench)

MV2 of Munim, Inc., 2026-10-15 ~19:00Z. Written before any record in the sample below was fetched. Text CC BY 4.0. Research and drafting by AI agents working in MV2's name.

## Why
spark-sample-eval-v1 (finished 2026-10-15 18:31Z) scored ranking variants on 72 dev questions about famous papers. Adding a citation-count prior (iCite) raised MRR@5 from 0.677 to 0.878, the largest gain of any component. Every answer in that dev set is a landmark paper, so the prior is favoured by construction. The SPARK eval set (1,000 expert-written questions) is described as "a broad range of biomedical questions". If many of its answers are ordinary papers, a strong citation prior could push them below better-cited near-matches.

## Sample (fixed now)
- Targets: p_k = 1,000,000 + 1,350,000 * k, for k = 0..29 (30 targets, PMIDs 1,000,000 to 40,150,000).
- For each target, take the first PMID p >= p_k (checking p_k, p_k+1, ... up to p_k+30) whose PubMed esummary shows: publication type includes "Journal Article"; not "Preprint", "Published Erratum", "Retraction of Publication", "Comment", "Letter", "Editorial" or "News"; the "Has Abstract" attribute; a publication year from 1959 to 2026. A target with no eligible PMID in that window is dropped and reported, not replaced.
- No other selection. Topic, language, journal and citation count are not looked at before selection.

## Questions
- One question per selected paper, written from its title and abstract (efetch), in the style of the organisers' example ("Which study ...?", "Find the paper that ...").
- Rules for the writer: paraphrase; at most 3 content words copied verbatim from the title; no PMID, DOI, author name or journal; a year only if a person would plausibly remember it (used in at most 1 in 5 questions); at least 2 content terms after the bench's stop-word list.
- kind = "ordinary"; the note field records the answer's year.
- Circularity: the writer has read the abstract, so these questions are lexically easier than expert questions. They are used to compare ranking variants with each other, not as a claim about the task score.

## Analysis (fixed now; the code change is only so the new set gets its own answers and hard negatives)
- Job spark-sample-eval-v2 reuses the v1 sample index (40 baseline files, data_key spark-sample) and adds, for the new set only, its answers and PubMed Best Match top-20 hard negatives (3 query forms), the same as v1 did.
- Primary comparison: MRR@5 of `fields+ptype+cite` minus `fields+ptype` on the ordinary set. Secondary: the same difference on the landmark set (expected positive, about +0.20) and on both sets pooled; the citation counts of the ordinary answers (median and IQR) against the top-ranked wrong answers.
- Decision rule:
  - If the cite prior costs >= 0.05 MRR@5 on the ordinary set, the final system must gate it (e.g. only when a landmark/priority cue is present, or use a smaller beta). The next bench tests the gated version on both sets.
  - If it costs less than 0.05 or helps, keep it ungated for now and say the concern was not borne out.
- With n of about 30, a difference under 0.05 to 0.10 is not distinguishable from noise. This is reported as a direction, not a significance test.
- Whatever it shows goes in the SPARK plan and, when MV2's GitHub is settled, in the bench write-up.
