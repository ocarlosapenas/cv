"""Load, validate and resolve cv.yaml into a per-variant render model.

The render model (build/<variant>/resolved.json) is the only input of every output:
the Typst template, the JSON Resume export and the checks. Variant logic lives here
and nowhere else.
"""

import datetime
import json
import os
import re

import jsonschema
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SCHEMA = os.path.join(ROOT, "schemas", "cv.schema.json")

SECTION_TITLES = {
    "summary": "Summary",
    "skills": "Skills",
    "work": "Experience",
    "projects": "Projects",
    "volunteer": "Volunteer",
    "education": "Education",
    "certificates": "Certifications",
    "languages": "Languages",
}

PRIVATE_KEYS = {"phone", "email"}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class CVError(Exception):
    """A problem in cv.yaml or in a private file, with a readable location."""


def load_cv(path):
    with open(path, encoding="utf-8") as fh:
        return _stringify_dates(yaml.safe_load(fh))


def _stringify_dates(node):
    # YAML turns an unquoted 2023-07-01 into a date object; the schema wants text.
    if isinstance(node, dict):
        return {k: _stringify_dates(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_stringify_dates(v) for v in node]
    if isinstance(node, (datetime.date, datetime.datetime)):
        return node.isoformat()
    return node


def format_path(parts):
    out = ""
    for part in parts:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out or "(root)"


def validate_cv(doc, schema_path=DEFAULT_SCHEMA):
    with open(schema_path, encoding="utf-8") as fh:
        schema = json.load(fh)
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    if errors:
        lines = [f"{format_path(e.absolute_path)}: {e.message}" for e in errors]
        raise CVError("cv.yaml does not match the schema:\n  " + "\n  ".join(lines))

    variants = set(doc["meta"]["variants"])
    problems = []
    _check_variant_names(doc, [], variants, problems)
    if problems:
        raise CVError("cv.yaml uses undeclared variants:\n  " + "\n  ".join(problems))


def _check_variant_names(node, path, variants, problems):
    declared = ", ".join(sorted(variants))
    if isinstance(node, dict):
        if "default" in node:
            # Only per-variant values may have a "default" key (the schema forbids it
            # everywhere else), so every other key here must be a declared variant.
            for key in node:
                if key != "default" and key not in variants:
                    problems.append(f"{format_path(path)}: unknown variant '{key}' (declared: {declared})")
        for tag in node.get("tags", []) if isinstance(node.get("tags"), list) else []:
            if tag not in variants:
                problems.append(f"{format_path(path)}.tags: unknown variant '{tag}' (declared: {declared})")
        for key, value in node.items():
            if key != "meta":
                _check_variant_names(value, path + [key], variants, problems)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _check_variant_names(value, path + [i], variants, problems)


def _text(value):
    return " ".join(value.split()) if isinstance(value, str) else value


def _pick(value, variant):
    if isinstance(value, dict):
        value = value.get(variant, value["default"])
    return _text(value)


def _included(item, variant):
    return not isinstance(item, dict) or "tags" not in item or variant in item["tags"]


def format_date(value):
    parts = value.split("-")
    if len(parts) == 1:
        return parts[0]
    return f"{MONTHS[int(parts[1]) - 1]} {parts[0]}"


def date_range(start, end, open_ended=True):
    if not start:
        return format_date(end) if end else None
    if end:
        return f"{format_date(start)} – {format_date(end)}"
    return f"{format_date(start)} – Present" if open_ended else format_date(start)


def _bullets(items, variant):
    out = []
    for item in items or []:
        if not _included(item, variant):
            continue
        if isinstance(item, str):
            out.append({"text": _text(item), "status": None})
        else:
            out.append({"text": _text(item["text"]), "status": item.get("status")})
    return out


def _display_url(url):
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


def _drop_none(entry):
    return {k: v for k, v in entry.items() if v is not None}


def resolve(doc, variant, version="dev", private=None):
    variants = doc["meta"]["variants"]
    if variant not in variants:
        raise CVError(f"unknown variant '{variant}' (declared: {', '.join(sorted(variants))})")
    config = variants[variant]
    b = doc["basics"]

    loc = b["location"]
    place = ", ".join(_text(loc[k]) for k in ("city", "region", "country") if loc.get(k))
    location_line = " · ".join(p for p in (place, _text(loc.get("remote")), _text(loc.get("timezone"))) if p)

    basics = _drop_none({
        "name": _text(b["name"]),
        "label": _pick(b["label"], variant),
        "email": b["email"],
        "url": b.get("url"),
        "url_display": _display_url(b["url"]) if b.get("url") else None,
        "summary": _pick(b["summary"], variant) if b.get("summary") else None,
        "location": {k: _text(v) for k, v in loc.items()},
        "location_line": location_line,
        "profiles": [
            {**p, "display": _display_url(p["url"])} for p in b.get("profiles", [])
        ],
    })

    if private is not None:
        unknown = set(private) - PRIVATE_KEYS
        if unknown:
            raise CVError(f"private file: unsupported keys {sorted(unknown)} (allowed: {sorted(PRIVATE_KEYS)})")
        basics.update({k: _text(str(v)) for k, v in private.items()})

    work = []
    for w in doc.get("work", []):
        if not _included(w, variant):
            continue
        compact = bool(w.get("compact"))
        work.append(_drop_none({
            "name": _text(w["name"]),
            "position": _pick(w["position"], variant),
            "url": w.get("url"),
            "location": _text(w.get("location")),
            "startDate": w["startDate"],
            "endDate": w.get("endDate"),
            "dates": date_range(w["startDate"], w.get("endDate")),
            "summary": _pick(w["summary"], variant) if w.get("summary") else None,
            "highlights": _bullets(w.get("highlights"), variant),
            "compact": compact,
        }))

    projects = []
    for p in doc.get("projects", []):
        if not _included(p, variant):
            continue
        projects.append(_drop_none({
            "name": _text(p["name"]),
            "description": _pick(p["description"], variant) if p.get("description") else None,
            "url": p.get("url"),
            "url_display": _display_url(p["url"]) if p.get("url") else None,
            "startDate": p.get("startDate"),
            "endDate": p.get("endDate"),
            "dates": date_range(p.get("startDate"), p.get("endDate")),
            "highlights": _bullets(p.get("highlights"), variant),
            "keywords": [_text(k) for k in p.get("keywords", [])],
        }))

    volunteer = [
        _drop_none({
            "organization": _text(v["organization"]),
            "position": _pick(v["position"], variant),
            "url": v.get("url"),
            "startDate": v["startDate"],
            "endDate": v.get("endDate"),
            "dates": date_range(v["startDate"], v.get("endDate")),
            "summary": _pick(v["summary"], variant) if v.get("summary") else None,
            "highlights": _bullets(v.get("highlights"), variant),
        })
        for v in doc.get("volunteer", []) if _included(v, variant)
    ]

    education = [
        _drop_none({
            "institution": _text(e["institution"]),
            "area": _text(e.get("area")),
            "studyType": _text(e.get("studyType")),
            "url": e.get("url"),
            "startDate": e.get("startDate"),
            "endDate": e.get("endDate"),
            "dates": date_range(e.get("startDate"), e.get("endDate")),
        })
        for e in doc.get("education", []) if _included(e, variant)
    ]

    certificates = [
        _drop_none({
            "name": _text(c["name"]),
            "issuer": _text(c.get("issuer")),
            "date": c.get("date"),
            "date_display": format_date(c["date"]) if c.get("date") else None,
            "url": c.get("url"),
        })
        for c in doc.get("certificates", []) if _included(c, variant)
    ]

    skills = [
        {"name": _text(s["name"]), "keywords": [_text(k) for k in s["keywords"]]}
        for s in doc.get("skills", []) if _included(s, variant)
    ]

    languages = [
        {"language": _text(lang["language"]), "fluency": _text(lang["fluency"])}
        for lang in doc.get("languages", []) if _included(lang, variant)
    ]

    content = {
        "summary": basics.get("summary"),
        "skills": skills,
        "work": work,
        "projects": projects,
        "volunteer": volunteer,
        "education": education,
        "certificates": certificates,
        "languages": languages,
    }
    sections = [
        {"key": key, "title": SECTION_TITLES[key]}
        for key in config["sections"] if content[key]
    ]

    verify_count = sum(
        1
        for entry in work + projects + volunteer
        for h in entry.get("highlights", [])
        if h["status"] == "verify"
    )

    return {
        "meta": {
            "variant": variant,
            "version": version,
            "title": f"{basics['name']} Resume",
            "max_pages": config.get("max_pages", 2),
            "verify_count": verify_count,
        },
        "basics": basics,
        "sections": sections,
        "work": work,
        "projects": projects,
        "volunteer": volunteer,
        "education": education,
        "certificates": certificates,
        "skills": skills,
        "languages": languages,
    }


def load_private(path):
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise CVError(f"{path}: expected a mapping")
    return data
