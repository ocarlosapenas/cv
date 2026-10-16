"""cv.yaml -> build/<variant>/resolved.json (the render model for one variant)."""

import argparse
import json
import os
import sys

from cvlib import CVError, load_cv, load_private, resolve, validate_cv


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="path to cv.yaml")
    parser.add_argument("--variant", required=True)
    parser.add_argument("--out", required=True, help="output JSON path")
    parser.add_argument("--version", default="dev")
    parser.add_argument("--private", help="private contact file (private builds only)")
    args = parser.parse_args(argv)

    try:
        doc = load_cv(args.source)
        validate_cv(doc)
        private = load_private(args.private) if args.private else None
        model = resolve(doc, args.variant, version=args.version, private=private)
    except CVError as err:
        print(f"resolve: {err}", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(model, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
