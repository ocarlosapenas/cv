"""Markdown body of the sticky PR preview comment.

Usage: pr_comment.py --dir build/preview --variants "backend ai fde" --gate FILE --out FILE

Reads, per variant, the page PNGs (<v>-page-<n>.png), the visual diff
(<v>-diff.json, from pdf_diff.py) and the text diff (<v>.diff). Image references are
plain file names; `gh pr comment --attach` uploads those files and rewrites the links.
"""

import argparse
import json
import os
import sys

from pdf_diff import pages

MARKER = "<!-- cv-preview -->"
NO_BASE = "No base build to compare with."
NO_CHANGES = "No visual or text changes."
TRUNCATED = "Diff truncated; the full diff is in the cv-preview artifact."


def _changed_pages(diff):
    return [p for p in diff if p["status"] != "same"]


def _details(name, diff_text):
    return f"<details><summary>{name}: text diff</summary>\n\n```diff\n{diff_text}```\n\n</details>"


def _truncate(diff_text, allowance):
    if len(diff_text) <= allowance:
        return diff_text
    cut = diff_text[:max(allowance, 0)]
    cut = cut[: cut.rfind("\n") + 1]
    return cut + f"... {TRUNCATED}\n"


def render(variants, text_diffs, gate, max_chars=60000):
    head = [MARKER, "## CV preview", "", "| Variant | Pages | Changed pages |", "|---|---|---|"]
    for v in variants:
        if v["diff"] is None:
            changed = "no base"
        else:
            changed = ", ".join(str(p["page"]) for p in _changed_pages(v["diff"])) or "none"
        head.append(f"| {v['name']} | {v['pages']}/{v['max_pages']} | {changed} |")
    head += ["", gate, ""]

    if any(v["diff"] is None for v in variants):
        head += [NO_BASE, ""]
    elif not any(_changed_pages(v["diff"]) for v in variants) and not any(
        text_diffs.get(v["name"], "").strip() for v in variants
    ):
        head += [NO_CHANGES, ""]

    sections, diffs = [], []
    for v in variants:
        name = v["name"]
        part = [f"### {name}", "", " ".join(f"![{name} page {n}]({f})" for n, f in enumerate(v["previews"], 1)), ""]
        overlays = [p for p in v["diff"] or [] if p["overlay"]]
        if overlays:
            part += ["Changes in red: " + " ".join(
                f"![{name} page {p['page']} changes]({os.path.basename(p['overlay'])})" for p in overlays
            ), ""]
        sections.append("\n".join(part))
        diff_text = text_diffs.get(name, "")
        diffs.append((name, diff_text if diff_text.strip() else ""))

    skeleton = "\n".join(head) + "\n" + "\n\n".join(sections)
    wanted = [(name, text) for name, text in diffs if text]
    overhead = sum(len(_details(name, "")) + 2 for name, _ in wanted) + len(TRUNCATED) * len(wanted) + 64
    allowance = (max_chars - len(skeleton) - overhead) // max(len(wanted), 1)

    body_sections = []
    for section, (name, text) in zip(sections, diffs):
        body_sections.append(section + ("\n" + _details(name, _truncate(text, allowance)) if text else ""))
    body = "\n".join(head) + "\n" + "\n\n".join(body_sections) + "\n"
    return body[:max_chars]


def _text_diff(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines(keepends=True)
    # Drop the git header (diff --git, index, ---, +++); keep from the first hunk on.
    for i, line in enumerate(lines):
        if line.startswith("@@"):
            return "".join(lines[i:])
    return ""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default="build/preview")
    parser.add_argument("--build", default="build")
    parser.add_argument("--variants", default="backend ai fde")
    parser.add_argument("--gate", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    variants, text_diffs = [], {}
    for name in args.variants.split():
        with open(os.path.join(args.build, name, "resolved.json"), encoding="utf-8") as fh:
            max_pages = json.load(fh)["meta"]["max_pages"]
        previews = [os.path.basename(p) for p in pages(os.path.join(args.dir, f"{name}-page"))]
        diff_path = os.path.join(args.dir, f"{name}-diff.json")
        diff = None
        if os.path.exists(diff_path):
            with open(diff_path, encoding="utf-8") as fh:
                diff = json.load(fh)
        variants.append({"name": name, "pages": len(previews), "max_pages": max_pages,
                         "previews": previews, "diff": diff})
        text_diffs[name] = _text_diff(os.path.join(args.dir, f"{name}.diff"))
    with open(args.gate, encoding="utf-8") as fh:
        gate = fh.read().strip()

    body = render(variants, text_diffs, gate)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(body)
    print(f"pr_comment: wrote {args.out} ({len(body)} characters)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
