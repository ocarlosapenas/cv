"""Confidentiality scan of the whole git history, every ref included.

Usage: scan_history.py [--repo DIR] [--denylist FILE] [--private FILE]
                       [--require-denylist] [--report FILE]

Rewriting history does not remove what others already fetched, so before the
repository goes public every reachable object is checked, not only the current tree:

- every blob reachable from any ref (branches, tags, refs/pull/*), once per blob;
- every commit message and annotated tag message;
- every author and committer email, which must be a GitHub noreply address.

Findings name the deny-list line, the object and the location, never the term or the
email itself, so the output is safe in CI logs. Exit 1 on any finding.
"""

import argparse
import os
import re
import subprocess
import sys

import yaml

from check_denylist import load_denylist, phone_like, private_values_found, scan

NOREPLY = re.compile(r"(@users\.noreply\.github\.com|^noreply@github\.com)$")
# Fake phone numbers live on purpose in test fixtures, vendored schemas, examples and the
# plans that quote them. The deny-list and private-value checks still cover these paths.
PHONE_EXEMPT_PREFIXES = ("tests/", "schemas/", "docs/plans/")
PHONE_EXEMPT_SUFFIXES = (".example.yaml",)


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True).stdout


def _phone_checked(path):
    return not path.startswith(PHONE_EXEMPT_PREFIXES) and not path.endswith(PHONE_EXEMPT_SUFFIXES)


def _check_text(entries, private, label, text, phone=True):
    findings = scan(entries, label, text)
    if phone:
        findings += [f"phone-like number in {label}:{n}" for n in phone_like(text)]
    findings += [f"private '{key}' value found in {label}" for key in private_values_found(private, text)]
    return findings


def _blobs(repo):
    """(sha, first path seen) for every blob reachable from any ref."""
    listing = _git(repo, "rev-list", "--objects", "--all").decode("utf-8", "replace").splitlines()
    paths = {}
    for line in listing:
        sha, _, path = line.partition(" ")
        if path and sha not in paths:
            paths[sha] = path
    if not paths:
        return []
    batch = subprocess.run(
        ["git", "-C", repo, "cat-file", "--batch-check=%(objectname) %(objecttype)"],
        input="\n".join(paths).encode(), check=True, capture_output=True,
    ).stdout.decode().splitlines()
    return [(sha, paths[sha]) for sha, kind in (l.split() for l in batch) if kind == "blob"]


def scan_repo(repo, entries, private):
    findings = []
    blobs = _blobs(repo)
    binary = 0
    for sha, path in blobs:
        data = _git(repo, "cat-file", "blob", sha)
        if b"\0" in data[:8000]:
            binary += 1
            continue
        label = f"blob {sha[:7]} {path}"
        findings += _check_text(entries, private, label, data.decode("utf-8", "replace"), _phone_checked(path))

    log = _git(repo, "log", "--all", "--format=%H%x00%ae%x00%ce%x00%B%x1e").decode("utf-8", "replace")
    commits = [record.strip("\n") for record in log.split("\x1e") if record.strip()]
    identities = set()
    for record in commits:
        sha, author, committer, message = record.split("\x00", 3)
        findings += _check_text(entries, private, f"commit {sha[:7]} message", message)
        for role, email in (("author", author), ("committer", committer)):
            identities.add(email)
            if not NOREPLY.search(email):
                findings.append(f"commit {sha[:7]} {role} email is not a GitHub noreply address")

    tags = _git(repo, "for-each-ref", "--format=%(objectname)%00%(objecttype)%00%(contents)%1e", "refs/tags")
    tag_count = 0
    for record in tags.decode("utf-8", "replace").split("\x1e"):
        if not record.strip():
            continue
        sha, kind, contents = record.strip("\n").split("\x00", 2)
        if kind == "tag":
            tag_count += 1
            findings += _check_text(entries, private, f"tag {sha[:7]} message", contents)

    return {
        "blobs": len(blobs) - binary,
        "binary": binary,
        "commits": len(commits),
        "tags": tag_count,
        "identities": len(identities),
        "findings": findings,
    }


def report_markdown(result, entries_count):
    lines = [
        "# History scan",
        "",
        "| Source | Count |",
        "|---|---|",
        f"| Blobs scanned | {result['blobs']} |",
        f"| Binary blobs skipped | {result['binary']} |",
        f"| Commits (messages and emails) | {result['commits']} |",
        f"| Annotated tags | {result['tags']} |",
        f"| Distinct emails | {result['identities']} |",
        f"| Deny-list entries | {entries_count} |",
        f"| Findings | {len(result['findings'])} |",
        "",
    ]
    lines += [f"- {f}" for f in result["findings"]] or ["No findings."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--denylist")
    parser.add_argument("--private")
    parser.add_argument("--require-denylist", action="store_true")
    parser.add_argument("--report")
    args = parser.parse_args(argv)

    entries = []
    if args.denylist and os.path.exists(args.denylist):
        with open(args.denylist, encoding="utf-8") as fh:
            entries = load_denylist(fh.read())
    if args.require_denylist and not entries:
        print("scan_history: FAILED: deny-list required but missing or empty", file=sys.stderr)
        return 1
    if not entries:
        print("scan_history: note: no deny-list, confidential-term check SKIPPED", file=sys.stderr)
    private = {}
    if args.private and os.path.exists(args.private):
        with open(args.private, encoding="utf-8") as fh:
            private = yaml.safe_load(fh) or {}

    result = scan_repo(args.repo, entries, private)
    if args.report:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(report_markdown(result, len(entries)))
    summary = (f"{result['blobs']} blobs, {result['binary']} binary skipped, {result['commits']} commits, "
               f"{result['tags']} annotated tags, {result['identities']} emails, {len(entries)} deny-list entries")
    if result["findings"]:
        print(f"scan_history: FAILED ({summary})", file=sys.stderr)
        for finding in result["findings"]:
            print(f"  - {finding}", file=sys.stderr)
        return 1
    print(f"scan_history: OK ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
