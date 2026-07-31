#!/usr/bin/env python3
"""
Triage Agent - AI-powered Issue triage for GitHub repositories
Analyzes issues using LLM and applies labels + comments
"""
import json
import os
import sys
import urllib.request
import urllib.error
import re

def github_api(method, path, data=None, token=None):
    """Call GitHub REST API"""
    url = f"https://api.github.com{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "triage-agent"
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 204:
                return None
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"GitHub API error {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
        return None

def call_llm(prompt, api_key, model=None, endpoint=None):
    """Call LLM API (OpenAI-compatible format)"""
    if not model:
        model = os.environ.get("LLM_MODEL", "glm-4-flash")
    if not endpoint:
        endpoint = os.environ.get("LLM_ENDPOINT", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1024
    }).encode()
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:500]
        print(f"LLM API HTTP {e.code}: {error_body}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"LLM API error: {e}", file=sys.stderr)
        return None

def get_existing_labels(repo, token):
    """Get all existing labels in the repo"""
    labels = github_api("GET", f"/repos/{repo}/labels?per_page=100", token=token)
    if labels:
        return {l["name"]: l for l in labels}
    return {}

def ensure_label(repo, token, name, color, description, existing):
    """Create label if it doesn't exist"""
    if name in existing:
        return True
    result = github_api("POST", f"/repos/{repo}/labels", {
        "name": name,
        "color": color,
        "description": description
    }, token=token)
    return result is not None

def rule_based_triage(title, body, existing_labels):
    """Fallback rule-based triage when LLM is unavailable"""
    title_lower = title.lower()
    body_lower = body.lower()
    combined = title_lower + " " + body_lower

    if any(w in combined for w in ["bug", "error", "crash", "fail", "broken", "exception", "traceback"]):
        issue_type = "bug"
    elif any(w in combined for w in ["feature", "request", "add", "support", "enhance", "improve"]):
        issue_type = "feature"
    elif any(w in combined for w in ["how to", "question", "?", "help", "how can"]):
        issue_type = "question"
    elif any(w in combined for w in ["doc", "readme", "guide", "tutorial"]):
        issue_type = "documentation"
    else:
        issue_type = "question"

    if any(w in combined for w in ["critical", "urgent", "blocker", "production", "down"]):
        priority = "critical"
    elif any(w in combined for w in ["important", "high", "asap"]):
        priority = "high"
    else:
        priority = "medium"

    area = None
    if any(w in combined for w in ["sdk", "api", "client"]):
        area = "sdk"
    elif any(w in combined for w in ["eval", "benchmark", "score"]):
        area = "evaluation"
    elif any(w in combined for w in ["security", "vulnerability", "cve"]):
        area = "security"
    elif any(w in combined for w in ["ci", "workflow", "action", "deploy"]):
        area = "ci"

    return {
        "type": issue_type,
        "priority": priority,
        "area": area,
        "summary": title[:100],
        "confidence": 0.6,
        "needs_triage": True
    }

def parse_llm_response(response):
    """Parse LLM JSON response, handling various formats"""
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    json_match = re.search(r'\{[^{}]*"type"[^{}]*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None

def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    llm_api_key = os.environ.get("LLM_API_KEY", "")
    # FIX: handle empty string for ISSUE_NUMBER
    issue_number_str = os.environ.get("ISSUE_NUMBER", "0").strip()
    issue_number = int(issue_number_str) if issue_number_str else 0
    confidence_threshold = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.7"))
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    if not issue_number:
        event_path = os.environ.get("GITHUB_EVENT_PATH", "")
        if event_path and os.path.exists(event_path):
            with open(event_path) as f:
                event = json.load(f)
            issue_number = event.get("issue", {}).get("number", 0)

    if not issue_number:
        print("No issue number found, exiting")
        return

    issue = github_api("GET", f"/repos/{repo}/issues/{issue_number}", token=token)
    if not issue:
        print(f"Could not fetch issue #{issue_number}")
        return

    title = issue.get("title", "")
    body = issue.get("body", "") or ""
    author = issue.get("user", {}).get("login", "")
    existing_labels = [l["name"] for l in issue.get("labels", [])]

    if "agent/triaged" in existing_labels:
        print(f"Issue #{issue_number} already triaged, skipping")
        return

    print(f"Triaging issue #{issue_number}: {title[:80]}")

    repo_labels = get_existing_labels(repo, token)

    TYPE_LABELS = {
        "bug": ("bug", "d73a4a"),
        "feature": ("enhancement", "a2eeef"),
        "question": ("question", "d876e3"),
        "documentation": ("documentation", "0075ca"),
        "duplicate": ("duplicate", "cfd3d7"),
    }
    PRIORITY_LABELS = {
        "critical": ("priority/critical", "b60205"),
        "high": ("priority/high", "d93f0b"),
        "medium": ("priority/medium", "fbca04"),
        "low": ("priority/low", "0e8a16"),
    }
    AREA_LABELS = {
        "sdk": ("area/sdk", "1d76db"),
        "evaluation": ("area/evaluation", "1d76db"),
        "community": ("area/community", "5319e7"),
        "security": ("area/security", "b0063c"),
        "infrastructure": ("area/infrastructure", "2d7d46"),
        "ci": ("area/infrastructure", "2d7d46"),
    }

    available_types = ", ".join(TYPE_LABELS.keys())
    available_priorities = ", ".join(PRIORITY_LABELS.keys())
    available_areas = ", ".join(AREA_LABELS.keys())

    prompt = f"""You are an expert issue triage agent for a GitHub open-source repository.
Analyze the following issue and classify it.

IMPORTANT: Respond ONLY with valid JSON, no markdown, no explanation outside JSON.

Issue Title: {title}
Issue Body (first 2000 chars): {body[:2000]}
Issue Author: {author}
Existing Labels: {existing_labels}

Classify this issue into:
1. type: one of [{available_types}]
2. priority: one of [{available_priorities}]
3. area: one of [{available_areas}] or null if unclear
4. summary: one-line summary of the issue (max 100 chars)
5. confidence: your confidence level from 0.0 to 1.0
6. needs_triage: true if this needs human review, false if classification is clear

Respond as JSON:
{{"type": "...", "priority": "...", "area": "...", "summary": "...", "confidence": 0.0, "needs_triage": true/false}}"""

    if not llm_api_key:
        print("No LLM API key, using rule-based fallback")
        result = rule_based_triage(title, body, existing_labels)
    else:
        llm_response = call_llm(prompt, llm_api_key)
        if not llm_response:
            print("LLM call failed, using rule-based fallback")
            result = rule_based_triage(title, body, existing_labels)
        else:
            result = parse_llm_response(llm_response)

    if not result:
        print("Could not parse triage result, skipping")
        return

    print(f"Triage result: {json.dumps(result, ensure_ascii=False)}")

    confidence = result.get("confidence", 0.5)
    labels_to_add = []
    actions = []

    issue_type = result.get("type", "")
    if issue_type in TYPE_LABELS:
        label_name, color = TYPE_LABELS[issue_type]
        if label_name not in existing_labels:
            labels_to_add.append(label_name)
            ensure_label(repo, token, label_name, color, "", repo_labels)
            actions.append(f"type: {label_name}")

    priority = result.get("priority", "")
    if priority in PRIORITY_LABELS and confidence >= confidence_threshold:
        label_name, color = PRIORITY_LABELS[priority]
        if label_name not in existing_labels:
            labels_to_add.append(label_name)
            ensure_label(repo, token, label_name, color, "", repo_labels)
            actions.append(f"priority: {label_name}")

    area = result.get("area")
    if area and area in AREA_LABELS and confidence >= confidence_threshold:
        label_name, color = AREA_LABELS[area]
        if label_name not in existing_labels:
            labels_to_add.append(label_name)
            ensure_label(repo, token, label_name, color, "", repo_labels)
            actions.append(f"area: {label_name}")

    labels_to_add.append("agent/triaged")
    ensure_label(repo, token, "agent/triaged", "bfd4f2", "Automatically triaged by AI agent", repo_labels)

    if labels_to_add and not dry_run:
        github_api("POST", f"/repos/{repo}/issues/{issue_number}/labels",
                   {"labels": labels_to_add}, token=token)
        print(f"Applied labels: {labels_to_add}")

    summary = result.get("summary", "")
    needs_triage = result.get("needs_triage", True)
    confidence_str = f"{confidence:.0%}"

    comment_parts = [f"### 🤖 Triage Agent\n"]
    if actions:
        comment_parts.append(f"**分类结果** (置信度: {confidence_str}):\n")
        for action in actions:
            comment_parts.append(f"- {action}\n")
    if summary:
        comment_parts.append(f"\n**摘要**: {summary}\n")
    if needs_triage or confidence < confidence_threshold:
        comment_parts.append(f"\n> ⚠️ 需要人工复核 — 置信度低于阈值 ({confidence_threshold:.0%})\n")
    comment_parts.append(f"\n<sub>triage-agent v1.0 | model: {os.environ.get('LLM_MODEL', 'glm-4-flash')}</sub>")

    comment_body = "".join(comment_parts)

    if not dry_run:
        github_api("POST", f"/repos/{repo}/issues/{issue_number}/comments",
                   {"body": comment_body}, token=token)
        print(f"Posted triage comment")
    else:
        print(f"[DRY RUN] Would add labels: {labels_to_add}")
        print(f"[DRY RUN] Would comment: {comment_body[:200]}")

if __name__ == "__main__":
    main()
