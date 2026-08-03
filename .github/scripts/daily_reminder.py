#!/usr/bin/env python3
"""每日 Issue 提醒 - 汇总所有未关闭 Issue"""

import os
import json
import requests
from datetime import datetime, timezone

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_ORG = os.environ.get("GITHUB_ORG", "huaweicloud-mate")
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


def get_repos():
    url = f"https://api.github.com/orgs/{GITHUB_ORG}/repos?per_page=100&sort=updated"
    resp = requests.get(url, headers=HEADERS)
    return [r for r in resp.json() if not r.get("archived") and not r.get("disabled")]


def get_open_issues(repo_full):
    issues = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo_full}/issues?state=open&per_page=100&page={page}&sort=created"
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        issues.extend([i for i in data if "pull_request" not in i])
        page += 1
    return issues


def main():
    repos = get_repos()
    now = datetime.now(timezone.utc)

    lines = []
    lines.append(f"# huaweicloud-mate 每日 Issue 提醒")
    lines.append(f"**{now.strftime('%Y-%m-%d %H:%M')} UTC**")
    lines.append("")

    total_open = 0
    has_any = False

    for repo in repos:
        issues = get_open_issues(repo["full_name"])
        if not issues:
            continue
        has_any = True
        total_open += len(issues)

        lines.append(f"## {repo['full_name']} ({len(issues)} 个)")
        lines.append("")
        lines.append("| # | 标题 | 标签 | 创建时间 | 负责人 |")
        lines.append("|---|------|------|---------|--------|")

        for issue in issues:
            labels = ", ".join(l["name"] for l in issue.get("labels", []))
            assignees = ", ".join(a["login"] for a in issue.get("assignees", [])) or "未分配"
            created = issue["created_at"][:10]
            html_url = issue["html_url"]
            number = issue["number"]
            title = issue["title"]

            # 超时标记
            flags = ""
            if "sla/breach" in labels:
                flags += " "
            elif "sla/warning" in labels:
                flags += " "

            lines.append(
                f"| [{flags}#{number}]({html_url}) "
                f"| {title[:40]}{'...' if len(title) > 40 else ''} "
                f"| {labels[:50]} "
                f"| {created} "
                f"| {assignees} |"
            )
        lines.append("")

    if not has_any:
        lines.append("  **所有仓库均无待处理 Issue。**")
        lines.append("")

    lines.append("---")
    lines.append(f"共 {total_open} 个待处理 Issue。请及时处理。")

    report = "\n".join(lines)
    print(report)

    # 写入文件供后续步骤使用
    os.makedirs("output", exist_ok=True)
    with open("output/reminder.md", "w", encoding="utf-8") as f:
        f.write(report)


if __name__ == "__main__":
    main()
