#!/usr/bin/env python3
"""
Issue Management Bot for huaweicloud-mate organization
Powerful by GitHub App authentication

Capabilities:
- Auto-triage new issues (classify type, priority, area)
- Send Feishu notification for repo creation requests
- Respond to slash commands in comments (/assign, /priority, /label, /close, /reopen)
- Greet first-time contributors
"""
import json
import os
import sys
import re
import time
import glob
import urllib.request
import urllib.error
from urllib.parse import quote
import hashlib
import hmac
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None

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

def get_app_installation_token(app_id, private_key_pem, installation_id):
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 600, "iss": int(app_id)}
    token_jwt = jwt_encode(payload, private_key_pem)
    
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {"Authorization": f"Bearer {token_jwt}", "Accept": "application/vnd.github+json", "User-Agent": "issue-bot"}
    req = urllib.request.Request(url, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("token")
    except urllib.error.HTTPError as e:
        print(f"Auth error {e.code}: {e.read().decode()[:300]}", file=sys.stderr)
        return None

def github_api(method, path, token, data=None):
    url = f"https://api.github.com{path}"
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "User-Agent": "issue-bot"}
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

def get_feishu_token(app_id, app_secret):
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
    token = get_feishu_token(app_id, app_secret)
    if not token:
        print("Failed to get Feishu token", file=sys.stderr)
        return False
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    body = {"receive_id": open_id, "msg_type": "interactive", "content": json.dumps(content, ensure_ascii=False)}
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

    approve_url = f"https://github.com/huaweicloud-mate/repository-requests/actions/workflows/approve-repo.yml"
    card = {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": "🏗️ 新建仓库申请"}, "template": "blue"},
        "elements": [
            {"tag": "markdown", "content": f"**{author}** 提交了建仓申请"},
            {
                "tag": "div",
                "fields": [
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**仓库名称**\n{fields.get('仓库名称', 'N/A')}"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**可见性**\n{fields.get('可见性', 'N/A')}"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**语言**\n{fields.get('主要编程语言', 'N/A')}"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**描述**\n{fields.get('仓库描述', 'N/A')}"}},
                ]
            },
            {"tag": "hr"},
            {"tag": "markdown", "content": f"📋 申请理由：{fields.get('申请理由', '未填写')}"},
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {"tag": "button", "text": {"tag": "plain_text", "content": "查看 Issue"}, "type": "default", "url": html_url},
                    {"tag": "button", "text": {"tag": "plain_text", "content": "✅ 审批通过"}, "type": "primary", "url": f"{approve_url}?issue_number={issue_number}"},
                ]
            },
            {"tag": "note", "elements": [{"tag": "plain_text", "content": f"点击审批通过 → 跳转 GitHub → 填入 Issue 号 #{issue_number} → Run workflow"}]}
        ]
    }
    send_feishu_dm(admin_open_id, card, app_id, app_secret)

