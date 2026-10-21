import yaml

from release_gate import main


def write_cv(tmp_path, doc):
    path = tmp_path / "cv.yaml"
    path.write_text(yaml.safe_dump(doc))
    return str(path)


def confirmed(doc):
    doc["work"][0]["highlights"][1].pop("status")
    return doc


def test_release_gate_blocks_pending_verify(doc, tmp_path, capsys):
    assert main([write_cv(tmp_path, doc), "--version", "2026.10.21-01"]) == 1
    err = capsys.readouterr().err
    assert "pending verification" in err
    assert "work[0].highlights[1]" in err


def test_release_gate_rejects_bad_version(doc, tmp_path, capsys):
    assert main([write_cv(tmp_path, confirmed(doc)), "--version", "preview"]) == 1
    assert "not a CalVer version" in capsys.readouterr().err


def test_release_gate_passes(doc, tmp_path, capsys):
    assert main([write_cv(tmp_path, confirmed(doc)), "--version", "2026.10.21-01"]) == 0
    assert "release gate: OK" in capsys.readouterr().out


def test_release_gate_report_never_fails(doc, tmp_path, capsys):
    assert main([write_cv(tmp_path, doc), "--report"]) == 0
    out = capsys.readouterr().out
    assert "blocked" in out
    assert "work[0].highlights[1]" in out


def test_release_gate_report_ready(doc, tmp_path, capsys):
    assert main([write_cv(tmp_path, confirmed(doc)), "--report"]) == 0
    assert "ready" in capsys.readouterr().out
