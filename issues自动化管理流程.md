# huaweicloud-mate Issues 自动化管理流程

## 完整流程

```
Issue 创建
    ↓
Issue Bot 触发 → 自动打标签（分类/优先级/领域）+ 自动分配负责人
    ↓
SLA 计时开始 → 根据 priority 设定响应/解决时限
    ↓
├── 超时未响应 → SLA 告警（标签 + email 通知管理员/负责人）
├── 超时未解决 → 升级告警（打 escalation 标签 + email）
    ↓
正常流转：status/pending → status/triaged → status/in-progress → status/resolved → status/completed
    ↓
定期触发（每周/月）→ 统计报表
    │   ├── GitHub Issues 统计（仓库维度）
    │   └── GitCode Issues 统计抓取 + 汇总
    │       ↓
    │   合并报表 → email 发送给管理员
    ↓
过期 Issue 定期扫描（stale bot）→ 打 stale 标签 → 14 天无更新 → 自动关闭
```

## 一、Issue 分类 / Triage

### 触发方式
- Issue Bot（`.github/actions/issue-bot/`）在 Issue 创建时自动运行
- 复用建仓流程中已有的 `issue-bot` 脚本，扩展分类能力

### 自动打标签规则

| 触发条件 | 标签 | 说明 |
|---------|------|------|
| 使用 bug_report 模板 | `type/bug` | 根据模板自动识别 |
| 使用 feature_request 模板 | `type/feature` | 根据模板自动识别 |
| 标题含 `doc`/`文档` | `type/documentation` | 关键字匹配 |
| 标题含 `question`/`问题` | `type/question` | 关键字匹配 |
| AI 分析 Issue 正文 | `priority/critical` `priority/high` `priority/medium` `priority/low` | 关键词 + 严重性判断 |
| 根据文件路径/标签匹配 | `area/*` | 领域分类（如 area/api, area/web, area/ci-cd...） |

### 自动分配负责人

| 标签/领域 | 负责人 |
|-----------|--------|
| `area/api` | @api-maintainer |
| `area/web` | @web-maintainer |
| `area/ci-cd` | @devops-maintainer |
| `type/bug` + `priority/critical` | @tech-lead |
| 无匹配 | @default-triage |

### 关键文件

| 文件 | 仓库 | 作用 |
|------|------|------|
| `actions/issue-bot/issue_bot.py` | `.github` | Issue Bot 核心脚本（分类+分配） |
| `configs/triage-rules.yml` | `.github` | 分类规则配置（标签映射、负责人映射） |
| `workflows/triage-issue.yml` | `.github` | Issue Triage 触发器 |

---

## 二、Issue 生命周期

### 状态流转

```
status/pending          → Issue 新建，待 triage
status/triaged          → 已分类 + 已分配
status/in-progress      → 开发中（负责人自行标记 / PR 关联自动标记）
status/resolved         → 已修复（关联 PR 合并后自动标记）
status/completed        → 已验证 / 管理员手动关闭
```

### 自动状态转换规则

| 事件 | 状态变更 | 触发方式 |
|------|---------|---------|
| Issue Bot 分类完成 | `pending` → `triaged` | Issue Bot 自动 |
| PR 链接到 Issue（Fixes/Closes #N） | `triaged` → `in-progress` | GitHub 原生联动 |
| 关联 PR 合并 | `in-progress` → `resolved` | 合并后 workflow |
| 管理员手动关闭 | `resolved` → `completed` | 管理员操作 |
| 无关联 PR 直接关闭 | 任意 → `completed` | 管理员操作 |

### Stale Issue 处理

```
Issue 持续 N 天无更新
    ↓
stale bot 检测 → 打 status/stale 标签 + 评论提醒
    ↓
14 天内无更新
    ↓
自动关闭 → status/completed + 评论说明
```

| 标签 | 过期天数 |
|------|---------|
| `type/bug` | 60 天 |
| `type/feature` | 90 天 |
| `type/question` | 30 天 |
| `type/documentation` | 180 天 |
| `priority/critical` | 365 天（不轻易关闭） |

### 关键文件

| 文件 | 仓库 | 作用 |
|------|------|------|
| `workflows/stale.yml` | `.github` | Stale bot 工作流 |
| `configs/stale-rules.yml` | `.github` | 各类型过期天数配置 |
| `workflows/status-transition.yml` | `.github` | 状态自动流转工作流 |

---

## 三、Issue 通知（Email）

### 通知触发场景

| 场景 | 接收人 | 频率 |
|------|--------|------|
| Issue 新建 + 已分类 | 分配的负责人 | 实时 |
| SLA 即将超时（24h 预警） | 负责人 + 管理员 | 实时 |
| SLA 已超时 | 负责人 + 管理员 + 技术主管 | 实时（单次） |
| Stale 即将关闭 | 负责人 | 实时 |
| Issue 被关闭 | 创建者 | 实时 |

### 邮件通知实现

```
GitHub Actions workflow
    ↓
调用组织级 reusable workflow: email-notify.yml
    ↓
使用 SendGrid / GitHub Actions Email 发送
    ↓
组织 Secrets: SENDGRID_API_KEY + EMAIL_FROM + EMAIL_ADMIN_LIST
```

