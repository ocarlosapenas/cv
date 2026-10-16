import os

import pytest

from cvlib import CVError
from linkedin_import import import_export, li_date, split_description

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "linkedin")


def test_li_date():
    assert li_date("Jul 2023") == "2023-07"
    assert li_date("2008") == "2008"
    assert li_date("") is None
    with pytest.raises(CVError):
        li_date("July 2023")


def test_split_description_inline_dashes():
    summary, bullets = split_description(
        "Backend work for a large site. - Migrated a 250GB database. - Built high-performance APIs."
    )
    assert summary == "Backend work for a large site."
    assert bullets == ["Migrated a 250GB database.", "Built high-performance APIs."]


def test_split_description_leading_dash_without_space():
    assert split_description("-Development of PHP modules. -Support for customers.") == (
        None,
        ["Development of PHP modules.", "Support for customers."],
    )


def test_split_description_keeps_hyphenated_words():
    assert split_description("Create new e-commerce features and high-performance carts.") == (
        "Create new e-commerce features and high-performance carts.",
        [],
    )


def test_import_maps_columns_by_name_and_strips():
    draft = import_export(FIXTURE)
    first = draft["work"][0]
    # Positions.csv in the fixture has its columns in a different order than LinkedIn's.
    assert first["name"] == "Example Ads"
    assert first["position"] == "Senior Software Engineer"
    assert first["startDate"] == "2023-07"
    assert "endDate" not in first
    assert first["highlights"] == ["Migrated a 250GB database with less than 2 hours of downtime.", "Built high-performance APIs."]
    assert draft["work"][1]["endDate"] == "2023-05"


def test_import_profile_with_bom():
    basics = import_export(FIXTURE)["basics"]
    assert basics["name"] == "Alex Example"
    assert basics["label"] == "Senior Backend Engineer | PHP, AWS"
    assert basics["location"] == {"city": "Springfield", "region": "State", "country": "Brazil"}


def test_import_skills_deduplicated_case_insensitively():
    assert import_export(FIXTURE)["skills"] == [{"name": "LinkedIn", "keywords": ["Laravel", "PHP", "Git"]}]


def test_import_keeps_raw_skill_list_with_duplicates():
    assert import_export(FIXTURE)["skills_raw"] == ["Laravel", "PHP", "laravel", "Git", "git"]


def test_import_education_certificates_volunteer():
    draft = import_export(FIXTURE)
    assert draft["education"] == [{"institution": "Federal Technical University", "studyType": "Technologist", "startDate": "2008", "endDate": "2011"}]
    assert draft["certificates"] == [{"name": "Cloud Practitioner", "issuer": "Example Cloud", "date": "2024-04", "url": "https://example.com/badge"}]
    assert draft["volunteer"][0]["organization"] == "Community Group"
    assert draft["volunteer"][0]["position"] == "Volunteer Engineer"


def test_missing_required_column_names_file_and_column(tmp_path):
    (tmp_path / "Positions.csv").write_text("Company Name,Title\nAcme,Dev\n")
    with pytest.raises(CVError) as err:
        import_export(str(tmp_path))
    assert "Positions.csv" in str(err.value)
    assert "Started On" in str(err.value)


def test_missing_files_are_skipped(tmp_path):
    assert import_export(str(tmp_path)) == {}
