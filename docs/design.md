# Design

CV as code: one data file, three role variants, verified outputs. This document
explains how the pieces fit and why. Phase 0 research and decisions D1–D14 are kept
out of git (`private/research/`); the decisions are summarized below.

## Data flow

```
cv.yaml ──validate (schemas/cv.schema.json)──▶ resolve --variant V ──▶ build/V/resolved.json
                                                                          │
                     ┌────────────────────────────────────────────────────┼──────────────────────┐
                     ▼                                                    ▼                      ▼
        typst compile template/cv.typ                    export_jsonresume.py            check_denylist.py
        (PDF/UA-1, tagged)                               (validated vs JSON Resume 1.3.1)        │
                     │                                                    │                      │
                     ▼                                                    ▼                      │
              build/V/cv.pdf ──▶ check_pdf.py                     build/V/resume.json ◀──────────┘
```

The render model (`resolved.json`) is the only input of every output. Variant logic
(per-variant values, tag filtering, section order) exists once, in `scripts/cvlib.py`.

## Decisions

| # | Decision | Status |
|---|---|---|
| D1 | Own thin layer: YAML source + small Typst template + scripts; fallback RenderCV v2.8 | Phase 1 (this) |
| D2 | `cv.yaml` uses JSON Resume names; exported and validated as pure JSON Resume | Phase 1 |
| D3 | Template derived from `basic-resume` (Unlicense): US Letter, one column, no icons, no small caps, no hyphenation, no ligatures, no date in metadata | Phase 1 |
| D4 | Variants `backend`, `ai`, `fde` from tags and per-variant values | Phase 1 (see deviations) |
| D5 | Public/private split; local deny-list | Phase 1 |
| D6 | Pinned toolchain in a container with the dockerized-tools baseline | Phase 1 (see deviations) |
| D7 | CI workflows: PR preview, release, weekly link check, workflow security | Phase 3 (`.github/workflows/`) |
| D8 | CalVer releases, immutable, stable `releases/latest/download/` link | Phase 3 (draft by CI, published by hand) |
| D9 | Commit subject rule enforced locally and in CI | Phase 3 (`tools/check-commit-msg`, `.githooks/`) |
| D10 | LinkedIn: official export in, paste-ready text out, all edits manual | Phase 2 |
| D11 | Living CV: local proposal skill, human approval, `status: verify` gate | Phase 3 (`release_gate.py`, `cv-propose`) |
| D12 | Content rewrite applying the research checklist | Phase 2 |
| D13 | Flagship SDK + evals project | Icebox (outside this repository) |
| D14 | Repository starts private; full-history scan before going public | Phase 1 → 3 |

## Deviations from the approved decisions

Both deviations below were approved on 2026-10-16, together with the Phase 1 design.

- **D4 mechanism.** Variants are resolved in Python (`resolve.py --variant`) and Typst
  receives the resolved JSON, instead of selecting the variant inside Typst with
  `--input variant=`. The JSON Resume export and the checks need the same resolution;
  doing it once avoids two implementations drifting apart.
- **D6 layout.** One image defined in this repository (`tools/Dockerfile`, D6's listed
  alternative) instead of a `typst` wrapper in dockerized-tools plus a separate check
  image. A public repository must build without a private one, and CI can build the
  same Dockerfile for exact local/CI parity. The wrapper `tools/run` keeps the
  dockerized-tools baseline flag for flag.

## Deviations in Phase 3

Approved on 2026-10-21 with the Phase 3 plan (`docs/plans/2026-10-21-phase-3.md`).

- **Hooks:** plain git hooks in `.githooks/` that call the pinned image, instead of the
  pre-commit framework, which installs itself and its hook environments on the host.
- **Spelling:** codespell from the Debian archive instead of typos (prose content, a
  signed package, one checksum pin less). check-jsonschema is not used: the scripts
  already validate `cv.yaml` and JSON Resume with python3-jsonschema.
- **Visual diff:** pdftoppm plus a small PIL script instead of diff-pdf, which is not
  in Debian.
- **Links:** lychee from the same image; only that command gets network access
  (`tools/run --net`).
- **Publishing:** CI creates a draft release and a person publishes it (GitHub's
  draft, attach, publish flow for immutable releases).

## Toolchain

| Piece | Pin | Why this source |
|---|---|---|
| Base image | `debian:trixie-slim@sha256:a292…f11f` (2026-10-05) | Digest is immutable |
| Typst | 0.15.1 musl binary, SHA256 per arch | Official release, checksum instead of a mutable tag |
| poppler-utils, python3, PyYAML, jsonschema, pytest | Debian trixie archive | Signed packages, long past the 2-day window, no pip in the image |
| JSON Resume schema | vendored 1.3.1, integrity recorded in `schemas/README.md` | Validation without npm or network |
| git, codespell, shellcheck, python3-pil, ca-certificates | Debian trixie archive | Same reason as the Python libraries |
| gitleaks 8.30.1, actionlint 1.7.12, zizmor 1.31.1, lychee 0.24.2 | release binaries, SHA256 per arch in `tools/tools.env` | Same pattern as Typst |

