"""ATS and metadata checks for one rendered variant.

Usage: check_pdf.py build/<variant>/resolved.json build/<variant>/cv.pdf

Text checks use `pdftotext -raw` (content-stream order, which is the tagged reading
order Typst writes). poppler's default layout mode moves right-aligned dates into a
separate block; commercial résumé parsers are built for that layout, a generic text
extractor is not, so order is asserted on the stream order instead.
"""

import json
import re
import subprocess
import sys

FORBIDDEN = [
    (0xFFFD, 0xFFFD),  # replacement character: a glyph with no Unicode mapping
    (0xE000, 0xF8FF),  # private use area: icon fonts
    (0xFB00, 0xFB06),  # ligatures that parsers read as one odd character
]


def parse_pdfinfo(text):
    info = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return info


def parse_pdffonts(text):
    fonts = []
    for line in text.splitlines()[2:]:
        parts = line.split()
        if len(parts) >= 6:
            fonts.append({"name": parts[0], "emb": parts[-5], "sub": parts[-4], "uni": parts[-3]})
    return fonts


def forbidden_chars(text):
    found = {f"U+{ord(ch):04X}" for ch in text if any(lo <= ord(ch) <= hi for lo, hi in FORBIDDEN)}
    return sorted(found)


def normalize(text):
    # A line break right after a hyphen is a wrap at a real hyphen ("multi-\nagent").
    # A word split by hyphenation ("data-\nbase") then fails the substring match.
    text = re.sub(r"-[ \t]*\n[ \t]*", "-", text)
    return " ".join(text.split())


def missing_bullets(model, text):
    haystack = normalize(text)
    return [
        h["text"]
        for entry in model["work"] + model["projects"] + model["volunteer"]
        for h in entry.get("highlights", [])
        if normalize(h["text"]) not in haystack
    ]


def section_order_ok(model, text):
    lines = [line.strip() for line in text.splitlines()]
    position = -1
    for section in model["sections"]:
        try:
            position = lines.index(section["title"], position + 1)
        except ValueError:
            return False
    return True


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)


def _tokens(text):
    return set(re.findall(r"\w+", text.casefold()))


def extra_tokens(model, text):
    allowed = set()
    for s in _strings(model):
        allowed |= _tokens(s)
    return _tokens(text) - allowed


def dates_detached(model, text):
    lines = [" ".join(line.split()) for line in text.splitlines()]
    pairs = [(w["position"], w["dates"]) for w in model["work"]]
    pairs += [(p["name"], p["dates"]) for p in model["projects"] if p.get("dates")]
    pairs += [(v["position"], v["dates"]) for v in model["volunteer"]]
    pairs += [(e["institution"], e["dates"]) for e in model["education"] if e.get("dates")]
    return [f"{label} ({dates})" for label, dates in pairs if not any(label in ln and dates in ln for ln in lines)]


def pdf_ua_declared(raw):
    return b"pdfuaid:part" in raw


def _run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {proc.stderr.strip()}")
    return proc.stdout


def check(model, pdf_path):
    info = parse_pdfinfo(_run(["pdfinfo", pdf_path]))
    fonts = parse_pdffonts(_run(["pdffonts", pdf_path]))
    text = _run(["pdftotext", "-raw", "-enc", "UTF-8", pdf_path, "-"])
    with open(pdf_path, "rb") as fh:
        raw = fh.read()

    meta, basics = model["meta"], model["basics"]
    failures = []
    pages = int(info.get("Pages", "0"))
    if pages > meta["max_pages"]:
        failures.append(f"{pages} pages, limit is {meta['max_pages']}")
    if info.get("Tagged") != "yes":
        failures.append("PDF is not tagged")
    if not pdf_ua_declared(raw):
        failures.append("PDF/UA-1 identification missing from XMP metadata")
    if info.get("Title") != meta["title"]:
        failures.append(f"Title is {info.get('Title')!r}, expected {meta['title']!r}")
    if info.get("Author") != basics["name"]:
        failures.append(f"Author is {info.get('Author')!r}, expected {basics['name']!r}")
    for font in fonts:
        if font["emb"] != "yes" or font["uni"] != "yes":
            failures.append(f"font {font['name']} embedded={font['emb']} unicode-map={font['uni']}")
    if not fonts:
        failures.append("no fonts found (is the text layer missing?)")
    chars = forbidden_chars(text)
    if chars:
        failures.append(f"unmappable or ligature characters in text: {', '.join(chars)}")
    for bullet in missing_bullets(model, text):
        failures.append(f"bullet not extractable as written: {bullet[:70]}")
    if not section_order_ok(model, text):
        failures.append("section headings missing or out of order: " + ", ".join(s["title"] for s in model["sections"]))
    extra = extra_tokens(model, text)
    if extra:
        failures.append(f"text in the PDF that is not in cv.yaml (hidden text?): {', '.join(sorted(extra))}")
    for item in dates_detached(model, text):
        failures.append(f"dates not on the same line as their entry: {item}")
    return pages, len(fonts), failures


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[0], encoding="utf-8") as fh:
        model = json.load(fh)
    pages, nfonts, failures = check(model, argv[1])
    variant = model["meta"]["variant"]
    if failures:
        print(f"check_pdf {variant}: FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(
        f"check_pdf {variant}: OK (pages {pages}/{model['meta']['max_pages']}, "
        f"{nfonts} fonts embedded with Unicode maps, tagged, PDF/UA-1, no hidden text, "
        f"{model['meta']['verify_count']} claims pending verification)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
