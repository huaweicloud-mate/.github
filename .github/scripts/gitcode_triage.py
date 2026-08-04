#!/usr/bin/env python3
"""GitCode Issue Triage - 自动分类打标签 (API v5)"""

import os
import json
import re
import requests

GITCODE_TOKEN = os.environ.get("GITCODE_TOKEN", "")
GITCODE_ORG = os.environ.get("GITCODE_ORG", "hd-vector")
GITCODE_API = "https://api.gitcode.com/api/v5"
HEADERS = {"PRIVATE-TOKEN": GITCODE_TOKEN, "Content-Type": "application/json"}

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


def get_repos():
    """获取组织下所有仓库（v5: /orgs/{org}/repos）"""
    url = f"{GITCODE_API}/orgs/{GITCODE_ORG}/repos?per_page=100"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return []
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("data", data.get("items", []))


def get_repo_issues(owner, repo):
    """获取仓库所有 Issue（v5: /repos/{owner}/{repo}/issues）"""
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

    print(f"GitCode Triage Bot (v5) - scanning {GITCODE_ORG}")
    repos = get_repos()
    total_updated = 0

    for repo in repos:
        repo_name = repo.get("path") or repo.get("name") or repo.get("full_name", "").split("/")[-1]
        if not repo_name:
            continue

        issues = get_repo_issues(GITCODE_ORG, repo_name)
        for issue in issues:
            number = issue.get("number", 0)
            title = issue.get("title", "")
            body = issue.get("description", "") or issue.get("body", "") or ""
            existing_labels = [l.get("name", l) if isinstance(l, dict) else str(l) for l in issue.get("labels", [])]

            if existing_labels:
                continue

            new_labels = classify_issue(title, body)
            if not new_labels:
                continue

            if update_issue(GITCODE_ORG, repo_name, number, {"labels": ",".join(new_labels)}):
                comment = f"  Issue Bot\n分类结果：`{', '.join(new_labels)}`"
                add_comment(GITCODE_ORG, repo_name, number, comment)
                print(f"[{repo_name}#{number}] Labelled: {','.join(new_labels)}")
                total_updated += 1

    print(f"\nTotal issues updated: {total_updated}")


if __name__ == "__main__":
    main()
