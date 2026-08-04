#!/usr/bin/env python3
"""GitCode Issues 统计抓取脚本 - 仅统计，不同步 (API v5)"""

import os
import json
import requests
from datetime import datetime, timezone

GITCODE_TOKEN = os.environ.get("GITCODE_TOKEN", "")
GITCODE_ORG = os.environ.get("GITCODE_ORG", "hd-vector")
GITCODE_API = "https://api.gitcode.com/api/v5"
HEADERS = {"PRIVATE-TOKEN": GITCODE_TOKEN, "Content-Type": "application/json"} if GITCODE_TOKEN else {}


def get_org_repos():
    """获取组织下所有仓库（v5: /orgs/{org}/repos）"""
    if not GITCODE_TOKEN:
        return {"error": "GITCODE_TOKEN not set"}

    url = f"{GITCODE_API}/orgs/{GITCODE_ORG}/repos?per_page=100"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}", "message": resp.text}
    except Exception as e:
        return {"error": str(e)}


def get_repo_issues(owner, repo):
    """获取仓库所有 Issue"""
    if not GITCODE_TOKEN:
        return []

    issues = []
    page = 1
    while True:
        url = f"{GITCODE_API}/repos/{owner}/{repo}/issues?per_page=100&page={page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
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

    repos = get_org_repos()

    if isinstance(repos, dict) and "error" in repos:
        result["error"] = repos["error"]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if isinstance(repos, list):
        repo_list = repos
    elif isinstance(repos, dict):
        repo_list = repos.get("data", repos.get("items", []))
    else:
        repo_list = []

    result["summary"]["accessible"] = True
    result["summary"]["total_projects"] = len(repo_list)

    for repo in repo_list:
        repo_name = repo.get("path") or repo.get("name") or repo.get("full_name", "").split("/")[-1]
        if not repo_name:
            continue

        issues = get_repo_issues(GITCODE_ORG, repo_name)
        open_issues = [i for i in issues if i.get("state") == "opened"]
        closed_issues = [i for i in issues if i.get("state") == "closed"]

        label_dist = {}
        for issue in issues:
            for label in issue.get("labels", []):
                label_name = label if isinstance(label, str) else label.get("name", str(label))
                label_dist[label_name] = label_dist.get(label_name, 0) + 1

        project_stats = {
            "name": repo_name,
            "path": f"{GITCODE_ORG}/{repo_name}",
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
