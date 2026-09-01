import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "embed_git_info.py"


def run_git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL
    ).strip()


class GitInfoReproducibilityTest(TestCase):
    def test_same_commit_ignores_remote_and_checkout_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            clone_a = root / "clone-a"
            clone_b = root / "clone-b"
            source.mkdir()

            run_git(source, "init")
            run_git(source, "config", "user.name", "Specter Test")
            run_git(source, "config", "user.email", "specter@example.invalid")
            (source / "payload.txt").write_text("same source\n")
            run_git(source, "add", "payload.txt")
            run_git(source, "commit", "-m", "fixture")
            commit = run_git(source, "rev-parse", "HEAD")

            run_git(root, "clone", str(source), str(clone_a))
            run_git(root, "clone", str(source), str(clone_b))

            run_git(clone_a, "checkout", "-b", "release-test")
            run_git(
                clone_a,
                "remote",
                "set-url",
                "origin",
                "git@example.invalid:fork/specter-diy.git",
            )

            run_git(clone_b, "checkout", "--detach", commit)
            run_git(
                clone_b,
                "remote",
                "set-url",
                "origin",
                "https://example.invalid/other/specter-diy.git",
            )

            output_a = root / "git-info-a.py"
            output_b = root / "git-info-b.py"
            subprocess.check_call(
                [sys.executable, str(SCRIPT), str(output_a)], cwd=clone_a
            )
            subprocess.check_call(
                [sys.executable, str(SCRIPT), str(output_b)], cwd=clone_b
            )

            content_a = output_a.read_text()
            content_b = output_b.read_text()

            self.assertEqual(content_a, content_b)
            # Checkout metadata is not source identity. Keeping it neutral also
            # avoids attributing fork-only commits to the upstream repository.
            self.assertIn("REPOSITORY = 'unknown'", content_a)
            self.assertIn("BRANCH = 'unknown'", content_a)
            self.assertIn("COMMIT = %r" % commit, content_a)
            self.assertNotIn("release-test", content_a)
            self.assertNotIn("example.invalid", content_a)
            self.assertNotIn("cryptoadvance/specter-diy", content_a)

    def test_without_git_metadata_uses_stable_unknown_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "git-info.py"

            subprocess.check_call(
                [sys.executable, str(SCRIPT), str(output)], cwd=root
            )
            content = output.read_text()

            self.assertIn("REPOSITORY = 'unknown'", content)
            self.assertIn("BRANCH = 'unknown'", content)
            self.assertIn("COMMIT = 'unknown'", content)
