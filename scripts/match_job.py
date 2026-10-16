"""Match a job description against the evidence-based skill report.

Usage: match_job.py --report build/skills.json --config skills.yaml private/jobs/<job>.txt

Lists the skills the job mentions that have evidence (with years and where they were
used), and the terms from the vocabulary in skills.yaml that the job mentions but the
evidence does not cover (gaps). It matches words, it does not read intent: a line such
as "Java is not required" still lists Java.
"""

import argparse
import json
import re
import sys

from skills import canonical, merge_configs, read_config

_LEFT = r"(?<![A-Za-z0-9_.#+])"
_RIGHT = r"(?![A-Za-z0-9_#+])"


def find_terms(text, terms):
    return {t for t in terms if re.search(_LEFT + re.escape(t) + _RIGHT, text, re.IGNORECASE)}


def _names(skill, config):
    return [skill, *config["aliases_of"].get(skill, [])]


def match(job_text, report, config):
    evidenced = {r["skill"].casefold() for r in report if r["months"] > 0 or r["confirmed"]}
    matched = [
        {"skill": r["skill"], "years": r["years"], "approx": r["approx"], "confirmed": r["confirmed"], "where": r["where"]}
        for r in report
        if r["skill"].casefold() in evidenced and find_terms(job_text, _names(r["skill"], config))
    ]
    gaps = sorted(
        {canonical(term, config) for term in config["vocabulary"]
         if canonical(term, config).casefold() not in evidenced
         and find_terms(job_text, _names(canonical(term, config), config) + [term])},
        key=str.casefold,
    )
    return {"matched": matched, "gaps": gaps}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", required=True)
    parser.add_argument("--config", action="append", required=True)
    parser.add_argument("job")
    args = parser.parse_args(argv)
    with open(args.report, encoding="utf-8") as fh:
        report = json.load(fh)["skills"]
    with open(args.job, encoding="utf-8") as fh:
        job = fh.read()
    result = match(job, report, merge_configs(*(read_config(path) for path in args.config)))
    print("| Skill in the job | Years (evidence) | Confirmed | Where |\n|---|---|---|---|")
    for m in result["matched"]:
        confirmed = m["confirmed"]["years"] if m["confirmed"] else ""
        print(f"| {m['skill']} | {'~' if m['approx'] else ''}{m['years']} | {confirmed} | {', '.join(m['where'])} |")
    print("\nGaps (mentioned in the job, no evidence): " + (", ".join(result["gaps"]) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
