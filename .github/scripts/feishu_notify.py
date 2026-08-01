#!/usr/bin/env python3
"""飞书通知发送脚本 - 通过飞书 Open API 发送 DM 消息"""

import os
import json
import requests

# 飞书凭证（组织 Secrets，建仓流程已配置）
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_ADMIN_OPEN_ID = os.environ.get("FEISHU_ADMIN_OPEN_ID", "")

# 事件参数
EVENT = os.environ.get("EVENT", "unknown")
ISSUE_NUMBER = os.environ.get("ISSUE_NUMBER", "")
ISSUE_TITLE = os.environ.get("ISSUE_TITLE", "")
ISSUE_URL = os.environ.get("ISSUE_URL", "")
SUBJECT = os.environ.get("SUBJECT", "Issue Notification")
BODY = os.environ.get("BODY", "")

# 飞书 API
FEISHU_API = "https://open.feishu.cn/open-apis"
RECEIVE_ID_TYPE = os.environ.get("FEISHU_ID_TYPE", "user_id")  # open_id / user_id / union_id / email


def get_tenant_token():
    """获取 tenant_access_token"""
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        print("WARNING: FEISHU_APP_ID/FEISHU_APP_SECRET not set")
        return None

    url = f"{FEISHU_API}/auth/v3/tenant_access_token/internal"
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    try:
        resp = requests.post(url, json=data, timeout=15)
        result = resp.json()
        if result.get("code") == 0:
            return result.get("tenant_access_token")
        else:
            print(f"Feishu auth failed: code={result.get('code')}, msg={result.get('msg')}")
    except Exception as e:
        print(f"Feishu auth error: {e}")
    return None


def send_dm(open_id, card_content):
    """发送飞书私信卡片"""
    token = get_tenant_token()
    if not token:
        print("Failed to get Feishu token, skipping notification")
        return False

    url = f"{FEISHU_API}/im/v1/messages?receive_id_type={RECEIVE_ID_TYPE}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "receive_id": open_id,
        "msg_type": "interactive",
        "content": json.dumps(card_content, ensure_ascii=False),
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        result = resp.json()
        if result.get("code") == 0:
            return True
        print(f"Feishu send failed: {result.get('msg', 'unknown error')}")
    except Exception as e:
        print(f"Feishu send error: {e}")
    return False


def build_card(event_type, subject, body, issue_url, issue_number, issue_title):
    """根据事件类型构建飞书卡片"""
    color_map = {
        "sla.breach": "red",
        "sla.escalation": "red",
        "sla.warning": "orange",
        "issue.created": "blue",
        "issue.closed": "green",
        "issue.stale": "yellow",
        "report.weekly": "turquoise",
        "report.monthly": "turquoise",
        "report.sla_daily": "carmine",
        "unknown": "grey",
    }

    emoji_map = {
        "sla.breach": "  SLA 违约",
        "sla.escalation": "  SLA 升级",
        "sla.warning": "  SLA 预警",
        "issue.created": "  New Issue",
        "issue.closed": "  Issue Closed",
        "issue.stale": "  Issue Stale",
        "report.weekly": "  周报",
        "report.monthly": "  月报",
        "report.sla_daily": "  SLA 日报",
        "unknown": "  Issue 通知",
    }

    color = color_map.get(event_type, "grey")
    header_title = emoji_map.get(event_type, "  Issue 通知")

    card = {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": header_title}, "template": color},
        "elements": [
            {"tag": "markdown", "content": body},
        ],
    }

    # Issue 相关事件添加链接按钮
    if issue_url:
        card["elements"].append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": f"查看 Issue #{issue_number}"},
                        "type": "primary",
                        "url": issue_url,
                    }
                ],
            }
        )

    card["elements"].append(
        {"tag": "note", "elements": [{"tag": "plain_text", "content": "huaweicloud-mate Issue Bot"}]}
    )

    return card


def send_notification(subject, body, open_ids=None, event_type=None):
    """发送飞书通知，主入口函数"""
    if not open_ids:
        open_ids = []
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        print("WARNING: Feishu credentials not configured, skipping")
        return False

    if not open_ids:
        open_ids = [FEISHU_ADMIN_OPEN_ID] if FEISHU_ADMIN_OPEN_ID else []

    open_ids = [oid.strip() for oid in open_ids if oid.strip()]
    if not open_ids:
        print("No recipients specified, skipping")
        return False

    card = build_card(
        event_type or EVENT, subject, body, ISSUE_URL, ISSUE_NUMBER, ISSUE_TITLE
    )

    success_count = 0
    for open_id in open_ids:
        if send_dm(open_id, card):
            print(f"Feishu notification sent to {open_id}")
            success_count += 1

    return success_count > 0


def main():
    open_ids = []
    if FEISHU_ADMIN_OPEN_ID:
        open_ids.append(FEISHU_ADMIN_OPEN_ID)

    send_notification(SUBJECT, BODY, open_ids, EVENT)


if __name__ == "__main__":
    main()
