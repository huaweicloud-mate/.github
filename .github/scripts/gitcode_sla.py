#!/usr/bin/env python3
"""GitCode SLA 监控 - 超时检测 + 告警"""

import os
import sys
import requests
from datetime import datetime, timedelta, timezone
from feishu_notify import send_notification
from email_notify import send_email

GITCODE_TOKEN = os.environ.get("GITCODE_TOKEN", "")
GITCODE_ORG = os.environ.get("GITCODE_ORG", "hd-vector")
GITCODE_API = "https://gitcode.com/api/v5"
HEADERS = {"PRIVATE-TOKEN": GITCODE_TOKEN}

REPORT_ONLY = "--report" in sys.argv

SLA_RULES = {
    "critical": {"response_h": 4, "resolve_d": 1, "escalate_h": 8},
    "high": {"response_h": 8, "resolve_d": 3, "escalate_h": 24},
    "medium": {"response_h": 24, "resolve_d": 7, "escalate_h": 72},
    "low": {"response_h": 48, "resolve_d": 30, "escalate_h": 336},
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


def check_sla(issue, project_name, project_id):
    labels = issue.get("labels", [])
    created_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    elapsed_h = (now - created_at).total_seconds() / 3600

    priority = "medium"
    for p in ["critical", "high", "medium", "low"]:
        if any(f"priority/{p}" in str(l) for l in labels):
            priority = p
            break

    rules = SLA_RULES.get(priority, SLA_RULES["medium"])

    result = {
        "project": project_name,
        "iid": issue.get("iid", 0),
        "title": issue.get("title", ""),
        "priority": priority,
        "elapsed_h": elapsed_h,
        "status": "ok",
        "alerts": [],
    }

    # 首次响应检查
    notes_url = f"{GITCODE_API}/projects/{project_id}/issues/{issue['iid']}/notes?per_page=1"
    notes_resp = requests.get(notes_url, headers=HEADERS, timeout=15)
    has_response = notes_resp.status_code == 200 and len(notes_resp.json()) > 0

    if not has_response and elapsed_h > rules["response_h"]:
        result["status"] = "breach"
        result["alerts"].append(f"首次响应超时: {elapsed_h:.0f}h (时限 {rules['response_h']}h)")

    # 解决检查
    resolve_h = rules["resolve_d"] * 24
    if elapsed_h > resolve_h:
        result["status"] = "breach"
        result["alerts"].append(f"解决超时: {elapsed_h:.0f}h (时限 {resolve_h}h)")

    # 升级检查
    if elapsed_h > rules["escalate_h"]:
        result["status"] = "escalation"
        result["alerts"].append(f"已超升级时限: {elapsed_h:.0f}h (时限 {rules['escalate_h']}h)")

    return result


def main():
    if not GITCODE_TOKEN:
        print("GITCODE_TOKEN not set, exiting")
        return

    projects = get_projects()
    all_results = []

    for project in projects:
        project_id = project.get("id") or project.get("project_id")
        if not project_id:
            continue

        issues = get_project_issues(project_id)
        for issue in issues:
            result = check_sla(issue, project["name"], project_id)
            all_results.append(result)

    # 生成日报
    breach = [r for r in all_results if r["status"] in ("breach", "escalation")]
    warning = [r for r in all_results if r["status"] == "warning"]
    total = len(all_results)

    print(f"\nGitCode SLA Summary: total={total}, breach={len(breach)}, warning={len(warning)}")

    if REPORT_ONLY and (breach or warning):
        lines = ["## GitCode SLA 日报", f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", ""]
        if breach:
            lines.append(f"### SLA 违约/升级 ({len(breach)} 个)")
            lines.append("| 仓库 | Issue | 优先级 | 超时(h) |")
            lines.append("|------|-------|--------|---------|")
            for r in breach:
                lines.append(f"| {r['project']} | #{r['iid']} | {r['priority']} | {r['elapsed_h']:.0f} |")
            lines.append("")
        if warning:
            lines.append(f"### SLA 预警 ({len(warning)} 个)")
            lines.append("| 仓库 | Issue | 优先级 | 超时(h) |")
            lines.append("|------|-------|--------|---------|")
            for r in warning:
                lines.append(f"| {r['project']} | #{r['iid']} | {r['priority']} | {r['elapsed_h']:.0f} |")
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
