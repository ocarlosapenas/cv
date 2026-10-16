"""LinkedIn data export (CSV folder) -> draft YAML in cv.yaml shape, for human review.

Usage: linkedin_import.py private/linkedin/<date> --out private/drafts/linkedin-<date>.yaml

Runs offline on the official "Download your data" export; it never talks to LinkedIn.
LinkedIn does not document the CSV columns, so columns are matched by NAME (not
position) and a missing column fails loudly with the file and column name.
The output is a draft: nothing here goes into cv.yaml without review.
"""

import argparse
import csv
import os
import re
import sys

import yaml

from cvlib import MONTHS, CVError

REQUIRED = {
    "Profile.csv": ["First Name", "Last Name", "Headline", "Summary", "Geo Location"],
    "Positions.csv": ["Company Name", "Title", "Description", "Location", "Started On", "Finished On"],
    "Education.csv": ["School Name", "Start Date", "End Date", "Degree Name"],
    "Certifications.csv": ["Name", "Url", "Authority", "Started On"],
    "Skills.csv": ["Name"],
    "Volunteering.csv": ["Company Name", "Role", "Started On", "Finished On", "Description"],
}


def _clean(value):
    return " ".join((value or "").split())


def read_csv(folder, name):
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = [c.strip() for c in reader.fieldnames or []]
        missing = [c for c in REQUIRED[name] if c not in columns]
        if missing:
            raise CVError(f"{name}: missing column(s) {', '.join(missing)} (found: {', '.join(columns)})")
        return [{k.strip(): _clean(v) for k, v in row.items() if k} for row in reader]


def li_date(value):
    value = _clean(value)
    if not value:
        return None
    if re.fullmatch(r"\d{4}", value):
        return value
    match = re.fullmatch(r"([A-Z][a-z]{2}) (\d{4})", value)
    if not match or match.group(1) not in MONTHS:
        raise CVError(f"unrecognized LinkedIn date {value!r} (expected 'Jul 2023' or '2023')")
    return f"{match.group(2)}-{MONTHS.index(match.group(1)) + 1:02d}"


def split_description(text):
    """Split LinkedIn's inline ' - ' bullets into (summary, bullets)."""
    parts = [_clean(p) for p in re.split(r"(?:^|\s+)-\s*", _clean(text))]
    summary = parts[0] or None
    return summary, [p for p in parts[1:] if p]


def _dated(entry, start, end):
    if start:
        entry["startDate"] = start
    if end:
        entry["endDate"] = end
    return entry


def import_export(folder):
    draft = {}

    profile = read_csv(folder, "Profile.csv")
    if profile:
        row = profile[0]
        place = [p.strip() for p in row["Geo Location"].split(",") if p.strip()]
        keys = ["city", "region", "country"] if len(place) == 3 else ["city", "country"]
        draft["basics"] = {
            "name": f"{row['First Name']} {row['Last Name']}".strip(),
            "label": row["Headline"],
            "summary": row["Summary"],
            "location": dict(zip(keys, place)),
        }

    positions = read_csv(folder, "Positions.csv")
    if positions is not None:
        draft["work"] = []
        for row in positions:
            summary, bullets = split_description(row["Description"])
            entry = {"name": row["Company Name"], "position": row["Title"], "location": row["Location"]}
            _dated(entry, li_date(row["Started On"]), li_date(row["Finished On"]))
            if summary:
                entry["summary"] = summary
            if bullets:
                entry["highlights"] = bullets
            draft["work"].append(entry)

    volunteering = read_csv(folder, "Volunteering.csv")
    if volunteering is not None:
        draft["volunteer"] = []
        for row in volunteering:
            summary, bullets = split_description(row["Description"])
            entry = {"organization": row["Company Name"], "position": row["Role"]}
            _dated(entry, li_date(row["Started On"]), li_date(row["Finished On"]))
            if summary:
                entry["summary"] = summary
            if bullets:
                entry["highlights"] = bullets
            draft["volunteer"].append(entry)

    education = read_csv(folder, "Education.csv")
    if education is not None:
        draft["education"] = []
        for row in education:
            entry = {"institution": row["School Name"], "studyType": row["Degree Name"]}
            _dated(entry, li_date(row["Start Date"]), li_date(row["End Date"]))
            if row.get("Activities"):
                entry["activities"] = row["Activities"]
            draft["education"].append(entry)

    certificates = read_csv(folder, "Certifications.csv")
    if certificates is not None:
        draft["certificates"] = []
        for row in certificates:
            entry = {"name": row["Name"], "issuer": row["Authority"], "date": li_date(row["Started On"])}
            if row["Url"]:
                entry["url"] = row["Url"]
            draft["certificates"].append({k: v for k, v in entry.items() if v})

    skills = read_csv(folder, "Skills.csv")
    if skills is not None:
        seen, keywords = set(), []
        for row in skills:
            if row["Name"] and row["Name"].casefold() not in seen:
                seen.add(row["Name"].casefold())
                keywords.append(row["Name"])
        draft["skills"] = [{"name": "LinkedIn", "keywords": keywords}]

    return draft


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", help="unzipped LinkedIn export folder (inside the repository)")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        draft = import_export(args.folder)
    except CVError as err:
        print(f"linkedin_import: {err}", file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("# DRAFT imported from the LinkedIn data export. Review before copying into cv.yaml.\n")
        yaml.safe_dump(draft, fh, sort_keys=False, allow_unicode=True, width=1000)
    counts = ", ".join(f"{k}: {len(v)}" for k, v in draft.items() if isinstance(v, list))
    print(f"linkedin_import: wrote {args.out} ({counts})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
