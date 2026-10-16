"""Confidentiality checks over source and build files.

Usage: check_denylist.py [--public] [--denylist FILE] [--private FILE] FILE...

- Deny-list: one confidential term per line (`#` comments; `re:` prefix = regex).
  A match is reported by deny-list line number and file location, NEVER by the term,
  so the output is safe to show in CI logs.
- --public: also fail on phone-number-like text and on any value from the private
  contact file. Used for every build that may be published.
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass

import yaml

PHONE_CANDIDATE = re.compile(r"\+?\(?\d[\d\s().-]{6,}\d")
# ISO dates (2026-07-22, 2026-08) are removed before looking for phone numbers, so
# "1.3.1 (2026-07-22)" or "2025-11-03 to 2026-04-15" do not add up to ten digits. The
# real phone is still caught exactly by the private-value check.
ISO_DATE = re.compile(r"\b(?:19|20)\d{2}-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?\b")


@dataclass(frozen=True)
class Entry:
    line: int
    pattern: str
    regex: bool


def load_denylist(text):
    entries = []
    for number, raw in enumerate(text.splitlines(), 1):
        item = raw.strip()
        if not item or item.startswith("#"):
            continue
        if item.startswith("re:"):
            entries.append(Entry(number, item[3:], True))
        else:
            entries.append(Entry(number, item.casefold(), False))
    return entries


def _matches(entry, line):
    if entry.regex:
        return re.search(entry.pattern, line, re.IGNORECASE) is not None
    return entry.pattern in line.casefold()


def scan(entries, name, text):
    return [
        f"denylist line {entry.line} matched {name}:{lineno}"
        for lineno, line in enumerate(text.splitlines(), 1)
        for entry in entries
        if _matches(entry, line)
    ]


def phone_like(text):
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for match in PHONE_CANDIDATE.finditer(ISO_DATE.sub(" ", line)):
            if len(re.sub(r"\D", "", match.group())) >= 10:
                hits.append(lineno)
                break
    return hits


def private_values_found(private, text):
    folded = text.casefold()
    compact = re.sub(r"[\s().+-]", "", text)
    found = []
    for key, value in private.items():
        value = str(value)
        digits = re.sub(r"\D", "", value)
        if value.casefold() in folded or (len(digits) >= 8 and digits in compact):
            found.append(key)
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--public", action="store_true")
    parser.add_argument("--denylist")
    parser.add_argument("--private")
    parser.add_argument("files", nargs="+")
    args = parser.parse_args(argv)

    entries, notes = [], []
    if args.denylist and os.path.exists(args.denylist):
        with open(args.denylist, encoding="utf-8") as fh:
            entries = load_denylist(fh.read())
    else:
        where = f"at {args.denylist}" if args.denylist else "given (--denylist)"
        notes.append(f"no deny-list {where}, confidential-term check SKIPPED")

    private = {}
    if args.public and args.private and os.path.exists(args.private):
        with open(args.private, encoding="utf-8") as fh:
            private = yaml.safe_load(fh) or {}
    elif args.public:
        where = f"at {args.private}" if args.private else "given (--private)"
        notes.append(f"no private contact file {where}, private-value check SKIPPED")

    findings = []
    for path in args.files:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        findings += scan(entries, path, text)
        if args.public:
            findings += [f"phone-like number in {path}:{n}" for n in phone_like(text)]
            findings += [f"private '{key}' value found in {path}" for key in private_values_found(private, text)]

    for note in notes:
        print(f"check_denylist: note: {note}", file=sys.stderr)
    if findings:
        print("check_denylist: FAILED", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1
    print(f"check_denylist: OK ({len(args.files)} files, {len(entries)} deny-list entries"
          f"{', public guards on' if args.public else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
