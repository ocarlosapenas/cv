import os
import subprocess

import pytest

from check_denylist import load_denylist
from scan_history import main, scan_repo

NOREPLY = "41978568+someone@users.noreply.github.com"
DENYLIST = "# confidential\nProject Nebula\n"


def git(repo, *args, email=NOREPLY):
    env = dict(os.environ, GIT_AUTHOR_NAME="A", GIT_AUTHOR_EMAIL=email,
               GIT_COMMITTER_NAME="A", GIT_COMMITTER_EMAIL=email)
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env).stdout


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    return path


def commit(repo, files, message="feat: change", email=NOREPLY):
    for name, text in files.items():
        target = repo / name
        if text is None:
            target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message, email=email)


def entries():
    return load_denylist(DENYLIST)


def test_clean_history_passes(repo):
    commit(repo, {"cv.yaml": "name: Alex\n"})
    result = scan_repo(str(repo), entries(), {})
    assert result["findings"] == []
    assert result["blobs"] == 1
    assert result["commits"] == 1


def test_scan_finds_term_in_deleted_file(repo):
    commit(repo, {"notes.md": "ok\nshipped Project Nebula\n"})
    commit(repo, {"notes.md": None})
    findings = scan_repo(str(repo), entries(), {})["findings"]
    assert len(findings) == 1
    assert findings[0].startswith("denylist line 2 matched blob ")
    assert findings[0].endswith(" notes.md:2")


def test_scan_finds_term_on_unmerged_ref(repo):
    commit(repo, {"cv.yaml": "name: Alex\n"})
    git(repo, "checkout", "-q", "-b", "topic")
    commit(repo, {"cv.yaml": "name: Alex\nproject: Project Nebula\n"})
    git(repo, "update-ref", "refs/pull/1/head", "topic")
    git(repo, "checkout", "-q", "main")
    git(repo, "branch", "-q", "-D", "topic")
    findings = scan_repo(str(repo), entries(), {})["findings"]
    assert any("cv.yaml:2" in f for f in findings)


def test_scan_flags_non_noreply_email(repo):
    commit(repo, {"cv.yaml": "name: Alex\n"}, email="alex.personal@example.com")
    findings = scan_repo(str(repo), entries(), {})["findings"]
    assert [f.split()[2] for f in findings] == ["author", "committer"]
    assert all("not a GitHub noreply address" in f for f in findings)
    assert all("alex.personal" not in f for f in findings)


def test_scan_finds_term_in_commit_message(repo):
    commit(repo, {"cv.yaml": "name: Alex\n"}, message="feat: ship Project Nebula")
    findings = scan_repo(str(repo), entries(), {})["findings"]
    assert len(findings) == 1
    assert findings[0].startswith("denylist line 2 matched commit ")


def test_scan_reports_entry_number_never_term(repo):
    commit(repo, {"a.md": "Project Nebula\n"}, message="feat: ship Project Nebula")
    findings = scan_repo(str(repo), entries(), {})["findings"]
    assert findings
    assert all("nebula" not in f.lower() for f in findings)


def test_phone_check_skips_test_fixtures_only(repo):
    commit(repo, {"tests/test_x.py": "PHONE = '+55 42 99999-9999'\n", "cv.yaml": "phone: +55 42 99999-9999\n"})
    findings = scan_repo(str(repo), entries(), {})["findings"]
    assert len(findings) == 1
    assert findings[0].startswith("phone-like number in blob ")
    assert findings[0].endswith(" cv.yaml:1")


def test_binary_blobs_counted_and_skipped(repo):
    (repo / "img.png").write_bytes(b"\x89PNG\x00Project Nebula")
    commit(repo, {})
    result = scan_repo(str(repo), entries(), {})
    assert result["binary"] == 1
    assert result["findings"] == []


def test_require_denylist_fails_when_missing(repo, tmp_path, capsys):
    commit(repo, {"cv.yaml": "name: Alex\n"})
    code = main(["--repo", str(repo), "--require-denylist", "--denylist", str(tmp_path / "absent")])
    assert code == 1
    assert "deny-list required but missing or empty" in capsys.readouterr().err


def test_main_writes_report_and_fails_on_findings(repo, tmp_path):
    commit(repo, {"notes.md": "Project Nebula\n"})
    denylist = tmp_path / "denylist.local"
    denylist.write_text(DENYLIST)
    report = tmp_path / "report.md"
    code = main(["--repo", str(repo), "--denylist", str(denylist), "--report", str(report)])
    assert code == 1
    text = report.read_text()
    assert "| Blobs scanned | 1 |" in text
    assert "denylist line 2 matched blob" in text
    assert "nebula" not in text.lower()
