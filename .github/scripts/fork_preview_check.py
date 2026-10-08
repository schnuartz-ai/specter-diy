#!/usr/bin/env python3
"""Fork-only Checks API prototype for the Specter browser preview.

Runs exclusively from the Specter fork's trusted default branch. It never
checks out PR code and uses only checks:write, pull-requests:read.
"""
import json
import os
import re
import sys
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO = "schnuartz-ai/specter-diy"
SIMULATOR = "schnuartz-ai/specter-diy-web-simulator"
PAGES = "https://schnuartz-ai.github.io/specter-diy-web-simulator/"
MARKER = "Experimental development build. Never enter a real seed phrase or use real funds."
NAME = "Specter Browser Preview"
SHA = re.compile(r"^[a-f0-9]{40}$")


def get_json(url, token=None, missing_ok=False):
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "specter-fork-preview-check",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            result = response.read(65537)
            if len(result) > 65536:
                raise ValueError("Response too large")
            return json.loads(result)
    except HTTPError as exc:
        if missing_ok and exc.code == 404:
            return None
        raise RuntimeError("GitHub/Pages GET failed with HTTP " + str(exc.code)) from exc


def github(method, path, token, payload=None):
    url = "https://api.github.com" + path
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Accept": "application/vnd.github+json",
               "Authorization": "Bearer " + token,
               "User-Agent": "specter-fork-preview-check",
               "X-GitHub-Api-Version": "2022-11-28"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        with urlopen(Request(url, data=body, headers=headers, method=method), timeout=30) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        raise RuntimeError("GitHub " + method + " returned HTTP " + str(exc.code)) from exc


def _validated_record(record, number):
    if not isinstance(record, dict):
        raise ValueError("Invalid preview record")
    sha = record.get("head_sha", "")
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise ValueError("Invalid preview SHA")
    run_id = record.get("workflow_run_id")
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("Invalid preview workflow run ID")
    run_url = f"https://github.com/{SIMULATOR}/actions/runs/{run_id}"
    if record.get("run_url") != run_url:
        raise ValueError("Unexpected build logs URL")
    preview = record.get("preview_url")
    if preview is not None and preview != PAGES + f"pr/{number}/{sha}/":
        raise ValueError("Unexpected browser preview URL")
    fw = record.get("firmware_url")
    if fw is not None and not (
        isinstance(fw, str) and re.fullmatch(re.escape(run_url) + r"/artifacts/[1-9][0-9]*", fw)
    ):
        raise ValueError("Unexpected firmware artifact URL")
    return sha, preview, fw, run_url


def format_preview_check(number, sha, head_repository, state):
    """Return (conclusion, Markdown output, trusted details URL).

    Preserve the existing comment's links, latest-success semantics, and warning.
    Public state is always revalidated against this exact live PR.
    """
    lines = ["## Specter Browser Preview", ""]
    detail = f"https://github.com/{SIMULATOR}/actions"
    conclusion = "neutral"

    if not isinstance(state, dict) or (
        state.get("pr_number") != number
        or state.get("source_sha") != sha
        or str(state.get("source_repository", "")).lower() != head_repository.lower()
    ):
        lines += ["No successful browser preview is available yet.", "",
                  "The published status for this exact PR commit is not available. "
                  "This does not mean the build succeeded.", ""]
    else:
        status = state.get("status")
        if status not in ("success", "failure", "cancelled"):
            lines += ["No successful browser preview is available yet.", "",
                      "The preview is not currently published.", ""]
        else:
            conclusion = "success" if status == "success" else "failure" if status == "failure" else "neutral"
            if status in ("failure", "cancelled"):
                outcome = "failed" if status == "failure" else "was cancelled"
                lines += [f"Latest build `{sha[:7]}` {outcome}.", ""]
            history = state.get("successful_previews", [])
            if not isinstance(history, list) or len(history) > 1:
                raise ValueError("Invalid preview history")
            if history:
                record_sha, preview, fw, logs = _validated_record(history[0], number)
                lines += ["### Latest", ""]
                if preview:
                    lines.append(f"`{record_sha[:7]}` → [Open browser simulator]({preview})")
                    detail = preview
                else:
                    lines.append(f"`{record_sha[:7]}` browser preview removed to stay within GitHub Pages storage limits. Push a new commit to publish a fresh preview.")
                if fw:
                    lines.append(f"[Firmware artifact]({fw})")
                lines.append(f"[Build logs]({logs})")
            else:
                lines.append("No successful browser preview is available yet.")
            latest = state.get("latest_run_url")
            if status in ("failure", "cancelled") and isinstance(latest, str) and re.fullmatch(
                rf"https://github\.com/{re.escape(SIMULATOR)}/actions/runs/[1-9][0-9]*", latest
            ):
                lines += ["", f"[Failed build logs]({latest})"]
            lines.append("")
    lines.append("⚠️ " + MARKER)
    return conclusion, "\n".join(lines), detail


def publish(number, token):
    if not 1 <= number <= 9999999:
        raise ValueError("Invalid PR number")
    pr = github("GET", f"/repos/{REPO}/pulls/{number}", token)
    if pr.get("state") != "open" or (pr.get("base", {}).get("repo") or {}).get("full_name", "").lower() != REPO:
        raise ValueError("Test requires an open PR targeting the Specter fork")
    head = pr.get("head") or {}
    head_repo = (head.get("repo") or {}).get("full_name", "")
    sha = head.get("sha", "")
    if not isinstance(sha, str) or not SHA.fullmatch(sha) or not head_repo:
        raise ValueError("Invalid live PR head")
    # Fetch only the fork's fixed public status path, never an untrusted URL.
    state_url = PAGES + f"status/pr/{number}.json"
    state = get_json(state_url, missing_ok=True)
    conclusion, summary, details_url = format_preview_check(number, sha, head_repo, state)
    external_id = f"specter-fork-preview-pr-{number}"
    check_runs = github(
        "GET", f"/repos/{REPO}/commits/{sha}/check-runs?per_page=100&filter=all", token
    ).get("check_runs", [])
    old = next((c for c in check_runs if c.get("name") == NAME
                and c.get("external_id") == external_id
                and (c.get("app") or {}).get("slug") == "github-actions"), None)
    payload = {"name": NAME, "status": "completed", "conclusion": conclusion,
               "details_url": details_url,
               "output": {"title": "Specter Browser Preview", "summary": summary}}
    if old:
        result = github("PATCH", f"/repos/{REPO}/check-runs/{old['id']}", token, payload)
        operation = "updated"
    else:
        payload["head_sha"] = sha
        payload["external_id"] = external_id
        result = github("POST", f"/repos/{REPO}/check-runs", token, payload)
        operation = "created"
    print(json.dumps({"operation": operation, "pr": number, "sha": sha,
                      "conclusion": conclusion, "check_url": result.get("html_url"),
                      "details_url": details_url, "summary": summary}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        publish(int(os.environ["PREVIEW_PR_NUMBER"]), os.environ["GITHUB_TOKEN"])
    except (KeyError, ValueError, RuntimeError) as exc:
        print(f"Preview check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
