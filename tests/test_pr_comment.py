from pr_comment import MARKER, render

READY = "**Release gate:** ✅ ready, no claims pending verification."
BLOCKED = "**Release gate:** ⛔ blocked, 1 claim pending verification: `work[0].highlights[1]`"


def variant(name, diff, pages=2):
    return {
        "name": name,
        "pages": pages,
        "max_pages": 2,
        "previews": [f"{name}-page-{n}.png" for n in range(1, pages + 1)],
        "diff": diff,
    }


SAME = [{"page": 1, "status": "same", "ratio": 0.0, "overlay": None},
        {"page": 2, "status": "same", "ratio": 0.0, "overlay": None}]
CHANGED = [{"page": 1, "status": "same", "ratio": 0.0, "overlay": None},
           {"page": 2, "status": "changed", "ratio": 0.01, "overlay": "build/preview/backend-page-2-changes.png"}]


def test_comment_starts_with_marker_and_lists_variants():
    body = render([variant("backend", SAME), variant("ai", SAME)], {}, READY)
    assert body.startswith(MARKER)
    assert "| backend | 2/2 |" in body
    assert "| ai | 2/2 |" in body
    assert READY in body


def test_comment_without_base():
    body = render([variant("backend", None)], {}, READY)
    assert "No base build to compare with." in body
    assert "![backend page 1](./backend-page-1.png)" in body
    assert "![backend page 2](./backend-page-2.png)" in body


def test_identical_builds_report_no_changes():
    body = render([variant("backend", SAME)], {"backend": ""}, READY)
    assert "No visual or text changes." in body
    assert "<details>" not in body


def test_changed_page_shows_overlay_and_text_diff():
    diff = "@@ -1 +1 @@\n-Old bullet\n+New bullet\n"
    body = render([variant("backend", CHANGED)], {"backend": diff}, READY)
    assert "| backend | 2/2 | 2 |" in body
    assert "![backend page 2 changes](./backend-page-2-changes.png)" in body
    assert "```diff\n" + diff in body
    assert "No visual or text changes." not in body


def test_comment_truncates_long_diff():
    diff = "".join(f"+line {n} " + "x" * 80 + "\n" for n in range(2500))
    body = render([variant("backend", CHANGED), variant("ai", CHANGED)], {"backend": diff, "ai": diff}, READY)
    assert len(body) <= 60000
    assert "Diff truncated; the full diff is in the cv-preview artifact." in body


def test_comment_shows_blocked_gate():
    body = render([variant("backend", SAME)], {}, BLOCKED)
    assert BLOCKED in body
