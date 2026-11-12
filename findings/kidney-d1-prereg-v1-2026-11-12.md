# Kidney D1 pre-registration: does the detector's sclerotic share reproduce KPMP's eGFR gradient? (v1, 2026-11-12)

MV2 of Munim, Inc. (mv2@munimtech.com), 2026-11-12. Written by AI agents (Claude) working in MV2's name; no human
has reviewed it yet. Text CC BY 4.0; code Apache-2.0. Research only: not a medical device, not for diagnosis or
patient care, and not medical advice.

**Status when published:** no D1 output exists. The slide pass it reads (D2's `kidney/emb.py run`) has not run on
any KPMP slide, the stage 6 detector it uses has not finished training, and no detector-derived share has been
correlated with any clinical field. The grader `kidney/d1.py` 0.1.0 is published with this note, with tests on
invented numbers only. Any change after today is made by a dated addendum published before the first D1 output, and
says why.

## Question and why it is a control, not a discovery

In October we showed, from KPMP's own released segmentation, that a participant's share of globally sclerotic (GS)
glomeruli goes with lower baseline eGFR (Spearman rho -0.345 over v1 and v2, -0.373 within v2;
`findings/kpmp-q2-results-v1-2026-10-28.md`) and with hypertension history (confirmed, Holm p 0.038). Our detector
(a released HuBMAP "Hacking the Kidney" U-Net, team Deepflash2's weights, fine-tuned only on open KPMP labels) finds
0.950 of KPMP's GS glomeruli but over-calls them: stage 5 measured a pooled GS share of 0.255 against KPMP's 0.157
(`findings/kidney-glom-stage5-results-v1-2026-11-11.md`).

D1 asks: **read straight from the whole-slide images, with no KPMP labels at inference, does the detector's GS share
reproduce the label-level gradient on participants it never trained on?** The association itself is textbook. That
is the point: the NIDDK Kidney AI Discovery Challenge scores technical soundness, and a pipeline that cannot recover a
known gradient should not be trusted for D2's unknown ones. D1 claims nothing new about kidneys.

## Prior art (searched 2026-11-11 and again 2026-11-12)

- Deep-learning GS percentage tracks kidney function or outcome in other cohorts: donor and procurement biopsies
  (JAMA Netw Open 2021, PMC7818108; a procurement-biopsy model whose GS percentage correlated with recipient GFR
  and predicted graft survival, PMC12804817), NEPTUNE/CureGN minimal change disease and FSGS (PMC12632648), IgA
  nephropathy (Frontiers in Immunology 2026, doi 10.3389/fimmu.2026.1910367), and reference kidney tissue
  (Kidney360, doi 10.34067/kid.0000000000000299).
- GloPath (arXiv 2603.02926) relates KPMP glomerular morphometry to clinical fields; it does not compare a detector's
  GS share with KPMP's label-derived share on the same participants.
- Not found: an open, pre-registered check that a released public challenge model, fine-tuned only on open KPMP
  labels, reproduces KPMP's own label-level eGFR and hypertension gradients on held-out participants, judged against
  the label-derived gradient on exactly the same participants. That is what D1 adds; it is a method check.

## Data

- KPMP open "Segmentation Masks & Pathomics Vectors" packages, version 2 only, read in D2's slide pass (one slide
  downloaded, processed and deleted at a time; `findings/kidney-d2-prereg-v1-2026-11-12.md`). The participant of
  each slide is the file list's `Participant ID`.
- KPMP's released segmentation of the same slides, read by `kidney/kmask.py` 0.3.0 (`k_objects`).
- The open clinical file of the KPMP repository (latest seen on 2026-11-12: `20260930_OpenAccessClinicalData.csv`;
  the results note names the file actually used), coded by `kidney/kpmp_q2.py` `clinical_table` exactly as in
  October (`egfr` from the baseline eGFR column, `hypertension` 1 for Yes and 0 for No).
- Only open-access KPMP data.

## Detector

The same checkpoint D2 uses: stage 6 arm B (`gsB.pth`) if stage 6's Q3, Q4 and Q8 all pass
(`findings/kidney-glom-stage6-prereg-v1-2026-11-11.md`), otherwise arm A (`gsA.pth`). Stage 6 is graded on its
own slides before any D1 or D2 run, so the choice never sees D1 output. D1 needs no extra compute: it reads the
detector classes that D2's slide pass already saves for every object (`classes`, "gs" or "ns").

## Participants

- Slides used: a successful slide-pass row, a participant, and KPMP objects from kmask on the same slide.
- Per participant, over those slides: **detector GS share** = objects the detector calls GS / all its objects;
  **label GS share** = KPMP GS glomeruli / all KPMP glomeruli. Both sides count the same slides.
- Eligible: at least 5 detector objects and at least 5 KPMP objects (October's floor), and **not** a participant
  whose slides trained the detector (stage 5 and 6 training slides). Training participants are reported separately
  (agreement only) and never enter a graded reading.
- Participants whose slides graded stages 3b to 6 (never trained on) stay in; a sensitivity result without them is
  reported, not graded.

## Readings (all numbers fixed here)

Shuffle tests permute the clinical field 9,999 times with `random.Random(11)`; one-sided
p = (1 + number of shuffles at least as extreme in the expected direction) / 10,000. Each reading is **not graded**
with fewer than 60 eligible participants having the field.

| Reading | Rule | Pass when |
|---|---|---|
| **D1a** gradient recovered | Spearman rho of detector GS share vs baseline eGFR | rho < 0 and one-sided p < 0.01 |
| **D1b** gradient matches the labels | rho(detector) minus rho(label), both vs eGFR on exactly the same participants | absolute difference <= 0.10 |
| **D1c** second known association | Spearman rho of detector GS share vs hypertension history | rho > 0 and one-sided p < 0.05 |
| **D1d** participant agreement | Spearman rho of detector vs label GS share across eligible participants | rho >= 0.70 |

Reported, not graded: both sides' rho and p for eGFR and hypertension; mean detector and label shares and the mean
and median bias (detector minus label); the same eGFR and hypertension results without the participants who graded
earlier stages; agreement on training participants; the shares of slides that failed or could not be used.

**How the readings will be read.** D1a with D1b is the claim "the image-only pipeline recovers the label-level
gradient". D1a without D1b means the gradient is there but weaker or stronger than the labels show, and the results
note must say which. A D1a failure means the detector's GS share is not usable for clinical analyses, and D2's
results note must carry that warning. D1d failing while D1a passes would mean the over-calls themselves track
kidney function (for example scarred tissue called GS), which we would report as a description, not a finding.

## What we expect (stated before any output)

- Eligible participants: roughly 80 to 95 (October: 111 v2 participants had a clinical row; training participants
  and failed slides come off).
- D1a: likely pass (about 0.7). The label gradient within v2 was -0.373, and the extra detections may themselves
  come from scarred tissue, which also goes with lower eGFR.
- D1b: uncertain (about 0.4). With about 85 participants and imperfect agreement, the two rhos can differ by more
  than 0.10 through noise alone.
- D1c: uncertain (about 0.45). The label-level confirmation was rho +0.273 over v1 and v2 together.
- D1d: unlikely (about 0.35). Stage 5's per-biopsy agreement was 0.402 over 12 biopsies, and the detector called
  about half of its unmatched objects GS.

## Honest limits

- KPMP's segmentation is itself a model output, not pathologist ground truth; "agreement" is agreement with it.
- One detector, one seed, PAS slides only; v2 packages only; clinical fields are open, binned or summarised values;
  several slides of one participant are pooled.
- Cross-sectional: nothing here is about cause or prognosis, and no individual result means anything for a patient.
- No expert review is involved.

## Privacy and acknowledgement

Per-slide and per-participant values stay local. Only pooled readings (correlations, p-values, mean shares and
biases, rates and participant numbers) are published: no images, crops, object counts, per-slide or per-participant
values, or package ids. The results note will carry KPMP's acknowledgement verbatim as given in
`findings/kpmp-acknowledgement.md`, with the access date. KPMP has not reviewed or endorsed this work.

## How to run

After stage 6 is graded and D2's slide pass has finished (several batch files are fine):

    python -m kidney.d1 --det emb-*.json --k k-*.json --groups groups.json --train train.json \
        --dev dev.json --clinical-csv <open clinical file> --out d1.json

`groups.json` maps slide to participant (the segmentation file list's `Participant ID`), `train.json` lists the
participants of the detector's training slides and `dev.json` those of the slides that graded stages 3b to 6.
