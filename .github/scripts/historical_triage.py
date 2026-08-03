#!/usr/bin/env python3
"""历史 Issue 批量 Triage"""

import os
import json
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_ORG = "huaweicloud-mate"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

KEYWORDS = {
    "type/bug": ["bug", "error", "crash", "broken", "fail", "exception", "traceback", "fix", "bug report", "报错", "崩溃", "错误", "异常"],
    "type/feature": ["feature", "request", "add", "support", "enhance", "improve", "new", "功能", "建议", "希望", "新增"],
    "type/question": ["question", "how to", "how do", "help", "usage", "example", "问题", "咨询", "请教"],
    "type/documentation": ["doc", "documentation", "readme", "guide", "tutorial", "文档", "说明"],
}

AREAS = {
    "area/api": ["api", "接口", "rest", "endpoint"],
    "area/frontend": ["ui", "前端", "frontend", "web", "页面", "界面", "布局", "按钮"],
    "area/ci-cd": ["ci", "cd", "pipeline", "workflow", "action", "构建", "部署", "deploy"],
    "area/sdk": ["sdk", "client", "library", "包", "依赖"],
    "area/security": ["security", "安全", "漏洞", "vulnerability", "auth", "token"],
    "area/performance": ["performance", "性能", "慢", "优化", "perf"],
}


def get_repos():
    url = f"https://api.github.com/orgs/{GITHUB_ORG}/repos?per_page=100&sort=updated"
    resp = requests.get(url, headers=HEADERS)
    return [r for r in resp.json() if not r["archived"] and not r["disabled"]]


def get_issues(repo_full, state="open"):
    issues = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo_full}/issues?state={state}&per_page=100&page={page}"
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        issues.extend([i for i in data if "pull_request" not in i])
        page += 1
    return issues


def classify(title, body):
    text = f"{title} {body or ''}".lower()
    labels = []

    for label, kws in KEYWORDS.items():
        if any(kw in text for kw in kws):
            labels.append(label)
            break

    priority = "priority/medium"
    if any(w in text for w in ["critical", "urgent", "emergency", "p0", "紧急", "宕机"]):
        priority = "priority/critical"
    elif any(w in text for w in ["high", "important", "blocker", "重要", "阻塞"]):
        priority = "priority/high"
    elif any(w in text for w in ["low", "minor", "cosmetic", "一般"]):
        priority = "priority/low"
    labels.append(priority)

    for label, kws in AREAS.items():
        if any(kw in text for kw in kws):
            labels.append(label)

    labels.append("agent/triaged")
    return labels


def add_labels(repo_full, issue_number, labels):
    url = f"https://api.github.com/repos/{repo_full}/issues/{issue_number}/labels"
    resp = requests.post(url, headers=HEADERS, json={"labels": labels})
    if resp.ok:
        return True
    print(f"  Failed: {resp.status_code} {resp.text[:200]}")
    return False


def main():
    repos = get_repos()
    print(f"Found {len(repos)} repos")
    total_updated = 0

    for repo in repos:
        repo_full = repo["full_name"]
        issues = get_issues(repo_full)
        untriaged = [i for i in issues if "agent/triaged" not in [l["name"] for l in i.get("labels", [])]]
        if not untriaged:
            continue

        print(f"\n{repo_full}: {len(untriaged)} untriaged")
        for issue in untriaged:
            labels = classify(issue.get("title", ""), issue.get("body", ""))
            existing = [l["name"] for l in issue.get("labels", [])]
            if set(labels).issubset(set(existing)):
                continue
            if add_labels(repo_full, issue["number"], labels):
                print(f"  #{issue['number']}: {', '.join(labels)}")
                total_updated += 1

    print(f"\nTotal updated: {total_updated}")


if __name__ == "__main__":
    main()
