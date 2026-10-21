"""Release gate: may this cv.yaml be published under this version?

Usage:
  release_gate.py cv.yaml --version YYYY.MM.DD-NN   exit 1 if blocked
  release_gate.py cv.yaml --report                  one Markdown line, always exit 0

Blocks a release when any claim in cv.yaml (in any variant, or in none) still has
`status: verify`, or when the version is not CalVer. The report mode feeds the PR
preview comment, where a pending claim is expected and must not fail the build.
"""

import argparse
import re
import sys

from cvlib import load_cv, pending_verify

CALVER = re.compile(r"^\d{4}\.\d{2}\.\d{2}-\d{2}$")


def report_line(pending):
    if not pending:
        return "**Release gate:** ✅ ready, no claims pending verification."
    noun = "claim" if len(pending) == 1 else "claims"
    return (f"**Release gate:** ⛔ blocked, {len(pending)} {noun} pending verification: "
            + ", ".join(f"`{p}`" for p in pending))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cv")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--version")
    mode.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    pending = pending_verify(load_cv(args.cv))
    if args.report:
        print(report_line(pending))
        return 0

    problems = []
    if not CALVER.match(args.version):
        problems.append(f"{args.version!r} is not a CalVer version (YYYY.MM.DD-NN)")
    problems += [f"{p}: claim pending verification" for p in pending]
    if problems:
        print("release gate: BLOCKED", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"release gate: OK ({args.version}, no claims pending verification)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
