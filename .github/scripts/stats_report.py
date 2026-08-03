#!/usr/bin/env python3
"""合并统计 + 生成报表 + 飞书通知 + 邮件报告"""

import os
import sys
import json
from datetime import datetime, timedelta, timezone
from feishu_notify import send_notification
from email_notify import send_email


def load_data(env_var):
    data = os.environ.get(env_var, "{}")
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return {}


def pct(part, total):
    if total == 0:
        return "-"
    return f"{part / total * 100:.1f}%"


def _level_bar(value, warn, danger):
    if value >= danger:
        return ""
    elif value >= warn:
        return ""
    return ""


def generate_weekly_report(github_data, gitcode_data):
    now = datetime.now(timezone.utc)
    # 回顾上周数据
    last_monday = now - timedelta(days=now.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    iso_year, iso_week, _ = last_monday.isocalendar()
    week_num = iso_week
    year = iso_year
    week_range = f"{last_monday.strftime('%m.%d')} - {last_sunday.strftime('%m.%d')}"

    gh = github_data.get("totals", {})
    repos = github_data.get("repos", [])
    type_totals = github_data.get("type_totals", {})
    sla_totals = github_data.get("sla_totals", {"ok": 0, "warning": 0, "breach": 0})
    total_sla = sum(sla_totals.values())
    gc = gitcode_data.get("summary", {})
    gc_projects = gitcode_data.get("projects", [])

    new_w = gh.get("new_this_week", 0)
    closed_w = gh.get("closed_this_week", 0)
    open_all = gh.get("open_issues", 0)
    total_all = gh.get("total_issues", 0)
    new_m = gh.get("new_this_month", 0)

    lines = []
    lines.append(f"# huaweicloud-mate Issues 周报")
    lines.append(f"**{year}-W{week_num:02d} | {week_range}** | 生成时间: {now.strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("")

    # 概览
    lines.append("## 概览")
    lines.append("")
    lines.append("| 指标 | 本周数值 | 总活跃/累计 |")
    lines.append("|------|---------|------------|")
    lines.append(f"| 本周新建 | {new_w} | / |")
    lines.append(f"| 本周关闭 | {closed_w} | / |")
    lines.append(f"| 活跃 Issue | {open_all} | / |")
    lines.append(f"| 历史累计 | / | {total_all} |")
    lines.append(f"| 本月新建 | / | {new_m} |")
    net = new_w - closed_w
    net_str = f"+{net}" if net > 0 else str(net)
    lines.append(f"| 本周净变化 | {net_str} | / |")
    lines.append("")

    # SLA
    lines.append("## SLA 概览")
    lines.append("")
    lines.append(f"- 总活跃 Issue：{open_all} 个")
    oc = sla_totals.get("ok", 0)
    wn = sla_totals.get("warning", 0)
    br = sla_totals.get("breach", 0)
    if total_sla > 0:
        ok_rate = oc / total_sla * 100
        flag = " " if ok_rate >= 90 else " "
        flag_b = "  " if br > 0 else ""
        lines.append(f"- 达标率：{ok_rate:.1f}% {flag}（目标 90%）")
    lines.append(f"- 正常：{oc} | 预警：{wn} | 违约：{br} {flag_b}")
    lines.append("")

    # 类型分布
    lines.append("## Issue 类型分布")
    lines.append("")
    lines.append("| 类型 | 总数 | 占比 |")
    lines.append("|------|------|------|")
    total_typed = sum(v for k, v in type_totals.items() if k != "other")
    for t in ["type/bug", "type/feature", "type/documentation", "type/question"]:
        c = type_totals.get(t, 0)
        lines.append(f"| {t} | {c} | {pct(c, max(total_typed, 1))} |")
    lines.append(f"| other | {type_totals.get('other', 0)} | - |")
    lines.append("")

    # 仓库明细
    if repos:
        lines.append("## 仓库明细")
        lines.append("")
        lines.append("| 仓库 | 活跃 | 本周新增 | 本周关闭 | 累计 |")
        lines.append("|------|------|---------|---------|------|")
        for r in sorted(repos, key=lambda x: x.get("open", 0), reverse=True):
            lines.append(
                f"| {r.get('repo', '')} | {r.get('open', 0)} | "
                f"{r.get('new_this_week', 0)} | {r.get('closed_this_week', 0)} | "
                f"{r.get('total', 0)} |"
            )
        lines.append("")

    # GitCode
    if gc_projects:
        lines.append("## GitCode 统计（hd-vector）")
        lines.append("")
        lines.append("| 仓库 | 开启 | 关闭 | 合计 |")
        lines.append("|------|------|------|------|")
        for proj in gc_projects:
            lines.append(
                f"| {proj.get('name', '')} | "
                f"{proj.get('open', 0)} | {proj.get('closed', 0)} | {proj.get('total', 0)} |"
            )
        lines.append("")

    # 小结
    lines.append("---")
    if br > 0:
        lines.append(f"  **注意**：有 {br} 个 Issue SLA 违约，请及时处理。")
    if new_w == 0 and closed_w == 0:
        lines.append("  本周无 Issue 活动。")
    elif new_w == 0:
        lines.append(f"  本周无新建 Issue，关闭 {closed_w} 个。")
    elif closed_w == 0:
        lines.append(f"  本周新建 {new_w} 个，无关闭。")
    lines.append("")

    return "\n".join(lines)


def generate_monthly_report(github_data, gitcode_data):
    now = datetime.now(timezone.utc)
    if now.month == 1:
        report_month = f"{now.year - 1}-12"
        month_start = now.replace(year=now.year - 1, month=12, day=1)
    else:
        report_month = f"{now.year}-{now.month - 1:02d}"
        month_start = now.replace(month=now.month - 1, day=1)
    if month_start.month == 12:
        month_end_date = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end_date = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
    month_range = f"{month_start.strftime('%m.%d')} - {month_end_date.strftime('%m.%d')}"

    gh = github_data.get("totals", {})
    repos = github_data.get("repos", [])
    type_totals = github_data.get("type_totals", {})
    gc = gitcode_data.get("summary", {})
    gc_projects = gitcode_data.get("projects", [])

    new_m = gh.get("new_this_month", 0)
    closed_all = gh.get("closed_issues", 0)
    open_all = gh.get("open_issues", 0)
    total_all = gh.get("total_issues", 0)

    lines = []
    lines.append(f"# huaweicloud-mate Issues 月报")
    lines.append(f"**{report_month} | {month_range}** | 生成时间: {now.strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("")

    # 概览
    lines.append("## 概览")
    lines.append("")
    lines.append("| 指标 | 本月数值 | 全量 |")
    lines.append("|------|---------|------|")
    lines.append(f"| 月度新建 | {new_m} | / |")
    lines.append(f"| 月度关闭 | / | {closed_all} |")
    lines.append(f"| 当前活跃 | {open_all} | / |")
    lines.append(f"| 历史累计 | / | {total_all} |")
    if total_all > 0:
        cr = pct(total_all - open_all, total_all)
        lines.append(f"| 累计关闭率 | / | {cr} |")
    lines.append("")

    # 类型分布
    lines.append("## Issue 类型分布")
    lines.append("")
    lines.append("| 类型 | 数量 | 占比 |")
    lines.append("|------|------|------|")
    total_typed = sum(v for k, v in type_totals.items() if k != "other")
    for t in ["type/bug", "type/feature", "type/documentation", "type/question"]:
        c = type_totals.get(t, 0)
        lines.append(f"| {t} | {c} | {pct(c, max(total_typed, 1))} |")
    lines.append(f"| other | {type_totals.get('other', 0)} | - |")
    lines.append("")

    # 仓库排行
    if repos:
        lines.append("## 仓库 Issue 排行")
        lines.append("")
        lines.append("| 排名 | 仓库 | 活跃 | 本月新建 | 累计 |")
        lines.append("|------|------|------|---------|------|")
        sorted_repos = sorted(repos, key=lambda x: x.get("total", 0), reverse=True)[:10]
        for i, r in enumerate(sorted_repos, 1):
            lines.append(
                f"| {i} | {r.get('repo', '')} | {r.get('open', 0)} | "
                f"{r.get('new_this_month', 0)} | {r.get('total', 0)} |"
            )
        lines.append("")

    # GitCode
    if gc_projects:
        lines.append("## GitCode 统计（hd-vector）")
        lines.append("")
        lines.append("| 仓库 | 开启 | 关闭 | 合计 |")
        lines.append("|------|------|------|------|")
        for proj in gc_projects:
            lines.append(
                f"| {proj.get('name', '')} | "
                f"{proj.get('open', 0)} | {proj.get('closed', 0)} | {proj.get('total', 0)} |"
            )
        lines.append("")

    lines.append("---")
    if new_m == 0:
        lines.append("  **提示**：本月无新建 Issue。")
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

    if not github_data:
        for path in ["output/github_stats.json", "github_stats.json"]:
            try:
                with open(path, "r") as f:
                    github_data = json.load(f)
                    break
            except (FileNotFoundError, json.JSONDecodeError):
                continue
        if not github_data:
            github_data = {"totals": {}, "repos": [], "type_totals": {}, "sla_totals": {}}

    if not gitcode_data:
        for path in ["output/gitcode_stats.json", "gitcode_stats.json"]:
            try:
                with open(path, "r") as f:
                    gitcode_data = json.load(f)
                    break
            except (FileNotFoundError, json.JSONDecodeError):
                continue
        if not gitcode_data:
            gitcode_data = {"projects": [], "summary": {}}

    if report_type == "monthly":
        now = datetime.now(timezone.utc)
        if now.month == 1:
            report_month = f"{now.year - 1}-12"
        else:
            report_month = f"{now.year}-{now.month - 1:02d}"
        subject = f"[Issue 月报] huaweicloud-mate {report_month}"
        report = generate_monthly_report(github_data, gitcode_data)
    else:
        # 周报：回顾上周
        last_monday = datetime.now(timezone.utc) - timedelta(days=datetime.now(timezone.utc).weekday() + 7)
        iso_year, iso_week, _ = last_monday.isocalendar()
        year = iso_year
        week_num = iso_week
        subject = f"[Issue 周报] huaweicloud-mate {year}-W{week_num:02d}"
        report = generate_weekly_report(github_data, gitcode_data)

    print(report)

    os.makedirs("output", exist_ok=True)
    report_path = os.environ.get("REPORT_FILE", "output/report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to {report_path}")

    event_type = "report.monthly" if report_type == "monthly" else "report.weekly"
    send_notification(subject=subject, body=report, event_type=event_type)

    send_email(subject=subject, body=report)


if __name__ == "__main__":
    main()