`tools/build.sh` labels the image with a hash of `tools/Dockerfile` + `tools/tools.env`;
`tools/run` refuses a stale image, so a changed pin never runs on the old toolchain.

## CI

Each workflow builds `tools/Dockerfile` with `tools/build.sh`, so CI and the local
machine run the same toolchain; the workflows only orchestrate.

- Top-level `permissions: {}`; each job asks for the minimum. Jobs that run repository
  code have a read-only token. The PR comment job has `pull-requests: write`, runs no
  repository code and only posts the artifact it downloads. The release job builds,
  checks and gates before it touches releases.
- Every action is pinned by commit SHA; every checkout uses `persist-credentials: false`.
- The deny-list comes from the secret `CV_DENYLIST`, written to a `0600` file for the
  check steps and removed afterwards. In CI a missing deny-list fails the job
  (`--require-denylist`). Checks report deny-list line numbers, never terms.
- Artifacts hold public build outputs only, kept 14 days.
- Branch protection is not available while the repository is private on the Free plan,
  so the commit rule also runs on every push to `main` (`security.yml`, job `commits`,
  with no path filter). CI checks the recorded message (`--recorded`), where a line
  starting with `#` is part of the commit, not a comment.

## Checks and what they prove

| Check | Proves |
|---|---|
| Schema + variant-name validation | No typo silently drops content (unknown tags and variant keys fail with a path) |
| `typst compile --pdf-standard ua-1` | Tagged PDF, document title, language, heading structure |
| Pages ≤ `max_pages` | Length budget per variant |
| Fonts embedded with Unicode maps | Every glyph extracts as real text |
| No U+FFFD, private-use or ligature codepoints | No icon-font junk, no ligature confusion |
| Every bullet extractable verbatim | No hyphenation splits, nothing lost in reading order |
| Section order | Headings appear in the variant's order |
| Dates on the same line as their entry | Entry/date association survives extraction |
| No extra tokens | Nothing in the PDF that is not in `cv.yaml` (hidden text, prompt injection) |
| Deny-list and public guards | See `CONFIDENTIALITY.md` |
| Version on every page | The PDF is tied to its release tag |
| Release gate | No release while any claim has `status: verify` |
| Commit rule | One-line `feat:`/`fix:`/`chore:` subjects, locally and in CI |

## Known limitations

- **Reading order is asserted on `pdftotext -raw`.** That is the content-stream order,
  which matches the tagged structure. poppler's default layout mode moves right-aligned
  dates into a separate block. Commercial résumé parsers are built for right-aligned
  dates (RenderCV, with the same layout, reports 20 of 20 PDFs parsed correctly by
  Affinda, Extracta and Klippa), but no public parser was tested here. If that risk
  matters more than the layout, move dates inline on the left. Decision on 2026-10-16:
  keep dates on the right.
- **poppler prints "Suspects object is wrong type (boolean)"** for Typst PDFs. The
  entry `/MarkInfo <</Marked true /Suspects false>>` is valid; poppler mishandles a
  false value. Harmless.
- **Font.** New Computer Modern is embedded in the Typst binary, so no font files are
  needed. A sans-serif font would mean vendoring OFL font files with checksums.
- **Phone heuristic.** Ten or more digits joined only by spaces, dots, parentheses or
  hyphens. Dates use an en dash, so they do not trigger it.

## Fallback trigger (D1)

Switch to RenderCV v2.8 if the own layer stops paying for itself. Measured at the end
of Phase 1 (code lines, excluding blanks and comments):

| Part | Code lines | Would RenderCV remove it? |
|---|---|---|
| Template (`template/*.typ`) | 100 | Yes |
| Resolver (`cvlib.py`, `resolve.py`) | 263 | Partly: tags, per-variant values and validation would still be needed |
| JSON Resume export | 65 | No (RenderCV declined JSON Resume) |
| Checks (`check_pdf.py`, `check_denylist.py`) | 236 | No |

Decision on 2026-10-16: keep the own layer. The original trigger (~400 lines of
template and scripts) was reached at about 430, but RenderCV would remove only the
template and display formatting (roughly 100 to 180 lines). From now on the trigger is
measured on what RenderCV would actually replace:

- template plus display formatting above ~300 code lines; or
- Phase 3 taking more than two weekends; or
- time going into layout instead of content.
