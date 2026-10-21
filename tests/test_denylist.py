from check_denylist import load_denylist, main, phone_like, private_values_found, scan, uncovered_private_values

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


def test_phone_like_ignores_hex_hashes():
    # Commit and checksum hashes often hold ten or more decimal digits in a row.
    text = "\n".join([
        "Merge 3fa1234567890bcd1234ef56789aa0b1c2d3e4f5 into 9b0987654321fedcba0987654321fedcba098765",
        "LYCHEE_SHA256_AMD64=ab12345678901cdef4f0ef7f6554a6ed33dd7ac144fb2e1bbed98598e7af9730",
        "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1",
        "pinned 0123456789abcdef0123456789abcdef01234567, call +55 42 99999-9999",
    ])
    assert phone_like(text) == [4]


def test_uncovered_private_values():
    entries = load_denylist(DENYLIST + "re:555.?010.?0000\n")
    private = {"phone": "+1 555 010 0000", "email": "alex.private@example.com"}
    assert uncovered_private_values(private, entries) == ["email"]


def test_public_check_fails_when_private_value_not_in_denylist(tmp_path, capsys):
    denylist = tmp_path / "denylist.local"
    denylist.write_text(DENYLIST)
    private = tmp_path / "contact.private.yaml"
    private.write_text("email: alex.private@example.com\n")
    target = tmp_path / "cv.txt"
    target.write_text("nothing private here\n")
    code = main(["--public", "--denylist", str(denylist), "--private", str(private), str(target)])
    out = capsys.readouterr()
    assert code == 1
    assert "private 'email' value is not covered by any deny-list entry" in out.err
    assert "alex.private" not in out.out + out.err
