"""Evidence-based skill tracking: how long each skill has been used, and where.

Usage:
  skills.py cv.yaml --config skills.yaml --today 2026-10 --json build/skills.json --md build/skills.md
            [--claims-csv private/linkedin/<date>/screening-1.csv ...]
            [--self-reported private/drafts/proxify-skills-2024-06.yaml]

Years are computed from the `stack` of each work, project and volunteer entry in
cv.yaml (plus project keywords and extra evidence in skills.yaml): the union of the
months in which a skill was in use, so parallel jobs never count twice. Self-reported
numbers (LinkedIn screening answers, old platform profiles) are compared against that
evidence, and large differences are flagged for the owner to resolve.
"""

import argparse
import csv
import json
import os
import re
import sys

import yaml

from cvlib import CVError, load_cv, validate_cv

DIVERGENCE_YEARS = 2

SCREENING_PATTERNS = [
    re.compile(r"^How many years of (?:work )?experience do you have (?:with|using|in) (.+?)\?$", re.IGNORECASE),
    re.compile(r"^Há quantos anos você já usa (.+?) no trabalho\?$", re.IGNORECASE),
]


def load_config(data):
    data = data or {}
    alias_map, aliases_of = {}, {}
    for canonical, aliases in (data.get("aliases") or {}).items():
        aliases_of[canonical] = list(aliases or [])
        for name in [canonical, *aliases_of[canonical]]:
            alias_map[name.casefold()] = canonical
    return {
        "alias_map": alias_map,
        "aliases_of": aliases_of,
        "vocabulary": list(data.get("vocabulary") or []),
        "confirmed": dict(data.get("confirmed") or {}),
        "evidence": list(data.get("evidence") or []),
        "linkedin_skills": list(data.get("linkedin_skills") or []),
    }


def read_config(path):
    with open(path, encoding="utf-8") as fh:
        return load_config(yaml.safe_load(fh))


def merge_configs(*configs):
    """Merge the public skills.yaml with private overlays (later files win)."""
    merged = load_config({})
    for config in configs:
        merged["alias_map"].update(config["alias_map"])
        merged["aliases_of"].update(config["aliases_of"])
        merged["vocabulary"] += [t for t in config["vocabulary"] if t not in merged["vocabulary"]]
        merged["confirmed"].update(config["confirmed"])
        merged["evidence"] += config["evidence"]
        merged["linkedin_skills"] = config["linkedin_skills"] or merged["linkedin_skills"]
    return merged


def confirmed_for(skill, config):
    """Owner-confirmed value for a skill, matched without regard to case."""
    wanted = skill.casefold()
    return next((v for k, v in config["confirmed"].items() if k.casefold() == wanted), None)


def canonical(name, config):
    return config["alias_map"].get(name.strip().casefold(), name.strip())


def month_index(value, end=False):
    parts = value.split("-")
    year = int(parts[0])
    if len(parts) == 1:
        return year * 12 + (11 if end else 0)
    return year * 12 + int(parts[1]) - 1


def format_month(index):
    return f"{index // 12}-{index % 12 + 1:02d}"


def _entries(doc, config):
    for w in doc.get("work", []):
        yield w["name"], w.get("startDate"), w.get("endDate"), w.get("stack", [])
    for p in doc.get("projects", []):
        yield p["name"], p.get("startDate"), p.get("endDate"), list(p.get("stack", [])) + list(p.get("keywords", []))
    for v in doc.get("volunteer", []):
        yield v["organization"], v.get("startDate"), v.get("endDate"), v.get("stack", [])
    for e in config["evidence"]:
        yield e["where"], e.get("startDate"), e.get("endDate"), e.get("stack", [])


def skill_report(doc, config, today):
    now = month_index(today)
    found, order = {}, {}
    for where, start, end, stack in _entries(doc, config):
        span = None
        if start:
            span = (month_index(start), month_index(end, end=True) if end else now)
        for item in stack:
            item = {"name": item} if isinstance(item, str) else item
            skill = order.setdefault(canonical(item["name"], config).casefold(), canonical(item["name"], config))
            row = found.setdefault(skill, {"months": set(), "fixed": 0, "where": [], "spans": []})
            if where not in row["where"]:
                row["where"].append(where)
            if span is None:
                continue
            if "years" in item:
                row["fixed"] += min(round(item["years"] * 12), span[1] - span[0] + 1)
                row["spans"].append(span)
                continue
            lo = month_index(item["startDate"]) if item.get("startDate") else span[0]
            hi = month_index(item["endDate"], end=True) if item.get("endDate") else span[1]
            row["months"].update(range(lo, min(hi, now) + 1))

    report = []
    for skill, row in found.items():
        months = len(row["months"]) + row["fixed"]
        marks = sorted(row["months"]) or sorted(m for span in row["spans"] for m in span)
        report.append({
            "skill": skill,
            "months": months,
            "years": round(months / 12, 1),
            "first": format_month(marks[0]) if marks else None,
            "last": ("present" if marks[-1] >= now else format_month(marks[-1])) if marks else None,
            "where": row["where"],
            "approx": row["fixed"] > 0,
            "confirmed": confirmed_for(skill, config),
        })
    return sorted(report, key=lambda r: (-r["months"], r["skill"].casefold()))


