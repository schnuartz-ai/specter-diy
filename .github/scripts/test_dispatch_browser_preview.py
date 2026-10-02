#!/usr/bin/env python3
"""Unit tests for preview dispatch authorization, comments, and timeout contracts."""
from pathlib import Path
from unittest.mock import patch
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dispatch_browser_preview as dispatcher


ROOT = Path(__file__).resolve().parents[2]


class BrowserPreviewDispatcherTests(unittest.TestCase):
    def test_fork_build_requires_exact_approval_label_but_same_repo_is_automatic(self):
        self.assertTrue(dispatcher.preview_authorized(
            "cryptoadvance/specter-diy", "cryptoadvance/specter-diy", []))
        self.assertFalse(dispatcher.preview_authorized(
            "cryptoadvance/specter-diy", "contributor/specter-diy", []))
        self.assertFalse(dispatcher.preview_authorized(
            "cryptoadvance/specter-diy", "contributor/specter-diy",
            [{"name": "ready-for-review"}]))
        self.assertTrue(dispatcher.preview_authorized(
            "cryptoadvance/specter-diy", "contributor/specter-diy",
            [{"name": "preview-approved"}]))

    def test_unknown_or_stale_pr_state_never_authorizes_a_comment(self):
        with patch.object(dispatcher, "current", return_value=None), \
                patch.object(dispatcher, "comment") as write_comment:
            self.assertFalse(dispatcher._comment_if_current(
                "cryptoadvance/specter-diy", 12, "build", "a" * 40, "token", "text"))
            write_comment.assert_not_called()
        with patch.object(dispatcher, "current", return_value=False), \
                patch.object(dispatcher, "comment") as write_comment:
            self.assertFalse(dispatcher._comment_if_current(
                "cryptoadvance/specter-diy", 12, "build", "a" * 40, "token", "text"))
            write_comment.assert_not_called()
        with patch.object(dispatcher, "current", return_value=True), \
                patch.object(dispatcher, "comment") as write_comment:
            self.assertTrue(dispatcher._comment_if_current(
                "cryptoadvance/specter-diy", 12, "build", "a" * 40, "token", "text"))
            write_comment.assert_called_once()

    def test_bot_comment_searches_all_api_pages(self):
        first = [{"id": index, "body": "other", "user": {"login": "someone"}}
                 for index in range(100)]
        second = [{"id": 900, "body": "previous " + dispatcher.MARKER,
                   "user": {"login": "github-actions[bot]"}}]
        calls = []

        def fake_gh(method, path, _token, data=None):
            calls.append((method, path, data))
            if method == "GET" and path.endswith("page=1"):
                return first
            if method == "GET" and path.endswith("page=2"):
                return second
            return None

        with patch.object(dispatcher, "gh", side_effect=fake_gh):
            dispatcher.comment("cryptoadvance/specter-diy", 12, "token", "updated")
        self.assertIn(("GET", "/repos/cryptoadvance/specter-diy/issues/12/comments?per_page=100&page=1", None), calls)
        self.assertIn(("GET", "/repos/cryptoadvance/specter-diy/issues/12/comments?per_page=100&page=2", None), calls)
        patch_calls = [call for call in calls if call[0] == "PATCH"]
        self.assertEqual(len(patch_calls), 1)
        self.assertEqual(patch_calls[0][1], "/repos/cryptoadvance/specter-diy/issues/comments/900")

    def test_timeout_constants_fit_remote_chain_and_caller_workflow(self):
        self.assertEqual(dispatcher.REMOTE_VALIDATE_TIMEOUT_MINUTES, 5)
        self.assertEqual(dispatcher.REMOTE_BUILD_TIMEOUT_MINUTES, 180)
        self.assertEqual(dispatcher.REMOTE_FINALIZE_TIMEOUT_MINUTES, 10)
        self.assertGreater(dispatcher.POLL_TIMEOUT_MINUTES,
                            dispatcher.REMOTE_VALIDATE_TIMEOUT_MINUTES +
                            dispatcher.REMOTE_BUILD_TIMEOUT_MINUTES +
                            dispatcher.REMOTE_FINALIZE_TIMEOUT_MINUTES)
        self.assertLess(dispatcher.POLL_TIMEOUT_MINUTES,
                        dispatcher.CALLER_WORKFLOW_TIMEOUT_MINUTES)
        workflow = (ROOT / ".github/workflows/browser-preview.yml").read_text()
        self.assertIn(f"timeout-minutes: {dispatcher.CALLER_WORKFLOW_TIMEOUT_MINUTES}", workflow)

    def test_approval_label_event_and_close_cleanup_bypass_are_wired(self):
        workflow = (ROOT / ".github/workflows/browser-preview.yml").read_text()
        source = (ROOT / ".github/scripts/dispatch_browser_preview.py").read_text()
        self.assertIn("labeled", workflow)
        self.assertIn("closed", workflow)
        self.assertIn("PR_LABELS_JSON:", workflow)
        self.assertIn("github.event.action == 'closed' && 'delete'", workflow)
        self.assertIn('if action == "build" and not preview_authorized', source)


if __name__ == "__main__":
    unittest.main()
