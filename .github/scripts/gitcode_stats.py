#!/usr/bin/env python3
"""GitCode Issues 统计抓取脚本 - 仅统计，不同步"""

import os
import json
import requests
from datetime import datetime, timezone

GITCODE_TOKEN = os.environ.get("GITCODE_TOKEN", "")
GITCODE_ORG = os.environ.get("GITCODE_ORG", "hd-vector")
GITCODE_API = "https://gitcode.com/api/v5"
HEADERS = {"PRIVATE-TOKEN": GITCODE_TOKEN} if GITCODE_TOKEN else {}


def get_org_projects():
    """获取组织下所有项目"""
    if not GITCODE_TOKEN:
        return {"error": "GITCODE_TOKEN not set"}

    url = f"{GITCODE_API}/groups/{GITCODE_ORG}/projects?per_page=100"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}", "message": resp.text}
    except Exception as e:
        return {"error": str(e)}


def get_project_issues(project_id):
    """获取项目 Issue 统计"""
    if not GITCODE_TOKEN:
        return []

    # 尝试获取全部 Issue
    issues = []
    page = 1
    while True:
        url = f"{GITCODE_API}/projects/{project_id}/issues?per_page=100&page={page}"
        try:
            resp = requests.get(url, headers=HEADERS)
            if resp.status_code != 200:
                break
            data = resp.json()
            if not data:
                break
            issues.extend(data)
            page += 1
        except Exception:
            break

    return issues


def main():
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "org": GITCODE_ORG,
        "projects": [],
        "summary": {
            "total_projects": 0,
            "total_issues": 0,
            "open_issues": 0,
            "closed_issues": 0,
            "accessible": False,
        },
        "error": None,
    }

    projects = get_org_projects()

    if isinstance(projects, dict) and "error" in projects:
        result["error"] = projects["error"]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 兼容不同 API 响应格式
    if isinstance(projects, list):
        project_list = projects
    elif isinstance(projects, dict):
        project_list = projects.get("data", projects.get("items", []))
    else:
        project_list = []

    result["summary"]["accessible"] = True
    result["summary"]["total_projects"] = len(project_list)

    for project in project_list:
        project_id = project.get("id") or project.get("project_id")
        project_name = project.get("name", "unknown")
        project_path = project.get("path_with_namespace", project_name)

        if not project_id:
            continue

        issues = get_project_issues(project_id)
        open_issues = [i for i in issues if i.get("state") == "opened"]
        closed_issues = [i for i in issues if i.get("state") == "closed"]

        # 按标签统计
        label_dist = {}
        for issue in issues:
            for label in issue.get("labels", []):
                label_name = label if isinstance(label, str) else label.get("name", str(label))
                label_dist[label_name] = label_dist.get(label_name, 0) + 1

        project_stats = {
            "name": project_name,
            "path": project_path,
            "total": len(issues),
            "open": len(open_issues),
            "closed": len(closed_issues),
            "labels": label_dist,
        }

        result["projects"].append(project_stats)
        result["summary"]["total_issues"] += len(issues)
        result["summary"]["open_issues"] += len(open_issues)
        result["summary"]["closed_issues"] += len(closed_issues)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    main()
