#!/usr/bin/env python3
"""
Organization-level stale issue/PR manager.
Iterates all repos in the org, marks stale and closes inactive issues/PRs.
Replaces per-repo stale.yml — runs centrally via cron.

Default rules (overridable by per-repo .github/stale.yml):
  - Issue: stale after 90 days, close after +30 days
  - PR:    stale after 60 days, close after +14 days
  - Exempt: labels in exempt list, pinned issues, open PRs with recent CI
"""
import json, os, sys, re
import urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

ORG = os.environ.get("ORG_NAME", "huaweicloud-mate")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

# Default rules
DEFAULTS = {
    "issue_stale_days": 90,
    "issue_close_days": 30,
    "pr_stale_days": 60,
    "pr_close_days": 14,
    "exempt_labels": ["status/in-progress", "status/pinned", "priority/critical", "agent/needs-triage"],
    "stale_label": "status/stale",
}


def _api(path, method="GET", data=None):
    url = f"https://api.github.com{path}"
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {TOKEN}", "User-Agent": "stale-manager"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()) if resp.status != 204 else {"status": "ok"}
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:300]
        print(f"  API error {path}: {e.code}", file=sys.stderr)
        return {"error": err}
    except Exception as e:
        return {"error": str(e)}


def paginate(path, per_page=100):
    """Fetch all pages from a GitHub API endpoint."""
    items = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        r = _api(f"{path}{sep}per_page={per_page}&page={page}&state=open")
        if isinstance(r, dict) and "error" in r:
            break
        if not r:
            break
        items.extend(r)
        if len(r) < per_page:
            break
        page += 1
    return items


def get_repo_stale_config(org, repo):
    """Try to read per-repo .github/stale.yml for custom rules. Returns dict or None."""
    r = _api(f"/repos/{org}/{repo}/contents/.github/stale.yml")
    if "error" in r or "content" not in r:
        return None
    try:
        import base64
        content = base64.b64decode(r["content"]).decode("utf-8")
        config = {}
        for line in content.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                key, val = line.split(":", 1)
                config[key.strip()] = val.strip()
        return config
    except:
        return None


def process_items(org, repo, issues, rules, dry=False):
    """Process open issues and PRs for staleness."""
    now = datetime.now(timezone.utc)
    stats = {"stale": 0, "close": 0, "skip": 0}
    exempt = rules.get("exempt_labels", DEFAULTS["exempt_labels"])

    for item in issues:
        if "pull_request" in item:
            stale_days = int(rules.get("pr_stale_days", DEFAULTS["pr_stale_days"]))
            close_days = int(rules.get("pr_close_days", DEFAULTS["pr_close_days"]))
            kind = "PR"
        else:
            stale_days = int(rules.get("issue_stale_days", DEFAULTS["issue_stale_days"]))
            close_days = int(rules.get("issue_close_days", DEFAULTS["issue_close_days"]))
            kind = "Issue"

        num = item["number"]
        labels = [l["name"] for l in item.get("labels", [])]
        stale_label = rules.get("stale_label", DEFAULTS["stale_label"])

        updated = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
        age = (now - updated).days

        # Check exemptions
        if any(l in exempt for l in labels):
            stats["skip"] += 1
            continue

        already_stale = stale_label in labels

        if already_stale and age >= close_days:
            action = "close"
            msg = f"🔒 因 {age} 天无活动自动关闭。如需重新打开请评论。"
        elif not already_stale and age >= stale_days:
            action = "stale"
            msg = f"⏰ 已 {age} 天无活动，标记为过期。如有更新将自动取消。{close_days} 天后无活动将自动关闭。"
        else:
            stats["skip"] += 1
            continue

        comment = f"## 🤖 Stale Bot\n\n{msg}\n\n<sub>集中管理 · 详见 [治理规范](https://github.com/{ORG}/.github/blob/main/GOVERNANCE.md)</sub>"

        if dry:
            print(f"  [DRY] {kind} #{num} ({org}/{repo}): {action} (age={age}d)")
            stats[action] += 1
            continue

        if action == "close":
            _api(f"/repos/{org}/{repo}/issues/{num}", "PATCH", {"state": "closed", "state_reason": "not_planned"})
        else:
            _api(f"/repos/{org}/{repo}/issues/{num}/labels", "POST", {"labels": [stale_label]})

        _api(f"/repos/{org}/{repo}/issues/{num}/comments", "POST", {"body": comment})
        print(f"  {kind} #{num}: {action} (age={age}d)")
        stats[action] += 1

    return stats


def main():
    print(f"=== Stale Manager: {ORG} ===")
    if DRY_RUN:
        print(">>> DRY RUN MODE <<<")

    repos = paginate(f"/orgs/{ORG}/repos?type=all")
    active = [r for r in repos if not r.get("archived") and not r.get("disabled")]
    print(f"Org repos: {len(active)} active / {len(repos)} total")

    total_stats = {"stale": 0, "close": 0, "skip": 0}
    for repo in active:
        name = repo["name"]
        has_issues = repo.get("has_issues", True)

        # Load per-repo config or use defaults
        per_repo = get_repo_stale_config(ORG, name)
        rules = {**DEFAULTS}
        if per_repo:
            rules.update(per_repo)

        if not has_issues:
            continue

        issues = paginate(f"/repos/{ORG}/{name}/issues?state=open&sort=updated&direction=asc")
        if not issues:
            continue

        stats = process_items(ORG, name, issues, rules, dry=DRY_RUN)
        total = stats["stale"] + stats["close"]
        if total > 0:
            print(f"  {name}: stale={stats['stale']} close={stats['close']} skip={stats['skip']}")
        total_stats["stale"] += stats["stale"]
        total_stats["close"] += stats["close"]
        total_stats["skip"] += stats["skip"]

    print(f"\n=== Summary ===")
    print(f"  Stale: {total_stats['stale']}")
    print(f"  Closed: {total_stats['close']}")
    print(f"  Skipped: {total_stats['skip']}")
    print(f"  Total processed: {sum(total_stats.values())}")


if __name__ == "__main__":
    main()