### 关键文件

| 文件 | 仓库 | 作用 |
|------|------|------|
| `workflows/email-notify.yml` | `.github` | 可复用邮件通知工作流 |
| `scripts/email_notify.py` | `.github` | 邮件发送脚本 |
| `configs/email-rules.yml` | `.github` | 通知规则配置 |
| `workflows/issue-notify.yml` | 各仓库 | Issue 事件 → 邮件通知触发 |

---

## 四、Issue 跨平台统计（GitCode）

### 说明
- **不做同步**，仅定期抓取 GitCode 对应仓库的 Issue 数据进行统计汇总
- 统计结果合并到 GitHub Issue 报表中

### 流程

```
每周一 09:00 UTC 触发
    ↓
gh-stats workflow → 并行执行
    ├── GitHub Issues 统计（所有 huaweicloud-mate 仓库）
    └── GitCode Issues 统计（hd-vector 下所有仓库）
    ↓
合并数据 → 生成报表
    ↓
email 发送给管理员列表
```

### GitCode 统计抓取

```
使用 GitCode Open API 获取 Issues
    ↓
按仓库聚合统计：
  - Issue 总数 / 已开启 / 已关闭
  - 按标签分布
  - 按创建者分布
  - 平均响应时间
  - 平均解决时间
    ↓
与 GitHub 数据合并输出
```

### 统计维度

| 维度 | GitHub | GitCode | 汇总 |
|------|--------|---------|------|
| Issue 总数 | ✅ | ✅ | ✅ |
| 开启数 | ✅ | ✅ | ✅ |
| 关闭数 | ✅ | ✅ | ✅ |
| 按类型分布 | ✅ | ✅ | ✅ |
| 按优先级分布 | ✅ | ✅ | ✅ |
| 平均响应时间 | ✅ | ✅ | ✅ |
| 平均解决时间 | ✅ | ✅ | ✅ |
| SLA 达标率 | ✅ | ❌ | ✅ |

### 关键文件

| 文件 | 仓库 | 作用 |
|------|------|------|
| `workflows/issue-stats.yml` | `.github` | 统计报表触发器 |
| `scripts/github_stats.py` | `.github` | GitHub Issue 统计脚本 |
| `scripts/gitcode_stats.py` | `.github` | GitCode Issue 统计脚本 |
| `scripts/stats_report.py` | `.github` | 合并 + 生成报表+ 发送邮件 |

---

## 五、Issue 报表

### 报表类型

| 报表 | 频率 | 内容 | 接收人 |
|------|------|------|--------|
| **周报** | 每周一 | 本周新建/关闭/活跃 Issue、SLA 达标率、趋势 | 管理员 + 技术主管 |
| **月报** | 每月 1 号 | 月度汇总、对比上月、团队贡献排行、重点关注 | 全部成员 |
| **SLA 日报** | 每日 | 超时未处理 Issue 清单 | 管理员 |

### 周报示例结构

```
## huaweicloud-mate Issues 周报（2026-W31）

### 概览
| 指标 | 本周 | 上周 | 变化 |
|------|------|------|------|
| 新建 Issue | 12 | 8 | +50% |
| 已关闭 | 9 | 11 | -18% |
| 活跃 | 23 | 20 | +15% |

### SLA 达标率
- 总达标率：87%（目标 90%）
- critical：100%
- high：85% ⚠️
- medium：82% ⚠️

### GitCode 统计（hd-vector）
| 仓库 | 开启 | 关闭 | 合计 |
|------|------|------|------|
| xxx-sdk | 5 | 12 | 17 |
| yyy-api | 2 | 8 | 10 |
...

### 重点关注
- #42 (critical) 已超时 3 天未分配
- #56 (high) 30 天无更新
```

### 关键文件

| 文件 | 仓库 | 作用 |
|------|------|------|
| `workflows/weekly-report.yml` | `.github` | 周报触发器 |
| `workflows/monthly-report.yml` | `.github` | 月报触发器 |
| `workflows/sla-daily.yml` | `.github` | SLA 日报触发器 |
| `scripts/stats_report.py` | `.github` | 报表生成脚本（复用） |
| `templates/report-weekly.md` | `.github` | 周报模板 |
| `templates/report-monthly.md` | `.github` | 月报模板 |

---

## 六、SLA 提醒

### SLA 标准

| 优先级 | 首次响应时限 | 解决时限（工作日） | 升级时限 |
|--------|------------|------------------|---------|
| `priority/critical` | 4 小时 | 1 天 | 8 小时 |
| `priority/high` | 8 小时 | 3 天 | 24 小时 |
| `priority/medium` | 24 小时 | 7 天 | 3 天 |
| `priority/low` | 48 小时 | 30 天 | 14 天 |

### SLA 监控流程

```
Issue 创建 → 记录 created_at
    ↓
SLA Monitor workflow（每小时运行一次）
    ↓
扫描所有未关闭 Issue
    ├── 首次响应超时（无回复/无分配）→ 打 label:sla/breach + email 管理员
    ├── 解决超时（超过解决时限）→ 打 label:sla/breach + label:escalation + email 技术主管
    └── 即将超时（剩余 < 24h）→ 打 label:sla/warning + email 负责人
```

