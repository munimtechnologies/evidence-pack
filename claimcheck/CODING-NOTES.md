# claimcheck coding notes: readings the plan leaves open

MV2 of Munim, Inc. Written by AI agents (Claude, claude-opus-5-5) in MV2's name; no human has reviewed it. Text CC BY 4.0; code Apache-2.0.

The checker is coded to the evaluation plan in `findings/claim-checker/` (v5, as amended by v6 and v7). v7 is the last amendment. Where the plan's words allow more than one implementation, the choice made in code is listed here **before the code is frozen and before it runs on any base text**. These are readings, not new rules. Each one is marked `reading:` in the code, and each one counts as a possible source of P3 false positives or misses, to be reported with its cause.

## Shared grammar (`grammar.py`, committed 2026-10-21, run 152)
1. **Line splitting** matches `bytes.splitlines()` (CRLF, CR, LF only), so line numbers agree with the hash job `basetext-hash-v1`.
2. **Emphasis removal (v5 "text read").** `**` and `*` are removed everywhere. `_` is removed only at a word edge, so identifiers like `rwe_recheck` survive (v4 lists `_` as emphasis without saying how to tell it from an identifier).
3. **Word boundary (v4).** The plan says "." is a boundary only when followed by a space or a line end. A "." directly *before* a word is followed by the word, so it is not a boundary there (`x.registered` does not match `registered`).
4. **URLs (v4 name matching).** v4's URL test ("a run of non-space characters with a '.' followed by a letter") would also exclude `ClinicalTrials.gov` itself. Reading: a name is inside a URL when its non-space run holds `://`, when `/` or `.` touches the name, or when the run *outside* the name still has a "." followed by a letter. `ClinicalTrials.gov's` is a name; `www.ClinicalTrials.gov` and `ClinicalTrials.gov/study` are not.
5. **Registry IDs (v4).** Each pattern must not follow a letter or digit, and `NCT\d{8}` must not be followed by a ninth digit. v4 doesn't say either.
6. **Sentences (v4).** Applied to one physical line at a time, after the bullet marker, on the raw text (so a `**` after ". " still triggers a split), and emphasis is removed afterwards. Straight double quotes toggle; curly quotes open and close. Table body rows are split like prose (v4 only excludes headings and header rows); modules read tables cell by cell.
7. **G1 numbers (v6).**
   - A number directly after a letter, digit, `_`, `.`, `/`, `:` or the middle dot is not a whole token, and nor is one directly before a letter, `_`, `/`, `:`, the middle dot, "-letter" or ".digit". Signed tokens follow the same test on the character before the sign, so `COVID-19` and `PF-03882845` hold no number.
   - Only the ASCII hyphen separates (`1.24-2.07`, `8.0%-10.4%`). A minus sign (U+2212) after a digit is read as glued, not as a separator.
   - Dates: `YYYY-MM` needs a month 01-12 and `YYYY-MM-DD` a day 01-31, with no digit on either side. `2019-2021` is not a date.
   - Every square-bracket span is masked, not only numeric citations.
   - Only the "95%" inside a G2 label is masked by the label rule; labels are matched case-sensitively and word-bounded.
8. **G4 (v6).** The label, when present, is followed by exactly one space and then the pair (`(95% CI: a-b)` is not a G4 tuple). The joiners are exactly `" to "`, `"-"` and `", "`. The one digit-free word before ")" follows a single space.
9. **G3/G4/G5 order.** For each "(", G4 is tried first. If G4's pair is present but G3 finds no estimate, G5 is tried on the same parenthesis. G5 needs a matched ")".
10. **Count phrase (v4/v7).** "At most 3 words in between" counts whitespace-separated tokens. Number words are matched in any case for both R2b/R5b (v4) and R7-a (v7). Punctuation around a token (`()[]"'*,.;:` and curly quotes) is ignored when matching the number and the noun.
11. **Citation brackets (v7 linking).** `[n]`, `[n, m]`, `[n; m]` and ranges with a hyphen or an en dash (`[6-8]` carries 6, 7 and 8). Keys may carry one lower-case letter (`[36a]`). A heading's citations count for every table under it until the next heading.
12. **Structure.** A pipe table is a run of lines starting with `|` whose second line is a separator row. The reference list is every `N. ` line under a heading that starts with "References". `#` and `##` headings both reset the `##` section.
