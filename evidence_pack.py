"""Triage generic drug -> condition pairs by how much clinical evidence exists, from public sources.

For each pair in pairs.json this gathers, with no login and no patient data:
- PubMed (NCBI E-utilities): how many papers name the drug and the condition,
  how many of them are randomized trials, meta-analyses, systematic reviews,
  observational studies and phase 2/3 trials, and the newest trial and review
  records (PMID, year, journal, title);
- ClinicalTrials.gov (API v2): registered studies of the drug in the
  condition, with phase, status, enrollment, sponsor and whether results are
  posted;
- openFDA drug labels: how many labels of the drug carry a boxed warning, and
  the text of one (safety context for an evidence package).

It is a first pass for choosing pairs for the NCATS Repurposing Generic (ReGen)
Drugs Evidence Package Challenge, not an evidence review: counts include papers
that only mention both terms, and nothing here judges study quality. Research
information, not medical advice.

Standard library only. Apache-2.0. Made by MV2 of Munim, Inc. with AI agents
(Claude) working in his name.
"""

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CTGOV = "https://clinicaltrials.gov/api/v2/studies"
OPENFDA = "https://api.fda.gov/drug/label.json"
USER_AGENT = "evidence-pack (MV2 of Munim, Inc.; munimversion2@gmail.com)"
NCBI = {"tool": "evidence-pack", "email": "munimversion2@gmail.com"}

DESIGNS = {
    "rct": "randomized controlled trial[pt]",
    "meta_analysis": "meta-analysis[pt]",
    "systematic_review": "systematic review[pt]",
    "observational": "observational study[pt]",
    "phase2": "clinical trial, phase ii[pt]",
    "phase3": "clinical trial, phase iii[pt]",
}
KEY_DESIGNS = ("rct", "meta_analysis", "systematic_review")
LATER_PHASES = {"PHASE2", "PHASE3", "PHASE4"}


def drug_clause(drug):
    return '("%s"[tiab] OR "%s"[mh])' % (drug, drug)


def pubmed_term(pair, design=None):
    """The PubMed query for a pair, optionally limited to one design (a key of DESIGNS) or a tuple of them."""
    term = "%s AND %s" % (drug_clause(pair["drug"]), pair["pubmed"])
    if design is None:
        return term
    designs = (design,) if isinstance(design, str) else design
    return "%s AND (%s)" % (term, " OR ".join(DESIGNS[d] for d in designs))


def parse_summary(uid, doc):
    """One PubMed esummary record as a small dict."""
    return {"pmid": uid, "year": (doc.get("pubdate") or "")[:4], "journal": doc.get("source", ""),
            "title": doc.get("title", ""), "types": doc.get("pubtype", [])}


def parse_study(study):
    """One ClinicalTrials.gov v2 study as a small dict."""
    p = study.get("protocolSection", {})
    ident, status = p.get("identificationModule", {}), p.get("statusModule", {})
    design, sponsor = p.get("designModule", {}), p.get("sponsorCollaboratorsModule", {})
    return {
        "nct": ident.get("nctId", ""),
        "title": ident.get("briefTitle", ""),
        "status": status.get("overallStatus", ""),
        "start": status.get("startDateStruct", {}).get("date", ""),
        "primary_completion": status.get("primaryCompletionDateStruct", {}).get("date", ""),
        "type": design.get("studyType", ""),
        "phases": design.get("phases", []),
        "enrollment": design.get("enrollmentInfo", {}).get("count"),
        "sponsor": sponsor.get("leadSponsor", {}).get("name", ""),
        "has_results": bool(study.get("hasResults")),
    }


def trial_counts(studies):
    """Counts over parsed ClinicalTrials.gov studies."""
    interventional = [s for s in studies if s["type"] == "INTERVENTIONAL"]
    later = [s for s in interventional if LATER_PHASES & set(s["phases"])]
    return {
        "registered": len(studies),
        "interventional": len(interventional),
        "phase2_or_later": len(later),
        "phase2_or_later_completed": sum(1 for s in later if s["status"] == "COMPLETED"),
        "phase2_or_later_with_results": sum(1 for s in later if s["has_results"]),
        "recruiting_or_active": sum(1 for s in interventional
                                    if s["status"] in ("RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING",
                                                       "ENROLLING_BY_INVITATION")),
    }


def score(pubmed, trials):
    """A rough triage score: trials and pooled analyses count most. A sort key, not a quality grade."""
    return pubmed["rct"] + 2 * pubmed["meta_analysis"] + 3 * trials["phase2_or_later_with_results"]


