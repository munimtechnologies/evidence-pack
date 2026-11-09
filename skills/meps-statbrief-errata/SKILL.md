---
name: meps-statbrief-errata
description: Use when quoting, checking or reproducing a number from an AHRQ Medical Expenditure Panel Survey (MEPS) Statistical Brief (meps.ahrq.gov stat<N>.shtml pages, health care spending, insurance, access and use estimates). Before you quote a brief's figure, look it up among 28 known slips (figure-vs-text conflicts, swapped cells, wrong labels, years and titles, a mistyped percentage, a truncated cell, a total its own subgroups cannot produce), 11 reproduction results from the public files and 2 documentation gaps, and avoid the traps met when recomputing briefs from MEPS public-use files. Works offline from a bundled table.
license: Apache-2.0
---

# MEPS Statistical Brief errata

Made with AI agents (Claude) working in MV2's name at Munim, Inc. Skill and script: Apache-2.0. Table
(`data/meps-statbrief-errata.csv`): CC BY 4.0; the published numbers in it are AHRQ's. Source and notes:
https://github.com/munimtechnologies/evidence-pack

AHRQ's MEPS Statistical Briefs are short reports of national estimates (spending, insurance, access to care)
from the Medical Expenditure Panel Survey. Open, pre-registered checks in the evidence-pack repository recomputed
eleven briefs from the public-use files they name and scanned the series for internal inconsistencies. This
skill bundles what they found. **Every row is a lead, not a confirmed error.** No person at Munim or at AHRQ has
reviewed them, and AHRQ has not been contacted. This is research information about published statistics, not
medical advice.

## When to use

- A user asks about, cites or summarises a MEPS Statistical Brief, or you are about to quote one of its numbers.
- You are recomputing a brief's estimates from a MEPS public-use file and your result differs from the brief.
- You are building a dataset or report from figures copied out of MEPS briefs.

## Step 1: look up known items

`scripts/meps_errata.py` needs Python 3.8+ and the standard library only. It is read-only, offline and uses the
bundled table (table 0.3.0: 41 rows).

```
python scripts/meps_errata.py --brief 558               # everything known about Brief #558
python scripts/meps_errata.py --brief 558 --value 6.2   # is this exact number involved in a known item?
python scripts/meps_errata.py --kind "figure vs text"   # one kind of item
python scripts/meps_errata.py --kind reproduction       # which briefs reproduce from their public file
python scripts/meps_errata.py --grep deductible --json  # text search, JSON output
python scripts/meps_errata.py --summary
```

Exit code 0 means at least one row matched, 1 none, 2 the table could not be read. `--version` prints the
versions; `--csv PATH` reads a newer copy of the table downloaded from the repository.

