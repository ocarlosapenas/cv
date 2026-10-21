from release_assets import asset_names, copy_assets, verify_assets

TAG = "2026.10.21-01"
VARIANTS = ["backend", "ai", "fde"]


def test_asset_names():
    names = asset_names("Carlos Apenas", TAG, VARIANTS)
    assert names == {
        "backend": ("Carlos-Apenas-Resume-Backend.pdf", "Carlos-Apenas-Resume-Backend-2026.10.21-01.pdf"),
        "ai": ("Carlos-Apenas-Resume-AI.pdf", "Carlos-Apenas-Resume-AI-2026.10.21-01.pdf"),
        "fde": ("Carlos-Apenas-Resume-FDE.pdf", "Carlos-Apenas-Resume-FDE-2026.10.21-01.pdf"),
    }


def make_build(tmp_path):
    build = tmp_path / "build"
    for v in VARIANTS:
        (build / v).mkdir(parents=True)
        (build / v / "cv.pdf").write_bytes(f"%PDF {v}".encode())
    return build


def test_copy_assets_writes_constant_and_dated_copies(tmp_path):
    build = make_build(tmp_path)
    out = tmp_path / "release"
    written = copy_assets(str(build), str(out), "Carlos Apenas", TAG, VARIANTS)
    assert len(written) == 6
    assert (out / "Carlos-Apenas-Resume-AI.pdf").read_bytes() == b"%PDF ai"
    assert (out / "Carlos-Apenas-Resume-AI-2026.10.21-01.pdf").read_bytes() == b"%PDF ai"
    assert verify_assets(str(out), "Carlos Apenas", TAG, VARIANTS) == []


def test_verify_assets_detects_missing_extra_and_mismatch(tmp_path):
    build = make_build(tmp_path)
    out = tmp_path / "release"
    copy_assets(str(build), str(out), "Carlos Apenas", TAG, VARIANTS)
    (out / "Carlos-Apenas-Resume-FDE.pdf").unlink()
    (out / "Carlos-Apenas-Resume-AI-2026.10.21-01.pdf").write_bytes(b"%PDF other")
    (out / "notes.txt").write_text("stray")
    problems = verify_assets(str(out), "Carlos Apenas", TAG, VARIANTS)
    assert "missing Carlos-Apenas-Resume-FDE.pdf" in problems
    assert "Carlos-Apenas-Resume-AI.pdf differs from Carlos-Apenas-Resume-AI-2026.10.21-01.pdf" in problems
    assert "unexpected file notes.txt" in problems
    assert len(problems) == 3
