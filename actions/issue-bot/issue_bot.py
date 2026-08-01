#!/usr/bin/env python3
"""
Issue Management Bot for huaweicloud-mate organization
Powered by GitHub App authentication

Capabilities:
- Auto-triage new issues (classify type, priority, area)
- Send Feishu notification for repo creation requests
- Respond to slash commands in comments (/assign, /priority, /label, /close, /reopen)
- Greet first-time contributors
- Detect stale issues
- Route issues to appropriate labels
"""
import json
import os
import sys
import re
import time
import urllib.request
import urllib.error
import hashlib
import hmac
from datetime import datetime, timezone

# ============================================================
# GitHub App Authentication
# ============================================================

def jwt_encode(payload, private_key_pem):
    """Create a JWT for GitHub App authentication"""
    import base64 as b64
    
    def base64url(data):
        return b64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')
    
    header = {"alg": "RS256", "typ": "JWT"}
    header_b64 = base64url(json.dumps(header, separators=(',', ':')).encode())
    
    payload_b64 = base64url(json.dumps(payload, separators=(',', ':')).encode())
    
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(), password=None
    )
    
    message = f"{header_b64}.{payload_b64}".encode()
    signature = private_key.sign(
        message,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    signature_b64 = base64url(signature)
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def get_app_installation_token(app_id, private_key_pem, installation_id):
    """Get an installation access token for the GitHub App"""
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 600,
        "iss": int(app_id)
    }
    
    token_jwt = jwt_encode(payload, private_key_pem)
    
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {token_jwt}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "issue-bot"
    }
    req = urllib.request.Request(url, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("token")
    except urllib.error.HTTPError as e:
        print(f"Auth error {e.code}: {e.read().decode()[:300]}", file=sys.stderr)
        return None


def github_api(method, path, token, data=None):
    """Call GitHub API with App installation token"""
    url = f"https://api.github.com{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "issue-bot"
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 204:
                return {"status": "success"}
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:500]
        print(f"API error {e.code}: {error_body}", file=sys.stderr)
        return {"error": error_body, "status_code": e.code}
    except Exception as e:
        print(f"API error: {e}", file=sys.stderr)
        return {"error": str(e)}


# ============================================================
# Feishu Notification
# ============================================================

