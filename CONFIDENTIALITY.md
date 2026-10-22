# Confidentiality policy

This repository may become public. Every rule below applies to the repository, its
full git history, CI logs and artifacts, and every published PDF or JSON file.

## Never published

| Category | Examples | Where it lives instead |
|---|---|---|
| Private contact data | phone number, street address, personal email | `private/contact.private.yaml` (gitignored), used only by `make private` |
| Personal identifiers | national ID or tax numbers, date of birth, marital status, photo | Nowhere in this repository |
| Employer-confidential facts | security incidents or vulnerabilities, internal system, service or repository names, customer, tenant or partner names, financial figures | Nowhere, unless the item was approved as public (below) |

## What may be published

- Public facts about roles: employer name, a descriptive job title, dates, location type.
- Metrics and claims the owner has confirmed as accurate **and** cleared as public, one
  item at a time. Until then a claim carries `status: verify` in `cv.yaml`, and
  `make release-gate` blocks every release while any remain.

## How it is enforced

| Control | Catches |
|---|---|
| `schemas/cv.schema.json` rejects `basics.phone` and `basics.location.address` | private data typed into the source |
| `private/` is gitignored | private files committed by accident |
| `scripts/check_denylist.py` with the local deny-list `private/denylist.local` | confidential terms in the source or any output. Matches are reported by deny-list line number and file location, never by the term itself, so logs stay clean |
| `--public` guards in the same script | phone-like numbers and any value from the private contact file in a public output |
| `scripts/check_pdf.py` hidden-text check | any text in the PDF that does not come from `cv.yaml` |
| `.githooks/pre-commit` (gitleaks, deny-list, codespell on staged files) | secrets or confidential terms before they are committed |
| `scripts/scan_history.py` (`make scan-history`, also weekly in CI) | confidential terms, phone numbers or private values in any blob of any ref (pull request refs included), any commit or tag message, and any author or committer email that is not a GitHub noreply address |
| gitleaks over the whole history (`make lint`) | credentials and tokens |
| CI artifacts limited to public build outputs, 14 days | private data in downloadable artifacts |
| Repository starts private; full-history scan before it goes public | anything that slipped into history (rewriting history does not remove data others already fetched) |

The deny-list itself is confidential: it lists exactly what must not leak, so it is
never committed. In CI it comes from the secret `CV_DENYLIST`, written to a `0600` file
only for the check steps; a missing or empty secret fails the job.

CI never sees the private contact file, so every private contact value must also be a
deny-list entry. When both files exist, `make check` fails on any private value that no
deny-list entry matches (reported by key name only).

The CI history scan also fetches every pull request ref (`refs/pull/*/head`), which
stays readable after a pull request is closed.
