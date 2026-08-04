#!/usr/bin/env python3
"""SLA 监控脚本 - 检测超时 Issue 并告警"""

import os
import sys
import json
import yaml
import requests
from datetime import datetime, timedelta, timezone
from feishu_notify import send_notification
from email_notify import send_email

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_ORG = os.environ.get("GITHUB_ORG", "huaweicloud-mate")
GITHUB_API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
REPORT_ONLY = "--report" in sys.argv


def load_sla_config():
    with open(".github/configs/sla-rules.yml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_all_repos():
    repos = []
    page = 1
    while True:
        url = f"{GITHUB_API}/orgs/{GITHUB_ORG}/repos?per_page=100&page={page}&sort=updated"
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        repos.extend([r["full_name"] for r in data if not r["archived"] and not r["disabled"]])
        page += 1
    return repos


def get_open_issues(repo_full):
    issues = []
    page = 1
    while True:
        url = f"{GITHUB_API}/repos/{repo_full}/issues?state=open&per_page=100&page={page}&sort=created&direction=asc"
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        issues.extend(data)
        page += 1
    return issues


def get_issue_comments(repo_full, issue_number):
    url = f"{GITHUB_API}/repos/{repo_full}/issues/{issue_number}/comments?per_page=100"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json()
    return []


def get_issue_timeline(repo_full, issue_number):
    url = f"{GITHUB_API}/repos/{repo_full}/issues/{issue_number}/timeline?per_page=100"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json()
    return []


def get_first_response_time(repo_full, issue):
    """计算首次响应时间（评论或分配）"""
    issue_number = issue["number"]
    created_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
    assignees = issue.get("assignees") or []

    # 检查分配时间
    if assignees:
        timeline = get_issue_timeline(repo_full, issue_number)
        for event in timeline:
            if event.get("event") == "assigned":
                assigned_at = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
                return assigned_at - created_at

    # 检查首次评论
    comments = get_issue_comments(repo_full, issue_number)
    for comment in comments:
        comment_at = datetime.fromisoformat(comment["created_at"].replace("Z", "+00:00"))
        return comment_at - created_at

    return None


def check_sla(issue, repo_full, config):
    labels = [l["name"] for l in issue.get("labels", [])]
    created_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    elapsed = now - created_at

    # 确定优先级
    priority = "priority/medium"
    for p in ["priority/critical", "priority/high", "priority/medium", "priority/low"]:
        if p in labels:
            priority = p
            break

    sla_config = config.get("response", {}).get(priority, {})
    response_hours = sla_config.get("hours", 24)
    resolution_config = config.get("resolution", {}).get(priority, {})
    resolution_days = resolution_config.get("workdays", 7)
    escalation_config = config.get("escalation", {}).get(priority, {})
    escalation_hours = escalation_config.get("hours", 24)
    warning_hours = config.get("warning", {}).get("hours_before_deadline", 24)

    result = {
        "number": issue["number"],
        "title": issue["title"],
        "repo": repo_full,
        "priority": priority,
        "created": created_at.isoformat(),
        "elapsed_hours": elapsed.total_seconds() / 3600,
        "status": "ok",
        "alerts": [],
    }

    elapsed_hours = elapsed.total_seconds() / 3600

    # 检查解决超时
    resolution_deadline = created_at + timedelta(days=resolution_days)
    resolution_hours_limit = resolution_days * 24

    # 检查首次响应
    first_response = get_first_response_time(repo_full, issue)
    if first_response is None:
        # 未响应
        if elapsed_hours > response_hours:
            result["status"] = "breach"
            result["alerts"].append(f"首次响应超时: {elapsed_hours:.1f}h (时限 {response_hours}h)")
    else:
        response_elapsed = first_response.total_seconds() / 3600
        if response_elapsed > response_hours:
            result["alerts"].append(f"首次响应延迟: {response_elapsed:.1f}h (时限 {response_hours}h)")

    # 检查解决时间
    if elapsed_hours > resolution_hours_limit and "status/resolved" not in labels:
        result["status"] = "breach"
        result["alerts"].append(f"解决超时: {elapsed_hours:.1f}h (时限 {resolution_hours_limit}h)")

    # 检查升级
    if elapsed_hours > escalation_hours and "status/resolved" not in labels:
        result["status"] = "escalation"
        result["alerts"].append(f"已超升级时限: {elapsed_hours:.1f}h (时限 {escalation_hours}h)")

    # 检查预警
    remaining = response_hours - elapsed_hours
    if 0 < remaining < warning_hours and first_response is None:
        result["status"] = "warning"
        result["alerts"].append(f"即将超时: 剩余 {remaining:.1f}h")

    return result


def add_labels(repo_full, issue_number, labels):
    owner, repo = repo_full.split("/")
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/labels"
    resp = requests.post(url, headers=HEADERS, json={"labels": labels})
    return resp.ok


def trunc(s, n=40):
    s = str(s)
    return s if len(s) <= n else s[:n] + "..."


def generate_daily_report(sla_results):
    """生成 SLA 日报"""
    breach_items = [r for r in sla_results if r["status"] in ("breach", "escalation")]
    warning_items = [r for r in sla_results if r["status"] == "warning"]
    ok_count = sum(1 for r in sla_results if r["status"] == "ok")

    lines = []
    lines.append(f"# huaweicloud-mate SLA 日报")
    lines.append(f"**{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC** | 共 {len(sla_results)} 个活跃 Issue")
    lines.append("")

    lines.append(f"- 正常：{ok_count} | 预警：{len(warning_items)} | 违约/升级：{len(breach_items)}")
    if len(sla_results) > 0:
        ok_rate = ok_count / len(sla_results) * 100
        flag = " " if ok_rate >= 90 else " "
        lines.append(f"- SLA 达标率：{ok_rate:.1f}% {flag}（目标 90%）")
    lines.append("")

    if breach_items:
        lines.append(f"## SLA 违约/升级（{len(breach_items)} 个）")
        lines.append("")
        lines.append("| 仓库 | Issue | 标题 | 优先级 | 超时(h) | 状态 | 详情 |")
        lines.append("|------|-------|------|--------|---------|------|------|")
        for item in breach_items:
            url = f"https://github.com/{item['repo']}/issues/{item['number']}"
            alerts = "; ".join(item.get("alerts", []))
            lines.append(
                f"| {item['repo']} | [#{item['number']}]({url}) | {trunc(item['title'], 40)} "
                f"| {item['priority']} | {item['elapsed_hours']:.0f}h | {item['status']} | {alerts} |"
            )
        lines.append("")

    if warning_items:
        lines.append(f"## SLA 预警（{len(warning_items)} 个）")
        lines.append("")
        lines.append("| 仓库 | Issue | 标题 | 优先级 | 超时(h) | 详情 |")
        lines.append("|------|-------|------|--------|---------|------|")
        for item in warning_items:
            url = f"https://github.com/{item['repo']}/issues/{item['number']}"
            alerts = "; ".join(item.get("alerts", []))
            lines.append(
                f"| {item['repo']} | [#{item['number']}]({url}) | {trunc(item['title'], 40)} "
                f"| {item['priority']} | {item['elapsed_hours']:.0f}h | {alerts} |"
            )
        lines.append("")

    if not breach_items and not warning_items:
        lines.append("## 状态")
        lines.append("")
        lines.append("  **所有 Issue 均在 SLA 时限内，无超时。**")
        lines.append("")

    return "\n".join(lines)


def main():
    config = load_sla_config()
    repos = get_all_repos()
    print(f"Found {len(repos)} repos in {GITHUB_ORG}")

    all_results = []

    for repo_full in repos:
        issues = get_open_issues(repo_full)
        if not issues:
            continue

        for issue in issues:
            # 跳过 PR
            if "pull_request" in issue:
                continue

            result = check_sla(issue, repo_full, config)
            all_results.append(result)

            # 打标签
            if not REPORT_ONLY:
                current_labels = [l["name"] for l in issue.get("labels", [])]
                new_labels = []

                breach_label = config.get("breach", {}).get("label", "sla/breach")
                warning_label = config.get("warning", {}).get("label", "sla/warning")
                escalation_label = config.get("escalation", {}).get("label", "escalation")

                if result["status"] == "warning" and warning_label not in current_labels:
                    new_labels.append(warning_label)
                if result["status"] == "breach" and breach_label not in current_labels:
                    new_labels.append(breach_label)
                if result["status"] == "escalation" and escalation_label not in current_labels:
                    new_labels.append(escalation_label)

                if new_labels:
                    add_labels(repo_full, issue["number"], new_labels)
                    print(f"[{repo_full}#{issue['number']}] Added labels: {new_labels}")

    # 发送飞书日报 + 邮件
    if all_results and REPORT_ONLY:
        report = generate_daily_report(all_results)
        print(report)
        # 保存报告文件
        os.makedirs("output", exist_ok=True)
        with open("output/sla_report.md", "w", encoding="utf-8") as f:
            f.write(report)
        send_notification(
            subject=f"[SLA 日报] {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            body=report,
            event_type="report.sla_daily",
        )
        send_email(subject=f"[SLA 日报] huaweicloud-mate {datetime.now(timezone.utc).strftime('%Y-%m-%d')}", body=report)

    # 汇总
    total = len(all_results)
    breach_count = sum(1 for r in all_results if r["status"] == "breach")
    escalation_count = sum(1 for r in all_results if r["status"] == "escalation")
    warning_count = sum(1 for r in all_results if r["status"] == "warning")
    ok_count = sum(1 for r in all_results if r["status"] == "ok")

    print(f"\nSLA Summary:")
    print(f"  Total open issues: {total}")
    print(f"  OK: {ok_count}")
    print(f"  Warning: {warning_count}")
    print(f"  Breach: {breach_count}")
    print(f"  Escalation: {escalation_count}")


if __name__ == "__main__":
    main()
