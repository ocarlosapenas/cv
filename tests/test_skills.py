import pytest

from cvlib import CVError, validate_cv
from skills import compare_claims, load_config, merge_configs, month_index, parse_screening, skill_report

CONFIG = {
    "aliases": {"Docker": ["Docker Products"], "Python": ["Python (Programming Language)"], "REST APIs": ["API Development"]},
    "vocabulary": ["Kubernetes"],
    "confirmed": {"PHP": {"years": 15, "as_of": "2026-10"}},
    "evidence": [{"where": "Old Shop (not on CV)", "startDate": "2010-01", "endDate": "2010-12", "stack": ["PHP"]}],
}


@pytest.fixture
def config():
    return load_config(CONFIG)


def row(report, skill):
    return next(r for r in report if r["skill"] == skill)


def test_month_index_year_only_start_and_end():
    assert month_index("2023-07") == 2023 * 12 + 6
    assert month_index("2013") == 2013 * 12
    assert month_index("2013", end=True) == 2013 * 12 + 11


def test_stack_string_counts_whole_entry_and_present_uses_today(doc, config):
    doc["work"][0]["stack"] = ["Laravel"]
    r = row(skill_report(doc, config, today="2024-06"), "Laravel")
    assert r["months"] == 12  # Jul 2023 to Jun 2024, inclusive
    assert r["first"] == "2023-07" and r["last"] == "present"
    assert r["where"] == ["Acme Corp"]


def test_overlapping_entries_not_double_counted(doc, config):
    doc["work"][0]["stack"] = ["PHP"]
    doc["work"][1]["stack"] = ["PHP"]
    doc["work"][1]["endDate"] = "2023-12"
    r = row(skill_report(doc, config, today="2024-06"), "PHP")
    # Old Co 2013-01..2023-12 and Acme 2023-07..2024-06 overlap; plus the 12 months of extra evidence.
    assert r["months"] == (2024 * 12 + 5) - (2013 * 12) + 1 + 12
    assert r["where"] == ["Acme Corp", "Old Co", "Old Shop (not on CV)"]


def test_stack_item_with_own_dates_and_approximate_years(doc, config):
    doc["work"][1]["stack"] = [{"name": "Docker", "startDate": "2019-01"}, {"name": "Python", "years": 1}]
    report = skill_report(doc, config, today="2024-06")
    assert row(report, "Docker")["months"] == (2022 * 12 + 11) - (2019 * 12) + 1
    python = row(report, "Python")
    assert python["months"] == 12 and python["approx"] is True


def test_evidence_uses_default_period_when_dates_differ_per_variant(doc, config):
    doc["work"][0]["startDate"] = {"default": "2023-07", "linkedin": "2024-06"}
    doc["work"][0]["stack"] = ["Go"]
    assert row(skill_report(doc, config, today="2024-06"), "Go")["months"] == 12


def test_aliases_canonicalize_stack_names(doc, config):
    doc["work"][0]["stack"] = ["docker products"]
    assert row(skill_report(doc, config, today="2024-06"), "Docker")["months"] == 12


def test_project_keywords_count_and_undated_project_lists_where(doc, config):
    doc["projects"] = [
        {"name": "Homelab", "startDate": "2024-01", "keywords": ["Ansible"]},
        {"name": "Idea", "stack": ["Ansible"]},
    ]
    r = row(skill_report(doc, config, today="2024-06"), "Ansible")
    assert r["months"] == 6
    assert r["where"] == ["Homelab", "Idea"]


def test_confirmed_value_is_reported(doc, config):
    doc["work"][0]["stack"] = ["PHP"]
    r = row(skill_report(doc, config, today="2026-10"), "PHP")
    assert r["confirmed"] == {"years": 15, "as_of": "2026-10"}


def test_stack_schema_accepts_strings_and_objects_only(doc, schema_path):
    doc["work"][0]["stack"] = ["PHP", {"name": "Python", "years": 1, "note": "scripting"}]
    validate_cv(doc, schema_path)
    doc["work"][0]["stack"] = [{"name": "PHP", "level": "expert"}]
    with pytest.raises(CVError):
        validate_cv(doc, schema_path)


def test_parse_screening_english_and_portuguese():
    rows = [
        {"Question": "How many years of work experience do you have with Docker Products?", "Answer": "3"},
        {"Question": "Há quantos anos você já usa Python no trabalho?", "Answer": "1"},
        {"Question": "Are you comfortable working in a remote setting?", "Answer": "Yes"},
        {"Question": "Mobile phone number", "Answer": "+55 00 00000-0000"},
    ]
    assert parse_screening(rows) == [
        {"question_skill": "Docker Products", "answer": 3.0},
        {"question_skill": "Python", "answer": 1.0},
    ]


def test_compare_flags_divergence_and_unknown_skill(doc, config):
    doc["work"][0]["stack"] = ["Docker"]
    report = skill_report(doc, config, today="2024-06")
    claims = [
        {"question_skill": "Docker Products", "answer": 5.0},
        {"question_skill": "API Development", "answer": 0.0},
        {"question_skill": "Kubernetes", "answer": 2.0},
    ]
    result = compare_claims(claims, report, config)
    docker = result[0]
    assert docker["skill"] == "Docker" and docker["evidence_years"] == 1.0 and docker["flag"] is True
    assert result[1]["skill"] == "REST APIs" and result[1]["flag"] is False
    assert result[2]["skill"] == "Kubernetes" and result[2]["evidence_years"] == 0.0 and result[2]["flag"] is True


def test_confirmed_lookup_ignores_case(doc):
    config = load_config({"confirmed": {"jQuery": {"years": 6}}})
    doc["work"][0]["stack"] = ["jquery"]
    report = skill_report(doc, config, today="2024-06")
    assert report[0]["confirmed"] == {"years": 6}
    (claim,) = compare_claims([{"question_skill": "JQuery", "answer": 6.0}], report, config)
    assert claim["suggested"] == 6


def test_private_overlay_merges_aliases_confirmed_and_evidence():
    public = load_config({"aliases": {"Docker": ["Docker Products"]}, "vocabulary": ["Java"], "evidence": [{"where": "A", "stack": ["PHP"]}]})
    private = load_config({"aliases": {"Node.js": ["NodeJS"]}, "vocabulary": ["Go"], "confirmed": {"PHP": {"years": 17}},
                           "evidence": [{"where": "B", "stack": ["React"]}]})
    merged = merge_configs(public, private)
    assert merged["alias_map"]["docker products"] == "Docker" and merged["alias_map"]["nodejs"] == "Node.js"
    assert merged["vocabulary"] == ["Java", "Go"]
    assert merged["confirmed"] == {"PHP": {"years": 17}}
    assert [e["where"] for e in merged["evidence"]] == ["A", "B"]


def test_suggested_answer_prefers_confirmed_then_whole_evidence_years(doc, config):
    doc["work"][0]["stack"] = ["Docker", "PHP"]
    report = skill_report(doc, config, today="2025-10")
    claims = [
        {"question_skill": "Docker", "answer": 1.0},
        {"question_skill": "PHP", "answer": 3.0},
        {"question_skill": "Kubernetes", "answer": 2.0},
    ]
    docker, php, k8s = compare_claims(claims, report, config)
    assert docker["evidence_years"] == 2.3 and docker["suggested"] == 2  # Jul 2023 to Oct 2025: 28 months
    assert php["suggested"] == 15  # confirmed in skills.yaml wins over evidence
    assert k8s["suggested"] == 0