Row ids: `MEPS-E...` a slip (kinds: figure vs text, swapped cells, inconsistent total, label, title, duplicate,
text, truncated cell); `MEPS-R...` a reproduction result (cells checked, computable from the named file, exact to
the printed digit, close: within 0.5 points for percentages, 1% for totals, means and medians); `MEPS-D...` a
documentation gap (something needed to reproduce the brief that it does not state). Each row gives the printed
value, the other value where there is one, the evidence (public file, the brief's own text or numbers, the page)
and a link to the note that found it.

## Step 2: tell the user

- For a slip, give both values, say which one you use and why, and link the note. Call it "a discrepancy listed
  in MV2's open MEPS errata table, not confirmed by AHRQ". Never silently pick one value.
- Where the evidence is the public file (for example `MEPS-E012`, Brief #491), the file supports the value shown
  as "other" or names the side it supports in the row text. Where the evidence is the brief's own numbers (for
  example `MEPS-E013`, Brief #481, where a distribution sums to 102.0 with the printed cell and 100.0 with the
  text's value, or `MEPS-E021`, Brief #450, where the Highlights, the figure and the head count all give 7.2
  percent against the Findings' 67.2), say so. Where the evidence is only the brief's text, say that the figure
  and the text disagree.
- Some rows do not decide which value is right (`MEPS-E015`, `MEPS-E016`, `MEPS-E018`, `MEPS-E019`, `MEPS-E020`,
  `MEPS-E025`). Quote neither as settled.
- `MEPS-E009` (Brief #558, Figure 1) is different: the printed total and the printed age rates cannot both be
  right, and the table does not say which is wrong. Quote neither as settled.
- For a reproduction row, "reproduces" means at least 80% of computable cells were close (the pre-registered
  threshold). Brief #558 does not reproduce from HC-233; say so if you rely on it.
- No match does not mean the number is right. The table covers only what these checks looked at: eleven
  single-file briefs recomputed in full (first 30-40 cells each), series-wide scans for titles, age bands and
  totals, and a scan of 540 briefs' text against the figures they cite (census M8), all 134 of whose flags were
  read by hand. That scan sees only one-digit differences between decimal numbers, so it misses many slips (the
  #450 "67.2" was found by eye). Briefs can also be revised later; the table does not track changes to AHRQ's
  pages.

## Step 3: traps when you recompute a brief yourself

1. **Name the file.** A brief's Data Source section names the public-use file (for example HC-233 for 2021).
   The data year is usually earlier than the publication year. Briefs on employer insurance (for example #536)
   use the MEPS Insurance Component, not the Household Component files.
2. **The named file may not be enough.** Brief #540 needs the Medical Conditions file for 10 of its cells, which
   its Data Source does not name (`MEPS-D001`).
3. **Download by hand.** As of November 2026 meps.ahrq.gov's robots.txt disallows automated fetching of the
   public-use file folders and of .zip, .csv and .xlsx files. Download the zip in a browser, keep it, and record
   its SHA-256 and byte size.
4. **Use the ASCII zip if there is no Stata file.** Some older Full Year Consolidated files (HC-163, HC-181,
   HC-192) have no Stata version; the fixed-width ASCII zip read with the codebook's column positions works.
   Check record counts and a variable's value table against the codebook before computing anything.
5. **Use the right unit and weight.** Person estimates use the person weight (PERWTyyF). Family briefs need a
   family definition and weight; Brief #507's results depend on an unstated rule for who counts as a child
   (`MEPS-D002`).
6. **Components may not add up.** In HC-163, payer components differ from total expenditure by more than $0.50
   for 4,553 of 35,068 persons. Use the total variable for totals and say which you used.
7. **Round like the brief.** Round half-up to the printed precision before you call a value "exact", and report
   the raw gap as well.
8. **Read the labels against the text.** Age bands can overlap or leave a gap (#170 prints "Age 40-65" next to
   "Age 65+"; #227 leaves age 18 out of every labelled group), a figure can repeat another figure's title
   (#533) or row labels (#430 labels percentages "persons in millions"; #481 Figure 7 labels poverty rows
   "Health status"), and a sentence can name the wrong year (#304, #481).
9. **When figure and text disagree, test both.** The public file sided with the table in #491 and with the text in
   #497; in #567 and #536 the brief's own subtotals sided with the text, and in #481 a distribution that must sum
   to about 100 did.
10. **Scraping brief pages:** pages before about #554 put the body text and figure citations inside HTML layout
    tables, so a parser that skips tables loses most of the text. Figure data is often a flat list of labels and
    values; asterisks can sit before or after the % sign ("21.2*%", "88.3%*"), an overall value can be glued
    to its label ("All 5.0%"), and a cell can be cut short ("26." in #192 Table 3). Text often prints a count
    next to the percentage the figure shows ("12.4 percent ... 12.2 million persons"), and bullets under
    "From table 4:" belong to Table 4 even when Table 3's image sits above them (#250).

## Report a new item

Open an issue in https://github.com/munimtechnologies/evidence-pack with the brief number, the place (figure,
table or text), both values and how you found them. Contact: MV2, Munim, Inc., mv2@munimtech.com.