def get_feishu_token(app_id, app_secret):
    """Get Feishu tenant access token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    data = {"app_id": app_id, "app_secret": app_secret}
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result.get("tenant_access_token")
    except Exception as e:
        print(f"Feishu auth error: {e}", file=sys.stderr)
        return None


def send_feishu_dm(open_id, content, app_id, app_secret):
    """Send a direct message to a Feishu user"""
    token = get_feishu_token(app_id, app_secret)
    if not token:
        print("Failed to get Feishu token", file=sys.stderr)
        return False

    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    body = {
        "receive_id": open_id,
        "msg_type": "interactive",
        "content": json.dumps(content, ensure_ascii=False)
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if result.get("code") == 0:
                print("Feishu notification sent successfully")
                return True
            print(f"Feishu send error: {result}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Feishu send exception: {e}", file=sys.stderr)
        return False


def notify_repo_request(issue, repo_full):
    """Send Feishu notification for new repo creation request"""
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    admin_open_id = os.environ.get("FEISHU_ADMIN_OPEN_ID", "")

    if not all([app_id, app_secret, admin_open_id]):
        print("Feishu credentials not configured, skipping notification")
        return

    issue_number = issue.get("number", 0)
    title = issue.get("title", "")
    author = issue.get("user", {}).get("login", "")
    body = issue.get("body", "") or ""
    html_url = issue.get("html_url", "")

    fields = {"仓库名称": "", "仓库描述": "", "可见性": "", "主要编程语言": ""}
    sections = re.split(r'### ', body)
    for section in sections[1:]:
        lines = section.strip().split('\n')
        if not lines:
            continue
        name = lines[0].strip()
        value = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''
        if value == '_No response_':
            value = ''
        if name in fields:
            fields[name] = value

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "🏗️ 新建仓库申请"},
            "template": "blue"
        },
        "elements": [
            {
                "tag": "markdown",
                "content": f"**{author}** 提交了一个新的建仓申请，请审核。"
            },
            {
                "tag": "div",
                "fields": [
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**仓库名称**\n{fields.get('仓库名称', 'N/A')}"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**可见性**\n{fields.get('可见性', 'N/A')}"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**编程语言**\n{fields.get('主要编程语言', 'N/A')}"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**仓库描述**\n{fields.get('仓库描述', 'N/A')}"}},
                ]
            },
            {
                "tag": "hr"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "查看详情"},
                        "type": "primary",
                        "url": html_url
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "审批通过（打标签）"},
                        "type": "default",
                        "url": f"{html_url}#partial-new-comment-form"
                    }
                ]
            },
            {
                "tag": "note",
                "elements": [
                    {"tag": "plain_text", "content": f"issue-bot · #{issue_number} · {repo_full}"}
                ]
            }
        ]
    }

    send_feishu_dm(admin_open_id, card, app_id, app_secret)


# ============================================================
# Issue Triage Logic
# ============================================================

def classify_issue(title, body, labels):
    """Classify an issue based on title, body, and existing labels"""
    text = f"{title}\n{body or ''}".lower()
    result = {"type": None, "priority": None, "area": None, "greeting": None}
    
    if any(w in text for w in ['bug', 'error', 'crash', 'broken', 'fail', 'exception', 'traceback', 'fix']):
        result["type"] = "bug"
    elif any(w in text for w in ['feature', 'request', 'add', 'support', 'enhance', 'improve', 'new']):
        result["type"] = "enhancement"
    elif any(w in text for w in ['question', 'how to', 'how do', 'help', 'usage', 'example']):
        result["type"] = "question"
    elif any(w in text for w in ['doc', 'documentation', 'readme', 'guide', 'tutorial']):
        result["type"] = "documentation"
    elif any(w in text for w in ['security', 'vulnerability', 'cve', 'xss', 'injection']):
        result["type"] = "bug"
        result["priority"] = "priority/critical"
    
    if not result["priority"]:
        if any(w in text for w in ['critical', 'urgent', 'emergency', 'production down', 'data loss']):
            result["priority"] = "priority/critical"
        elif any(w in text for w in ['important', 'high', 'blocking', 'blocker']):
            result["priority"] = "priority/high"
        elif any(w in text for w in ['medium', 'normal']):
            result["priority"] = "priority/medium"
        elif any(w in text for w in ['low', 'minor', 'nice to have', 'cosmetic']):
            result["priority"] = "priority/low"
        elif result["type"] == "bug":
            result["priority"] = "priority/high"
        elif result["type"] == "enhancement":
            result["priority"] = "priority/medium"
        else:
            result["priority"] = "priority/medium"
    
    if any(w in text for w in ['sdk', 'api', 'client', 'library']):
        result["area"] = "area/sdk"
    elif any(w in text for w in ['ui', 'frontend', 'web', 'dashboard', 'interface']):
        result["area"] = "area/frontend"
    elif any(w in text for w in ['ci', 'cd', 'pipeline', 'workflow', 'deploy', 'build', 'test']):
        result["area"] = "area/ci-cd"
    elif any(w in text for w in ['doc', 'documentation', 'readme', 'guide']):
        result["area"] = "area/docs"
    elif any(w in text for w in ['security', 'auth', 'permission', 'token']):
        result["area"] = "area/security"
    
    return result


def is_first_time_contributor(author, repo, token):
    """Check if this is the author's first issue in the repo"""
    result = github_api("GET", f"/repos/{repo}/issues?creator={author}&per_page=2&state=all", token)
    if isinstance(result, list):
        return len(result) <= 1
    return False


