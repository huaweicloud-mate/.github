#!/usr/bin/env python3
"""合并统计 + 生成报表 + 飞书通知"""

import os
import sys
import json
from datetime import datetime, timezone
from feishu_notify import send_notification


def load_data(env_var):
    data = os.environ.get(env_var, "{}")
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return {}


def generate_weekly_report(github_data, gitcode_data):
    now = datetime.now(timezone.utc)
    week_num = now.isocalendar()[1]
    year = now.year

    lines = []
    lines.append(f"## huaweicloud-mate Issues 周报（{year}-W{week_num:02d}）")
    lines.append("")
    lines.append("### 概览")
    lines.append("")

    gh_totals = github_data.get("totals", {})
    lines.append("| 指标 | 本周 |")
    lines.append("|------|------|")
    lines.append(f"| 新建 Issue | {gh_totals.get('new_this_week', 0)} |")
    lines.append(f"| 已关闭 | {gh_totals.get('closed_this_week', 0)} |")
    lines.append(f"| 活跃 (已开启) | {gh_totals.get('open_issues', 0)} |")
    lines.append(f"| 总 Issue 数 | {gh_totals.get('total_issues', 0)} |")
    lines.append("")

    # 按类型分布
    type_totals = github_data.get("type_totals", {})
    lines.append("### Issue 类型分布")
    lines.append("")
    lines.append("| 类型 | 数量 |")
    lines.append("|------|------|")
    for t, count in sorted(type_totals.items(), key=lambda x: -x[1]):
        lines.append(f"| {t} | {count} |")
    lines.append("")

    # SLA 状态
    sla_totals = github_data.get("sla_totals", {"ok": 0, "warning": 0, "breach": 0})
    total_sla = sum(sla_totals.values())
    lines.append("### SLA 达标率")
    lines.append("")
    if total_sla > 0:
        ok_rate = sla_totals["ok"] / total_sla * 100
        lines.append(f"- 总达标率：{ok_rate:.1f}%（目标 90%）")
    lines.append(f"- 正常：{sla_totals.get('ok', 0)}")
    lines.append(f"- 预警：{sla_totals.get('warning', 0)}")
    lines.append(f"- 违约：{sla_totals.get('breach', 0)}")
    lines.append("")

    # GitCode 统计
    gitcode_projects = gitcode_data.get("projects", [])
    if gitcode_projects:
        lines.append("### GitCode 统计（hd-vector）")
        lines.append("")
        lines.append("| 仓库 | 开启 | 关闭 | 合计 |")
        lines.append("|------|------|------|------|")
        for proj in gitcode_projects:
            lines.append(
                f"| {proj.get('name', '')} | "
                f"{proj.get('open', 0)} | {proj.get('closed', 0)} | {proj.get('total', 0)} |"
            )
        lines.append("")

    # 按仓库明细
    repos = github_data.get("repos", [])
    if repos:
        lines.append("### 仓库明细")
        lines.append("")
        lines.append("| 仓库 | 开启 | 新增(周) | 关闭(周) |")
        lines.append("|------|------|---------|---------|")
        for r in repos:
            lines.append(
                f"| {r.get('repo', '')} | {r.get('open', 0)} | "
                f"{r.get('new_this_week', 0)} | {r.get('closed_this_week', 0)} |"
            )
        lines.append("")

    return "\n".join(lines)


def generate_monthly_report(github_data, gitcode_data):
    now = datetime.now(timezone.utc)

    lines = []
    lines.append(f"## huaweicloud-mate Issues 月报（{now.strftime('%Y-%m')}）")
    lines.append("")

    gh_totals = github_data.get("totals", {})
    lines.append("### 概览")
    lines.append("")
    lines.append("| 指标 | 本月 |")
    lines.append("|------|------|")
    lines.append(f"| 新建 Issue | {gh_totals.get('new_this_month', 0)} |")
    lines.append(f"| 已关闭 | {gh_totals.get('closed_issues', 0)} |")
    lines.append(f"| 活跃 (已开启) | {gh_totals.get('open_issues', 0)} |")
    lines.append(f"| 总 Issue 数 | {gh_totals.get('total_issues', 0)} |")
    lines.append("")

    # 按类型
    type_totals = github_data.get("type_totals", {})
    lines.append("### 按类型分布")
    lines.append("")
    lines.append("| 类型 | 数量 |")
    lines.append("|------|------|")
    for t, count in sorted(type_totals.items(), key=lambda x: -x[1]):
        lines.append(f"| {t} | {count} |")
    lines.append("")

    # GitCode
    gitcode_projects = gitcode_data.get("projects", [])
    if gitcode_projects:
        lines.append("### GitCode 统计（hd-vector）")
        lines.append("")
        lines.append("| 仓库 | 开启 | 关闭 | 合计 |")
        lines.append("|------|------|------|------|")
        for proj in gitcode_projects:
            lines.append(
                f"| {proj.get('name', '')} | "
                f"{proj.get('open', 0)} | {proj.get('closed', 0)} | {proj.get('total', 0)} |"
            )
        lines.append("")

    # 仓库贡献排行
    repos = github_data.get("repos", [])
    if repos:
        lines.append("### 仓库 Issue 排行（按总量）")
        lines.append("")
        lines.append("| 排名 | 仓库 | 总数 | 开启 |")
        lines.append("|------|------|------|------|")
        sorted_repos = sorted(repos, key=lambda x: x.get("total", 0), reverse=True)[:10]
        for i, r in enumerate(sorted_repos, 1):
            lines.append(f"| {i} | {r.get('repo', '')} | {r.get('total', 0)} | {r.get('open', 0)} |")
        lines.append("")

    return "\n".join(lines)


def main():
    report_type = "weekly"
    for arg in sys.argv:
        if arg.startswith("--type"):
            report_type = arg.split("=", 1)[1] if "=" in arg else "weekly"

    report_type = os.environ.get("REPORT_TYPE", report_type)

    github_data = load_data("GITHUB_DATA")
    gitcode_data = load_data("GITCODE_DATA")

    # 如果数据为空，尝试从文件读取
    if not github_data:
        try:
            with open("github_stats.json", "r") as f:
                github_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            github_data = {"totals": {}, "repos": [], "type_totals": {}, "sla_totals": {}}

    if not gitcode_data:
        try:
            with open("gitcode_stats.json", "r") as f:
                gitcode_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            gitcode_data = {"projects": [], "summary": {}}

    # 生成报告
    if report_type == "monthly":
        subject = f"[Issue 月报] huaweicloud-mate {datetime.now(timezone.utc).strftime('%Y-%m')}"
        report = generate_monthly_report(github_data, gitcode_data)
    else:
        week_num = datetime.now(timezone.utc).isocalendar()[1]
        year = datetime.now(timezone.utc).year
        subject = f"[Issue 周报] huaweicloud-mate {year}-W{week_num:02d}"
        report = generate_weekly_report(github_data, gitcode_data)

    print(report)

    # 发送飞书通知
    event_type = "report.monthly" if report_type == "monthly" else "report.weekly"
    send_notification(subject=subject, body=report, event_type=event_type)


if __name__ == "__main__":
    main()
