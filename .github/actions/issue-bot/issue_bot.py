#!/usr/bin/env python3
"""Issue Bot - 自动分类、打标签、分配负责人"""

import os
import re
import yaml
import requests

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
GITHUB_API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH", "")
CONFIG_PATH = os.environ.get("CONFIG_PATH", "configs/triage-rules.yml")


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_event():
    import json
    if not EVENT_PATH or not os.path.exists(EVENT_PATH):
        return None
    with open(EVENT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def match_keywords(text, keywords):
    if not text or not keywords:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def classify_issue(title, body, config):
    labels_to_add = []

    # 类型分类
    for rule in config.get("label_rules", []):
        search_text = f"{title} {body or ''}"
        if match_keywords(search_text, rule["keywords"]):
            labels_to_add.append(rule["label"])
            break

    # 优先级分类
    for rule in config.get("priority_rules", []):
        search_text = f"{title} {body or ''}"
        if match_keywords(search_text, rule["keywords"]):
            labels_to_add.append(rule["label"])
            break

    # 领域分类
    for rule in config.get("area_rules", []):
        search_text = f"{title} {body or ''}"
        if match_keywords(search_text, rule["keywords"]):
            labels_to_add.append(rule["label"])

    return list(set(labels_to_add))


def find_assignee(labels, config):
    for rule in config.get("assignee_rules", []):
        area = rule.get("area")
        atype = rule.get("type")
        priority = rule.get("priority")

        match = True
        if area and area not in labels and area != "default":
            match = False
        if atype and (not priority or priority not in labels):
            match = False

        if match:
            return rule["assignee"]

    return "default-triage"


def add_labels(owner, repo, issue_number, labels):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/labels"
    resp = requests.post(url, headers=HEADERS, json={"labels": labels})
    return resp.ok


def add_assignee(owner, repo, issue_number, assignee):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/assignees"
    resp = requests.post(url, headers=HEADERS, json={"assignees": [assignee]})
    return resp.ok


def main():
    config = load_config(CONFIG_PATH)
    event = load_event()

    if not event or "issue" not in event:
        print("No issue event found, exiting")
        return

    issue = event["issue"]
    title = issue.get("title", "")
    body = issue.get("body", "")
    issue_number = issue["number"]

    owner, repo = GITHUB_REPOSITORY.split("/")
    existing_labels = [l["name"] for l in issue.get("labels", [])]

    # 分类
    new_labels = classify_issue(title, body, config)

    # 合并现有标签
    all_labels = list(set(existing_labels + new_labels))
    if all_labels != existing_labels:
        add_labels(owner, repo, issue_number, all_labels)
        print(f"Added labels: {[l for l in new_labels if l not in existing_labels]}")

    # 分配负责人
    if not issue.get("assignees"):
        assignee = find_assignee(all_labels, config)
        add_assignee(owner, repo, issue_number, assignee)
        print(f"Assigned to: {assignee}")


if __name__ == "__main__":
    main()
