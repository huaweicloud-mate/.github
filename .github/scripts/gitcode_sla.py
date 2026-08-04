#!/usr/bin/env python3
"""GitCode SLA 监控 - 超时检测 + 告警 (API v5)"""

import os
import sys
import requests
from datetime import datetime, timedelta, timezone
from feishu_notify import send_notification
from email_notify import send_email

GITCODE_TOKEN = os.environ.get("GITCODE_TOKEN", "")
GITCODE_ORG = os.environ.get("GITCODE_ORG", "hd-vector")
GITCODE_API = "https://api.gitcode.com/api/v5"
HEADERS = {"PRIVATE-TOKEN": GITCODE_TOKEN, "Content-Type": "application/json"}

REPORT_ONLY = "--report" in sys.argv

SLA_RULES = {
    "critical": {"response_h": 4, "resolve_d": 1, "escalate_h": 8},
    "high": {"response_h": 8, "resolve_d": 3, "escalate_h": 24},
    "medium": {"response_h": 24, "resolve_d": 7, "escalate_h": 72},
    "low": {"response_h": 48, "resolve_d": 30, "escalate_h": 336},
}


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


def get_issue_comments(owner, repo, number):
    url = f"{GITCODE_API}/repos/{owner}/{repo}/issues/{number}/comments?per_page=1"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        return resp.json()
    return []


def check_sla(issue, repo_name):
    labels = [l.get("name", l) if isinstance(l, dict) else str(l) for l in issue.get("labels", [])]
    created_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    elapsed_h = (now - created_at).total_seconds() / 3600

    priority = "medium"
    for p in ["critical", "high", "medium", "low"]:
        if f"priority/{p}" in labels:
            priority = p
            break

    rules = SLA_RULES.get(priority, SLA_RULES["medium"])

    result = {
        "repo": repo_name,
        "number": issue.get("number", 0),
        "title": issue.get("title", ""),
        "priority": priority,
        "elapsed_h": elapsed_h,
        "status": "ok",
        "alerts": [],
    }

    comments = get_issue_comments(GITCODE_ORG, repo_name, issue["number"])
    has_response = len(comments) > 0

    if not has_response and elapsed_h > rules["response_h"]:
        result["status"] = "breach"
        result["alerts"].append(f"首次响应超时: {elapsed_h:.0f}h (时限 {rules['response_h']}h)")

    resolve_h = rules["resolve_d"] * 24
    if elapsed_h > resolve_h:
        result["status"] = "breach"
        result["alerts"].append(f"解决超时: {elapsed_h:.0f}h (时限 {resolve_h}h)")

    if elapsed_h > rules["escalate_h"]:
        result["status"] = "escalation"
        result["alerts"].append(f"已超升级时限: {elapsed_h:.0f}h (时限 {rules['escalate_h']}h)")

    return result


def main():
    if not GITCODE_TOKEN:
        print("GITCODE_TOKEN not set, exiting")
        return

    repos = get_repos()
    all_results = []

    for repo in repos:
        repo_name = repo.get("path") or repo.get("name") or repo.get("full_name", "").split("/")[-1]
        if not repo_name:
            continue

        issues = get_repo_issues(GITCODE_ORG, repo_name)
        for issue in issues:
            result = check_sla(issue, repo_name)
            all_results.append(result)

    breach = [r for r in all_results if r["status"] in ("breach", "escalation")]
    warning = [r for r in all_results if r["status"] == "warning"]
    total = len(all_results)

    print(f"\nGitCode SLA Summary: total={total}, breach={len(breach)}, warning={len(warning)}")

    if REPORT_ONLY and (breach or warning):
        lines = ["## GitCode SLA 日报", f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", ""]
        if breach:
            lines.append(f"### SLA 违约/升级 ({len(breach)} 个)")
            lines.append("| 仓库 | Issue | 标题 | 优先级 | 超时(h) |")
            lines.append("|------|-------|------|--------|---------|")
            for r in breach:
                lines.append(f"| {r['repo']} | #{r['number']} | {r['title'][:20]} | {r['priority']} | {r['elapsed_h']:.0f} |")
            lines.append("")
        if warning:
            lines.append(f"### SLA 预警 ({len(warning)} 个)")
            lines.append("| 仓库 | Issue | 优先级 | 超时(h) |")
            lines.append("|------|-------|--------|---------|")
            for r in warning:
                lines.append(f"| {r['repo']} | #{r['number']} | {r['priority']} | {r['elapsed_h']:.0f} |")
            lines.append("")

        report = "\n".join(lines)
        print(report)
        send_notification(
            subject=f"[GitCode SLA 日报] {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            body=report,
            event_type="report.sla_daily",
        )
        send_email(subject=f"[GitCode SLA 日报] hd-vector {datetime.now(timezone.utc).strftime('%Y-%m-%d')}", body=report)


if __name__ == "__main__":
    main()
