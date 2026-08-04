#!/usr/bin/env python3
"""GitCode Stale 管理 - 过期 Issue 自动关闭 (API v5)"""

import os
import requests
from datetime import datetime, timedelta, timezone

GITCODE_TOKEN = os.environ.get("GITCODE_TOKEN", "")
GITCODE_ORG = os.environ.get("GITCODE_ORG", "hd-vector")
GITCODE_API = "https://api.gitcode.com/api/v5"
HEADERS = {"PRIVATE-TOKEN": GITCODE_TOKEN, "Content-Type": "application/json"}

STALE_RULES = {
    "type/bug": 60,
    "type/feature": 90,
    "type/question": 30,
    "type/documentation": 180,
    "default": 90,
}

STALE_LABEL = "status/stale"
GRACE_DAYS = 14


def get_repos():
    url = f"{GITCODE_API}/orgs/{GITCODE_ORG}/repos?per_page=100"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return []
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("data", data.get("items", []))


def get_repo_issues(owner, repo):
    issues = []
    page = 1
    while True:
        url = f"{GITCODE_API}/repos/{owner}/{repo}/issues?state=opened&per_page=100&page={page}"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        issues.extend(data)
        page += 1
    return issues


def update_issue(owner, repo, number, data):
    url = f"{GITCODE_API}/repos/{owner}/{repo}/issues/{number}"
    resp = requests.patch(url, headers=HEADERS, json=data, timeout=15)
    return resp.status_code in (200, 201)


def add_comment(owner, repo, number, body):
    url = f"{GITCODE_API}/repos/{owner}/{repo}/issues/{number}/comments"
    resp = requests.post(url, headers=HEADERS, json={"body": body}, timeout=15)
    return resp.status_code in (200, 201)


def close_issue(owner, repo, number):
    url = f"{GITCODE_API}/repos/{owner}/{repo}/issues/{number}"
    resp = requests.patch(url, headers=HEADERS, json={"state": "closed"}, timeout=15)
    return resp.status_code in (200, 201)


def get_stale_days(labels):
    for l_type, days in STALE_RULES.items():
        if l_type == "default":
            continue
        if any(l_type in str(l) for l in labels):
            return days
    if any("priority/critical" in str(l) for l in labels):
        return 365
    return STALE_RULES["default"]


def main():
    if not GITCODE_TOKEN:
        print("GITCODE_TOKEN not set, exiting")
        return

    print(f"GitCode Stale Bot (v5) - scanning {GITCODE_ORG}")
    repos = get_repos()
    now = datetime.now(timezone.utc)
    total_closed = 0
    total_stale = 0

    for repo in repos:
        repo_name = repo.get("path") or repo.get("name") or repo.get("full_name", "").split("/")[-1]
        if not repo_name:
            continue

        issues = get_repo_issues(GITCODE_ORG, repo_name)
        for issue in issues:
            number = issue.get("number", 0)
            labels = [l.get("name", l) if isinstance(l, dict) else str(l) for l in issue.get("labels", [])]
            updated_at = issue.get("updated_at", "")
            if not updated_at:
                continue

            last_updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            days_since = (now - last_updated).days
            stale_days = get_stale_days(labels)

            if days_since >= stale_days and STALE_LABEL not in labels:
                full_labels = labels + [STALE_LABEL]
                update_issue(GITCODE_ORG, repo_name, number, {"labels": ",".join(full_labels)})
                add_comment(GITCODE_ORG, repo_name, number,
                            f"  Issue 已 {days_since} 天无更新，将在 {GRACE_DAYS} 天后自动关闭。"
                            f"如需保留请回复此 Issue。")
                print(f"[{repo_name}#{number}] Marked stale ({days_since}d)")
                total_stale += 1

            elif STALE_LABEL in labels and days_since >= stale_days + GRACE_DAYS:
                add_comment(GITCODE_ORG, repo_name, number, "  该 Issue 因长时间无活动已自动关闭。")
                close_issue(GITCODE_ORG, repo_name, number)
                print(f"[{repo_name}#{number}] Auto-closed ({days_since}d)")
                total_closed += 1

    print(f"\nSummary: {total_stale} marked stale, {total_closed} auto-closed")


if __name__ == "__main__":
    main()
