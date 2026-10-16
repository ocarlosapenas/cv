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
  releases are blocked while any remain (Phase 3).

## How it is enforced

| Control | Catches |
|---|---|
| `schemas/cv.schema.json` rejects `basics.phone` and `basics.location.address` | private data typed into the source |
| `private/` is gitignored | private files committed by accident |
| `scripts/check_denylist.py` with the local deny-list `private/denylist.local` | confidential terms in the source or any output. Matches are reported by deny-list line number and file location, never by the term itself, so logs stay clean |
| `--public` guards in the same script | phone-like numbers and any value from the private contact file in a public output |
| `scripts/check_pdf.py` hidden-text check | any text in the PDF that does not come from `cv.yaml` |
| Repository starts private; full-history scan before it goes public | anything that slipped into history (rewriting history does not remove data others already fetched) |

The deny-list itself is confidential: it lists exactly what must not leak, so it is
never committed. In CI (Phase 3) it is provided as a secret.
