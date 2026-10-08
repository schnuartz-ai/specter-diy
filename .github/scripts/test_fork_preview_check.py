#!/usr/bin/env python3
"""Tests for fork-only status-to-check rendering. No GitHub credentials needed."""
import unittest

from fork_preview_check import format_preview_check

SHA = "a" * 40
OLDER = "b" * 40
REPO = "schnuartz-ai/specter-diy"
SIM = "schnuartz-ai/specter-diy-web-simulator"
ROOT = "https://schnuartz-ai.github.io/specter-diy-web-simulator/"


def record(sha=SHA):
    run_id = 12345
    run_url = f"https://github.com/{SIM}/actions/runs/{run_id}"
    return {
        "head_sha": sha,
        "workflow_run_id": run_id,
        "run_url": run_url,
        "firmware_url": run_url + "/artifacts/67890",
        "preview_url": ROOT + f"pr/4/{sha}/",
    }


def state(status="success", history=None):
    return {
        "pr_number": 4,
        "source_sha": SHA,
        "source_repository": REPO,
        "status": status,
        "successful_previews": [record()] if history is None else history,
        "latest_run_url": f"https://github.com/{SIM}/actions/runs/12346",
    }


class PreviewCheckTests(unittest.TestCase):
    def test_success_has_all_original_comment_links_and_warning(self):
        conclusion, markdown, detail = format_preview_check(4, SHA, REPO, state())
        self.assertEqual(conclusion, "success")
        self.assertIn("## Specter Browser Preview", markdown)
        self.assertIn("[Open browser simulator](" + ROOT + "pr/4/" + SHA, markdown)
        self.assertIn("[Firmware artifact](https://github.com/" + SIM, markdown)
        self.assertIn("[Build logs](https://github.com/" + SIM, markdown)
        self.assertIn("Never enter a real seed phrase or use real funds", markdown)
        self.assertEqual(detail, ROOT + f"pr/4/{SHA}/")

    def test_failure_keeps_previous_success_and_shows_failure_logs(self):
        old = record(OLDER)
        conclusion, markdown, _ = format_preview_check(
            4, SHA, REPO, state("failure", [old])
        )
        self.assertEqual(conclusion, "failure")
        self.assertIn("Latest build `aaaaaaa` failed.", markdown)
        self.assertIn("pr/4/" + OLDER, markdown)
        self.assertIn("[Failed build logs]", markdown)
        self.assertIn("Never enter a real seed phrase", markdown)

    def test_unpublished_status_and_stale_commit_do_not_fake_success(self):
        for raw in (None, state(), {"status": "success"}):
            sha = "c" * 40
            conclusion, markdown, detail = format_preview_check(4, sha, REPO, raw)
            self.assertEqual(conclusion, "neutral")
            self.assertIn("No successful browser preview is available yet", markdown)
            self.assertNotIn("Open browser simulator", markdown)
            self.assertIn("Never enter a real seed phrase", markdown)
            self.assertEqual(detail, f"https://github.com/{SIM}/actions")

    def test_refuses_untrusted_preview_url(self):
        bad = record()
        bad["preview_url"] = "https://evil.example/seed-phishing"
        with self.assertRaisesRegex(ValueError, "Unexpected browser preview URL"):
            format_preview_check(4, SHA, REPO, state(history=[bad]))

    def test_refuses_untrusted_firmware_url(self):
        bad = record()
        bad["firmware_url"] = "https://evil.example/firmware.zip"
        with self.assertRaisesRegex(ValueError, "Unexpected firmware artifact URL"):
            format_preview_check(4, SHA, REPO, state(history=[bad]))

    def test_prevents_wrong_pr_reuse(self):
        conclusion, markdown, _ = format_preview_check(10, SHA, REPO, state())
        self.assertEqual(conclusion, "neutral")
        self.assertNotIn("Open browser simulator", markdown)


if __name__ == "__main__":
    unittest.main()
