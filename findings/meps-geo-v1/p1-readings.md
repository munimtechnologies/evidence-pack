# Census M2, prediction P1: hand readings of the three candidate briefs

MV2 of Munim, Inc., 2026-11-02. Written by AI agents (Claude) working in MV2's name; no human has reviewed it yet.
Text CC BY 4.0. Quoted brief text is US government work, quoted for analysis.

Rule (from `findings/meps-geo-prereg-v1-2026-11-01.md`): a candidate counts only if the page shows at least one
estimate for an MSA / non-MSA (or metropolitan / nonmetropolitan) group for a data year of 2013 or later (text,
figure label or table), not just a definition. Each reading below was written from the job's `snippets.jsonl`
and a fresh read of the live page (2026-11-02, about 04:30 UTC) before any count was made.

## #512 "Insurance and Access to Care in Urban and Rural Areas, 2014-2015" (May 2018)

- Class PUF (M1), anchor `post`. Data Source: "the 2014 and 2015 MEPS Full Year Consolidated Data Files (HC-171
  and HC-181)".
- Estimates by metro / non-metro for 2014-2015, for example: "Metro residents under age 65 were more likely to
  lack a usual source of care than their non-metro counterparts (25 versus 19 percent) (figure 2a)"; under 65,
  "non-metro residents were less likely to have private insurance (62 versus 69 percent)".
- Groups come from county of residence matched to the USDA 2013 Rural-Urban Continuum Codes (three metro and,
  merged, four non-metro groups). The page does not say which file or variable supplied the county.
- Reading: **counts** (metropolitan / nonmetropolitan estimates, data years 2014-2015). Note: these are
  county-based metro groups, not the MSA indicator itself; the rule names metropolitan / nonmetropolitan
  groups, so it counts.

## #554 "Characteristics of Young Adults Aged 18-24 Who Had Ever Used an Electronic Nicotine Product, 2021" (February 2024)

- Class PUF (M1), anchor `post`. Data Source: the "2021 Medical Expenditure Panel Survey (MEPS) Full-Year
  Consolidated Data File (HC-233)" and the 2021 Social and Health Experiences Self-Administered Questionnaire.
- Figure 3, "by region and MSA status, 2021": MSA "Yes" 29.6%, "No" 39.3%; text: "(39.3 percent and 29.6 percent,
  respectively)".
- MSA definition: "based on the county of residence around the time the supplement was initiated"; no variable
  name, and no statement that internal data were used.
- Reading: **counts** (MSA / non-MSA estimates, data year 2021).

## #569 "Bone Density Scan (DEXA) Utilization Among Women Without Diagnosed Osteoporosis Aged 50 and Older in the United States, 2022" (December 2025)

- Class PUF (M1), anchor `post`. Data Source names only HC-243.
- Figure 7, "by US geographic region and metropolitan (MSA) residence": MSA 42.7%, non-MSA 43.3% (transcribed twice
  on 2026-11-01; both reads agreed).
- Reading: **counts** (MSA / non-MSA estimates, data year 2022).
