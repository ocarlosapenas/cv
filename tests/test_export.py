import json

import pytest

from cvlib import CVError, resolve
from export_jsonresume import to_jsonresume, validate_jsonresume

EXTENSION_KEYS = {"tags", "status", "dates", "sections", "compact", "location_line", "display", "url_display", "date_display"}


def walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from walk_keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_keys(value)


def test_export_validates_against_vendored_schema(doc):
    validate_jsonresume(to_jsonresume(resolve(doc, "ai")))


def test_invalid_export_raises(doc):
    out = to_jsonresume(resolve(doc, "ai"))
    out["work"][0]["startDate"] = "July 2023"
    with pytest.raises(CVError):
        validate_jsonresume(out)


def test_no_extension_keys_leak(doc):
    out = to_jsonresume(resolve(doc, "backend", version="2026.10.14-01"))
    assert not EXTENSION_KEYS & set(walk_keys(out))
    assert out["meta"]["version"] == "2026.10.14-01"


def test_current_role_has_no_enddate(doc):
    out = to_jsonresume(resolve(doc, "backend"))
    assert "endDate" not in out["work"][0]
    assert out["work"][1]["endDate"] == "2022"


def test_highlights_are_strings(doc):
    out = to_jsonresume(resolve(doc, "ai"))
    assert out["work"][0]["highlights"] == [
        "Migrated a 250 GB database with under 2 hours of downtime.",
        "Wrote agent skills for release runbooks.",
    ]


def test_location_keeps_only_jsonresume_fields(doc):
    out = to_jsonresume(resolve(doc, "backend"))
    assert out["basics"]["location"] == {"city": "Springfield", "countryCode": "BR"}


def test_volunteer_exported_in_jsonresume_shape(doc):
    out = to_jsonresume(resolve(doc, "ai"))
    assert out["volunteer"][0] == {
        "organization": "Community Group",
        "position": "Volunteer Engineer",
        "startDate": "2020-05",
        "endDate": "2023-07",
        "highlights": ["Built an e-learning platform for 500+ students."],
    }
    assert out["volunteer"][1] == {"organization": "Talk Club", "position": "Conversation Facilitator", "startDate": "2022-11", "endDate": "2025-09"}
    validate_jsonresume(out)


def test_output_is_json_serializable(doc):
    json.dumps(to_jsonresume(resolve(doc, "backend")))
