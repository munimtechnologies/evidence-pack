# meps-census-v1 validation gate: hand readings (written BEFORE opening briefs.csv)

Read 2026-11-01 ~12:30-12:45 UTC from the live .shtml pages through a page summariser (WebFetch), one fetch
each, classified by the prereg rules (order: NOPAGE, NOSECTION, IC, NONPUBLIC, PUF, NOID).

| # | year | my class | basis |
|---|---|---|---|
| 47 | 2004 | IC | MEPS-IC, no HC id ("special computation runs on the confidential MEPS-IC data"; IC wins by rule order) |
| 55 | 2004 | IC | "1997 and 2002 MEPS-IC", no ids |
| 90 | 2005 | IC | "2003 MEPS-IC", no ids |
| 96 | 2005 | NOID | "2002 MEPS full-year files", PMED files, no ids, no markers |
| 126 | 2006 | NOSECTION | no Data Source heading (About MEPS-HC instead) |
| 180 | 2007 | NOSECTION | no Data Source heading |
| 205 | 2008 | PUF | HC-094A, HC-051A |
| 232 | 2009 | PUF | HC-105, HC-102A |
| 245 | 2009 | PUF | HC-050, HC-105, HC-102A |
| 254 | 2009 | PUF | HC-105, HC-102A (B, D, E, G as bare suffixes) |
| 267 | 2009 | NOID | descriptive file names only, "public use files" |
| 273 | 2009 | IC | "2008 MEPS-IC", special computation / confidential |
| 298 | 2010 | PUF | HC-113 |
| 334 | 2011 | PUF | HC-121, HC-120, HC-118A/D/E/F/G/H |
| 392 | 2012 | PUF | HC-129, HC-138, HC-139 |
| 408 | 2013 | PUF | HC-138 |
| 411 | 2013 | NOID | descriptive names only ("MEPS-HC 2010 Full Year Consolidated Data File ...") |
| 510 | 2018 | PUF | HC-163, HC-171, HC-181, HC-172, HC-183 |
| 511 | 2018 | PUF | HC-097, HC-181, HC-131 |
| 549 | 2023 | NONPUBLIC | HC-224 etc. plus "2020 MEPS internal data file with MSA variables" |

Side notes (not graded): #245 lists HC-050 (2000 FYC) for a 2006 brief; #511 lists HC-131 (2000-2013
employment file) for 2015 data; #254 lists only 2006 files although it compares with 1996.