def is_repo_request(body):
    """Check if the issue is a repo creation request"""
    return "### 仓库名称" in (body or "")


# ============================================================
# Slash Command Handler
# ============================================================

def handle_slash_command(command, args, issue_number, repo, token, commenter):
    """Handle slash commands in issue comments"""
    responses = {
        "assign": handle_assign,
        "priority": handle_priority,
        "label": handle_label,
        "close": handle_close,
        "reopen": handle_reopen,
        "help": handle_help,
    }
    
    handler = responses.get(command)
    if handler:
        return handler(args, issue_number, repo, token, commenter)
    return f"Unknown command: `/{command}`. Type `/help` for available commands."


def handle_assign(args, issue_number, repo, token, commenter):
    assignee = args.strip().lstrip('@') if args.strip() else commenter
    github_api("POST", f"/repos/{repo}/issues/{issue_number}/assignees", token, {"assignees": [assignee]})
    return f"Assigned @{assignee} to this issue."


def handle_priority(args, issue_number, repo, token, commenter):
    priority_map = {
        "critical": "priority/critical",
        "high": "priority/high",
        "medium": "priority/medium",
        "low": "priority/low",
    }
    level = args.strip().lower()
    label = priority_map.get(level)
    if not label:
        return f"Invalid priority: `{level}`. Use: critical, high, medium, low"
    
    issue = github_api("GET", f"/repos/{repo}/issues/{issue_number}", token)
    if isinstance(issue, dict) and "labels" in issue:
        for lbl in issue["labels"]:
            if lbl["name"].startswith("priority/"):
                github_api("DELETE", f"/repos/{repo}/issues/{issue_number}/labels/{lbl['name']}", token)
    
    github_api("POST", f"/repos/{repo}/issues/{issue_number}/labels", token, {"labels": [label]})
    return f"Priority set to `{label}`."


def handle_label(args, issue_number, repo, token, commenter):
    labels = [l.strip() for l in args.split(',') if l.strip()]
    if not labels:
        return "Usage: `/label label1, label2`"
    github_api("POST", f"/repos/{repo}/issues/{issue_number}/labels", token, {"labels": labels})
    return f"Added label(s): {', '.join(f'`{l}`' for l in labels)}."


def handle_close(args, issue_number, repo, token, commenter):
    github_api("PATCH", f"/repos/{repo}/issues/{issue_number}", token, {"state": "closed", "state_reason": "completed"})
    return "Issue closed."


def handle_reopen(args, issue_number, repo, token, commenter):
    github_api("PATCH", f"/repos/{repo}/issues/{issue_number}", token, {"state": "open"})
    return "Issue reopened."


def handle_help(args, issue_number, repo, token, commenter):
    return """**Available commands:**
- `/assign @user` — Assign issue to user (defaults to yourself)
- `/priority <level>` — Set priority (critical/high/medium/low)
- `/label <labels>` — Add comma-separated labels
- `/close` — Close the issue
- `/reopen` — Reopen the issue
- `/help` — Show this help

<sub>issue-bot v1.0</sub>"""


# ============================================================
# Main Handler
# ============================================================

