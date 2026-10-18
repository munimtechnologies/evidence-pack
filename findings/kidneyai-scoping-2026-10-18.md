# Scoping: NIDDK Kidney AI Discovery Challenge on open KPMP data (2026-10-18)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0.
Research information, not medical advice. No KPMP data file has been downloaded yet; everything below comes from public web pages and public source code read on 2026-10-18 (about 03:30-04:15 UTC). No independent human check yet.

## Why this note

The Kidney Artificial Intelligence Discovery Challenge ("From Nebulae to Nephrons"), run for NIDDK through NASA Tournament Lab on HeroX, pays $50k / $30k / $20k for discoveries of rare or unexpected image features in kidney biopsy whole-slide images (WSIs). Only open data from the KPMP Kidney Tissue Atlas may be used. This note records what that data is, how it can be reached, what limits a small CPU sandbox imposes, what has already been published, and the first steps we would take. It is a plan, not a result.

## The challenge (herox.com/KidneyAI, read 2026-10-18)

- Stage: pre-registration. Launch 2026-09-15; registration and submissions 2026-11-05 to 2027-04-29; judging 2027-04-30 to 06-30; winners 2027-09-01.
- Data: "the exclusive use of KPMP data, limited to publicly available ('open') data in the KPMP Kidney Tissue Atlas"; no controlled (DUA) data. "NIH will provide participants with access to a common set of eligible KPMP images."
- Submission requirements are "being finalized" and will be posted before the window opens. For each discovery: evidence, rationale, methods, assumptions, validation, reliability, limitations. Code must be "provided in a runnable form that allows HeroX to independently execute and verify the reported findings". A cover-page agreement sentence is mandatory.
- Judging: discovery and novelty 50 (image features, e.g. patterns, objects, anomalies, in WSIs); technical approach and performance 30 (detect, rank, retrieve, cluster or localise rare, hidden or expert-validated findings; generalisation beyond development data); interpretability and expert usability 20 (including whether the team consults experts who can evaluate kidney biopsy findings).
- Eligibility: US citizens or permanent residents aged 18+, or entities incorporated in and based in the US; no federal grant or cooperative-agreement funds. Individual, team or entity registration.
- The page shows 53 teams and 2 forum posts; the FAQ has only two generic entries. No hardware or environment is specified.

## The open data (kpmp.org/available-data and atlas.kpmp.org)

- Light-microscopy WSIs are **open** for the main study (AKI n=92, CKD n=524, DM-R n=67 participants enrolled) and for the healthy-reference groups (living donor, kidney stone donor, pilot 1). Search snippets of the Atlas home page give 625 participants with WSIs and 6,625 WSI files (110 reference, 4,881 CKD, 1,022 AKI, 612 DM-R); the Spatial Viewer lists 5,321 WSI entries including PAS segmentation masks. These counts are second-hand and will be checked against the file manifest.
- Stains: H&E, PAS, trichrome and Jones' methenamine silver (toluidine blue is also scanned). Published KPMP studies describe Aperio AT2 scans at 40x (0.25 um/pixel) in SVS format and, later, an Aperio GT450. File sizes are not published anywhere we found.
- Also open: **KPMP TIV descriptor scores** (pathologist descriptor scoring) and **segmentation masks** (glomeruli, tubules and other structures), plus single-cell, spatial transcriptomics, imaging mass cytometry (tif/csv/svs) and other omics. A limited set of clinical variables is open; fuller clinical data (eGFR, outcomes) is controlled. Electron microscopy and immunofluorescence are controlled.
- Terms: KPMP asks for a set acknowledgement sentence and grant list. The site footer forbids reproducing website content without permission and does not say whether downloaded files may be redistributed, so **we will not re-host any KPMP file**; only code, derived statistics and our own text will be published.

## How the files can be reached (KPMP's own open-source code, github.com/KPMP)

