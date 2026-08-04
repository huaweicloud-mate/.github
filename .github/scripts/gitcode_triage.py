#!/usr/bin/env python3
"""GitCode Issue Triage - 自动分类打标签"""

import os
import json
import re
import requests
from datetime import datetime, timezone

GITCODE_TOKEN = os.environ.get("GITCODE_TOKEN", "")
GITCODE_ORG = os.environ.get("GITCODE_ORG", "hd-vector")
GITCODE_API = "https://gitcode.com/api/v5"
HEADERS = {"PRIVATE-TOKEN": GITCODE_TOKEN}

KEYWORDS = {
    "type/bug": ["bug", "错误", "crash", "崩溃", "报错", "异常", "fix", "broken"],
    "type/feature": ["feature", "功能", "新增", "enhancement", "建议", "希望", "support"],
    "type/documentation": ["doc", "文档", "documentation", "readme", "说明"],
    "type/question": ["question", "问题", "咨询", "请教", "how to", "怎么"],
}

PRIORITIES = {
    "priority/critical": ["urgent", "紧急", "线上", "production", "p0", "宕机", "data loss"],
    "priority/high": ["important", "重要", "严重影响", "blocker", "阻塞"],
    "priority/low": ["minor", "一般", "优化", "improve", "nice to have"],
}


def get_projects():
    url = f"{GITCODE_API}/groups/{GITCODE_ORG}/projects?per_page=100"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return []
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("data", data.get("items", []))


def get_project_issues(project_id, state="opened"):
    issues = []
    page = 1
    while True:
        url = f"{GITCODE_API}/projects/{project_id}/issues?state={state}&per_page=100&page={page}"
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


def classify_issue(title, body):
    text = f"{title}\n{body or ''}".lower()
    labels = []

    for label, keywords in KEYWORDS.items():
        if any(kw in text for kw in keywords):
            labels.append(label)
            break

    priority = "priority/medium"
    for p_label, keywords in PRIORITIES.items():
        if any(kw in text for kw in keywords):
            priority = p_label
            break
    labels.append(priority)

    return labels


def main():
    if not GITCODE_TOKEN:
        print("GITCODE_TOKEN not set, exiting")
        return

    print(f"GitCode Triage Bot - scanning {GITCODE_ORG}")
    projects = get_projects()
    total_updated = 0

    for project in projects:
        project_id = project.get("id") or project.get("project_id")
        project_name = project.get("name", "unknown")
        if not project_id:
            continue

        issues = get_project_issues(project_id)
        for issue in issues:
            iid = issue.get("iid", 0)
            title = issue.get("title", "")
            body = issue.get("description", "") or ""
            existing_labels = issue.get("labels", [])

            # 跳过高已分类的
            if existing_labels:
                continue

            new_labels = classify_issue(title, body)
            if not new_labels:
                continue

            labels_str = ",".join(new_labels)
            if update_issue(project_id, iid, {"labels": labels_str}):
                comment = f"  Issue Bot\n分类结果：`{', '.join(new_labels)}`"
                add_note(project_id, iid, comment)
                print(f"[{project_name}#{iid}] Labelled: {labels_str}")
                total_updated += 1

    print(f"\nTotal issues updated: {total_updated}")


if __name__ == "__main__":
    main()
