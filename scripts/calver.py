"""Next release version, CalVer YYYY.MM.DD-NN.

Usage: calver.py --today YYYY-MM-DD --existing FILE

FILE lists existing tag and release names, one per line (drafts included). NN is one
more than the highest NN already used today. The names come from a file, not stdin,
because tools/run attaches no stdin.
"""

import argparse
import datetime
import re
import sys

CALVER = re.compile(r"^(\d{4}\.\d{2}\.\d{2})-(\d{2})$")


def next_version(today, existing):
    day = today.strftime("%Y.%m.%d")
    used = [
        int(match.group(2))
        for name in existing
        if (match := CALVER.match(name.strip())) and match.group(1) == day
    ]
    number = max(used, default=0) + 1
    if number > 99:
        raise ValueError(f"no CalVer number left for {day}")
    return f"{day}-{number:02d}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--today", required=True, type=datetime.date.fromisoformat)
    parser.add_argument("--existing", required=True)
    args = parser.parse_args(argv)
    with open(args.existing, encoding="utf-8") as fh:
        names = fh.read().splitlines()
    print(next_version(args.today, names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