def find_triage_config():
    """Locate triage-rules.yml, preferring TRIAGE_CONFIG env var."""
    candidates = []
    env_path = os.environ.get("TRIAGE_CONFIG", "")
    if env_path:
        candidates.append(env_path)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates += [
        os.path.join(script_dir, "..", "..", "configs", "triage-rules.yml"),
        os.path.join(script_dir, "..", "..", ".github", "configs", "triage-rules.yml"),
        os.path.join(os.getcwd(), "configs", "triage-rules.yml"),
        os.path.join(os.getcwd(), ".github", "configs", "triage-rules.yml"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def load_triage_config():
    """Load triage rules from triage-rules.yml. Returns dict or empty dict."""
    if yaml is None:
        print("PyYAML not installed, using built-in rules", file=sys.stderr)
        return {}
    config_path = find_triage_config()
    if not config_path:
        print("triage-rules.yml not found, using built-in rules", file=sys.stderr)
        return {}
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        print(f"Loaded triage config: {config_path}")
        return cfg
    except Exception as e:
        print(f"Failed to load triage config: {e}", file=sys.stderr)
        return {}


def match_rules(text, rules):
    """Return label for the first rule whose any keyword is found in text."""
    for rule in rules or []:
        keywords = rule.get("keywords") or []
        label = rule.get("label")
        if not label:
            continue
        if any(kw in text for kw in keywords):
            return label
    return None


def classify_issue(title, body, labels, config=None):
    text = f"{title}\n{body or ''}".lower()
    result = {"type": None, "priority": None, "area": None}
    cfg = config or {}

    label_rules = cfg.get("label_rules") or []
    priority_rules = cfg.get("priority_rules") or []
    area_rules = cfg.get("area_rules") or []

    if label_rules:
        type_label = match_rules(text, label_rules)
        if type_label:
            result["type"] = type_label
    if not result["type"]:
        if any(w in text for w in ['bug', 'error', 'crash', 'broken', 'fail', 'exception', 'traceback', 'fix']):
            result["type"] = "type/bug"
        elif any(w in text for w in ['feature', 'request', 'add', 'support', 'enhance', 'improve', 'new']):
            result["type"] = "type/feature"
        elif any(w in text for w in ['question', 'how to', 'how do', 'help', 'usage', 'example']):
            result["type"] = "type/question"
        elif any(w in text for w in ['doc', 'documentation', 'readme', 'guide', 'tutorial']):
            result["type"] = "type/documentation"
        elif any(w in text for w in ['security', 'vulnerability', 'cve', 'xss', 'injection']):
            result["type"] = "type/bug"
            result["priority"] = "priority/critical"

    if priority_rules:
        priority_label = match_rules(text, priority_rules)
        if priority_label:
            result["priority"] = priority_label

    if not result["priority"]:
        if any(w in text for w in ['critical', 'urgent', 'emergency', 'production down', 'data loss']):
            result["priority"] = "priority/critical"
        elif any(w in text for w in ['important', 'high', 'blocking', 'blocker']):
            result["priority"] = "priority/high"
        elif any(w in text for w in ['medium', 'normal']):
            result["priority"] = "priority/medium"
        elif any(w in text for w in ['low', 'minor', 'nice to have', 'cosmetic']):
            result["priority"] = "priority/low"
        elif result["type"] == "type/bug":
            result["priority"] = "priority/high"
        elif result["type"] == "type/feature":
            result["priority"] = "priority/medium"
        else:
            result["priority"] = "priority/medium"

    if area_rules:
        area_label = match_rules(text, area_rules)
        if area_label:
            result["area"] = area_label

    if not result["area"]:
        if any(w in text for w in ['sdk', 'api', 'client', 'library']):
            result["area"] = "area/sdk"
        elif any(w in text for w in ['ui', 'frontend', 'web', 'dashboard', 'interface']):
            result["area"] = "area/web"
        elif any(w in text for w in ['ci', 'cd', 'pipeline', 'workflow', 'deploy', 'build', 'test']):
            result["area"] = "area/ci-cd"
        elif any(w in text for w in ['doc', 'documentation', 'readme', 'guide']):
            result["area"] = "area/documentation"
        elif any(w in text for w in ['security', 'auth', 'permission', 'token']):
            result["area"] = "area/security"
    return result

def is_first_time_contributor(author, repo, token):
    result = github_api("GET", f"/repos/{repo}/issues?creator={author}&per_page=2&state=all", token)
    if isinstance(result, list):
        return len(result) <= 1
    return False

def is_repo_request(body):
    return "### 仓库名称" in (body or "")

def handle_slash_command(command, args, issue_number, repo, token, commenter):
    responses = {
        "assign": handle_assign, "priority": handle_priority,
        "label": handle_label, "unlabel": handle_unlabel,
        "retriage": handle_retriage, "close": handle_close,
        "reopen": handle_reopen, "help": handle_help,
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
    priority_map = {"critical": "priority/critical", "high": "priority/high", "medium": "priority/medium", "low": "priority/low"}
    level = args.strip().lower()
    label = priority_map.get(level)
    if not label:
        return f"Invalid priority: `{level}`. Use: critical, high, medium, low"
    issue = github_api("GET", f"/repos/{repo}/issues/{issue_number}", token)
    if isinstance(issue, dict) and "labels" in issue:
        for lbl in issue["labels"]:
            if lbl["name"].startswith("priority/"):
                encoded = quote(lbl["name"], safe="")
                github_api("DELETE", f"/repos/{repo}/issues/{issue_number}/labels/{encoded}", token)
    github_api("POST", f"/repos/{repo}/issues/{issue_number}/labels", token, {"labels": [label]})
    return f"Priority set to `{label}`."

def get_repo_labels(repo, token):
    """Fetch all labels that already exist in the repo (paginated)."""
    labels = set()
    page = 1
    while page <= 10:
        result = github_api("GET", f"/repos/{repo}/labels?per_page=100&page={page}", token)
        if not isinstance(result, list):
            break
        if not result:
            break
        labels.update(l["name"] for l in result if isinstance(l, dict) and "name" in l)
        if len(result) < 100:
            break
        page += 1
    return labels

def handle_label(args, issue_number, repo, token, commenter):
    labels = [l.strip() for l in args.split(',') if l.strip()]
    if not labels:
        return "Usage: `/label label1, label2`"
    existing = get_repo_labels(repo, token)
    unknown = [l for l in labels if l not in existing]
    known = [l for l in labels if l in existing]
    if unknown:
        hint = f"仅允许仓库中已存在的标签（新增标签不会自动创建）。不存在的标签: {', '.join(f'`{l}`' for l in unknown)}"
        if known:
            github_api("POST", f"/repos/{repo}/issues/{issue_number}/labels", token, {"labels": known})
            return f"Added label(s): {', '.join(f'`{l}`' for l in known)}. {hint}"
        return hint
    github_api("POST", f"/repos/{repo}/issues/{issue_number}/labels", token, {"labels": labels})
    return f"Added label(s): {', '.join(f'`{l}`' for l in labels)}."

def handle_unlabel(args, issue_number, repo, token, commenter):
    labels = [l.strip() for l in args.split(',') if l.strip()]
    if not labels:
        return "Usage: `/unlabel label1, label2`"
    removed, missing = [], []
    for label in labels:
        encoded = quote(label, safe="")
        result = github_api("DELETE", f"/repos/{repo}/issues/{issue_number}/labels/{encoded}", token)
        if isinstance(result, dict) and result.get("status_code") == 404:
            missing.append(label)
        else:
            removed.append(label)
    parts = []
    if removed:
        parts.append(f"Removed label(s): {', '.join(f'`{l}`' for l in removed)}.")
    if missing:
        parts.append(f"Not present: {', '.join(f'`{l}`' for l in missing)}.")
    return " ".join(parts) or "No labels specified."

def handle_retriage(args, issue_number, repo, token, commenter):
    """Force re-triage: remove agent/triaged then re-run classification."""
    github_api("DELETE", f"/repos/{repo}/issues/{issue_number}/labels/agent%2Ftriaged", token)
    issue = github_api("GET", f"/repos/{repo}/issues/{issue_number}", token)
    if not isinstance(issue, dict) or "labels" not in issue:
        return "Could not fetch issue for re-triage."
    handle_issue_opened({"issue": issue, "repository": {"full_name": repo}}, token, force=True)
    return "Re-triage complete. Review the classification comment above."

def handle_close(args, issue_number, repo, token, commenter):
    github_api("PATCH", f"/repos/{repo}/issues/{issue_number}", token, {"state": "closed", "state_reason": "completed"})
    issue = github_api("GET", f"/repos/{repo}/issues/{issue_number}", token)
    if isinstance(issue, dict) and "labels" in issue:
        labels = [l["name"] for l in issue["labels"]]
        new_labels = [l for l in labels if not l.startswith("status/")] + ["status/completed"]
        github_api("PUT", f"/repos/{repo}/issues/{issue_number}/labels", token, {"labels": new_labels})
    return "Issue closed."

def handle_reopen(args, issue_number, repo, token, commenter):
    github_api("PATCH", f"/repos/{repo}/issues/{issue_number}", token, {"state": "open"})
    return "Issue reopened."

def handle_help(args, issue_number, repo, token, commenter):
    return """**Available commands:**
- `/assign @user` — Assign issue
- `/priority <level>` — Set priority (critical/high/medium/low)
- `/label <labels>` — Add labels
- `/unlabel <labels>` — Remove labels
- `/retriage` — Re-run automatic classification
- `/close` / `/reopen` — Close or reopen issue
- `/help` — Show this help
<sub>issue-bot v1.0</sub>"""

def handle_issue_opened(event, token, force=False):
    issue = event["issue"]
    repo = event["repository"]["full_name"]
    issue_number = issue["number"]
    title = issue.get("title", "")
    body = issue.get("body", "") or ""
    author = issue.get("user", {}).get("login", "")
    existing_labels = [l["name"] for l in issue.get("labels", [])]
    
    if "agent/triaged" in existing_labels and not force:
        print(f"Issue #{issue_number} already triaged, skipping")
        return

    config = load_triage_config()
    classification = classify_issue(title, body, existing_labels, config)
    print(f"Classification: {json.dumps(classification, ensure_ascii=False)}")

    # 分类标签替换而非追加：移除旧 type/priority/area，保留其他（status/agent/社区）
    labels_to_add = ["agent/triaged"]
    if classification["type"]:
        labels_to_add.append(classification["type"])
    if classification["priority"]:
        labels_to_add.append(classification["priority"])
    if classification["area"]:
        labels_to_add.append(classification["area"])
    keep = [l for l in existing_labels if not (l.startswith("type/") or l.startswith("priority/") or l.startswith("area/"))]
    final_labels = keep + labels_to_add
    github_api("PUT", f"/repos/{repo}/issues/{issue_number}/labels", token, {"labels": final_labels})
    
    parts = ["### 🤖 Issue Bot\n", "**分类结果：**\n"]
    if classification["type"]:
        parts.append(f"- 类型: `{classification['type']}`\n")
    if classification["priority"]:
        parts.append(f"- 优先级: `{classification['priority']}`\n")
    if classification["area"]:
        parts.append(f"- 领域: `{classification['area']}`\n")
    parts.append("\n> 若分类有误，可评论 `/retriage` 重新分类，或使用 `/unlabel <标签>` 手动移除错误标签。\n")
    parts.append("\n可用 `/help` 查看管理命令。\n")
    parts.append("\n<sub>issue-bot v1.0 · triage</sub>")
    
    github_api("POST", f"/repos/{repo}/issues/{issue_number}/comments", token, {"body": "".join(parts)})
    
    if is_first_time_contributor(author, repo, token):
        github_api("POST", f"/repos/{repo}/issues/{issue_number}/comments", token,
                   {"body": f"👋 Welcome @{author}! Thanks for your first issue."})

def handle_issue_comment(event, token):
    comment = event["comment"]
    issue = event["issue"]
    repo = event["repository"]["full_name"]
    issue_number = issue["number"]
    body = comment.get("body", "")
    commenter = comment.get("user", {}).get("login", "")
    
    if not body.startswith('/') or comment.get("performed_via_github_app"):
        return
    parts = body.strip().split(None, 1)
    command = parts[0].lstrip('/')
    args = parts[1] if len(parts) > 1 else ""
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
        token = os.environ.get("GITHUB_TOKEN", "")
    else:
        token = get_app_installation_token(app_id, private_key, installation_id)
        if not token:
            token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("No token available, exiting")
        return
    
    if event_action == "issues":
        action = event.get("action", "")
        if action in ("opened", "edited"):
            handle_issue_opened(event, token)
    elif event_action == "issue_comment":
        if event.get("action") == "created":
            handle_issue_comment(event, token)

if __name__ == "__main__":
    main()
