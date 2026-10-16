"""Render model -> pure JSON Resume (validated against the vendored 1.3.1 schema)."""

import argparse
import json
import os
import sys

import jsonschema

from cvlib import ROOT, CVError, format_path

JSONRESUME_SCHEMA = os.path.join(ROOT, "schemas", "jsonresume-1.3.1.schema.json")


def _keep(entry, keys):
    return {k: entry[k] for k in keys if entry.get(k) not in (None, [], "")}


def _texts(highlights):
    return [h["text"] for h in highlights]


def to_jsonresume(model):
    b = model["basics"]
    basics = _keep(b, ("name", "label", "email", "phone", "url", "summary"))
    basics["location"] = _keep(b["location"], ("city", "region", "countryCode"))
    basics["profiles"] = [_keep(p, ("network", "username", "url")) for p in b.get("profiles", [])]

    out = {
        "basics": basics,
        "work": [
            {**_keep(w, ("name", "position", "url", "location", "startDate", "endDate", "summary")),
             **({"highlights": _texts(w["highlights"])} if w["highlights"] else {})}
            for w in model["work"]
        ],
        "projects": [
            {**_keep(p, ("name", "description", "url", "startDate", "endDate", "keywords")),
             **({"highlights": _texts(p["highlights"])} if p["highlights"] else {})}
            for p in model["projects"]
        ],
        "volunteer": [
            {**_keep(v, ("organization", "position", "url", "startDate", "endDate", "summary")),
             **({"highlights": _texts(v["highlights"])} if v["highlights"] else {})}
            for v in model["volunteer"]
        ],
        "education": [
            _keep(e, ("institution", "url", "area", "studyType", "startDate", "endDate"))
            for e in model["education"]
        ],
        "certificates": [_keep(c, ("name", "date", "url", "issuer")) for c in model["certificates"]],
        "skills": [_keep(s, ("name", "keywords")) for s in model["skills"]],
        "languages": [_keep(lang, ("language", "fluency")) for lang in model["languages"]],
        "meta": {"version": model["meta"]["version"]},
    }
    return {k: v for k, v in out.items() if v not in ([], {})}


def validate_jsonresume(doc, schema_path=JSONRESUME_SCHEMA):
    with open(schema_path, encoding="utf-8") as fh:
        schema = json.load(fh)
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    if errors:
        lines = [f"{format_path(e.absolute_path)}: {e.message}" for e in errors]
        raise CVError("JSON Resume export is invalid:\n  " + "\n  ".join(lines))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", help="build/<variant>/resolved.json")
    parser.add_argument("out", help="build/<variant>/resume.json")
    args = parser.parse_args(argv)

    with open(args.model, encoding="utf-8") as fh:
        model = json.load(fh)
    doc = to_jsonresume(model)
    try:
        validate_jsonresume(doc)
    except CVError as err:
        print(f"export_jsonresume: {err}", file=sys.stderr)
        return 1
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
