"""Release asset names, copies and verification.

Usage:
  release_assets.py --copy build --out build/release --tag TAG [--variants "backend ai fde"]
  release_assets.py --verify DIR --tag TAG [--variants "backend ai fde"]

Each published variant gets a constant name, so that
`releases/latest/download/<name>` is a stable link, plus a dated copy with the same
bytes. --verify also checks that the version is printed on every page of every PDF.
"""

import argparse
import filecmp
import os
import re
import shutil
import subprocess
import sys

from check_pdf import version_on_every_page
from cvlib import load_cv

LABELS = {"backend": "Backend", "ai": "AI", "fde": "FDE"}


def asset_names(name, tag, variants):
    stem = "-".join(name.split()) + "-Resume"
    return {
        v: (f"{stem}-{LABELS[v]}.pdf", f"{stem}-{LABELS[v]}-{tag}.pdf")
        for v in variants
    }


def copy_assets(build_dir, out_dir, name, tag, variants):
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for variant, pair in asset_names(name, tag, variants).items():
        source = os.path.join(build_dir, variant, "cv.pdf")
        for filename in pair:
            target = os.path.join(out_dir, filename)
            shutil.copyfile(source, target)
            written.append(target)
    return written


def verify_assets(directory, name, tag, variants):
    names = asset_names(name, tag, variants)
    expected = {f for pair in names.values() for f in pair}
    present = set(os.listdir(directory))
    problems = [f"missing {f}" for f in sorted(expected - present)]
    problems += [f"unexpected file {f}" for f in sorted(present - expected)]
    for constant, dated in names.values():
        if {constant, dated} <= present and not filecmp.cmp(
            os.path.join(directory, constant), os.path.join(directory, dated), shallow=False
        ):
            problems.append(f"{constant} differs from {dated}")
    return problems


def _pdf_text(path):
    proc = subprocess.run(["pdftotext", "-raw", "-enc", "UTF-8", path, "-"], capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    return proc.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--copy", metavar="BUILD_DIR")
    mode.add_argument("--verify", metavar="DIR")
    parser.add_argument("--out", default="build/release")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--variants", default="backend,ai,fde")
    parser.add_argument("--cv", default="cv.yaml")
    args = parser.parse_args(argv)

    name = load_cv(args.cv)["basics"]["name"]
    variants = [v for v in re.split(r"[,\s]+", args.variants) if v]

    if args.copy:
        for path in copy_assets(args.copy, args.out, name, args.tag, variants):
            print(f"release asset: {path}")
        return 0

    problems = verify_assets(args.verify, name, args.tag, variants)
    for filename in sorted(os.listdir(args.verify)):
        if not filename.endswith(".pdf"):
            continue
        text = _pdf_text(os.path.join(args.verify, filename))
        if text is None:
            problems.append(f"{filename}: pdftotext failed")
            continue
        missing = version_on_every_page(args.tag, text)
        if missing:
            problems.append(f"{filename}: version {args.tag} missing on page(s) {','.join(map(str, missing))}")
    if problems:
        print("release assets: FAILED", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"release assets: OK ({len(variants)} variants, constant and dated names, version {args.tag} on every page)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
