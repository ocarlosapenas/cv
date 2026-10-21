# cv

CV as code: one `cv.yaml`, three role variants, each rendered to a tagged, ATS-clean
PDF and to a JSON Resume file, with automated checks on every output.

> **Phase 2:** `cv.yaml` holds real content under review. Claims marked
> `status: verify` are not confirmed yet.

## Quickstart

Requires Docker and make. Nothing else is installed on the host: every tool runs in a
pinned, network-less container (see `tools/`). The same image carries the lint and scan
tools (gitleaks, actionlint, zizmor, codespell, lychee), pinned in `tools/tools.env`.

```sh
tools/build.sh   # build the pinned toolchain image once
make check       # unit tests, render all variants, run every check
```

## Outputs

For each variant `backend`, `ai`, `fde`, under `build/<variant>/`:

| File | What |
|---|---|
| `cv.pdf` | US Letter, tagged PDF/UA-1, one column |
| `resume.json` | JSON Resume, validated against schema 1.3.1 |
| `resolved.json` | Render model the other outputs are built from |

## Editing

- Edit `cv.yaml` (schema: `schemas/cv.schema.json`; conventions at the top of the file).
- `make check` before every commit.
- `make hooks` once per clone enables the git hooks in `.githooks/`:
  - `commit-msg`: one-line subjects matching `^(feat|fix|chore): [A-Za-z0-9 ]+$`
    (no scope, no body, no trailers);
  - `pre-commit`: gitleaks on the staged diff, the deny-list and codespell on staged
    text files, actionlint and zizmor when a workflow changes, and `make check` when
    the CV, template, scripts, schemas or toolchain change.
- `make lint` runs the same tools over the whole tree and history, as CI does.
- `make private` builds PDFs with private contact details into `build/private/`.
  They are never published.

## Privacy

See [CONFIDENTIALITY.md](CONFIDENTIALITY.md). In short: no phone or address in this
repository, a local deny-list for confidential terms, and checks that fail on any
private value or hidden text in a public output.

## Design

See [docs/design.md](docs/design.md).
