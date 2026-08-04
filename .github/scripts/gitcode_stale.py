#!/usr/bin/env python3
"""GitCode Stale 管理 - 过期 Issue 自动关闭"""

import os
import requests
from datetime import datetime, timedelta, timezone

GITCODE_TOKEN = os.environ.get("GITCODE_TOKEN", "")
GITCODE_ORG = os.environ.get("GITCODE_ORG", "hd-vector")
GITCODE_API = "https://gitcode.com/api/v5"
HEADERS = {"PRIVATE-TOKEN": GITCODE_TOKEN}

# 按类型差异化过期天数
STALE_RULES = {
    "type/bug": 60,
    "type/feature": 90,
    "type/question": 30,
    "type/documentation": 180,
    "default": 90,
}

STALE_LABEL = "status/stale"
GRACE_DAYS = 14


def get_projects():
    url = f"{GITCODE_API}/groups/{GITCODE_ORG}/projects?per_page=100"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return []
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("data", data.get("items", []))


def get_project_issues(project_id):
    issues = []
    page = 1
    while True:
        url = f"{GITCODE_API}/projects/{project_id}/issues?state=opened&per_page=100&page={page}"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        issues.extend(data)
        page += 1
    return issues


def update_issue(project_id, issue_iid, data):
    url = f"{GITCODE_API}/projects/{project_id}/issues/{issue_iid}"
    resp = requests.put(url, headers=HEADERS, json=data, timeout=15)
    return resp.status_code in (200, 201)


def add_note(project_id, issue_iid, body):
    url = f"{GITCODE_API}/projects/{project_id}/issues/{issue_iid}/notes"
    resp = requests.post(url, headers=HEADERS, json={"body": body}, timeout=15)
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

    print(f"GitCode Stale Bot - scanning {GITCODE_ORG}")
    projects = get_projects()
    now = datetime.now(timezone.utc)
    total_closed = 0
    total_stale = 0

    for project in projects:
        project_id = project.get("id") or project.get("project_id")
        project_name = project.get("name", "unknown")
        if not project_id:
            continue

        issues = get_project_issues(project_id)
        for issue in issues:
            iid = issue.get("iid", 0)
            labels = issue.get("labels", [])
            updated_at = issue.get("updated_at", "")
            if not updated_at:
                continue

            last_updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            days_since = (now - last_updated).days
            stale_days = get_stale_days(labels)

            # 阶段 1: 打 stale 标签
            if days_since >= stale_days and STALE_LABEL not in labels:
                full_labels = labels + [STALE_LABEL]
                update_issue(project_id, iid, {"labels": ",".join(full_labels)})
                add_note(project_id, iid,
                         f"  Issue 已 {days_since} 天无更新，将在 {GRACE_DAYS} 天后自动关闭。"
                         f"如需保留请回复此 Issue。")
                print(f"[{project_name}#{iid}] Marked stale ({days_since}d)")
                total_stale += 1

            # 阶段 2: 已 stale + 超过 grace 天数 → 关闭
            elif STALE_LABEL in labels and days_since >= stale_days + GRACE_DAYS:
                add_note(project_id, iid, "  该 Issue 因长时间无活动已自动关闭。")
                update_issue(project_id, iid, {"state_event": "close"})
                print(f"[{project_name}#{iid}] Auto-closed ({days_since}d)")
                total_closed += 1

    print(f"\nSummary: {total_stale} marked stale, {total_closed} auto-closed")


if __name__ == "__main__":
    main()
