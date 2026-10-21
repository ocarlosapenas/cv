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


def check_recorded(tmp_path, text):
    path = tmp_path / "recorded"
    path.write_text(text)
    return subprocess.run(["sh", SCRIPT, "--recorded", str(path)], capture_output=True, text=True)


def test_recorded_message_accepts_one_line(tmp_path):
    assert check_recorded(tmp_path, "feat: add release workflow\n").returncode == 0


@pytest.mark.parametrize("text", [
    "feat: add x\n\n# Summary\n\n# Generated with an assistant\n",
    "feat: add x\n# ------------------------ >8 ------------------------\nCo-Authored-By: Someone <s@example.com>\n",
    "# feat: add x\n",
])
def test_recorded_message_keeps_comment_lines(tmp_path, text):
    # A recorded commit message has no git comments: every line counts.
    assert check_recorded(tmp_path, text).returncode == 1


RANGE_SCRIPT = os.path.join(ROOT, "tools", "check-commit-range")


def make_repo(tmp_path, messages):
    repo = tmp_path / "repo"
    repo.mkdir()
    env = dict(os.environ, GIT_AUTHOR_NAME="A", GIT_AUTHOR_EMAIL="a@users.noreply.github.com",
               GIT_COMMITTER_NAME="A", GIT_COMMITTER_EMAIL="a@users.noreply.github.com")
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    shas = []
    for message in messages:
        msg = tmp_path / "msg"
        msg.write_text(message)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "--allow-empty", "--cleanup=verbatim", "-F", str(msg)],
                       check=True, env=env)
        shas.append(subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                                   capture_output=True, text=True).stdout.strip())
    return repo, shas


def test_commit_range_passes_good_commits(tmp_path):
    repo, shas = make_repo(tmp_path, ["feat: first\n", "fix: second\n", "chore: third\n"])
    result = subprocess.run(["sh", RANGE_SCRIPT, f"{shas[0]}..{shas[2]}"], cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("ok ") == 2


def test_commit_range_rejects_recorded_comment_body(tmp_path):
    repo, shas = make_repo(tmp_path, ["feat: first\n", "feat: add x\n\n# Generated with an assistant\n", "fix: third\n"])
    result = subprocess.run(["sh", RANGE_SCRIPT, f"{shas[0]}..{shas[2]}"], cwd=repo, capture_output=True, text=True)
    assert result.returncode == 1
    assert f"FAIL {shas[1][:7]}" in result.stdout
    assert f"ok   {shas[2][:7]}" in result.stdout


def test_commit_range_single_commit(tmp_path):
    repo, shas = make_repo(tmp_path, ["Merge pull request #3 from x/y\n"])
    result = subprocess.run(["sh", RANGE_SCRIPT, "-1", shas[0]], cwd=repo, capture_output=True, text=True)
    assert result.returncode == 1