- The Atlas Repository front end (KPMP/hydra-web, MIT) searches an Elastic App Search engine named `atlas-repository` with a browser search key, and downloads a file from `https://atlas.kpmp.org/api/v1/file/download/<package_id>/<file_name>`.
- The file service (KPMP/atlas-file-service, MIT) serves a file only if KPMP's own table marks it `open`, streaming it in 1 MB chunks; anything else returns 404.
- The search endpoint returns HTTP 401 without the key. We will **not** extract the browser key to script searches. The Repository has its own "export file list" CSV button, which is the intended way to get a manifest (file name, package id, size, format, stain or data type, participant metadata). Getting that CSV through the site's own interface is the first step.

## Prior art (searched 2026-10-18)

- Supervised glomerulus detection and segmentation on kidney WSIs is crowded (U-Net variants, Omni-Seg, glomerulosclerosis quantification, lesion classification).
- The closest unsupervised work: Hasko et al., "Seeing Abnormal from Normal: Glomerular Abnormality in Representations of Normal Renal Morphology", arXiv 2609.19444 (Sept 2026). One-class Mahalanobis scoring on a frozen Omni-Seg encoder fitted on normal glomeruli only; pooled AUROC 0.926 against PaDiM and PatchCore, on PAS glomeruli from two institutions. KPMP is not named on the abstract page; no code link.
- A cell-level foundation-model evaluation in kidney pathology (Communications Medicine 2025) does not do anomaly detection.
- So "anomaly detection on glomeruli" is no longer new by itself. Whatever we submit must add something: a different unit (tubulointerstitium, vessels, whole-biopsy layout), a cross-stain consistency test, discovery on the open KPMP cohort specifically, or pre-registered false-positive control. Which of these is feasible depends on the manifest.

## What our sandbox can and cannot do

- MV2's compute is a shared CPU sandbox: about 4 CPUs, 6 GB RAM, no GPU, jobs queued for many hours. Gigapixel SVS files must be read pyramid level by level (tifffile, or openslide via the `openslide-bin` wheel), never whole.
- All 6,625 WSIs are out of reach (likely terabytes). A realistic scale is one stain (PAS, the stain of the segmentation masks) and one slide per participant, streamed, featurised at low magnification or on mask-located structures, then deleted.
- Deep foundation-model encoders on CPU are slow; hand-crafted morphometry from the open masks (structure counts, areas, shapes, spacing) plus small CNN features at reduced resolution are feasible.
- The open TIV descriptor scores are pathologist-made labels. They can serve as "expert-validated findings" to check whether flagged anomalies concentrate where pathologists scored lesions. This partly answers the 20-point expert criterion without contacting anyone, but it is not a substitute for a pathologist reading our flags; that gap stays open and will be stated.

## Plan, in order (each step a separate, dated note)

1. Get the Repository's own CSV exports for WSIs, segmentation masks and TIV descriptor scores (through the site's interface). Record counts, sizes and formats; check the second-hand counts above.
2. Feasibility job (one PAS slide plus its mask, chosen by a rule fixed in advance: the smallest open PAS WSI that has a mask): download time, file size, pyramid levels, peak memory, time to read a level-2 tile grid. Pass or fail written down before it runs.
3. If feasible: a pre-registered pilot on a seeded sample of participants, with a held-out half, negative controls (shuffled participants, stain-swapped slides) and predictions about where anomalies concentrate relative to TIV scores, committed before any image is featurised.
4. Register on HeroX when registration opens on 2026-11-05 (Munim, Inc. as the entity) and read the final submission requirements and the common image set before building further.

## Honest limits

- Nothing has been run. Counts are from search snippets and will be replaced by manifest counts.
- No member of the team is a kidney pathologist; the judging rubric rewards one.
- The common image set NIH will provide may differ from what is listed here.
- Odds are unknown; 53 teams had registered interest before submissions opened.

## Sources

- https://www.herox.com/KidneyAI (summary, rules, FAQ)
- https://www.kpmp.org/available-data
- https://www.kpmp.org/help-docs/study-overview?tabname=citingkpmpdata
- https://github.com/KPMP/hydra-web (src/components/Repository/FileList.js, FileListHolder.js, .env.example)
- https://github.com/KPMP/atlas-file-service (app.py)
- https://arxiv.org/abs/2609.19444
- https://pmc.ncbi.nlm.nih.gov/articles/PMC8392148/ (KPMP WSI scanning: Aperio AT2, 40x, SVS)
