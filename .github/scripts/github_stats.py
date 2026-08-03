#!/usr/bin/env python3
"""GitHub Issues 统计脚本"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_ORG = os.environ.get("GITHUB_ORG", "huaweicloud-mate")
GITHUB_API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

NOW = datetime.now(timezone.utc)

# 本周范围：上周一 0:00 → 本周一 0:00（回顾上周数据）
week_day = NOW.weekday()
week_start = (NOW - timedelta(days=week_day + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
week_end = week_start + timedelta(days=7)

# 本月范围：从本月 1 号开始
this_month_start = NOW.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

# 上月范围：从上月 1 号到本月 1 号
if this_month_start.month == 1:
    last_month_start = this_month_start.replace(year=this_month_start.year - 1, month=12)
else:
    last_month_start = this_month_start.replace(month=this_month_start.month - 1)

def get_month_start(report_type):
    if report_type == "monthly":
        return last_month_start
    return this_month_start


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
        repos.extend([r for r in data if not r["archived"] and not r["disabled"]])
        page += 1
    return repos


def get_repo_issues(repo_full, state="all", since=None):
    issues = []
    page = 1
    params = {"state": state, "per_page": 100, "sort": "updated", "direction": "desc"}
    if since:
        params["since"] = since.isoformat()

    while True:
        url = f"{GITHUB_API}/repos/{repo_full}/issues"
        resp = requests.get(url, headers=HEADERS, params={**params, "page": page})
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        issues.extend([i for i in data if "pull_request" not in i])
        page += 1

    return issues


def calc_stats(repo, issues, report_type="weekly"):
    month_start = get_month_start(report_type)
    open_issues = [i for i in issues if i["state"] == "open"]
    closed_issues = [i for i in issues if i["state"] == "closed"]

    # 本周新建（自然周：周一 0:00 起）
    new_this_week = [
        i for i in issues
        if datetime.fromisoformat(i["created_at"].replace("Z", "+00:00")) >= week_start
    ]

    # 本周关闭
    closed_this_week = [
        i for i in closed_issues
        if i.get("closed_at") and datetime.fromisoformat(i["closed_at"].replace("Z", "+00:00")) >= week_start
    ]

    # 月度新建
    new_this_month = [
        i for i in issues
        if datetime.fromisoformat(i["created_at"].replace("Z", "+00:00")) >= month_start
    ]

    # 标签分布
    label_dist = {}
    for issue in issues:
        for label in issue.get("labels", []):
            name = label["name"]
            if name not in label_dist:
                label_dist[name] = 0
            label_dist[name] += 1

    # 按类型统计
    type_stats = {"type/bug": 0, "type/feature": 0, "type/documentation": 0, "type/question": 0, "other": 0}
    for issue in issues:
        labels = [l["name"] for l in issue.get("labels", [])]
        matched = False
        for t in ["type/bug", "type/feature", "type/documentation", "type/question"]:
            if t in labels:
                type_stats[t] += 1
                matched = True
                break
        if not matched:
            type_stats["other"] += 1

    # 按优先级统计
    priority_stats = {
        "priority/critical": 0, "priority/high": 0,
        "priority/medium": 0, "priority/low": 0, "unknown": 0
    }
    for issue in open_issues:
        labels = [l["name"] for l in issue.get("labels", [])]
        matched = False
        for p in ["priority/critical", "priority/high", "priority/medium", "priority/low"]:
            if p in labels:
                priority_stats[p] += 1
                matched = True
                break
        if not matched:
            priority_stats["unknown"] += 1

    # SLA 状态
    sla_stats = {"ok": 0, "warning": 0, "breach": 0}
    for issue in open_issues:
        labels = [l["name"] for l in issue.get("labels", [])]
        if "sla/breach" in labels:
            sla_stats["breach"] += 1
        elif "sla/warning" in labels:
            sla_stats["warning"] += 1
        else:
            sla_stats["ok"] += 1

    return {
        "repo": repo["full_name"],
        "total": len(issues),
        "open": len(open_issues),
        "closed": len(closed_issues),
        "new_this_week": len(new_this_week),
        "closed_this_week": len(closed_this_week),
        "new_this_month": len(new_this_month),
        "type_stats": type_stats,
        "priority_stats": priority_stats,
        "sla_stats": sla_stats,
        "label_distribution": label_dist,
    }


def main():
    import sys
    report_type = "weekly"
    for arg in sys.argv:
        if arg == "--monthly":
            report_type = "monthly"
    report_type = os.environ.get("REPORT_TYPE", report_type)

    repos = get_all_repos()
    all_stats = []

    for repo in repos:
        issues = get_repo_issues(repo["full_name"])
        if not issues:
            continue
        stats = calc_stats(repo, issues, report_type)
        all_stats.append(stats)

    # 汇总
    summary = {
        "generated_at": NOW.isoformat(),
        "org": GITHUB_ORG,
        "repo_count": len(all_stats),
        "repos": all_stats,
        "totals": {
            "total_issues": sum(s["total"] for s in all_stats),
            "open_issues": sum(s["open"] for s in all_stats),
            "closed_issues": sum(s["closed"] for s in all_stats),
            "new_this_week": sum(s["new_this_week"] for s in all_stats),
            "closed_this_week": sum(s["closed_this_week"] for s in all_stats),
            "new_this_month": sum(s["new_this_month"] for s in all_stats),
        },
        "type_totals": {
            t: sum(s["type_stats"].get(t, 0) for s in all_stats)
            for t in ["type/bug", "type/feature", "type/documentation", "type/question", "other"]
        },
        "sla_totals": {
            t: sum(s["sla_stats"].get(t, 0) for s in all_stats)
            for t in ["ok", "warning", "breach"]
        },
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    main()
