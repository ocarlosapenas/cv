"""Visual diff of two renders of the same CV, page by page.

Usage: pdf_diff.py --base PREFIX --head PREFIX --out DIR --json FILE

Pages are PNG files named <PREFIX>-<n>.png (pdftoppm output). For each changed or
added page, DIR receives <head page name>-changes.png: the new page with every changed
pixel tinted red. When no base page exists at all, FILE holds `null`.
"""

import argparse
import glob
import json
import os
import re
import sys

from PIL import Image, ImageChops

TINT = (255, 0, 0)


def _overlay_path(head_path, out_dir):
    stem = os.path.splitext(os.path.basename(head_path))[0]
    return os.path.join(out_dir, f"{stem}-changes.png")


def _tinted(image):
    return Image.blend(image, Image.new("RGB", image.size, TINT), 0.6)


def _compare(base_path, head_path, out_dir):
    base = Image.open(base_path).convert("RGB")
    head = Image.open(head_path).convert("RGB")
    if base.size != head.size:
        os.makedirs(out_dir, exist_ok=True)
        overlay = _overlay_path(head_path, out_dir)
        _tinted(head).save(overlay)
        return "changed", 1.0, overlay
    mask = ImageChops.difference(base, head).convert("L").point(lambda p: 255 if p else 0)
    changed = sum(1 for p in mask.getdata() if p)
    if not changed:
        return "same", 0.0, None
    os.makedirs(out_dir, exist_ok=True)
    overlay = _overlay_path(head_path, out_dir)
    Image.composite(_tinted(head), head, mask).save(overlay)
    return "changed", changed / (head.width * head.height), overlay


def compare_pages(base, head, out_dir):
    results = []
    for index in range(max(len(base), len(head))):
        number = index + 1
        if index >= len(head):
            results.append({"page": number, "status": "removed", "ratio": 1.0, "overlay": None})
            continue
        if index >= len(base):
            os.makedirs(out_dir, exist_ok=True)
            overlay = _overlay_path(head[index], out_dir)
            _tinted(Image.open(head[index]).convert("RGB")).save(overlay)
            results.append({"page": number, "status": "added", "ratio": 1.0, "overlay": overlay})
            continue
        status, ratio, overlay = _compare(base[index], head[index], out_dir)
        results.append({"page": number, "status": status, "ratio": ratio, "overlay": overlay})
    return results


def pages(prefix):
    found = []
    for path in glob.glob(f"{prefix}-*.png"):
        match = re.fullmatch(re.escape(prefix) + r"-(\d+)\.png", path)
        if match:
            found.append((int(match.group(1)), path))
    return [path for _, path in sorted(found)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--json", required=True)
    args = parser.parse_args(argv)

    base, head = pages(args.base), pages(args.head)
    result = compare_pages(base, head, args.out) if base else None
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
    changed = [p["page"] for p in result or [] if p["status"] != "same"]
    summary = "no base" if result is None else (f"changed pages {changed}" if changed else "no visual changes")
    print(f"pdf_diff {os.path.basename(args.head)}: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
