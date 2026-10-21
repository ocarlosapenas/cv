import datetime

import pytest

from calver import main, next_version

TODAY = datetime.date(2026, 10, 21)


def test_next_version_without_existing_names():
    assert next_version(TODAY, []) == "2026.10.21-01"


def test_next_version_counts_only_today_and_ignores_junk():
    existing = ["2026.10.21-01", "2026.10.21-02", "2026.10.20-05", "v1", "junk", ""]
    assert next_version(TODAY, existing) == "2026.10.21-03"


def test_next_version_uses_highest_not_count():
    assert next_version(TODAY, ["2026.10.21-04"]) == "2026.10.21-05"


def test_next_version_refuses_past_99():
    with pytest.raises(ValueError):
        next_version(TODAY, ["2026.10.21-99"])


def test_cli_reads_existing_names_from_file(tmp_path, capsys):
    existing = tmp_path / "existing.txt"
    existing.write_text("2026.10.21-01\n2026.10.21-01\n")
    assert main(["--today", "2026-10-21", "--existing", str(existing)]) == 0
    assert capsys.readouterr().out == "2026.10.21-02\n"
