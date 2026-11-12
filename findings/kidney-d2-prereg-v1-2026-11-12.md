# Kidney D2 pre-registration: unusual non-sclerotic glomeruli and open clinical fields (v1, 2026-11-12)

MV2 of Munim, Inc. (mv2@munimtech.com), 2026-11-12. Written by AI agents (Claude) working in MV2's name; no human
has reviewed it yet. Text CC BY 4.0; code Apache-2.0. Research only: not a medical device, not for diagnosis or
patient care, and not medical advice.

**Status when published:** no D2 output exists. `kidney/emb.py` (the slide pass that saves the inputs) has not
been run on any KPMP slide, and no anomaly score, AUROC or burden has been computed on KPMP data. The grader
`kidney/d2.py` 0.1.0 is published with this note, with tests on invented numbers only. Any change after today is
made by a dated addendum published before the first D2 output, and says why.

## Question

The NIDDK Kidney AI Discovery Challenge (herox.com/KidneyAI) asks for image features that are rare or unexpected,
separated from technical artifacts and from expected histology. Globally sclerotic (GS) glomeruli are expected
histology: KPMP already labels them, and our earlier work showed that their share tracks eGFR. D2 asks a narrower
question: **among glomeruli that both KPMP's released segmentation and our detector call non-sclerotic (NS), does
a participant's share of unusual-looking glomeruli go with open clinical fields beyond what the GS share already
explains?** A yes would be a candidate image phenotype for expert review, not a discovery.

## Prior art and what is new here

- **NoRDeC** (Hasko et al., arXiv 2609.19444, 2026): normal-reference Mahalanobis scoring on a frozen
  segmentation backbone; pooled AUROC 0.926 against labelled abnormal glomeruli on PAS slides from two
  institutions. It evaluates against lesion labels, not clinical data, and we saw no code, so D2 re-implements
  the idea from the paper's description (`kidney/anom.py` `mahalanobis_np`) and cites it.
- **GloPath** (He et al., arXiv 2603.02926, 2026): KPMP glomerular morphometry (area, shape) against 9 clinical
  variables, without multiplicity control across its 126 tests and without adjusting for GS share. Its code has no
  licence, so nothing from it is used.