def handle_issue_opened(event, token):
    """Handle issues.opened event"""
    issue = event["issue"]
    repo = event["repository"]["full_name"]
    issue_number = issue["number"]
    title = issue.get("title", "")
    body = issue.get("body", "") or ""
    author = issue.get("user", {}).get("login", "")
    existing_labels = [l["name"] for l in issue.get("labels", [])]
    
    if "agent/triaged" in existing_labels:
        print(f"Issue #{issue_number} already triaged, skipping")
        return

    # Send Feishu notification for repo creation requests
    if is_repo_request(body):
        print(f"Repo creation request detected, sending Feishu notification")
        notify_repo_request(issue, repo)
    
    classification = classify_issue(title, body, existing_labels)
    print(f"Classification: {json.dumps(classification, ensure_ascii=False)}")
    
    labels_to_add = ["agent/triaged"]
    if classification["type"]:
        labels_to_add.append(classification["type"])
    if classification["priority"]:
        labels_to_add.append(classification["priority"])
    if classification["area"]:
        labels_to_add.append(classification["area"])
    
    github_api("POST", f"/repos/{repo}/issues/{issue_number}/labels", token, {"labels": labels_to_add})
    print(f"Added labels: {labels_to_add}")
    
    parts = ["### 🤖 Issue Bot\n"]
    parts.append(f"**分类结果：**\n")
    if classification["type"]:
        parts.append(f"- 类型: `{classification['type']}`\n")
    if classification["priority"]:
        parts.append(f"- 优先级: `{classification['priority']}`\n")
    if classification["area"]:
        parts.append(f"- 领域: `{classification['area']}`\n")
    parts.append(f"\n可用 `/help` 查看管理命令。\n")
    parts.append(f"\n<sub>issue-bot v1.0 · triage</sub>")
    
    comment = "".join(parts)
    github_api("POST", f"/repos/{repo}/issues/{issue_number}/comments", token, {"body": comment})
    
    if is_first_time_contributor(author, repo, token):
        greeting = f"👋 Welcome @{author}! Thanks for your first issue in this repo. We'll triage it shortly."
        github_api("POST", f"/repos/{repo}/issues/{issue_number}/comments", token, {"body": greeting})
        print(f"Greeted first-time contributor: @{author}")


def handle_issue_comment(event, token):
    """Handle issue_comment.created event - slash commands"""
    comment = event["comment"]
    issue = event["issue"]
    repo = event["repository"]["full_name"]
    issue_number = issue["number"]
    body = comment.get("body", "")
    commenter = comment.get("user", {}).get("login", "")
    
    if not body.startswith('/'):
        return
    
    parts = body.strip().split(None, 1)
    command = parts[0].lstrip('/')
    args = parts[1] if len(parts) > 1 else ""
    
    if comment.get("performed_via_github_app"):
        return
    
    print(f"Slash command: /{command} {args} by @{commenter}")
    
    response = handle_slash_command(command, args, issue_number, repo, token, commenter)
    if response:
        github_api("POST", f"/repos/{repo}/issues/{issue_number}/comments", token, {"body": response})


def main():
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path or not os.path.exists(event_path):
        print("No event payload found")
        return
    
    with open(event_path) as f:
        event = json.load(f)
    
    event_action = os.environ.get("GITHUB_EVENT_NAME", "")
    print(f"Event: {event_action}")
    
    app_id = os.environ.get("APP_ID", "")
    private_key = os.environ.get("APP_PRIVATE_KEY", "")
    installation_id = os.environ.get("APP_INSTALLATION_ID", "")
    
    if not all([app_id, private_key, installation_id]):
        print("Missing App credentials, falling back to GITHUB_TOKEN")
        token = os.environ.get("GITHUB_TOKEN", "")
    else:
        print(f"Authenticating as App #{app_id}...")
        token = get_app_installation_token(app_id, private_key, installation_id)
        if not token:
            print("App auth failed, falling back to GITHUB_TOKEN")
            token = os.environ.get("GITHUB_TOKEN", "")
    
    if not token:
        print("No token available, exiting")
        return
    
    if event_action == "issues":
        action = event.get("action", "")
        if action == "opened":
            handle_issue_opened(event, token)
        elif action == "edited":
            handle_issue_opened(event, token)
        else:
            print(f"Unhandled issues action: {action}")
    
    elif event_action == "issue_comment":
        action = event.get("action", "")
        if action == "created":
            handle_issue_comment(event, token)
        else:
            print(f"Unhandled issue_comment action: {action}")
    
    else:
        print(f"Unhandled event: {event_action}")


if __name__ == "__main__":
    main()
