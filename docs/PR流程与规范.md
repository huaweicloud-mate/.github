# huaweicloud-mate PR 流程与规范

## 完整流程

```
Issue 创建
    ↓
Issue Bot → 自动分类打标签 + 分配负责人 + 邮件通知
    ↓
创建 Feature Branch → git checkout -b feat/xxx
    ↓
开发 → commit + push
    ↓
New Pull Request (Fixes #N)
    ↓
┌─────────────────────────────────────────────┐
│ CI 自动触发                                  │
│   ├── lint : 代码风格检查                     │
│   ├── test : 自动化测试                       │
│   └── build : 构建验证                        │
│                                              │
│ Status Transition 自动触发                    │
│   └── Issue 标记 status/in-progress          │
│                                              │
│ CODEOWNERS 自动分配 Reviewer                 │
│                                              │
│ 需要 2 人 Approve                             │
│   ├── 新 commit 后旧 Approve 失效              │
│   └── Code Owner 必须 Review                  │
│                                              │
│ Conversation 必须 Resolve                     │
└─────────────────────────────────────────────┘
    ↓
CI 全绿 + 2 Approve + 对话 Resolve
    ↓
Merge PR
    ↓
Issue 自动关闭 → status/resolved
```

---

## 一、PR 标准配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **CI Pipeline** | lint → test → build | .github/workflows/ci.yml |
| **需 Approve 数** | 2 人 | 不能自己 approve 自己 |
| **Code Owner Review** | 必须 | CODEOWNERS 中指定的人必须审批 |
| **过期 Review 作废** | 开启 | push 新 commit 后旧 approve 失效 |
| **Conversation Resolve** | 必须 | 所有评论对话必须解决 |
| **Branch 必须最新** | strict 模式 | 合并前自动检查是否 behind main |
| **强制推送** | 禁止 | `git push -f` 被阻止 |
| **分支删除** | 禁止 | 无法删除 main 分支 |
| **直接 push main** | 禁止 | 必须通过 PR |
| **签名提交** | 暂时关闭 | 后续为 bot 配置 GPG 后开启 |

---

## 二、CI Pipeline（.github/workflows/ci.yml）

```
pull_request → main 分支
    ↓
┌───────┐    ┌───────┐    ┌───────┐
│ lint  │ → │ test  │ → │ build │
└───────┘    └───────┘    └───────┘
```

| Job | 作用 | 配置方式 |
|-----|------|---------|
| `lint` | 代码风格/格式检查 | 按语言选择工具：Python→ruff，JS→eslint，Go→golangci-lint |
| `test` | 自动化测试 | Python→pytest，JS→npm test，Go→go test |
| `build` | 构建验证 | Python→pip install，JS→npm build，Go→go build |

任一阶段失败，整个 CI 标红，无法合并。

### 各语言 CI 模板

**Python**
```bash
pip install ruff pytest
ruff check .
pytest
```

**JavaScript/TypeScript**
```bash
npm ci
npx eslint .
npm test
npm run build
```

**Go**
```bash
golangci-lint run ./...
go test ./...
go build ./...
```

---

## 三、Review 规范

### 谁可以 Review

| 角色 | 权限 |
|------|------|
| 组织成员 | 可以 Approve / Request Changes / Comment |
| Code Owner | 必须 Review（合并前必须审批） |
| PR 作者 | 不能 approve 自己 |

### Review 状态

| 状态 | 说明 |
|------|------|
| `REVIEW_REQUIRED` | 尚未满足 2 人 approve |
| `APPROVED` | 已满足条件，等待 CI 通过 |
| `CHANGES_REQUESTED` | 有人要求修改，需重新 review |
| `DISMISSED` | push 新 commit 后旧 approve 失效 |

### Review 操作

1. 打开 PR 页面 → **Files changed** 标签
2. 检查代码变更
3. 点击绿色 **Review changes** 按钮
4. 选择：
   - **Comment** — 一般评论
   - **Approve** — 批准
   - **Request changes** — 要求修改
5. 填写评论后 **Submit review**

### Approve 失效规则

PR 作者 push 新 commit 后，所有已有 Approve 自动失效，需要重新审批。

---

## 四、CODEOWNERS

`.github/CODEOWNERS` 文件定义代码所有者：

```codeowners
# 全局默认 reviewer
* @shuangheaven

# 按目录分配
/api/          @shuangheaven
/frontend/     @shuangheaven
/docs/         @shuangheaven
/.github/      @shuangheaven
```

创建 PR 时 CODEOWNERS 自动被请求 review。

---

## 五、Issue 与 PR 联动

| PR 操作 | Issue 变化 |
|---------|-----------|
| 创建 PR，描述含 `Fixes #N` | Issue 标记 `status/in-progress` |
| 合并 PR | Issue 自动关闭 + 标记 `status/resolved` |

### 支持的关闭关键词

```
close #19  closes #19  closed #19
fix #19    fixes #19   fixed #19
resolve #19 resolves #19 resolved #19
```

---

## 六、提交规范

### Commit Message 格式

```
<type>: <简短描述>

<type> 可选值：
  feat     : 新功能
  fix      : 修复 bug
  docs     : 文档变更
  style    : 代码格式（不影响功能）
  refactor : 重构
  test     : 测试相关
  chore    : 构建/工具变更
  ci       : CI 配置变更
```

示例：
```
docs: add Chinese quickstart to README
fix: resolve API timeout issue
feat: add user login module
```

### 签名提交（后续启用）

```
git config --global user.signingkey <KEY_ID>
git commit -S -m "feat: xxx"
```

---

## 七、不能合并的情况

| 原因 | 表现 |
|------|------|
| CI 未通过 | `lint`/`test`/`build` 任一项标红 |
| Approve 不足 | 需 2 人，当前 0-1 人 |
| Code Owner 未 review | 指定目录的代码所有者未审批 |
| 对话未解决 | 有未 resolve 的 conversation |
| Branch 过期 | 需要 rebase main |
| Approve 失效 | push 了新 commit 需重新审批 |
| 签名缺失 | （暂未启用） |

---

## 八、PR 模板

组织级模板位于 `.github/PULL_REQUEST_TEMPLATE.md`，创建 PR 时自动填充。建议包含：

```markdown
## 变更说明
<!-- 描述做了什么改动 -->

## 关联 Issue
Fixes #N

## 测试
- [ ] 单元测试通过
- [ ] 手动测试通过

## Checklist
- [ ] 代码符合规范
- [ ] 已更新相关文档
- [ ] CI 通过
```

---

## 九、快速操作命令

```powershell
# 创建 Issue
gh issue create -R huaweicloud-mate/<repo> --title "title" --body "body"

# 创建 PR（描述中关联 Issue）
gh pr create -R huaweicloud-mate/<repo> --title "feat: xxx" --body "Fixes #N" --base main

# 查看 PR 状态
gh pr view <N> -R huaweicloud-mate/<repo> --json mergeStateStatus,reviewDecision

# 查看 CI 检查
gh pr checks <N> -R huaweicloud-mate/<repo>

# Approve PR
gh pr review <N> -R huaweicloud-mate/<repo> --approve

# 合并 PR（满足条件时）
gh pr merge <N> -R huaweicloud-mate/<repo> --merge --delete-branch

# 强制合并（管理员，跳过等待）
gh pr merge <N> -R huaweicloud-mate/<repo> --merge --admin --delete-branch
```