def parse_screening(rows):
    claims = []
    for row in rows:
        question, answer = (row.get("Question") or "").strip(), (row.get("Answer") or "").strip()
        for pattern in SCREENING_PATTERNS:
            match = pattern.match(question)
            if match:
                try:
                    claims.append({"question_skill": match.group(1).strip(), "answer": float(answer)})
                except ValueError:
                    pass
                break
    return claims


def compare_claims(claims, report, config):
    by_skill = {r["skill"].casefold(): r for r in report}
    result = []
    for claim in claims:
        skill = canonical(claim["question_skill"], config)
        row = by_skill.get(skill.casefold())
        evidence = row["years"] if row else 0.0
        answer = claim["answer"]
        confirmed = confirmed_for(skill, config)
        result.append({
            "question_skill": claim["question_skill"],
            "skill": skill,
            "answer": answer,
            "evidence_years": evidence,
            "confirmed": confirmed,
            # What to answer from now on: the owner's confirmed number, else whole years of evidence.
            "suggested": confirmed["years"] if confirmed else int(evidence),
            "flag": abs(answer - evidence) >= DIVERGENCE_YEARS or (evidence == 0 and answer > 0),
        })
    return result


def _markdown(report, comparisons, today):
    lines = [f"# Skills by evidence (as of {today})", "",
             "Computed by scripts/skills.py from the `stack` of each entry in cv.yaml. "
             "`~` marks approximate durations. Confirmed values come from skills.yaml.", "",
             "| Skill | Years | First | Last | Confirmed | Where |", "|---|---|---|---|---|---|"]
    for r in report:
        years = f"{'~' if r['approx'] else ''}{r['years']}"
        confirmed = f"{r['confirmed']['years']} ({r['confirmed'].get('as_of', '?')})" if r["confirmed"] else ""
        lines.append(f"| {r['skill']} | {years} | {r['first'] or ''} | {r['last'] or ''} | {confirmed} | {', '.join(r['where'])} |")
    for source, rows in comparisons:
        lines += ["", f"## Self-reported vs evidence: {source}", "",
                  "| Asked about | Skill | Answered | Evidence | Suggested | Flag |", "|---|---|---|---|---|---|"]
        for c in sorted(rows, key=lambda c: (not c["flag"], c["skill"].casefold())):
            change = " ✏️" if c["suggested"] != c["answer"] else ""
            lines.append(f"| {c['question_skill']} | {c['skill']} | {c['answer']:g} | {c['evidence_years']:g} "
                         f"| {c['suggested']:g}{change} | {'⚠️' if c['flag'] else ''} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source")
    parser.add_argument("--config", action="append", required=True,
                        help="skills.yaml, then optional private overlays (repeatable)")
    parser.add_argument("--today", required=True, help="YYYY-MM")
    parser.add_argument("--json", required=True)
    parser.add_argument("--md", required=True)
    parser.add_argument("--claims-csv", action="append", default=[])
    parser.add_argument("--self-reported", action="append", default=[])
    args = parser.parse_args(argv)

    try:
        doc = load_cv(args.source)
        validate_cv(doc)
        config = merge_configs(*(read_config(path) for path in args.config))
    except CVError as err:
        print(f"skills: {err}", file=sys.stderr)
        return 1

    report = skill_report(doc, config, args.today)
    comparisons = []
    for path in args.claims_csv:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            claims = parse_screening(csv.DictReader(fh))
        comparisons.append((f"screening answers ({os.path.basename(path)})", compare_claims(claims, report, config)))
    for path in args.self_reported:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        as_of = data["as_of"]
        then = skill_report(doc, config, as_of)
        claims = [{"question_skill": k, "answer": float(v)} for k, v in data["skills"].items()]
        comparisons.append((f"{data['source']} (as of {as_of})", compare_claims(claims, then, config)))

    os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump({"as_of": args.today, "skills": report,
                   "comparisons": [{"source": s, "rows": r} for s, r in comparisons]}, fh, ensure_ascii=False, indent=2)
    with open(args.md, "w", encoding="utf-8") as fh:
        fh.write(_markdown(report, comparisons, args.today))
    flagged = sum(c["flag"] for _, rows in comparisons for c in rows)
    print(f"skills: {len(report)} skills with evidence; {flagged} self-reported answers diverge by {DIVERGENCE_YEARS}+ years "
          f"-> {args.md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
