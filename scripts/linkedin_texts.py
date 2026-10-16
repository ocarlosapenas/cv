"""Paste-ready LinkedIn texts from the `linkedin` render model, with limit checks.

Usage:
  linkedin_texts.py build/linkedin/resolved.json --config skills.yaml [--config private/...]
                    [--current build/linkedin/current.yaml] --out build/linkedin

Writes profile.md (every field in a copyable block, with character counts), one .txt per
long field, and, when the current profile is given (a draft from linkedin_import.py),
checklist.md with what to change on LinkedIn. Nothing here talks to LinkedIn: every
edit is pasted by hand. Exits 1 if any field is over its limit.
"""

import argparse
import json
import os
import re
import sys
import unicodedata

import yaml

from skills import canonical, merge_configs, read_config

# Character limits. Sources (see the Phase 0 research): LinkedIn Help for the number of
# skills; third-party measurements (Sept 2026) for the others. Fields marked "assumed"
# have no published limit; the experience limit is applied to them as a safe default.
LIMITS = {"headline": 220, "about": 2600, "title": 100, "company": 100, "location": 100, "description": 2000, "skills_count": 100}
ASSUMED = {"volunteer description", "project description"}
NEAR = 0.95


def format_description(entry):
    parts = []
    if entry.get("summary"):
        parts.append(entry["summary"])
    bullets = "\n".join(f"• {h['text']}" for h in entry.get("highlights", []))
    if bullets:
        parts.append(bullets)
    return "\n\n".join(parts)


def build_texts(model, config):
    b = model["basics"]
    return {
        "headline": b["label"],
        "about": b.get("summary", ""),
        "experience": [
            {"company": w["name"], "title": w["position"], "location": w.get("location", ""),
             "start": w["startDate"], "end": w.get("endDate"),
             "description": "" if w.get("compact") else format_description(w)}
            for w in model["work"]
        ],
        "volunteer": [
            {"organization": v["organization"], "role": v["position"], "start": v["startDate"], "end": v.get("endDate"),
             "description": format_description(v)}
            for v in model.get("volunteer", [])
        ],
        "projects": [
            {"name": p["name"], "url": p.get("url"), "start": p.get("startDate"), "end": p.get("endDate"),
             "description": format_description({"summary": p.get("description"), "highlights": p.get("highlights", [])})}
            for p in model.get("projects", [])
        ],
        "education": [
            {"school": e["institution"], "degree": e.get("studyType", ""), "field": e.get("area", ""),
             "start": e.get("startDate"), "end": e.get("endDate")}
            for e in model.get("education", [])
        ],
        "certificates": [
            {"name": c["name"], "issuer": c.get("issuer", ""), "date": c.get("date"), "url": c.get("url")}
            for c in model.get("certificates", [])
        ],
        "skills": list(config["linkedin_skills"]),
    }


def _row(field, text, limit):
    length = len(text or "")
    status = "over" if length > limit else "near" if length > NEAR * limit else "ok"
    return {"field": field, "length": length, "limit": limit, "status": status}


def check_limits(texts):
    rows = [_row("headline", texts["headline"], LIMITS["headline"]), _row("about", texts["about"], LIMITS["about"])]
    for e in texts.get("experience", []):
        for key in ("title", "company", "location", "description"):
            rows.append(_row(f"experience[{e['company']}].{key}", e[key], LIMITS[key]))
    for v in texts.get("volunteer", []):
        rows.append(_row(f"volunteer[{v['organization']}].role", v["role"], LIMITS["title"]))
        rows.append(_row(f"volunteer[{v['organization']}].description", v["description"], LIMITS["description"]))
    for p in texts.get("projects", []):
        rows.append(_row(f"project[{p['name']}].description", p["description"], LIMITS["description"]))
    count = len(texts.get("skills", []))
    rows.append({"field": "skills (count)", "length": count, "limit": LIMITS["skills_count"],
                 "status": "over" if count > LIMITS["skills_count"] else "ok"})
    return rows


def _fold(text):
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in text if not unicodedata.combining(ch)).casefold().strip()


def _norm(text):
    return " ".join((text or "").split())


def _match(items, current, start_key="startDate", name_key="name"):
    """Pair each CV item with a current LinkedIn item: same start date, else same name."""
    pairs, used = [], set()
    for item in items:
        found = None
        for i, cur in enumerate(current):
            if i not in used and item.get("start") and cur.get(start_key) == item["start"]:
                found = i
                break
        if found is None:
            for i, cur in enumerate(current):
                if i not in used and _fold(cur.get(name_key)) == _fold(item.get("company") or item.get("organization") or item.get("school") or item.get("name")):
                    found = i
                    break
        if found is not None:
            used.add(found)
        pairs.append((item, current[found] if found is not None else None))
    leftovers = [cur for i, cur in enumerate(current) if i not in used]
    return pairs, leftovers


