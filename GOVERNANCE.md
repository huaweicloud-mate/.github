# huaweicloud 组织开源治理规范

> 版本: v1.0
> 生效日期: 2026-08-03
> 适用范围: huaweicloud GitHub 组织下所有仓库
> 制定: Hermes Agent
> 审批: 待 TMG 评审

---

## 目录

1. [总则](#一总则)
2. [三级准入体系](#二三级准入体系)
3. [仓库创建标准](#三仓库创建标准)
4. [维护与运营要求](#四维护与运营要求)
5. [退出与归档机制](#五退出与归档机制)
6. [角色与职责](#六角色与职责)
7. [合规检查与度量](#七合规检查与度量)
8. [附录](#八附录)

---

## 一、总则

### 1.1 目的

本规范为 huaweicloud GitHub 组织的所有仓库建立统一的治理标准，确保开源项目的法律合规性、安全性和社区健康度。

### 1.2 适用范围

- 本组织下所有**公开仓库**
- 私有仓库参照执行（受 Free plan 限制的部分条款除外）
- 归档仓库仅受退出标准约束

### 1.3 核心原则

1. **法律先行** — License 是开源的第一道门。无 License 的代码在法律上保留所有权利，他人不可合法使用、修改或分发。本组织所有公开仓库必须有 OSI 批准的 LICENSE 文件。

2. **安全不可妥协** — 分支保护、依赖扫描、安全漏洞报告渠道不是可选项。有 Star 的项目就有用户，有用户就要对安全负责。

3. **可发现性决定社区规模** — 仓库描述、Topics 标签、README 决定用户在 GitHub 上能否找到你。找不到就不会用，不会用就不会贡献。

4. **渐变而非休克** — 治理标准按仓库影响力分级实施，不搞一刀切。

5. **默认开放** — 仓库默认 public，Issues 默认开启，Discussion 鼓励启用。除非有明确的保密需求，否则信息应公开透明。

### 1.4 术语定义

| 术语 | 定义 |
|------|------|
| **活跃仓库** | 未被归档的仓库 |
| **核心仓库** | Stars ≥ 50 的仓库 |
| **关注仓库** | Stars ≥ 20 的仓库 |
| **僵尸仓库** | 连续 180 天无 git 推送的仓库 |
| **单人维护仓库** | 仅有 1 个写权限成员的仓库 |
| **OSI 批准许可证** | Open Source Initiative 认可的开源许可证列表中的许可证 |

---

## 二、三级准入体系

仓库按影响力（Stars）分为三级，逐级提升治理要求。

### 2.1 等级划分

| 等级 | 判定标准 | 仓库数量 | 治理强度 |
|:----:|----------|:-------:|:--------:|
| **L1 准入** | 所有活跃仓库 | 155 | 法律底线 + 可发现性 |
| **L2 健康** | Stars ≥ 20 | 38 | L1 + 安全底线 + 社区参与 |
| **L3 标杆** | Stars ≥ 50 | 17 | L2 + 工程卓越 + 社区运营 |

### 2.2 L1 — 准入门槛（所有活跃仓库必须满足）

| 序号 | 检查项 | 要求 | 严重程度 |
|:----:|--------|------|:--------:|
| L1-1 | LICENSE | 根目录存在 OSI 批准的 LICENSE 文件，推荐 Apache-2.0 | **阻断** |
| L1-2 | README.md | 包含项目简介、安装说明、基础使用示例 | **阻断** |
| L1-3 | 仓库描述 | GitHub Description 字段非空 | **警告** |
| L1-4 | 默认分支 | 必须为 `main` | **警告** |
| L1-5 | Issues 开启 | `has_issues=true` | **阻断** |
| L1-6 | 非归档 | `archived=false` | — |
| L1-7 | Topics 标签 | 至少 3 个 Topics 标签 | 建议 |

> **阻断项**：不满足则仓库不应存在于组织中。
> **警告项**：不满足需在 30 天内整改。
> **建议项**：鼓励满足，不强制。

### 2.3 L2 — 健康基准（Stars ≥ 20 仓库必须满足）

在 L1 基础上增加：

| 序号 | 检查项 | 要求 | 严重程度 |
|:----:|--------|------|:--------:|
| L2-1 | 分支保护 | require PR + ≥2 review + dismiss stale reviews | **阻断** |
| L2-2 | 贡献者冗余 | ≥2 名写权限成员 | **阻断** |
| L2-3 | SECURITY.md | 存在安全漏洞报告策略文件 | **阻断** |
| L2-4 | CONTRIBUTING.md | 存在贡献指南文件 | **阻断** |
| L2-5 | CODE_OF_CONDUCT.md | 存在行为准则文件 | **警告** |
| L2-6 | Dependabot | 启用 Dependabot alerts + security updates | **阻断** |
| L2-7 | PR Template | 存在 Pull Request 模板 | **警告** |
| L2-8 | Issue Template | 存在 Bug Report + Feature Request 模板 | 建议 |

### 2.4 L3 — 标杆标准（Stars ≥ 50 仓库应当满足）

在 L2 基础上增加：

| 序号 | 检查项 | 要求 | 严重程度 |
|:----:|--------|------|:--------:|
| L3-1 | CI/CD | lint + test 自动化工作流 | **阻断** |
| L3-2 | CodeQL | 代码安全扫描已启用 | **阻断** |
| L3-3 | Issue 标签体系 | type/*, priority/*, status/* 标签 | **警告** |
| L3-4 | Issue 响应 SLA | 首次响应 ≤7 天，关闭 ≤90 天 | **警告** |
| L3-5 | SemVer | 版本号遵循语义化版本规范 | **警告** |
| L3-6 | Changelog | 存在 CHANGELOG.md 或 Release Notes | 建议 |
| L3-7 | Discussions | GitHub Discussions 已启用 | 建议 |
| L3-8 | good-first-issue | 至少 1 个适合新贡献者的 Issue | 建议 |

---

## 三、仓库创建标准

> **详细建仓流程请参见 [建仓流程文档](./docs/建仓流程文档.md)**，本章仅列出核心要点。

### 3.1 新建仓库流程

```
建仓申请 → 审核 → 创建 → 初始化 → 验收
```

### 3.2 创建时自动配置清单

新建仓库应自动包含以下配置（由建仓流程 `repo_creator.py` 自动注入）：

- [ ] Apache-2.0 LICENSE 文件
- [ ] README.md（含项目简介 + 安装 + 快速开始）
- [ ] .github/ISSUE_TEMPLATE/bug_report.yml
- [ ] .github/ISSUE_TEMPLATE/feature_request.yml
- [ ] .github/ISSUE_TEMPLATE/config.yml
- [ ] .github/PULL_REQUEST_TEMPLATE.md
- [ ] .github/CODEOWNERS（PR 自动分配 Reviewer）
- [ ] .github/dependabot.yml
- [ ] .github/workflows/ci.yml（CI：lint → test → build）
- [ ] .github/workflows/triage-issue.yml（产品级）
- [ ] .github/workflows/status-transition.yml（产品级）
- [ ] .github/workflows/sync-to-gitcode.yml（产品级）
- [ ] 安全告警 + 自动修复（Dependabot alerts/fixes）
- [ ] 仓库描述（Description）
- [ ] 至少 3 个 Topics 标签
- [ ] 默认分支 `main`
- [ ] Issues 开启
- [ ] Squash merge 开启（默认）

### 3.3 命名规范

- 使用小写字母 + 连字符：`huaweicloud-sdk-python-v3`
- 避免与已有仓库名冲突
- SDK 命名：`huaweicloud-sdk-{语言}-{变体}`
- IoT 命名：`huaweicloud-iot-{类别}-sdk-{语言}`
- 工具/插件命名：`{功能}-{平台}`

### 3.4 可见性选择

| 场景 | 推荐可见性 |
|------|:----------:|
| SDK、工具、示例代码 | public |
| 内部文档、配置 | private |
| 实验性项目 | public（标注 experimental） |
| 包含敏感信息 | private |

---

## 四、维护与运营要求

### 4.1 仓库维护者职责

1. **Issue 响应**：7 天内首次响应新 Issue
2. **PR Review**：14 天内完成 PR Review
3. **安全漏洞**：按 SECURITY.md 中的 SLA 处理
4. **依赖更新**：Dependabot PR 在 30 天内合并或关闭
5. **季度检查**：每季度验证 L1/L2 标准合规状态

### 4.2 社区运营要求（L3 仓库）

1. **good-first-issue**：始终保留至少 1 个适合新贡献者的 Issue
2. **贡献者认可**：在 README 或 CONTRIBUTORS.md 中致谢贡献者
3. **Release 说明**：每次 Release 附带 Changelog
4. **Breaking Change 通知**：破坏性变更至少提前 30 天公告

### 4.3 许可证要求

| 项目类型 | 推荐 License |
|----------|-------------|
| SDK / 库 | Apache-2.0 |
| 工具 / CLI | Apache-2.0 或 MIT |
| 示例 / Demo | Apache-2.0 |
| 数据集 | CC-BY-4.0 |
| 文档 | CC-BY-4.0 |

**GPL 使用限制：** GPL 代码不得混入 Apache-2.0 项目，除非经过法务审查确认许可兼容性。现有 GPL 仓库需逐个评估许可迁移方案。

---

## 五、退出与归档机制

### 5.1 归档条件

满足以下**任一**条件，应启动归档流程：

| 条件 | 说明 |
|------|------|
| 连续 180 天无 git 推送 | 可能已停止维护 |
| 维护者确认停止维护 | 主动声明 |
| 已被其他仓库替代 | 功能合并/迁移 |
| 存在未修复 Critical 漏洞 >90 天 | 安全责任 |

### 5.2 归档流程

1. 联系仓库维护者确认
2. 若 7 天无响应，升级到组织管理员决策
3. 更新 README.md 添加归档声明：
   ```
   > ⚠️ 此项目已归档，不再维护。请查看 [替代方案]。
   ```
4. 执行 `gh repo archive huaweicloud/{repo}`
5. 在组织治理报告中记录

### 5.3 删除条件

满足以下**全部**条件，可考虑删除：

- Stars = 0 且 Forks = 0
- 超过 365 天无任何活动
- 维护者确认可以删除
- 组织管理员审批通过

> ⚠️ 删除前需备份，删除操作不可逆。

---

## 六、角色与职责

### 6.1 角色定义

| 角色 | 权限 | 职责 |
|------|------|------|
| **组织管理员** | 组织级 Owner | 制定治理政策、审批归档/删除、月度巡检 |
| **仓库 Owner** | 仓库 Admin | 仓库合规第一责任人、分支保护配置、安全漏洞响应 |
| **维护者** | 仓库 Write/Maintain | 日常维护、Issue/PR 处理、代码 Review |
| **贡献者** | Fork + PR | 提交代码/文档贡献 |
| **社区用户** | Read + Issue | 使用项目、反馈问题 |

### 6.2 组织管理员职责（OSPO 职能）

1. 维护 `.github` 组织仓库中的模板和规范
2. 执行月度治理巡检，产出巡检报告
3. 违规仓库的跟踪和整改督促
4. 新建仓库的审核和初始化
5. 组织级安全事件的协调

### 6.3 仓库 Owner 承诺

成为仓库 Owner 即表示承诺：

1. 确保仓库满足 L1 准入标准
2. 仓库 Stars ≥ 20 后，60 天内升级到 L2 标准
3. 仓库 Stars ≥ 50 后，90 天内升级到 L3 标准
4. 按 SLA 处理 Issue 和安全漏洞
5. 停止维护时主动发起归档流程

---

## 七、合规检查与度量

### 7.1 检查频率

| 检查类型 | 频率 | 覆盖范围 | 执行方式 |
|----------|------|----------|----------|
| 新建仓库检查 | 实时（仓库创建时） | 新建仓库 | 建仓脚本自动 |
| 月度巡检 | 每月 1 日 | 所有活跃仓库 | governance-audit.yml |
| 季度深度审计 | 每季末 | L2 + L3 仓库 | 人工 + 脚本 |
| 即时检查 | 按需 | 特定仓库 | `gh api` |

### 7.2 核心指标（KPI）

| 指标 | 当前值 | L1 目标 | L2 目标 |
|------|:-----:|:------:|:------:|
| License 覆盖率 | 80.0% | **100%** | 100% |
| 分支保护率（L2仓库） | ~7% | — | **100%** |
| 单人维护率 | 43.2% | — | ≤10% |
| 社区文件均分 | 0.98/6 | — | ≥3/6 |
| Security 告警(Critical) | 135 | — | ≤10 |
| Issue 首次响应（中位） | — | — | ≤7天 |

### 7.3 违规处理流程

```
巡检发现违规 → 自动创建 Issue（标注 priority/high）→ @mention 仓库 Owner
    ↓
7 天未响应 → 升级到组织管理员
    ↓
30 天未整改（阻断项）→ 组织管理员强制执行
    ↓
60 天未整改 → 启动归档流程
```

### 7.4 豁免机制

以下情况可申请临时豁免：

- 私人仓库（Free plan 不支持分支保护）：自动豁免 L2-1
- 镜像仓库：自动豁免 Issue/PR 相关项
- 有明确替代方案的特殊场景：需提交豁免申请，组织管理员审批

豁免需在仓库 README 或 .github/GOVERNANCE.md 中明确标注豁免项及原因。

---

## 八、附录

### 附录 A：检查清单（快速参考）

#### 新建仓库检查清单

```
[ ] LICENSE 文件（Apache-2.0）
[ ] README.md（项目简介 + 安装 + 使用示例）
[ ] 仓库描述（Description）
[ ] Topics 标签（≥3个）
[ ] 默认分支 = main
[ ] Issues 已开启
[ ] .github/ISSUE_TEMPLATE/（bug_report + feature_request + config）
[ ] .github/PULL_REQUEST_TEMPLATE.md
[ ] .github/dependabot.yml
```

#### 存量仓库升级到 L2 检查清单

```
[ ] 分支保护（require PR + 1 review）
[ ] 添加≥1名额外写权限成员
[ ] SECURITY.md
[ ] CONTRIBUTING.md
[ ] CODE_OF_CONDUCT.md
[ ] 启用 Dependabot
[ ] PULL_REQUEST_TEMPLATE.md
```

### 附录 B：许可证选择指南

| 场景 | 推荐 | 备选 |
|------|------|------|
| 通用 SDK / 库 | Apache-2.0 | MIT |
| 强 Copyleft 需求 | GPL-3.0 | — |
| 宽松许可 | MIT | BSD-3-Clause |
| Mozilla 系项目 | MPL-2.0 | — |
| 数据集 | CC-BY-4.0 | CC0-1.0 |
| 文档 | CC-BY-4.0 | — |

### 附录 C：相关资源

- GitHub 社区健康文件文档：https://docs.github.com/en/communities
- OpenSSF Scorecard：https://securityscorecards.dev
- OSI 批准许可证列表：https://opensource.org/licenses
- 语义化版本规范：https://semver.org/lang/zh-CN
- Conventional Commits：https://www.conventionalcommits.org
- 贡献者公约：https://www.contributor-covenant.org

### 附录 D：模板文件索引

所有组织级模板位于 `huaweicloud/.github` 仓库：

| 文件路径 | 用途 |
|----------|------|
| `LICENSE` | 默认许可证（Apache-2.0） |
| `CONTRIBUTING.md` | 组织级贡献指南 |
| `SECURITY.md` | 安全漏洞报告策略 |
| `CODE_OF_CONDUCT.md` | 贡献者行为准则 |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | Bug 报告表单 |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | 功能请求表单 |
| `.github/ISSUE_TEMPLATE/config.yml` | Issue 配置 |
| `.github/PULL_REQUEST_TEMPLATE.md` | PR 模板 |
| `.github/dependabot.yml` | 依赖更新配置 |
| `.github/workflows/stale.yml` | 过期 Issue/PR 自动清理 |
| `.github/workflows/governance-audit.yml` | 月度治理巡检 |

---

> *本文档由 Hermes Agent 起草，待 TMG（技术管理组）评审后正式生效。*
> *生效后，所有新增仓库必须满足 L1 标准。存量仓库按本规范第八条的分级时间表逐步达标。*
