#!/usr/bin/env python3
"""
Issue Digest Bot - Daily issue statistics and notification

Runs daily to:
1. Collect all open issues across the organization
2. Summarize by assignee/repository/priority
3. Notify via GitHub (create/update a tracking issue with @mentions)
4. Notify via Feishu (send card message to group or individuals)
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
import base64

# ============================================================
# GitHub App Authentication
# ============================================================

def jwt_encode(payload, private_key_pem):
    import base64 as b64
    def base64url(data):
        return b64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')
    header = {"alg": "RS256", "typ": "JWT"}
    header_b64 = base64url(json.dumps(header, separators=(',', ':')).encode())
    payload_b64 = base64url(json.dumps(payload, separators=(',', ':')).encode())
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    message = f"{header_b64}.{payload_b64}".encode()
    signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    signature_b64 = base64url(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def get_installation_token(app_id, private_key_pem, installation_id):
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 600, "iss": int(app_id)}
    token_jwt = jwt_encode(payload, private_key_pem)
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {"Authorization": f"Bearer {token_jwt}", "Accept": "application/vnd.github+json", "User-Agent": "issue-digest"}
    req = urllib.request.Request(url, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()).get("token")
    except Exception as e:
        print(f"Auth error: {e}", file=sys.stderr)
        return None

def github_api(method, path, token, data=None):
    url = f"https://api.github.com{path}"
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "User-Agent": "issue-digest"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 204:
                return {"status": "success"}
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:500]
        return {"error": error_body, "status_code": e.code}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Issue Collection
# ============================================================

def get_org_repos(org, token):
    """Get all repos the App can access"""
    result = github_api("GET", f"/installation/repositories?per_page=100", token)
    repos = result.get("repositories", [])
    return [r for r in repos if r["full_name"].startswith(f"{org}/")]

def get_open_issues(repo_full_name, token):
    """Get all open issues for a repo (not PRs)"""
    issues = []
    page = 1
    while True:
        result = github_api("GET", f"/repos/{repo_full_name}/issues?state=open&per_page=100&page={page}", token)
        if not isinstance(result, list) or not result:
            break
        # Filter out PRs (GitHub returns PRs in the issues API)
        for item in result:
            if "pull_request" not in item:
                issues.append(item)
        if len(result) < 100:
            break
        page += 1
    return issues

def collect_all_issues(org, token):
    """Collect all open issues across the organization"""
    repos = get_org_repos(org, token)
    print(f"Found {len(repos)} repos")
    
    all_issues = []
    for repo in repos:
        repo_name = repo["full_name"]
        issues = get_open_issues(repo_name, token)
        if issues:
            print(f"  {repo_name}: {len(issues)} open issues")
            for issue in issues:
                issue["_repo"] = repo_name
                issue["_repo_url"] = repo["html_url"]
            all_issues.extend(issues)
    
    print(f"Total: {len(all_issues)} open issues")
    return all_issues

# ============================================================
# Summarize
# ============================================================

def summarize_by_assignee(issues):
    """Group issues by assignee"""
    by_assignee = {}
    unassigned = []
    
    for issue in issues:
        assignees = issue.get("assignees", [])
        labels = [l["name"] for l in issue.get("labels", [])]
        priority = next((l for l in labels if l.startswith("priority/")), "priority/medium")
        
        info = {
            "number": issue["number"],
            "title": issue["title"],
            "repo": issue["_repo"],
            "url": issue["html_url"],
            "priority": priority,
            "labels": labels,
            "created_at": issue.get("created_at", ""),
            "updated_at": issue.get("updated_at", ""),
        }
        
        if assignees:
            for assignee in assignees:
                login = assignee["login"]
                by_assignee.setdefault(login, []).append(info)
        else:
            unassigned.append(info)
    
    return by_assignee, unassigned

def summarize_by_repo(issues):
    """Group issues by repository"""
    by_repo = {}
    for issue in issues:
        repo = issue["_repo"]
        labels = [l["name"] for l in issue.get("labels", [])]
        priority = next((l for l in labels if l.startswith("priority/")), "priority/medium")
        info = {
            "number": issue["number"],
            "title": issue["title"],
            "url": issue["html_url"],
            "priority": priority,
            "assignees": [a["login"] for a in issue.get("assignees", [])],
        }
        by_repo.setdefault(repo, []).append(info)
    return by_repo

def summarize_by_priority(issues):
    """Group issues by priority"""
    by_priority = {}
    for issue in issues:
        labels = [l["name"] for l in issue.get("labels", [])]
        priority = next((l for l in labels if l.startswith("priority/")), "priority/medium")
        by_priority.setdefault(priority, []).append(issue)
    return by_priority

# ============================================================
# Format Reports
# ============================================================

def format_github_report(by_assignee, unassigned, by_repo, by_priority, date_str):
    """Format the digest as a GitHub comment"""
    lines = []
    lines.append(f"## 📊 Issue 日报 — {date_str}\n")
    
    # Overview
    total = sum(len(v) for v in by_assignee.values()) + len(unassigned)
    critical = len(by_priority.get("priority/critical", []))
    high = len(by_priority.get("priority/high", []))
    lines.append(f"**概览：** {total} 个未关闭 Issue | 🔴 {critical} Critical | 🟠 {high} High | ⚪ {len(unassigned)} 未分配\n")
    
    # By assignee
    lines.append("### 按责任人\n")
    if by_assignee:
        for assignee in sorted(by_assignee.keys()):
            items = by_assignee[assignee]
            critical_count = sum(1 for i in items if i["priority"] == "priority/critical")
            high_count = sum(1 for i in items if i["priority"] == "priority/high")
            lines.append(f"**@{assignee}** — {len(items)} 个 Issue")
            if critical_count:
                lines.append(f" 🔴{critical_count}")
            if high_count:
                lines.append(f" 🟠{high_count}")
            lines.append("\n")
            for item in sorted(items, key=lambda x: ["priority/critical","priority/high","priority/medium","priority/low"].index(x["priority"])):
                repo_short = item["repo"].split("/")[-1]
                priority_emoji = {"priority/critical": "🔴", "priority/high": "🟠", "priority/medium": "🟡", "priority/low": "🟢"}.get(item["priority"], "⚪")
                lines.append(f"- {priority_emoji} [{repo_short}#{item['number']}]({item['url']}) {item['title'][:60]}\n")
            lines.append("\n")
    
    if unassigned:
        lines.append(f"**未分配** — {len(unassigned)} 个 Issue\n")
        for item in sorted(unassigned, key=lambda x: ["priority/critical","priority/high","priority/medium","priority/low"].index(x["priority"]))[:10]:
            repo_short = item["repo"].split("/")[-1]
            priority_emoji = {"priority/critical": "🔴", "priority/high": "🟠", "priority/medium": "🟡", "priority/low": "🟢"}.get(item["priority"], "⚪")
            lines.append(f"- {priority_emoji} [{repo_short}#{item['number']}]({item['url']}) {item['title'][:60]}\n")
        if len(unassigned) > 10:
            lines.append(f"- ...还有 {len(unassigned) - 10} 个\n")
        lines.append("\n")
    
    # By repo summary
    lines.append("### 按仓库\n")
    for repo in sorted(by_repo.keys()):
        items = by_repo[repo]
        repo_short = repo.split("/")[-1]
        lines.append(f"- **{repo_short}**: {len(items)} 个\n")
    lines.append("\n")
    
    lines.append("<sub>issue-digest-bot v1.0</sub>")
    return "".join(lines)

def format_feishu_report(by_assignee, unassigned, by_priority, date_str):
    """Format the digest as a Feishu interactive card"""
    total = sum(len(v) for v in by_assignee.values()) + len(unassigned)
    critical = len(by_priority.get("priority/critical", []))
    high = len(by_priority.get("priority/high", []))
    
    # Build card elements
    elements = []
    
    # Header
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**📊 Issue 日报 — {date_str}**\n{total} 个未关闭 | 🔴 {critical} Critical | 🟠 {high} High | ⚪ {len(unassigned)} 未分配"
        }
    })
    elements.append({"tag": "hr"})
    
    # By assignee
    for assignee in sorted(by_assignee.keys()):
        items = by_assignee[assignee]
        critical_count = sum(1 for i in items if i["priority"] == "priority/critical")
        high_count = sum(1 for i in items if i["priority"] == "priority/high")
        
        header = f"**@{assignee}** — {len(items)} 个"
        if critical_count:
            header += f" 🔴{critical_count}"
        if high_count:
            header += f" 🟠{high_count}"
        
        item_lines = []
        for item in sorted(items, key=lambda x: ["priority/critical","priority/high","priority/medium","priority/low"].index(x["priority"]))[:5]:
            repo_short = item["repo"].split("/")[-1]
            priority_emoji = {"priority/critical": "🔴", "priority/high": "🟠", "priority/medium": "🟡", "priority/low": "🟢"}.get(item["priority"], "⚪")
            item_lines.append(f"{priority_emoji} [{repo_short}#{item['number']}]({item['url']}) {item['title'][:50]}")
        if len(items) > 5:
            item_lines.append(f"...还有 {len(items) - 5} 个")
        
        content = header + "\n" + "\n".join(item_lines)
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": content}
        })
    
    # Unassigned
    if unassigned:
        unassigned_lines = [f"**未分配** — {len(unassigned)} 个"]
        for item in unassigned[:3]:
            repo_short = item["repo"].split("/")[-1]
            unassigned_lines.append(f"⚪ [{repo_short}#{item['number']}]({item['url']}) {item['title'][:50]}")
        if len(unassigned) > 3:
            unassigned_lines.append(f"...还有 {len(unassigned) - 3} 个")
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "\n".join(unassigned_lines)}
        })
    
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "📊 Issue 日报"},
            "template": "blue"
        },
        "elements": elements
    }
    return card

# ============================================================
# Notification: GitHub
# ============================================================

def notify_github(org, report, token):
    """Create or update a tracking issue in the .github repo with @mentions"""
    repo = f"{org}/.github"
    title = "📊 Issue 日报 (自动更新)"
    
    # Search for existing digest issue
    result = github_api("GET", f"/repos/{repo}/issues?labels=issue-digest&state=open&per_page=1", token)
    
    if isinstance(result, list) and result:
        # Update existing issue
        issue_number = result[0]["number"]
        github_api("POST", f"/repos/{repo}/issues/{issue_number}/comments", token, {"body": report})
        print(f"Updated digest issue #{issue_number}")
        return issue_number
    else:
        # Create new issue
        result = github_api("POST", f"/repos/{repo}/issues", token, {
            "title": title,
            "body": report,
            "labels": ["issue-digest", "agent/triaged"]
        })
        if isinstance(result, dict) and "number" in result:
            print(f"Created digest issue #{result['number']}")
            return result["number"]
    return None

# ============================================================
# Notification: Feishu
# ============================================================

def notify_feishu(card, webhook_url):
    """Send interactive card to Feishu group via webhook"""
    if not webhook_url:
        print("FEISHU_WEBHOOK_URL not set, skipping Feishu notification")
        return False
    
    payload = {"msg_type": "interactive", "card": card}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(webhook_url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            print(f"Feishu response: {result}")
            return result.get("code", -1) == 0
    except Exception as e:
        print(f"Feishu notification failed: {e}", file=sys.stderr)
        return False

# ============================================================
# Main
# ============================================================

def main():
    org = os.environ.get("ORG_NAME", "huaweicloud-mate")
    
    # Authenticate
    app_id = os.environ.get("APP_ID", "")
    private_key = os.environ.get("APP_PRIVATE_KEY", "")
    installation_id = os.environ.get("APP_INSTALLATION_ID", "")
    
    if all([app_id, private_key, installation_id]):
        print(f"Authenticating as App #{app_id}...")
        token = get_installation_token(app_id, private_key, installation_id)
    else:
        token = os.environ.get("GITHUB_TOKEN", "")
    
    if not token:
        print("No token available")
        return
    
    # Collect issues
    print("Collecting open issues...")
    issues = collect_all_issues(org, token)
    
    if not issues:
        print("No open issues found")
        return
    
    # Summarize
    by_assignee, unassigned = summarize_by_assignee(issues)
    by_repo = summarize_by_repo(issues)
    by_priority = summarize_by_priority(issues)
    
    date_str = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    
    # GitHub notification
    print("\nGenerating GitHub report...")
    github_report = format_github_report(by_assignee, unassigned, by_repo, by_priority, date_str)
    issue_num = notify_github(org, github_report, token)
    
    # Feishu notification
    feishu_webhook = os.environ.get("FEISHU_WEBHOOK_URL", "")
    if feishu_webhook:
        print("\nGenerating Feishu report...")
        feishu_card = format_feishu_report(by_assignee, unassigned, by_priority, date_str)
        notify_feishu(feishu_card, feishu_webhook)
    
    # Print summary
    print(f"\n=== Digest Summary ===")
    print(f"Date: {date_str}")
    print(f"Total issues: {len(issues)}")
    print(f"Assignees: {len(by_assignee)}")
    print(f"Unassigned: {len(unassigned)}")
    print(f"GitHub issue: #{issue_num}")

if __name__ == "__main__":
    main()