### SLA 告警邮件内容

```
主题：[SLA ⚠️] Issue #42 首次响应超时

Issue: huaweicloud-mate/xxx-repo#42
标题: API 接口 500 错误
优先级: critical
创建时间: 2026-08-01 09:00
应响应时间: 2026-08-01 13:00
当前状态: 超时 2h 未响应

操作: https://github.com/huaweicloud-mate/xxx-repo/issues/42
```

### SLA 达标率计算

```
达标率 = (时限内完成数 / 总应完成数) × 100%

分级统计:
- 按优先级
- 按仓库
- 按负责人
```

### 关键文件

| 文件 | 仓库 | 作用 |
|------|------|------|
| `workflows/sla-monitor.yml` | `.github` | SLA 监控触发器（每小时） |
| `scripts/sla_monitor.py` | `.github` | SLA 检测 + 告警脚本 |
| `configs/sla-rules.yml` | `.github` | SLA 时限配置 |

---

## 七、完整文件清单

| 文件 | 仓库 | 作用 |
|------|------|------|
| `actions/issue-bot/issue_bot.py` | `.github` | Issue Bot（分类+分配） |
| `workflows/triage-issue.yml` | `.github` | Triage 触发 |
| `workflows/stale.yml` | `.github` | Stale 检测 |
| `workflows/status-transition.yml` | `.github` | 状态流转 |
| `workflows/sla-monitor.yml` | `.github` | SLA 监控（每小时） |
| `workflows/issue-notify.yml` | `.github` | Issue 事件邮件通知 |
| `workflows/email-notify.yml` | `.github` | 可复用邮件发送 |
| `workflows/issue-stats.yml` | `.github` | 统计报表触发 |
| `workflows/weekly-report.yml` | `.github` | 周报触发 |
| `workflows/monthly-report.yml` | `.github` | 月报触发 |
| `workflows/sla-daily.yml` | `.github` | SLA 日报触发 |
| `scripts/email_notify.py` | `.github` | 邮件发送 |
| `scripts/sla_monitor.py` | `.github` | SLA 检测+告警 |
| `scripts/github_stats.py` | `.github` | GitHub 统计 |
| `scripts/gitcode_stats.py` | `.github` | GitCode 统计抓取 |
| `scripts/stats_report.py` | `.github` | 合并报表生成 |
| `configs/triage-rules.yml` | `.github` | 分类规则配置 |
| `configs/stale-rules.yml` | `.github` | 过期规则配置 |
| `configs/sla-rules.yml` | `.github` | SLA 时限配置 |
| `configs/email-rules.yml` | `.github` | 邮件通知规则 |
| `templates/report-weekly.md` | `.github` | 周报模板 |
| `templates/report-monthly.md` | `.github` | 月报模板 |

---

## 八、组织 Secrets

| Secret | 用途 |
|--------|------|
| `SENDGRID_API_KEY` | 邮件发送 |
| `EMAIL_FROM` | 发件人地址 |
| `EMAIL_ADMIN_LIST` | 管理员邮件列表（逗号分隔） |
| `GITCODE_TOKEN` | GitCode API 访问（统计抓取用，已有） |
| `GITHUB_TOKEN` | GitHub API 访问（默认提供） |

---

## 九、管理员操作速查

```powershell
# 查看超时 Issue（所有仓库）
gh issue list -R huaweicloud-mate/<repo> -l "sla/breach"

# 查看待处理 Issue
gh issue list -R huaweicloud-mate/<repo> -l "status/pending"

# 查看 escalation Issue
gh issue list -R huaweicloud-mate/<repo> -l "escalation"

# 手动触发统计报表
gh workflow run issue-stats.yml -R huaweicloud-mate/.github

# 手动触发 SLA 检查
gh workflow run sla-monitor.yml -R huaweicloud-mate/.github

# 查看某仓库 Issue 统计
gh issue list -R huaweicloud-mate/<repo> --limit 1000 --json state,labels | `
  ConvertFrom-Json | Group-Object state | Select-Object Name,Count
```

---

## 十、标签体系（标准 14 标签 + 扩展）

### 标准标签（建仓时自动创建）

| 标签 | 用途 |
|------|------|
| `type/bug` | Bug 报告 |
| `type/feature` | 功能请求 |
| `type/documentation` | 文档相关 |
| `type/question` | 问题咨询 |
| `priority/critical` | 紧急 |
| `priority/high` | 高 |
| `priority/medium` | 中 |
| `priority/low` | 低 |
| `status/pending` | 待处理 |
| `status/triaged` | 已分类 |
| `status/in-progress` | 进行中 |
| `status/resolved` | 已解决 |
| `status/completed` | 已完成 |
| `status/stale` | 即将过期 |

### Issue 自动化专用标签

| 标签 | 用途 |
|------|------|
| `sla/breach` | SLA 已违约 |
| `sla/warning` | SLA 即将违约 |
| `escalation` | 已升级 |
