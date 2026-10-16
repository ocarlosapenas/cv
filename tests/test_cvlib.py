import pytest

from cvlib import CVError, load_cv, resolve, validate_cv


def test_base_doc_is_valid(doc, schema_path):
    validate_cv(doc, schema_path)


def test_variant_scalar_uses_override_then_default(doc, schema_path):
    validate_cv(doc, schema_path)
    assert resolve(doc, "ai")["basics"]["label"] == "Backend Engineer moving into AI engineering"
    assert resolve(doc, "backend")["basics"]["label"] == "Senior Backend Engineer"


def test_untagged_bullet_in_all_variants_tagged_only_in_listed(doc):
    backend = [h["text"] for h in resolve(doc, "backend")["work"][0]["highlights"]]
    ai = [h["text"] for h in resolve(doc, "ai")["work"][0]["highlights"]]
    assert backend == ["Migrated a 250 GB database with under 2 hours of downtime."]
    assert ai == [
        "Migrated a 250 GB database with under 2 hours of downtime.",
        "Wrote agent skills for release runbooks.",
    ]


def test_tagged_work_entry_and_skill_group_filtered(doc):
    ai = resolve(doc, "ai")
    assert [w["name"] for w in ai["work"]] == ["Acme Corp"]
    assert [s["name"] for s in ai["skills"]] == ["Backend", "AI tooling"]
    backend = resolve(doc, "backend")
    assert [w["name"] for w in backend["work"]] == ["Acme Corp", "Old Co"]
    assert [s["name"] for s in backend["skills"]] == ["Backend"]


def test_unknown_tag_raises_with_path(doc, schema_path):
    doc["work"][0]["highlights"][1]["tags"] = ["fd"]
    with pytest.raises(CVError) as err:
        validate_cv(doc, schema_path)
    assert "fd" in str(err.value)
    assert "work[0].highlights[1]" in str(err.value)


def test_unknown_variant_key_raises(doc, schema_path):
    doc["basics"]["label"] = {"default": "A", "aii": "B"}
    with pytest.raises(CVError) as err:
        validate_cv(doc, schema_path)
    assert "aii" in str(err.value)


def test_unknown_variant_requested_raises(doc):
    with pytest.raises(CVError):
        resolve(doc, "fde")


def test_yaml_date_normalized(tmp_path):
    path = tmp_path / "cv.yaml"
    path.write_text("work:\n  - startDate: 2023-07-01\n    endDate: 2024-05-31T10:00:00\n")
    loaded = load_cv(str(path))
    assert loaded["work"][0]["startDate"] == "2023-07-01"
    assert loaded["work"][0]["endDate"].startswith("2024-05-31")


def test_boolean_where_text_expected_rejected(doc, schema_path, tmp_path):
    path = tmp_path / "cv.yaml"
    path.write_text("countryCode: NO\n")
    doc["basics"]["location"]["countryCode"] = load_cv(str(path))["countryCode"]
    with pytest.raises(CVError) as err:
        validate_cv(doc, schema_path)
    assert "basics.location.countryCode" in str(err.value)


@pytest.mark.parametrize("where", ["phone", "address"])
def test_phone_or_address_in_cv_yaml_rejected(doc, schema_path, where):
    if where == "phone":
        doc["basics"]["phone"] = "+1 555 010 0000"
    else:
        doc["basics"]["location"]["address"] = "1 Main St"
    with pytest.raises(CVError) as err:
        validate_cv(doc, schema_path)
    assert where in str(err.value)


def test_compact_entry_cannot_carry_bullets(doc, schema_path):
    doc["work"][1]["highlights"] = ["Something that would be silently dropped."]
    with pytest.raises(CVError):
        validate_cv(doc, schema_path)


def test_dates_display(doc):
    model = resolve(doc, "backend")
    assert model["work"][0]["dates"] == "Jul 2023 – Present"
    assert model["work"][1]["dates"] == "2013 – 2022"
    assert model["education"][0]["dates"] == "2008 – 2011"
    doc["work"][0]["startDate"] = "2022-03-15"
    doc["work"][0]["endDate"] = "2023-01"
    assert resolve(doc, "backend")["work"][0]["dates"] == "Mar 2022 – Jan 2023"


def test_sections_follow_variant_order(doc):
    assert [s["key"] for s in resolve(doc, "ai")["sections"]] == ["summary", "work", "skills", "education"]
    assert [s["title"] for s in resolve(doc, "backend")["sections"]] == ["Summary", "Skills", "Experience", "Volunteer", "Education"]


def test_volunteer_resolved_and_filtered(doc):
    backend = resolve(doc, "backend")["volunteer"]
    assert [v["organization"] for v in backend] == ["Community Group"]
    assert backend[0]["dates"] == "May 2020 – Jul 2023"
    assert backend[0]["highlights"] == [{"text": "Built an e-learning platform for 500+ students.", "status": None}]
    assert [v["organization"] for v in resolve(doc, "ai")["volunteer"]] == ["Community Group", "Talk Club"]


def test_verify_count_includes_volunteer(doc):
    doc["volunteer"][0]["highlights"] = [{"text": "Served 500+ students.", "status": "verify"}]
    assert resolve(doc, "backend")["meta"]["verify_count"] == 1


def test_empty_section_is_dropped(doc):
    doc["meta"]["variants"]["ai"]["sections"].append("projects")
    assert "projects" not in [s["key"] for s in resolve(doc, "ai")["sections"]]


def test_verify_count_and_status_kept(doc):
    model = resolve(doc, "ai")
    assert model["meta"]["verify_count"] == 1
    assert model["work"][0]["highlights"][1]["status"] == "verify"
    assert resolve(doc, "backend")["meta"]["verify_count"] == 0


def test_text_whitespace_collapsed(doc):
    doc["basics"]["summary"] = "Line one\nline two.  \n"
    assert resolve(doc, "backend")["basics"]["summary"] == "Line one line two."


def test_private_merge_only_when_given(doc):
    assert "phone" not in resolve(doc, "backend")["basics"]
    model = resolve(doc, "backend", private={"phone": "+1 555 010 0000", "email": "alex.private@example.com"})
    assert model["basics"]["phone"] == "+1 555 010 0000"
    assert model["basics"]["email"] == "alex.private@example.com"


def test_private_file_with_unknown_key_rejected(doc):
    with pytest.raises(CVError):
        resolve(doc, "backend", private={"address": "1 Main St"})


def test_meta_title_and_version(doc):
    meta = resolve(doc, "backend", version="2026.10.14-01")["meta"]
    assert meta["title"] == "Alex Example Resume"
    assert meta["version"] == "2026.10.14-01"
    assert meta["max_pages"] == 2
