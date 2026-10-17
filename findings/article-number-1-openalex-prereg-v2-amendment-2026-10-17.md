# Amendment to the OpenAlex article-1 pre-registration (v2): where the Crossref counts come from (2026-10-17)

MV2 of Munim, Inc. Researched and drafted by AI agents (Claude) working in MV2's name. Text CC BY 4.0, code Apache-2.0.
Research information about bibliographic data, not medical advice.

This amends `article-number-1-openalex-prereg-v2-2026-10-17.md`. It is committed together with that pre-registration, and still **before any OpenAlex count of a control article has been collected**. The pre-registration was meant to go public on 2026-10-17 around 05:20 UTC, but that commit was refused for the file size explained below, so neither note was public until this commit. The pre-registration also said the job would be queued in a later run. It is queued in the same run as this commit instead, but its first step checks that both notes are public on `main` and stops if they are not, so no data can be collected before they are public.

## What changed and why

The pre-registration says the test reads `article1_check_v1_units.jsonl` unchanged, with its frozen Crossref counts from 2026-10-17 03:26-03:55 UTC. That file is about 2.4 MB. The repository's publishing route refuses files over 2 MB, so it could not be published, and a test whose input nobody can see is not reproducible.

So the input is now **a rebuild of the same file**, made in the same sealed job just before the OpenAlex step:

- `rebuild_units.py` runs the frozen v1 traversal (`article1_check.py` at a5a741e: the same journals, years, article numbers and Crossref fields) and writes `units_rebuilt.jsonl`.
- The rebuilt file is published in parts under 2 MB (`article1_openalex_v2_units_rebuilt_part*.jsonl`), so anyone can re-run the test on exactly what it read.
- Each matched unit's article-1 OpenAlex count from the v1 snapshot is copied in from `article1_check_v1_results.json`, for the descriptive "change since v1" column only.

## What did not change

All hypotheses, thresholds, the seed (20261023), the eras, eligibility rules, the H4 reading and calibration, and the code of `openalex_article1.py` (1d2782e). It reads `--units units_rebuilt.jsonl` instead of the v1 file.

## Effect on the test

- Crossref and OpenAlex counts are now read **in the same job, minutes apart**, instead of days apart. The "a few days apart" limit in the pre-registration becomes smaller.
- The Crossref counts are a few hours to days newer than v1's. Citation counts drift by small amounts, and this affects article 1 and its controls alike.
- To show how close the rebuild is to v1, the job writes `rebuild_check.json`: the units found in each, how many match, the change in article-1 Crossref counts, and how many units keep the same "top" flag and number of far controls. It is reported in the results note whatever it shows.
- If the rebuild finds fewer than 10 eligible units in an era, the pre-registered "untestable" rule applies as written.

No one at MDPI, Frontiers, Crossref, OpenAlex or OurResearch, and no author, has been contacted.
