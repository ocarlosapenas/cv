from match_job import find_terms, match
from skills import load_config

CONFIG = load_config({
    "aliases": {"Node.js": ["NodeJS"], "C#": [], "Vue.js": ["Vue"], "PostgreSQL": ["Postgres"]},
    "vocabulary": ["Java", "Kubernetes", "Go"],
    "confirmed": {},
})

REPORT = [
    {"skill": "JavaScript", "months": 120, "years": 10.0, "where": ["Acme"], "approx": False, "confirmed": None},
    {"skill": "PostgreSQL", "months": 14, "years": 1.2, "where": ["Fleet"], "approx": False, "confirmed": None},
    {"skill": "Vue.js", "months": 30, "years": 2.5, "where": ["Acme"], "approx": False, "confirmed": None},
]


def test_java_does_not_match_javascript():
    found = find_terms("Strong JavaScript skills required.", ["Java", "JavaScript"])
    assert found == {"JavaScript"}


def test_terms_with_punctuation_and_aliases():
    text = "Experience with NodeJS, C# and Vue; Postgres is a plus."
    assert find_terms(text, ["Node.js", "NodeJS", "C#", "Vue.js", "Vue", "Postgres"]) == {"NodeJS", "C#", "Vue", "Postgres"}


def test_go_matches_only_as_a_word():
    assert find_terms("Go or Rust", ["Go"]) == {"Go"}
    assert find_terms("Good knowledge of Google Cloud", ["Go"]) == set()


def test_match_reports_matches_with_evidence_and_gaps():
    job = "We use JavaScript, Postgres and Kubernetes. Java is not required."
    result = match(job, REPORT, CONFIG)
    assert [(m["skill"], m["years"]) for m in result["matched"]] == [("JavaScript", 10.0), ("PostgreSQL", 1.2)]
    assert result["gaps"] == ["Java", "Kubernetes"]
