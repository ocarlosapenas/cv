from check_denylist import load_denylist, main, phone_like, private_values_found, scan

DENYLIST = """# confidential terms, one per line
Project Nebula

re:tenant-\\d+
"""


def test_denylist_reports_line_number_never_term():
    entries = load_denylist(DENYLIST)
    hits = scan(entries, "build/ai/cv.txt", "ok line\nshipped project nebula fast\n")
    assert hits == ["denylist line 2 matched build/ai/cv.txt:2"]
    assert all("nebula" not in h.lower() for h in hits)


def test_denylist_regex_entry():
    entries = load_denylist(DENYLIST)
    assert scan(entries, "cv.yaml", "fixed tenant-42 isolation\n") == ["denylist line 4 matched cv.yaml:1"]
    assert scan(entries, "cv.yaml", "tenant isolation\n") == []


def test_comments_and_blank_lines_ignored():
    assert [e.line for e in load_denylist(DENYLIST)] == [2, 4]


def test_phone_like_positive_and_negatives():
    text = "\n".join([
        "Call +55 42 99999-9999 anytime",
        "State Agency 2013-2022",
        "Migrated a 250 GB database",
        "Kept an API serving 20M+ pageviews",
        "Jul 2023 – Present",
        "(415) 555-0100",
    ])
    assert phone_like(text) == [1, 6]


def test_phone_like_ignores_versions_next_to_iso_dates():
    text = "\n".join([
        "schema 1.3.1 (2026-07-22), integrity recorded",
        "Upgraded to Laravel 13 (2026-08) with zero errors",
        "Window 2025-11-03 to 2026-04-15",
        "Call +1 555 010 0000",
    ])
    assert phone_like(text) == [4]


def test_phone_like_ignores_digits_inside_urls():
    text = "\n".join([
        "url: https://app.block.co/certificate/0506953b-e288-4546-8887-913e3c52603c/",
        "see https://example.com/call/+55-42-99999-9999 for details",
        "Call +55 42 99999-9999",
    ])
    assert phone_like(text) == [3]


def test_private_values_reported_by_key():
    private = {"phone": "+1 555 010 0000", "email": "alex.private@example.com"}
    assert private_values_found(private, "contact alex.private@example.com") == ["email"]
    assert private_values_found(private, "tel 1-555-010-0000") == ["phone"]
    assert private_values_found(private, "nothing here 2013 2022") == []


def test_calver_version_is_not_a_phone():
    # The release version printed in the PDF footer (YYYY.MM.DD-NN) has ten digits.
    assert phone_like("Carlos Apenas · 2026.10.21-01") == []
    assert phone_like("2026.10.21-01 +55 42 99999-9999") == [1]


def test_require_denylist_fails_when_missing(tmp_path, capsys):
    target = tmp_path / "cv.txt"
    target.write_text("Project Nebula shipped\n")
    code = main(["--require-denylist", "--denylist", str(tmp_path / "absent.local"), str(target)])
    out = capsys.readouterr()
    assert code == 1
    assert "deny-list required but missing or empty" in out.err


def test_require_denylist_fails_when_empty(tmp_path, capsys):
    denylist = tmp_path / "denylist.local"
    denylist.write_text("# only comments\n\n")
    target = tmp_path / "cv.txt"
    target.write_text("Project Nebula shipped\n")
    code = main(["--require-denylist", "--denylist", str(denylist), str(target)])
    out = capsys.readouterr()
    assert code == 1
    assert "deny-list required but missing or empty" in out.err
    assert "nebula" not in (out.out + out.err).lower()


def test_require_denylist_passes_with_entries(tmp_path):
    denylist = tmp_path / "denylist.local"
    denylist.write_text(DENYLIST)
    target = tmp_path / "cv.txt"
    target.write_text("nothing confidential\n")
    assert main(["--require-denylist", "--denylist", str(denylist), str(target)]) == 0