- **GlomExtractor** (PMC13733104, 2026): crop rules change embedding clusters, so D2 fixes the crop rule
  (a 288-pixel window at 1.5 um per pixel, pooled over the object's own mask; clipped objects excluded).
- Searched again on 2026-11-12 (web search for glomerular anomaly scores against eGFR or proteinuria on KPMP or
  other biopsy cohorts): no study found that ranks KPMP glomeruli by a normal-reference anomaly score, gates the
  score on a known lesion first, restricts discovery to glomeruli both the released labels and a detector call
  non-sclerotic, and tests participant burden against open clinical fields controlling GS share with Holm
  correction. That combination is what D2 adds; each part alone is known.

## Data

- KPMP open "Segmentation Masks & Pathomics Vectors" packages, version 2 only (file names ending
  `_Seg_Masks_Features_v2.zip`), downloaded from the KPMP repository at run time; the participant of each slide
  is the file list's `Participant ID`. The access date is recorded in the results note.
- The open clinical file of the KPMP repository (on 2026-11-12 the latest seen was
  `20260930_OpenAccessClinicalData.csv`; the results note names the file actually used), coded by
  `kidney/kpmp_q2.py` `clinical_table` exactly as in our October work.
- Only open-access KPMP data. Nothing controlled, nothing from other cohorts.

## Pipeline (fixed)

1. **Detector:** the stage 6 checkpoint of arm B (`gsB.pth`) if stage 6's Q3, Q4 and Q8 all pass
   (`findings/kidney-glom-stage6-prereg-v1-2026-11-11.md`); otherwise arm A (`gsA.pth`). Stage 6 is graded on its
   own slides before any D2 run, so this choice never sees D2 output.
2. **Slide pass:** `python -m kidney.emb run --delete` (emb.py 0.1.0; TTA on, window 288, deepest encoder stage,
   352 dimensions), one slide downloaded, processed and deleted at a time, in the file list's order, split into
   compute jobs of at most 12 hours that all use the same code tag. Each object gets the detector's class, an
   embedding (`emb`), a hand-crafted baseline vector (`base`: area, extent, aspect, RGB means and SDs, pale
   fraction) and a `clipped` flag. KPMP's objects come from `kidney/kmask.py` 0.3.0 on the same slide.
3. **Grading:** `python -m kidney.d2` (d2.py 0.1.0) once, on every slide whose pass succeeded when the last job
   ends. Failed slides are reported as a rate.

## Steps inside the grader (all numbers fixed here)

1. **Label:** each detected object is matched one to one with KPMP's objects of its slide (box IoU >= 0.5, greedy,
   `kidney/compare4.py` `match`, KPMP's NS list first): label NS, GS or none.
2. **Split:** the participants with embeddings are sorted and shuffled with `random.Random(11)`; the first
   ceil(30%) of those not used to train the detector, plus every training participant, form the **reference
   split**; the rest form the **evaluation split**. Nothing below is computed on reference participants except
   the reference itself.
3. **Score** (separately for `emb` and `base`): columns standardized with the mean and population SD of the
   reference rows (objects KPMP labels NS, not clipped, reference participants), then the Mahalanobis distance from
   those rows with shrinkage 0.1 toward the scaled identity (pseudo-inverse).
4. **Readings** on the evaluation split, unclipped objects only:

| Reading | Rule | Pass when |
|---|---|---|
| **G1** positive control | AUROC of the emb score for KPMP GS vs KPMP NS (needs >= 30 GS objects) | >= 0.80 |
| **R1** beats the baseline | emb AUROC minus base AUROC | >= 0.05 |
| **R2** not one odd biopsy | Discovery set = objects KPMP labels NS **and** the detector calls NS; top set = the top 5% of their emb scores (ceil); largest share of the top set from one participant | <= 0.20 |
| **R3** clinical association | Burden = a participant's share of its discovery-set objects in the top set (participants with >= 5 such objects). For each of eGFR, proteinuria, albuminuria, A1c, diabetes history and hypertension history: partial Spearman of burden vs the field, controlling the participant's KPMP label-derived GS share; two-sided shuffle p (9,999 shuffles of the field, seed 11); Holm across the fields with >= 50 participants | any field Holm p < 0.05 |

- **If G1 does not pass, R1-R3 are reported as uninformative.** A score that cannot tell a known lesion from
  normal is not trusted to find unknown ones.
- The whole lane is **not graded** with fewer than 50 evaluation participants.
- Reported, not graded: the base side's AUROC, concentration and R3 table; each field's n, partial rho, p and Holm
  p; the shares of evaluation objects that are clipped or have no KPMP label; the share of slides that failed.

## What we expect (stated before any output)

- G1: likely pass (about 0.8). GS glomeruli look very different from NS ones, and the encoder was fine-tuned to
  separate them, which also makes this gate easier than NoRDeC's frozen-backbone setting. A pass shows the score
  works, not that it is novel.
- R1: uncertain (about 0.4). The baseline's pale fraction and colour features may already separate GS well.
- R2: likely pass (about 0.6), since the top set is spread over many biopsies unless a stain or scanner batch
  dominates it.
- R3: unlikely (about 0.3). After GS share is removed, little clinical signal may be left in NS glomeruli at this
  sample size, and the clinical fields are binned.

## Honest limits

- No expert review: a top-ranked glomerulus is a **candidate** anomaly. The challenge's "expert-confirmed
  discovery rate" stays unmeasured until a renal pathologist reviews a blinded sample; none is involved yet.
- Artifact screening is limited to KPMP's segmentation confirming the object (unlabelled objects never enter the
  discovery set) and excluding clipped windows; slide-level QC flags are not applied in v1.
- The encoder was trained for GS vs NS, so "unusual NS" may mean "GS-like NS" (for example segmental sclerosis
  or label disagreement). That would be a known lesion, and the results note must say so if it looks that way.
- One detector, one seed, one window size; clinical fields are open, binned summaries; several slides of one
  participant are pooled into one burden.
- Associations are cross-sectional and say nothing about cause or prognosis.

## Privacy and acknowledgement

Outputs hold per-object values from KPMP slides and stay local; only pooled readings (AUROCs, shares, correlations,
p-values and participant numbers) are published. No images, crops, embeddings, per-slide or per-participant values
or package ids. The results note will carry KPMP's acknowledgement verbatim as given in
`findings/kpmp-acknowledgement.md`, with the access date. KPMP has not reviewed or endorsed this work.
