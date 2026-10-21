"""tools/check-commit-msg: the commit subject rule, shared by the git hook and CI."""

import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "tools", "check-commit-msg")

GIT_EDITOR_TAIL = """
# Please enter the commit message for your changes. Lines starting
# with '#' will be ignored, and an empty message aborts the commit.
#
# On branch phase-3-ci
# ------------------------ >8 ------------------------
# Do not modify or remove the line above.
# Everything below it will be ignored.
diff --git a/cv.yaml b/cv.yaml
+feat(x): this line is part of the diff, not the message
"""


def check(tmp_path, text):
    path = tmp_path / "COMMIT_EDITMSG"
    path.write_text(text)
    return subprocess.run(["sh", SCRIPT, str(path)], capture_output=True, text=True)


@pytest.mark.parametrize("text", [
    "feat: add release workflow\n",
    "fix: keep paragraph breaks\n\n\n",
    "chore: add phase 3 plan and evidence" + GIT_EDITOR_TAIL,
])
def test_accepted(tmp_path, text):
    result = check(tmp_path, text)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("text", [
    "feat(ci): add x\n",
    "fix: stop dump.\n",
    "docs: add x\n",
    "feat: add x\n\nA body explaining why.\n",
    "feat: add x\n\nCo-Authored-By: Someone <someone@example.com>\n",
    "Merge pull request #3 from ocarlosapenas/phase-3-ci\n",
    "feat: add x (#12)\n",
    "feat: add-x\n",
    "",
    "\n# only a comment\n",
])
def test_rejected(tmp_path, text):
    result = check(tmp_path, text)
    assert result.returncode == 1


def test_rejection_names_the_rule_and_the_subject(tmp_path):
    result = check(tmp_path, "feat(ci): add x\n")
    assert "^(feat|fix|chore): [A-Za-z0-9 ]+$" in result.stderr
    assert "feat(ci): add x" in result.stderr