def render(results, run_date):
    """triage.md for a list of per-pair results."""
    ranked = sorted(results, key=lambda r: (-r["score"], r["slug"]))
    lines = ["# ReGen triage: clinical evidence per generic drug -> condition pair (%s)" % run_date, "",
             "Counts are PubMed records naming both the drug and the condition, by publication type, and "
             "ClinicalTrials.gov registrations. They are a first pass for choosing pairs, not a review of "
             "study quality. Score = RCTs + 2 x meta-analyses + 3 x phase 2+ trials with posted results.", "",
             "| Pair | PubMed | RCT | Meta-an. | Sys. rev. | Observ. | CT.gov interv. | Phase 2+ | with results "
             "| active | Boxed-warning labels | Score |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in ranked:
        p, t, f = r["pubmed"], r["trials"], r["fda"]
        lines.append("| %s -> %s | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d/%d | %d |" % (
            r["drug"], r["condition"], p["all"], p["rct"], p["meta_analysis"], p["systematic_review"],
            p["observational"], t["interventional"], t["phase2_or_later"], t["phase2_or_later_with_results"],
            t["recruiting_or_active"], f["boxed_labels"], f["labels"], r["score"]))
    for r in ranked:
        lines += ["", "## %s -> %s" % (r["drug"], r["condition"]), "", "PubMed query: `%s`" % r["query"], "",
                  "Newest trials and reviews:", ""]
        for paper in r["papers"]:
            lines.append("- PMID %s (%s, %s): %s" % (paper["pmid"], paper["year"], paper["journal"], paper["title"]))
        later = [s for s in r["studies"] if s["type"] == "INTERVENTIONAL" and LATER_PHASES & set(s["phases"])]
        if later:
            lines += ["", "Phase 2+ registrations:", ""]
            for s in later:
                lines.append("- %s %s, %s, n=%s, %s%s: %s" % (
                    s["nct"], "/".join(s["phases"]), s["status"], s["enrollment"], s["sponsor"],
                    ", results posted" if s["has_results"] else "", s["title"]))
        if r["fda"]["boxed_text"]:
            lines += ["", "A boxed warning on a current label (openFDA): %s" % r["fda"]["boxed_text"]]
    lines += ["", "Research information, not medical advice. Sources: NCBI E-utilities, ClinicalTrials.gov API v2, "
              "openFDA (which says its data are unvalidated)."]
    return "\n".join(lines) + "\n"


def get_json(url, params, pause=0.4, tries=5):
    """GET a JSON API; None on HTTP 404."""
    request = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": USER_AGENT})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
            time.sleep(pause)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                time.sleep(pause)
                return None
            if attempt == tries - 1:
                raise
        except urllib.error.URLError:
            if attempt == tries - 1:
                raise
        time.sleep(3 * 2 ** attempt)
    return None


def pubmed_count(term):
    data = get_json(EUTILS + "esearch.fcgi", dict(NCBI, db="pubmed", term=term, retmode="json", retmax=0))
    return int(data["esearchresult"]["count"])


def pubmed_papers(term, n=15):
    data = get_json(EUTILS + "esearch.fcgi", dict(NCBI, db="pubmed", term=term, retmode="json", retmax=n,
                                                  sort="pub_date"))
    ids = data["esearchresult"]["idlist"]
    if not ids:
        return []
    summary = get_json(EUTILS + "esummary.fcgi", dict(NCBI, db="pubmed", id=",".join(ids), retmode="json"))
    result = summary["result"]
    return [parse_summary(uid, result[uid]) for uid in result.get("uids", []) if uid in result]


def ctgov_studies(condition, drug):
    studies, token = [], None
    while True:
        params = {"query.cond": condition, "query.intr": drug, "pageSize": 100, "format": "json"}
        if token:
            params["pageToken"] = token
        data = get_json(CTGOV, params)
        if not data:
            break
        studies.extend(parse_study(s) for s in data.get("studies", []))
        token = data.get("nextPageToken")
        if not token:
            break
    return studies


def fda_facts(drug):
    name = 'openfda.generic_name:"%s"' % drug
    every = get_json(OPENFDA, {"search": name, "limit": 1})
    boxed = get_json(OPENFDA, {"search": name + " AND _exists_:boxed_warning", "limit": 1})
    text = ""
    if boxed and boxed.get("results"):
        text = " ".join(boxed["results"][0].get("boxed_warning", []))[:600]
    return {"labels": every["meta"]["results"]["total"] if every else 0,
            "boxed_labels": boxed["meta"]["results"]["total"] if boxed else 0,
            "boxed_text": " ".join(text.split())}


def gather(pair):
    pubmed = {"all": pubmed_count(pubmed_term(pair))}
    for design in DESIGNS:
        pubmed[design] = pubmed_count(pubmed_term(pair, design))
    studies = ctgov_studies(pair["ctgov"], pair["drug"])
    trials = trial_counts(studies)
    return dict(pair, query=pubmed_term(pair), pubmed=pubmed, papers=pubmed_papers(pubmed_term(pair, KEY_DESIGNS)),
                studies=studies, trials=trials, fda=fda_facts(pair["drug"]), score=score(pubmed, trials))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pairs", default="pairs.json")
    parser.add_argument("--out", default="out")
    args = parser.parse_args(argv)

    with open(args.pairs, encoding="utf-8") as f:
        pairs = json.load(f)["pairs"]
    os.makedirs(args.out, exist_ok=True)
    results = []
    for pair in pairs:
        try:
            result = gather(pair)
        except Exception as e:  # one failing source should not lose the other pairs
            print("%s: failed: %r" % (pair["slug"], e), file=sys.stderr)
            continue
        results.append(result)
        with open(os.path.join(args.out, pair["slug"] + ".json"), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=1)
        print("%s: %d PubMed, %d RCT, %d registered" % (pair["slug"], result["pubmed"]["all"],
                                                         result["pubmed"]["rct"], result["trials"]["registered"]),
              file=sys.stderr)
    text = render(results, dt.date.today().isoformat())
    with open(os.path.join(args.out, "triage.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