def _changes(pairs, fields):
    out = []
    for item, cur in pairs:
        name = item.get("company") or item.get("organization") or item.get("school") or item.get("name")
        if cur is None:
            out.append({"company": name, "linkedin_company": None, "changes": ["add this entry"]})
            continue
        changes = []
        for label, mine, theirs in fields(item, cur):
            # An empty CV field (e.g. a compact line) keeps what LinkedIn has; only the end
            # date is meaningful when empty (a current role).
            if not mine and label != "end":
                continue
            if _norm(mine) != _norm(theirs):
                if label == "description":
                    changes.append(f"description: replace ({len(mine or '')} chars)")
                else:
                    changes.append(f"{label}: {theirs or '(empty)'} -> {mine or '(empty)'}")
        current_name = cur.get("name") or cur.get("organization") or cur.get("institution")
        out.append({"company": name, "linkedin_company": current_name, "changes": changes})
    return out


def checklist(texts, current, config):
    work_pairs, work_left = _match(texts["experience"], current.get("work", []))
    vol_pairs, vol_left = _match(texts["volunteer"], current.get("volunteer", []), name_key="organization")
    edu_pairs, edu_left = _match(texts["education"], current.get("education", []), name_key="institution")
    cert_pairs, cert_left = _match(texts["certificates"], current.get("certificates", []), start_key="date")

    def describe(cur, who="position"):
        name = cur.get("name") or cur.get("organization") or cur.get("institution")
        role = cur.get(who) or cur.get("studyType") or ""
        return f"{name} ({role}, {cur.get('startDate') or cur.get('date') or '?'} to {cur.get('endDate') or 'present'})"

    current_skills = current.get("skills_raw") or [k for group in current.get("skills", []) for k in group.get("keywords", [])]
    wanted = {canonical(s, config).casefold() for s in texts["skills"]}
    have, remove = set(), []
    for skill in current_skills:
        key = canonical(skill, config).casefold()
        if key in have:
            remove.append(f"{skill} (duplicate)")
        elif key not in wanted:
            remove.append(skill)
        have.add(key)
    add = [s for s in texts["skills"] if canonical(s, config).casefold() not in have]

    basics = current.get("basics", {})
    return {
        "headline": {"current": basics.get("label"), "new": texts["headline"]},
        "about": {"current": basics.get("summary"), "new": texts["about"]},
        "experience": _changes(work_pairs, lambda m, c: [
            # Company names are not compared: on LinkedIn they point to a company page.
            ("title", m["title"], c.get("position")), ("start", m["start"], c.get("startDate")), ("end", m["end"], c.get("endDate")),
            ("location", m["location"], c.get("location")),
            ("description", m["description"], format_description({"summary": c.get("summary"), "highlights": [{"text": h} for h in c.get("highlights", [])]})),
        ]),
        "linkedin_only": [describe(c) for c in work_left],
        "volunteer": _changes(vol_pairs, lambda m, c: [
            ("role", m["role"], c.get("position")), ("start", m["start"], c.get("startDate")), ("end", m["end"], c.get("endDate")),
            ("description", m["description"], format_description({"summary": c.get("summary"), "highlights": [{"text": h} for h in c.get("highlights", [])]})),
        ]),
        "volunteer_linkedin_only": [describe(c) for c in vol_left],
        "education": _changes(edu_pairs, lambda m, c: [
            ("degree", m["degree"], c.get("studyType")), ("start", m["start"], c.get("startDate")), ("end", m["end"], c.get("endDate")),
        ]),
        "education_linkedin_only": [describe(c, "studyType") for c in edu_left],
        "certificates": _changes(cert_pairs, lambda m, c: [("name", m["name"], c.get("name"))]),
        "certificates_linkedin_only": [f"{c.get('name')} ({c.get('issuer', '')}, {c.get('date') or '?'})" for c in cert_left],
        "skills_add": add,
        "skills_remove": remove,
    }


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", _fold(text)).strip("-")[:40]


def _block(title, text, limit=None):
    count = f" ({len(text or '')}" + (f" / {limit})" if limit else ")")
    return [f"### {title}{count}", "", "```text", text or "", "```", ""]


