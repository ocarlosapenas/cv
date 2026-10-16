from cvlib import resolve
from linkedin_texts import LIMITS, build_texts, check_limits, checklist
from skills import load_config

CONFIG = load_config({
    "aliases": {"Docker": ["Docker Products"]},
    "linkedin_skills": ["PHP", "Laravel", "Docker"],
})


def linkedin_model(doc):
    doc["meta"]["variants"]["linkedin"] = {"sections": ["summary", "work", "volunteer", "skills", "education"]}
    doc["basics"]["label"]["linkedin"] = "Senior Backend Engineer | PHP, Laravel, AWS"
    doc["basics"]["summary"] = {"default": "Short summary.", "linkedin": "Longer About text for LinkedIn."}
    return resolve(doc, "linkedin")


def test_texts_use_linkedin_values_and_bullets(doc):
    texts = build_texts(linkedin_model(doc), CONFIG)
    assert texts["headline"] == "Senior Backend Engineer | PHP, Laravel, AWS"
    assert texts["about"] == "Longer About text for LinkedIn."
    acme = texts["experience"][0]
    assert acme["company"] == "Acme Corp" and acme["title"] == "Senior Software Engineer"
    assert acme["start"] == "2023-07" and acme["end"] is None
    assert acme["description"] == (
        "Backend services and AWS infrastructure.\n\n"
        "• Migrated a 250 GB database with under 2 hours of downtime."
    )


def test_compact_entry_has_no_description(doc):
    doc["work"][1]["tags"] = ["backend", "linkedin"]
    texts = build_texts(linkedin_model(doc), CONFIG)
    assert texts["experience"][1]["company"] == "Old Co"
    assert texts["experience"][1]["description"] == ""


def test_skills_come_from_config_list(doc):
    assert build_texts(linkedin_model(doc), CONFIG)["skills"] == ["PHP", "Laravel", "Docker"]


def test_check_limits_flags_over_and_near():
    texts = {"headline": "x" * 221, "about": "y" * 2500, "experience": [], "volunteer": [], "skills": ["s"] * 101}
    status = {(r["field"], r["status"]) for r in check_limits(texts)}
    assert ("headline", "over") in status
    assert ("about", "near") in status  # above 95% of 2,600
    assert ("skills (count)", "over") in status
    assert LIMITS["headline"] == 220


def test_check_limits_covers_each_experience_field(doc):
    texts = build_texts(linkedin_model(doc), CONFIG)
    texts["experience"][0]["title"] = "t" * 101
    rows = [r for r in check_limits(texts) if r["status"] == "over"]
    assert [r["field"] for r in rows] == ["experience[Acme Corp].title"]


EXPORT = {
    "work": [
        {"name": "ACME CORP", "position": "Developer", "startDate": "2023-07"},
        {"name": "Velha Empresa", "position": "Developer", "startDate": "2013", "endDate": "2022"},
        {"name": "Gone Inc", "position": "Intern", "startDate": "2010-01", "endDate": "2010-06"},
    ],
    "skills": [{"name": "LinkedIn", "keywords": ["Laravel", "laravel", "Docker Products", "Bitcoin"]}],
}


def test_checklist_matches_positions_by_start_date_then_name(doc):
    doc["work"][1]["tags"] = ["backend", "linkedin"]
    texts = build_texts(linkedin_model(doc), CONFIG)
    items = checklist(texts, EXPORT, CONFIG)
    acme = next(i for i in items["experience"] if i["company"] == "Acme Corp")
    assert acme["linkedin_company"] == "ACME CORP"
    assert "title: Developer -> Senior Software Engineer" in acme["changes"]
    old_co = next(i for i in items["experience"] if i["company"] == "Old Co")
    assert old_co["linkedin_company"] == "Velha Empresa"  # matched by start date across languages
    assert items["linkedin_only"] == ["Gone Inc (Intern, 2010-01 to 2010-06)"]


def test_checklist_keeps_linkedin_value_when_cv_field_is_empty_and_skips_company_names(doc):
    doc["work"][1]["tags"] = ["backend", "linkedin"]
    current = {"work": [{"name": "Velha Empresa", "position": "Developer", "startDate": "2013", "endDate": "2022",
                         "location": "Springfield", "summary": "Kept PHP modules running."}]}
    items = checklist(build_texts(linkedin_model(doc), CONFIG), current, CONFIG)
    old_co = next(i for i in items["experience"] if i["company"] == "Old Co")
    assert old_co["changes"] == []  # compact on the CV: no description or location to push


def test_checklist_uses_raw_skill_list_to_find_duplicates(doc):
    current = {"skills": [{"name": "LinkedIn", "keywords": ["Laravel", "PHP", "Docker"]}],
               "skills_raw": ["Laravel", "PHP", "laravel", "Docker"]}
    items = checklist(build_texts(linkedin_model(doc), CONFIG), current, CONFIG)
    assert items["skills_remove"] == ["laravel (duplicate)"]


CONFIG_SYNCED = load_config({
    "aliases": {"Docker": ["Docker Products"]},
    "linkedin_skills": ["PHP", "Laravel", "Docker", "Git"],
    "linkedin_top_skills": ["Laravel", "PHP"],
    "linkedin_skills_keep": ["git", "Bitcoin"],
})


def test_top_skills_keep_list_contact_and_employment_type(doc):
    doc["work"][0]["employmentType"] = "Full-time"
    texts = build_texts(linkedin_model(doc), CONFIG_SYNCED)
    assert texts["top_skills"] == ["Laravel", "PHP"]
    assert texts["skills_keep"] == ["git", "Bitcoin"]
    assert texts["contact"]["email"] == "alex@example.com"
    assert texts["experience"][0]["type"] == "Full-time"


def test_top_skills_limit_checked(doc):
    texts = build_texts(linkedin_model(doc), CONFIG_SYNCED)
    texts["top_skills"] = ["a", "b", "c", "d", "e", "f"]
    assert ("top skills (count)", "over") in {(r["field"], r["status"]) for r in check_limits(texts)}


def test_checklist_respects_keep_list_by_exact_name(doc):
    current = {"skills_raw": ["Laravel", "PHP", "Docker", "Git", "git", "laravel", "Bitcoin"]}
    items = checklist(build_texts(linkedin_model(doc), CONFIG_SYNCED), current, CONFIG_SYNCED)
    assert items["skills_remove"] == ["laravel (duplicate)"]
    assert items["skills_add"] == []


def test_checklist_skills_add_and_remove_with_aliases(doc):
    items = checklist(build_texts(linkedin_model(doc), CONFIG), EXPORT, CONFIG)
    assert items["skills_add"] == ["PHP"]
    assert items["skills_remove"] == ["laravel (duplicate)", "Bitcoin"]
