import copy
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

BASE_DOC = {
    "meta": {
        "variants": {
            "backend": {"sections": ["summary", "skills", "work", "volunteer", "education"], "max_pages": 2},
            "ai": {"sections": ["summary", "work", "skills", "education"], "max_pages": 2},
        }
    },
    "basics": {
        "name": "Alex Example",
        "label": {"default": "Senior Backend Engineer", "ai": "Backend Engineer moving into AI engineering"},
        "email": "alex@example.com",
        "location": {"city": "Springfield", "countryCode": "BR", "country": "Brazil", "remote": "Remote", "timezone": "UTC-3"},
        "profiles": [{"network": "GitHub", "username": "alex", "url": "https://github.com/alex"}],
        "summary": "Backend engineer focused on production reliability.",
    },
    "work": [
        {
            "name": "Acme Corp",
            "position": "Senior Software Engineer",
            "startDate": "2023-07",
            "summary": "Backend services and AWS infrastructure.",
            "highlights": [
                "Migrated a 250 GB database with under 2 hours of downtime.",
                {"text": "Wrote agent skills for release runbooks.", "tags": ["ai"], "status": "verify"},
            ],
        },
        {
            "name": "Old Co",
            "position": "Developer",
            "startDate": "2013",
            "endDate": "2022",
            "compact": True,
            "tags": ["backend"],
        },
    ],
    "skills": [
        {"name": "Backend", "keywords": ["PHP", "Laravel"]},
        {"name": "AI tooling", "keywords": ["MCP"], "tags": ["ai"]},
    ],
    "volunteer": [
        {
            "organization": "Community Group",
            "position": "Volunteer Engineer",
            "startDate": "2020-05",
            "endDate": "2023-07",
            "highlights": ["Built an e-learning platform for 500+ students."],
        },
        {
            "organization": "Talk Club",
            "position": "Conversation Facilitator",
            "startDate": "2022-11",
            "endDate": "2025-09",
            "tags": ["ai"],
        },
    ],
    "education": [
        {"institution": "State University", "studyType": "Associate degree", "area": "Systems Analysis", "startDate": "2008", "endDate": "2011"}
    ],
}


@pytest.fixture
def doc():
    return copy.deepcopy(BASE_DOC)


@pytest.fixture
def schema_path():
    return os.path.join(ROOT, "schemas", "cv.schema.json")
