#!/usr/bin/env python3
"""
Issue Management B
ot for huaweicloud-mate organization
Powerful
 by GitHub App authentication

Capabilities:

- Auto-triage new issues (classify type, prio
rity, area)
- Send Feishu notification for re
po creation requests
- Respond to slash comma
nds in comments (/assign, /priority, /label, 
/close, /reopen)
- Greet first-time contribut
ors
"""
import json
import os
import sys
impo
rt re
import time
import urllib.request
impor
t urllib.error
import hashlib
import hmac
fro
m datetime import datetime, timezone

def jwt
_encode(payload, private_key_pem):
    import
 base64 as b64
    
    def base64url(data):

        return b64.urlsafe_b64encode(data).rs
trip(b'=').decode('ascii')
    
    header = 
{"alg": "RS256", "typ": "JWT"}
    header_b64
 = base64url(json.dumps(header, separators=('
,', ':')).encode())
    payload_b64 = base64u
rl(json.dumps(payload, separators=(',', ':'))
.encode())
    
    from cryptography.hazmat.
primitives import hashes, serialization
    f
rom cryptography.hazmat.primitives.asymmetric
 import padding
    
    private_key = serial
ization.load_pem_private_key(private_key_pem.
encode(), password=None)
    message = f"{hea
der_b64}.{payload_b64}".encode()
    signatur
e = private_key.sign(message, padding.PKCS1v1
5(), hashes.SHA256())
    signature_b64 = bas
e64url(signature)
    return f"{header_b64}.{
payload_b64}.{signature_b64}"

def get_app_in
stallation_token(app_id, private_key_pem, ins
tallation_id):
    now = int(time.time())
   
 payload = {"iat": now - 60, "exp": now + 600
, "iss": int(app_id)}
    token_jwt = jwt_enc
ode(payload, private_key_pem)
    
    url = 
f"https://api.github.com/app/installations/{i
nstallation_id}/access_tokens"
    headers = 
{"Authorization": f"Bearer {token_jwt}", "Acc
ept": "application/vnd.github+json", "User-Ag
ent": "issue-bot"}
    req = urllib.request.R
equest(url, headers=headers, method="POST")
 
   try:
        with urllib.request.urlopen(r
eq, timeout=15) as resp:
            data = j
son.loads(resp.read())
            return dat
a.get("token")
    except urllib.error.HTTPEr
ror as e:
        print(f"Auth error {e.code}
: {e.read().decode()[:300]}", file=sys.stderr
)
        return None

def github_api(method,
 path, token, data=None):
    url = f"https:/
/api.github.com{path}"
    headers = {"Accept
": "application/vnd.github+json", "Authorizat
ion": f"Bearer {token}", "User-Agent": "issue
-bot"}
    body = json.dumps(data).encode() i
f data else None
    req = urllib.request.Req
uest(url, data=body, headers=headers, method=
method)
    try:
        with urllib.request.
urlopen(req, timeout=30) as resp:
           
 if resp.status == 204:
                retur
n {"status": "success"}
            return js
on.loads(resp.read())
    except urllib.error
.HTTPError as e:
        error_body = e.read(
).decode()[:500]
        print(f"API error {e
.code}: {error_body}", file=sys.stderr)
     
   return {"error": error_body, "status_code"
: e.code}
    except Exception as e:
        
print(f"API error: {e}", file=sys.stderr)
   
     return {"error": str(e)}

def get_feishu
_token(app_id, app_secret):
    url = "https:
//open.feishu.cn/open-apis/auth/v3/tenant_acc
ess_token/internal"
    headers = {"Content-T
ype": "application/json; charset=utf-8"}
    
data = {"app_id": app_id, "app_secret": app_s
ecret}
    body = json.dumps(data).encode()
 
   req = urllib.request.Request(url, data=bod
y, headers=headers, method="POST")
    try:
 
       with urllib.request.urlopen(req, timeo
ut=15) as resp:
            result = json.loa
ds(resp.read())
            return result.get
("tenant_access_token")
    except Exception 
as e:
        print(f"Feishu auth error: {e}"
, file=sys.stderr)
        return None

def s
end_feishu_dm(open_id, content, app_id, app_s
ecret):
    token = get_feishu_token(app_id, 
app_secret)
    if not token:
        print("
Failed to get Feishu token", file=sys.stderr)

        return False
    url = f"https://ope
n.feishu.cn/open-apis/im/v1/messages?receive_
id_type=open_id"
    headers = {"Authorizatio
n": f"Bearer {token}", "Content-Type": "appli
cation/json; charset=utf-8"}
    body = {"rec
eive_id": open_id, "msg_type": "interactive",
 "content": json.dumps(content, ensure_ascii=
False)}
    req = urllib.request.Request(url,
 data=json.dumps(body).encode(), headers=head
ers, method="POST")
    try:
        with url
lib.request.urlopen(req, timeout=15) as resp:

            result = json.loads(resp.read())

            if result.get("code") == 0:
    
            print("Feishu notification sent s
uccessfully")
                return True
   
         print(f"Feishu send error: {result}"
, file=sys.stderr)
            return False
 
   except Exception as e:
        print(f"Fei
shu send exception: {e}", file=sys.stderr)
  
      return False

def notify_repo_request(i
ssue, repo_full):
    app_id = os.environ.get
("FEISHU_APP_ID", "")
    app_secret = os.env
iron.get("FEISHU_APP_SECRET", "")
    admin_o
pen_id = os.environ.get("FEISHU_ADMIN_OPEN_ID
", "")
    if not all([app_id, app_secret, ad
min_open_id]):
        print("Feishu credenti
als not configured, skipping notification")
 
       return

    issue_number = issue.get("
number", 0)
    title = issue.get("title", ""
)
    author = issue.get("user", {}).get("log
in", "")
    body = issue.get("body", "") or 
""
    html_url = issue.get("html_url", "")


    fields = {"仓库名称": "", "仓库描�
��": "", "可见性": "", "主要编程语言
": ""}
    sections = re.split(r'### ', body)

    for section in sections[1:]:
        lin
es = section.strip().split('\n')
        if n
ot lines:
            continue
        name =
 lines[0].strip()
        value = '\n'.join(l
ines[1:]).strip() if len(lines) > 1 else ''
 
       if value == '_No response_':
         
   value = ''
        if name in fields:
    
        fields[name] = value

    approve_url
 = f"https://github.com/huaweicloud-mate/repo
sitory-requests/actions/workflows/approve-rep
o.yml"
    card = {
        "config": {"wide_
screen_mode": True},
        "header": {"titl
e": {"tag": "plain_text", "content": "🏗️
 新建仓库申请"}, "template": "blue"},
 
       "elements": [
            {"tag": "mar
kdown", "content": f"**{author}** 提交了�
�仓申请"},
            {
                "
tag": "div",
                "fields": [
    
                {"is_short": True, "text": {"
tag": "lark_md", "content": f"**仓库名称*
*\n{fields.get('仓库名称', 'N/A')}"}},
  
                  {"is_short": True, "text": 
{"tag": "lark_md", "content": f"**可见性**
\n{fields.get('可见性', 'N/A')}"}},
      
              {"is_short": True, "text": {"ta
g": "lark_md", "content": f"**语言**\n{fiel
ds.get('主要编程语言', 'N/A')}"}},
    
                {"is_short": True, "text": {"
tag": "lark_md", "content": f"**描述**\n{fi
elds.get('仓库描述', 'N/A')}"}},
        
        ]
            },
            {"tag": 
"hr"},
            {"tag": "markdown", "conte
nt": f"📋 申请理由：{fields.get('申�
�理由', '未填写')}"},
            {"tag"
: "hr"},
            {
                "tag":
 "action",
                "actions": [
     
               {"tag": "button", "text": {"ta
g": "plain_text", "content": "查看 Issue"},
 "type": "default", "url": html_url},
       
             {"tag": "button", "text": {"tag"
: "plain_text", "content": "✅ 审批通过"
}, "type": "primary", "url": f"{approve_url}?
issue_number={issue_number}"},
              
  ]
            },
            {"tag": "note"
, "elements": [{"tag": "plain_text", "content
": f"点击审批通过 → 跳转 GitHub →
 填入 Issue 号 #{issue_number} → Run wor
kflow"}]}
        ]
    }
    send_feishu_dm(
admin_open_id, card, app_id, app_secret)

def
 classify_issue(title, body, labels):
    tex
t = f"{title}\n{body or ''}".lower()
    resu
lt = {"type": None, "priority": None, "area":
 None}
    
    if any(w in text for w in ['b
ug', 'error', 'crash', 'broken', 'fail', 'exc
eption', 'traceback', 'fix']):
        result
["type"] = "bug"
    elif any(w in text for w
 in ['feature', 'request', 'add', 'support', 
'enhance', 'improve', 'new']):
        result
["type"] = "enhancement"
    elif any(w in te
xt for w in ['question', 'how to', 'how do', 
'help', 'usage', 'example']):
        result[
"type"] = "question"
    elif any(w in text f
or w in ['doc', 'documentation', 'readme', 'g
uide', 'tutorial']):
        result["type"] =
 "documentation"
    elif any(w in text for w
 in ['security', 'vulnerability', 'cve', 'xss
', 'injection']):
        result["type"] = "b
ug"
        result["priority"] = "priority/cr
itical"
    
    if not result["priority"]:
 
       if any(w in text for w in ['critical',
 'urgent', 'emergency', 'production down', 'd
ata loss']):
            result["priority"] =
 "priority/critical"
        elif any(w in te
xt for w in ['important', 'high', 'blocking',
 'blocker']):
            result["priority"] 
= "priority/high"
        elif any(w in text 
for w in ['medium', 'normal']):
            r
esult["priority"] = "priority/medium"
       
 elif any(w in text for w in ['low', 'minor',
 'nice to have', 'cosmetic']):
            re
sult["priority"] = "priority/low"
        eli
f result["type"] == "bug":
            result
["priority"] = "priority/high"
        elif r
esult["type"] == "enhancement":
            r
esult["priority"] = "priority/medium"
       
 else:
            result["priority"] = "prio
rity/medium"
    
    if any(w in text for w 
in ['sdk', 'api', 'client', 'library']):
    
    result["area"] = "area/sdk"
    elif any(
w in text for w in ['ui', 'frontend', 'web', 
'dashboard', 'interface']):
        result["a
rea"] = "area/frontend"
    elif any(w in tex
t for w in ['ci', 'cd', 'pipeline', 'workflow
', 'deploy', 'build', 'test']):
        resul
t["area"] = "area/ci-cd"
    elif any(w in te
xt for w in ['doc', 'documentation', 'readme'
, 'guide']):
        result["area"] = "area/d
ocs"
    elif any(w in text for w in ['securi
ty', 'auth', 'permission', 'token']):
       
 result["area"] = "area/security"
    return 
result

def is_first_time_contributor(author,
 repo, token):
    result = github_api("GET",
 f"/repos/{repo}/issues?creator={author}&per_
page=2&state=all", token)
    if isinstance(r
esult, list):
        return len(result) <= 1

    return False

def is_repo_request(body):

    return "### 仓库名称" in (body or ""
)

def handle_slash_command(command, args, is
sue_number, repo, token, commenter):
    resp
onses = {
        "assign": handle_assign, "p
riority": handle_priority,
        "label": h
andle_label, "close": handle_close,
        "
reopen": handle_reopen, "help": handle_help,

    }
    handler = responses.get(command)
  
  if handler:
        return handler(args, is
sue_number, repo, token, commenter)
    retur
n f"Unknown command: `/{command}`. Type `/hel
p` for available commands."

def handle_assig
n(args, issue_number, repo, token, commenter)
:
    assignee = args.strip().lstrip('@') if 
args.strip() else commenter
    github_api("P
OST", f"/repos/{repo}/issues/{issue_number}/a
ssignees", token, {"assignees": [assignee]})

    return f"Assigned @{assignee} to this iss
ue."

def handle_priority(args, issue_number,
 repo, token, commenter):
    priority_map = 
{"critical": "priority/critical", "high": "pr
iority/high", "medium": "priority/medium", "l
ow": "priority/low"}
    level = args.strip()
.lower()
    label = priority_map.get(level)

    if not label:
        return f"Invalid pr
iority: `{level}`. Use: critical, high, mediu
m, low"
    issue = github_api("GET", f"/repo
s/{repo}/issues/{issue_number}", token)
    i
f isinstance(issue, dict) and "labels" in iss
ue:
        for lbl in issue["labels"]:
     
       if lbl["name"].startswith("priority/")
:
                github_api("DELETE", f"/rep
os/{repo}/issues/{issue_number}/labels/{lbl['
name']}", token)
    github_api("POST", f"/re
pos/{repo}/issues/{issue_number}/labels", tok
en, {"labels": [label]})
    return f"Priorit
y set to `{label}`."

def handle_label(args, 
issue_number, repo, token, commenter):
    la
bels = [l.strip() for l in args.split(',') if
 l.strip()]
    if not labels:
        return
 "Usage: `/label label1, label2`"
    github_
api("POST", f"/repos/{repo}/issues/{issue_num
ber}/labels", token, {"labels": labels})
    
return f"Added label(s): {', '.join(f'`{l}`' 
for l in labels)}."

def handle_close(args, i
ssue_number, repo, token, commenter):
    git
hub_api("PATCH", f"/repos/{repo}/issues/{issu
e_number}", token, {"state": "closed", "state
_reason": "completed"})
    return "Issue clo
sed."

def handle_reopen(args, issue_number, 
repo, token, commenter):
    github_api("PATC
H", f"/repos/{repo}/issues/{issue_number}", t
oken, {"state": "open"})
    return "Issue re
opened."

def handle_help(args, issue_number,
 repo, token, commenter):
    return """**Ava
ilable commands:**
- `/assign @user` — Assi
gn issue
- `/priority <level>` — Set priori
ty (critical/high/medium/low)
- `/label <labe
ls>` — Add labels
- `/close` / `/reopen` �
� Close or reopen issue
- `/help` — Show th
is help
<sub>issue-bot v1.0</sub>"""

def han
dle_issue_opened(event, token):
    issue = e
vent["issue"]
    repo = event["repository"][
"full_name"]
    issue_number = issue["number
"]
    title = issue.get("title", "")
    bod
y = issue.get("body", "") or ""
    author = 
issue.get("user", {}).get("login", "")
    ex
isting_labels = [l["name"] for l in issue.get
("labels", [])]
    
    if "agent/triaged" i
n existing_labels:
        print(f"Issue #{is
sue_number} already triaged, skipping")
     
   return


    classification 
= classify_issue(title, body, existing_labels
)
    print(f"Classification: {json.dumps(cla
ssification, ensure_ascii=False)}")
    
    
labels_to_add = ["agent/triaged"]
    if clas
sification["type"]:
        labels_to_add.app
end(classification["type"])
    if classifica
tion["priority"]:
        labels_to_add.appen
d(classification["priority"])
    if classifi
cation["area"]:
        labels_to_add.append(
classification["area"])
    github_api("POST"
, f"/repos/{repo}/issues/{issue_number}/label
s", token, {"labels": labels_to_add})
    
  
  parts = ["### 🤖 Issue Bot\n", "**分类�
��果：**\n"]
    if classification["type"]:

        parts.append(f"- 类型: `{classific
ation['type']}`\n")
    if classification["pr
iority"]:
        parts.append(f"- 优先级:
 `{classification['priority']}`\n")
    if cl
assification["area"]:
        parts.append(f"
- 领域: `{classification['area']}`\n")
    
parts.append("\n可用 `/help` 查看管理�
�令。\n")
    parts.append("\n<sub>issue-bo
t v1.0 · triage</sub>")
    
    github_api(
"POST", f"/repos/{repo}/issues/{issue_number}
/comments", token, {"body": "".join(parts)})

    
    if is_first_time_contributor(author,
 repo, token):
        github_api("POST", f"/
repos/{repo}/issues/{issue_number}/comments",
 token,
                   {"body": f"👋 We
lcome @{author}! Thanks for your first issue.
"})

def handle_issue_comment(event, token):

    comment = event["comment"]
    issue = ev
ent["issue"]
    repo = event["repository"]["
full_name"]
    issue_number = issue["number"
]
    body = comment.get("body", "")
    comm
enter = comment.get("user", {}).get("login", 
"")
    
    if not body.startswith('/') or c
omment.get("performed_via_github_app"):
     
   return
    parts = body.strip().split(None
, 1)
    command = parts[0].lstrip('/')
    a
rgs = parts[1] if len(parts) > 1 else ""
    
print(f"Slash command: /{command} {args} by @
{commenter}")
    response = handle_slash_com
mand(command, args, issue_number, repo, token
, commenter)
    if response:
        github_
api("POST", f"/repos/{repo}/issues/{issue_num
ber}/comments", token, {"body": response})

d
ef main():
    event_path = os.environ.get("G
ITHUB_EVENT_PATH", "")
    if not event_path 
or not os.path.exists(event_path):
        pr
int("No event payload found")
        return

    with open(event_path) as f:
        event
 = json.load(f)
    
    event_action = os.en
viron.get("GITHUB_EVENT_NAME", "")
    print(
f"Event: {event_action}")
    
    app_id = o
s.environ.get("APP_ID", "")
    private_key =
 os.environ.get("APP_PRIVATE_KEY", "")
    in
stallation_id = os.environ.get("APP_INSTALLAT
ION_ID", "")
    
    if not all([app_id, pri
vate_key, installation_id]):
        token = 
os.environ.get("GITHUB_TOKEN", "")
    else:

        token = get_app_installation_token(ap
p_id, private_key, installation_id)
        i
f not token:
            token = os.environ.g
et("GITHUB_TOKEN", "")
    if not token:
    
    print("No token available, exiting")
    
    return
    
    if event_action == "issue
s":
        action = event.get("action", "")

        if action in ("opened", "edited"):
  
          handle_issue_opened(event, token)
 
   elif event_action == "issue_comment":
    
    if event.get("action") == "created":
    
        handle_issue_comment(event, token)

i
f __name__ == "__main__":
    main()


