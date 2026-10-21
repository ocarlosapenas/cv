---
name: cv-propose
description: Use when the owner asks to update the CV from new evidence, run the quarterly CV review, or turn session notes, the evolution log ("Registro de Evolução") or GitHub activity into CV bullets for cv.yaml.
---

# cv-propose

Turn new evidence into English CV bullet **proposals** that the owner approves one by
one. The proposal file is the product. `cv.yaml` changes only after approval.

## 1. Config and since date

Read `private/cv-propose.yaml` (format: `cv-propose.example.yaml`). If it is missing, stop
and say so.

Since date, the first that exists:
1. the date in the name of the newest file in `proposals_dir`;
2. the date of the newest release tag (`git tag -l` sorted, CalVer `YYYY.MM.DD-NN`);
3. the last commit that touched `cv.yaml` (`git log -1 --format=%cs -- cv.yaml`).

## 2. Sources (read only)

- `registro`: only the `registro_heading` section; entries whose heading date, or the
  end of its date range, is on or after the since date.
- `sessions`: only the folders in `contexts`; notes whose frontmatter `data:` is on or
  after the since date.
- GitHub: `gh search prs --author <github_user> --merged-at ">=<since>" --json repository,title,closedAt --limit 200`
  (`--merged-at` filters by date; `--merged` alone is only the merged state).
  Use counts per owner only; a bullet never names a repository.

Never write to the source folders.

## 3. Judge each candidate

| Check | Rule |
|---|---|
| Actor | In many notes "I" or "eu" is the assistant. Set `Actor: owner` only when the note shows the owner did or decided it, and quote that line. Otherwise `Actor: assistant` (drop it) or `Actor: unclear` (ask). |
| Shipped | Propose only work that reached production or was finished. In-progress work gets `Decision: wait` and the date to look again. |
| Confidential | Drop security incidents and vulnerabilities, sensitive data found where it should not be, internal system, service or repository names, customer, tenant or partner names, and financial figures. Generalize only if what is left still says something true. See `CONFIDENTIALITY.md`. |
| Numbers | List every number in the bullet under "Numbers to confirm", with the source line. |
| Duplicate | If an existing `cv.yaml` bullet already says it, propose an edit to that bullet instead. |

## 4. Write `<proposals_dir>/<today>.md`

The file is exactly this shape:

```markdown
# CV proposals <today>

Since <since date> (<rule used>). Sources: <n> Registro entries, <n> session notes, <n> merged PRs (<owner>: <count>, ...).

## P1: <short title>
- Target: work[<i>] <employer>, highlights (new | edit of highlights[<j>])
- Variants: [backend, ai, fde, linkedin] (only those that fit)
- Bullet: "<verb, action, result, scale; one sentence; past tense for finished work; cv.yaml style>"
- Source: <path> (<date>)
- Actor: owner | unclear: "<quoted line from the source>"
- Numbers to confirm: <each number and where it comes from> | none
- Proposed status: verify | confirmed
- Decision: approve / edit / drop / wait

## Left out
- <candidate>: <rule from section 3 that excluded it>
```

`Proposed status` is `confirmed` only when the bullet has no number and the actor is
`owner`.

## 5. Guard, then show

Run `tools/run python3 scripts/check_denylist.py --public --denylist private/denylist.local --private private/contact.private.yaml <proposal file>`.
On a match, rewrite or drop that proposal and run it again until it reports OK. Then show
the owner the file path and a table: id, title, variants, actor, decision needed.

## 6. After the owner decides

Only for approved items:
1. create a branch;
2. add the bullets to `cv.yaml`, with `status: verify` unless the owner confirmed every
   number;
3. run `make check`, and report pages per variant (each has a `max_pages`);
4. show the diff and a commit message (`feat: ...`, one line, rule in
   `tools/check-commit-msg`).

Never commit, push or open a PR without the owner's OK for that action.

## Common mistakes

| Mistake | Fix |
|---|---|
| A paste-ready YAML block for every candidate | Proposals first; YAML only for approved items |
| Building PDFs with unapproved bullets | Build only in step 6 |
| "Led", "built", "found" for something the assistant did | Actor rule, with a quoted line |
| Hinting at an incident ("sensitive data in a log table") | Drop it; there is no safe paraphrase |
| A bullet for work that has not shipped | `Decision: wait` |
