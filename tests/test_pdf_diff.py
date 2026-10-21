import os

from PIL import Image

from pdf_diff import compare_pages


def page(tmp_path, name, size=(20, 30), dot=None):
    image = Image.new("RGB", size, "white")
    if dot:
        image.putpixel(dot, (0, 0, 0))
    path = tmp_path / name
    image.save(path)
    return str(path)


def test_identical_pages_same(tmp_path):
    out = tmp_path / "out"
    result = compare_pages([page(tmp_path, "base-page-1.png")], [page(tmp_path, "head-page-1.png")], str(out))
    assert result == [{"page": 1, "status": "same", "ratio": 0.0, "overlay": None}]
    assert not out.exists() or not os.listdir(out)


def test_changed_page_overlay_written(tmp_path):
    out = tmp_path / "out"
    result = compare_pages(
        [page(tmp_path, "base-page-1.png")],
        [page(tmp_path, "head-page-1.png", dot=(3, 4))],
        str(out),
    )
    assert result[0]["status"] == "changed"
    assert result[0]["ratio"] > 0
    overlay = result[0]["overlay"]
    assert overlay == str(out / "head-page-1-changes.png")
    assert os.path.exists(overlay)
    # The changed pixel is tinted red; unchanged pixels keep the head page.
    image = Image.open(overlay).convert("RGB")
    red, green, blue = image.getpixel((3, 4))
    assert red > green and red > blue
    assert image.getpixel((0, 0)) == (255, 255, 255)


def test_added_and_removed_pages(tmp_path):
    out = tmp_path / "out"
    added = compare_pages(
        [page(tmp_path, "b1.png")],
        [page(tmp_path, "h1.png"), page(tmp_path, "h2.png")],
        str(out),
    )
    assert [p["status"] for p in added] == ["same", "added"]
    assert added[1]["overlay"] and os.path.exists(added[1]["overlay"])
    removed = compare_pages(
        [page(tmp_path, "b1.png"), page(tmp_path, "b2.png")],
        [page(tmp_path, "h1.png")],
        str(out),
    )
    assert removed[1] == {"page": 2, "status": "removed", "ratio": 1.0, "overlay": None}


def test_page_size_change_counts_as_changed(tmp_path):
    result = compare_pages(
        [page(tmp_path, "b1.png", size=(20, 30))],
        [page(tmp_path, "h1.png", size=(20, 31))],
        str(tmp_path / "out"),
    )
    assert result[0]["status"] == "changed"
    assert result[0]["ratio"] == 1.0
