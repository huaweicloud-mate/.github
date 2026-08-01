#!/usr/bin/env python3
"""Email 通知发送脚本 - 通过 SendGrid API 发送"""

import os
import json
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "no-reply@huaweicloud-mate.dev")
EMAIL_ADMIN_LIST = os.environ.get("EMAIL_ADMIN_LIST", "")

EVENT = os.environ.get("EVENT", "unknown")
ISSUE_NUMBER = os.environ.get("ISSUE_NUMBER", "")
ISSUE_TITLE = os.environ.get("ISSUE_TITLE", "")
ISSUE_URL = os.environ.get("ISSUE_URL", "")
SUBJECT = os.environ.get("SUBJECT", "GitHub Issue Notification")
BODY = os.environ.get("BODY", "")
TO_EMAILS = os.environ.get("TO_EMAILS", "")


def build_html_body(event, body, issue_url, issue_title):
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #0366d6; color: white; padding: 16px; border-radius: 8px 8px 0 0;">
            <h2 style="margin:0;">huaweicloud-mate Issue 通知</h2>
        </div>
        <div style="border: 1px solid #e1e4e8; padding: 20px; border-radius: 0 0 8px 8px;">
            <p style="white-space: pre-wrap;">{body}</p>
            <hr style="border: none; border-top: 1px solid #e1e4e8; margin: 20px 0;">
            <p>
                <a href="{issue_url}" style="
                    display: inline-block;
                    background-color: #2ea44f;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: bold;
                ">查看 Issue #{issue_number}</a>
            </p>
            <p style="color: #586069; font-size: 12px; margin-top: 20px;">
                此为自动发送的邮件，请勿回复。<br>
                huaweicloud-mate Issue Bot
            </p>
        </div>
    </body>
    </html>
    """.replace("{issue_number}", str(ISSUE_NUMBER or ""))


def send_email(to_emails_list, subject, html_body):
    if not SENDGRID_API_KEY:
        print("WARNING: SENDGRID_API_KEY not set, skipping email")
        return False

    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)

    message = Mail(
        from_email=Email(EMAIL_FROM),
        to_emails=[To(email) for email in to_emails_list],
        subject=subject,
        html_content=Content("text/html", html_body),
    )

    try:
        response = sg.send(message)
        print(f"Email sent. Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def main():
    # 解析收件人
    to_list = []
    if TO_EMAILS:
        to_list = [e.strip() for e in TO_EMAILS.split(",") if e.strip()]

    # 如果没有指定收件人，发送到管理员列表
    if not to_list:
        to_list = [e.strip() for e in EMAIL_ADMIN_LIST.split(",") if e.strip()]

    if not to_list:
        print("No recipients specified, skipping")
        return

    html_body = build_html_body(EVENT, BODY, ISSUE_URL, ISSUE_TITLE)
    send_email(to_list, SUBJECT, html_body)


if __name__ == "__main__":
    main()