def write_outputs(texts, limits, items, out):
    os.makedirs(out, exist_ok=True)
    lines = ["# LinkedIn profile texts", "", "Paste each block into the matching LinkedIn field. Generated from cv.yaml (target `linkedin`).", ""]
    lines += _block("Headline", texts["headline"], LIMITS["headline"]) + _block("About", texts["about"], LIMITS["about"])
    lines += ["## Experience", ""]
    for i, e in enumerate(texts["experience"], 1):
        period = f"{e['start']} to {e['end'] or 'present'}"
        lines += [f"**{e['title']}** at **{e['company']}** · {e['location'] or 'no location'} · {period}", ""]
        if e["description"]:
            lines += _block(f"Description: {e['company']}", e["description"], LIMITS["description"])
            with open(os.path.join(out, f"experience-{i:02d}-{_slug(e['company'])}.txt"), "w", encoding="utf-8") as fh:
                fh.write(e["description"] + "\n")
    lines += ["## Volunteer", ""]
    for v in texts["volunteer"]:
        lines += [f"**{v['role']}** at **{v['organization']}** · {v['start']} to {v['end'] or 'present'}", ""]
        lines += _block(f"Description: {v['organization']}", v["description"], LIMITS["description"])
    lines += ["## Projects", ""]
    for p in texts["projects"]:
        lines += [f"**{p['name']}** · {p['url'] or 'no link'}", ""] + _block(f"Description: {p['name']}", p["description"], LIMITS["description"])
    lines += ["## Education", ""] + [f"- **{e['school']}**: {e['degree']}, {e['field']} ({e['start']} to {e['end']})" for e in texts["education"]] + [""]
    lines += ["## Certifications", ""] + [f"- **{c['name']}**, {c['issuer']} ({c['date']}) {c['url'] or ''}" for c in texts["certificates"]] + [""]
    lines += [f"## Skills ({len(texts['skills'])} / {LIMITS['skills_count']}, in this order; pin the first 3)", ""]
    lines += [", ".join(texts["skills"]), ""]
    with open(os.path.join(out, "profile.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    for name in ("headline", "about"):
        with open(os.path.join(out, f"{name}.txt"), "w", encoding="utf-8") as fh:
            fh.write(texts[name] + "\n")

    if items is not None:
        c = ["# LinkedIn update checklist", "", "Current profile (from the data export) versus cv.yaml. Every edit is manual.", ""]
        for key in ("headline", "about"):
            same = _norm(items[key]["current"]) == _norm(items[key]["new"])
            c.append(f"- [{'x' if same else ' '}] {key.title()}: {'already up to date' if same else 'replace (see profile.md)'}")
        c += ["", "## Experience", ""]
        for e in items["experience"]:
            mark = "x" if not e["changes"] else " "
            c.append(f"- [{mark}] {e['company']}" + (f" (LinkedIn: {e['linkedin_company']})" if e["linkedin_company"] and e["linkedin_company"] != e["company"] else ""))
            c += [f"  - {ch}" for ch in e["changes"]]
        c += ["", "On LinkedIn but not on the CV (keep or remove, your call):", ""]
        c += [f"- [ ] {x}" for x in items["linkedin_only"]] or ["- none"]
        for section in ("volunteer", "education", "certificates"):
            c += ["", f"## {section.title()}", ""]
            for e in items[section]:
                c.append(f"- [{'x' if not e['changes'] else ' '}] {e['company']}")
                c += [f"  - {ch}" for ch in e["changes"]]
            extra = items[f"{section}_linkedin_only"]
            if extra:
                c += ["", "On LinkedIn but not on the CV:"] + [f"- [ ] {x}" for x in extra]
        c += ["", "## Skills", "", "Add: " + (", ".join(items["skills_add"]) or "none"),
              "", "Remove: " + (", ".join(items["skills_remove"]) or "none"), ""]
        with open(os.path.join(out, "checklist.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(c))

    over = [r for r in limits if r["status"] == "over"]
    near = [r for r in limits if r["status"] == "near"]
    for r in over + near:
        print(f"linkedin_texts: {r['status'].upper()} {r['field']}: {r['length']}/{r['limit']}", file=sys.stderr)
    return over


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model")
    parser.add_argument("--config", action="append", required=True)
    parser.add_argument("--current", help="current profile draft from linkedin_import.py")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    with open(args.model, encoding="utf-8") as fh:
        model = json.load(fh)
    config = merge_configs(*(read_config(path) for path in args.config))
    texts = build_texts(model, config)
    limits = check_limits(texts)
    items = None
    if args.current:
        with open(args.current, encoding="utf-8") as fh:
            items = checklist(texts, yaml.safe_load(fh) or {}, config)
    over = write_outputs(texts, limits, items, args.out)
    longest = max(limits, key=lambda r: r["length"] / r["limit"])
    print(f"linkedin_texts: wrote {args.out}/profile.md{' and checklist.md' if items else ''}; "
          f"{len(limits)} fields checked, {len(over)} over the limit; tightest: {longest['field']} {longest['length']}/{longest['limit']}")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
