# Email Agent 设计文档

> 日期: 2026-07-27  
> 状态: 待用户审核  
> 目标: 2-4 周内完成 MVP，用于个人简历 Agent 开发工程师岗位

---

## 1. 概述

### 1.1 项目定位

一个自建 Agent 循环的智能邮件助手，不依赖 LangChain 等框架。核心逻辑全部手写，用于展示 Agent 开发工程师的核心能力：Agent 循环设计、工具编排、记忆系统、人在回路、错误处理。

### 1.2 一句话描述

每日自动处理未读邮件：分类优先级、提取待办事项、生成日报/周报。角色模板支持打工人、求职者、高校导师三种场景，Agent 首次运行自动推断角色并经用户确认后锁定。

### 1.3 技术栈

| 类别 | 选择 |
|------|------|
| 语言 | Python 3.12+ |
| LLM | Claude API (claude-sonnet-5) |
| 包管理 | uv |
| 邮箱协议 | IMAP/SMTP (163 邮箱) |
| 存储 | SQLite |
| Lint/Format | ruff |
| 测试 | pytest |

---

## 2. 项目结构

```
email-agent/
├── pyproject.toml
├── config.yaml.example
├── README.md
│
├── src/
│   └── email_agent/
│       ├── __init__.py
│       ├── cli.py                      # CLI 入口 (argparse 子命令)
│       ├── config.py                   # 配置加载 (env var + config.yaml)
│       │
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── core.py                 # Agent 主循环 (perceive→think→act→observe)
│       │   └── tools/
│       │       ├── __init__.py
│       │       ├── registry.py         # Tool 注册中心
│       │       ├── fetch.py            # 拉取未读邮件 + 去重
│       │       ├── scan_fetch.py       # 按时间段拉取全部邮件（含已读）
│       │       ├── classify.py         # 分类 + 优先级
│       │       ├── extract_todos.py    # 提取待办事项
│       │       └── report.py           # 生成日报/周报/扫描报告
│       │
│       ├── email/
│       │   ├── __init__.py
│       │   ├── base.py                 # 抽象邮件适配器接口
│       │   └── imap_.py               # IMAP/163 实现
│       │
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── store.py                # SQLite 操作封装
│       │   └── models.py              # 数据模型 (dataclass)
│       │
│       ├── llm/
│       │   ├── __init__.py
│       │   └── client.py              # Claude API 封装
│       │
│       └── prompts/
│           ├── __init__.py
│           ├── system.py               # Agent System Prompt (根据 profile 动态生成)
│           └── tools.py                # 各 tool 的 prompt 模板
│
└── tests/
    ├── __init__.py
    ├── conftest.py                     # 共享 fixtures (MockClaude, sample emails)
    ├── test_agent_core.py
    ├── test_tools/
    ├── test_email_adapter.py
    └── test_memory.py
```

---

## 3. Agent 核心循环

### 3.1 循环模型

```
PERCEIVE → THINK → ACT → OBSERVE → (循环)
```

### 3.2 单封邮件处理流程

1. **PERCEIVE**: IMAP 拉取所有未读邮件，基于 Message-ID 去重（已存在于 `processed_emails` 表的跳过）
2. **THINK**: 将邮件 + 发件人历史 + 当前待办列表作为 context 发送给 Claude，Claude 决定调用哪些 tool
3. **ACT**: 执行 Claude 请求的 tool 调用（classify_email / extract_todos 等），结果返回 Claude
4. **OBSERVE**: tool 执行结果写入 SQLite，统计本轮处理数据，输出到终端

### 3.3 Stop Condition

| 优先级 | 条件 | 行为 |
|--------|------|------|
| 1 | Claude 返回 `stop_reason != "tool_use"` | 处理完成，结束 |
| 2 | Claude 调用了 tool | 执行 tool → 结果送回 Claude → 继续 |
| 3 | 达到 `MAX_TURNS = 5` | 强制终止，已执行的 tool 结果保留，记 warning 日志 |

### 3.4 Claude API 调用参数

| 参数 | 值 | 原因 |
|------|-----|------|
| model | claude-sonnet-5 | 分类和提取任务性价比最优 |
| max_tokens | 1024 | tool 调用的输出短，不需要更多 |
| temperature | 0 | 分类需要确定性输出 |
| tools | 动态注册 | 通过 registry 注入 |

---

## 4. PERCEIVE 去重策略

### 4.1 核心原则

用 **Message-ID**（RFC 5322 全球唯一标识）做主键去重，不用 UID。

**为什么不用 UID**：
- 邮件移动到其他文件夹再移回来，UID 会变
- 多设备同步场景下不可靠

### 4.2 去重流程

```
IMAP SEARCH UNSEEN → 取每封的 Message-ID 头
                           │
                  ┌────────┴────────┐
                  │ 已存在于 DB？    │
                  ├────────┬────────┤
                  │ YES    │ NO     │
                  ▼        ▼        │
                跳过     标记"需处理"
                                   │
                                   ▼
                         处理完成 → INSERT 到 processed_emails
```

### 4.3 SQLite 索引

```sql
CREATE INDEX idx_processed_sender
ON processed_emails(sender_email, received_at DESC);
```

当前数据量小（< 1000 条），索引不是性能必需，但作为设计规范列出，展示对数据增长的考量。

---

## 5. Memory 系统

### 5.1 数据模型

```sql
-- 已处理的邮件
CREATE TABLE processed_emails (
    message_id TEXT PRIMARY KEY,
    uid INTEGER,
    sender_email TEXT NOT NULL,
    sender_name TEXT,
    subject TEXT,
    received_at TIMESTAMP,
    category TEXT,               -- 分类标签（根据 profile 变化）
    priority TEXT,               -- urgent / high / normal / low
    summary TEXT,                -- Claude 一句话摘要
    classification_reason TEXT   -- 分类依据
);

-- 待办事项
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    source_email_id TEXT,        -- 关联邮件
    due_date TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 跳过的邮件
CREATE TABLE skipped_emails (
    message_id TEXT PRIMARY KEY,
    uid INTEGER,
    sender_email TEXT,
    subject TEXT,
    reason TEXT,                 -- 跳过原因
    skipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 邮件报告
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,                   -- daily / weekly
    period_start TEXT,
    period_end TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2 Claude Context 注入

处理每封邮件时，注入以下上下文：

1. 当前邮件（发件人、主题、正文）
2. 该发件人历史（最近 10 封 + 统计：频次、优先级分布）
3. 当前 pending 待办列表

格式为可读的自然语言摘要，而非原始 SQL 行。

### 5.3 为什么 MVP 不加 Vector Store

当前场景是结构化分类 + 提取，不需要语义搜索。SQLite 完全满足。如果后续需要语义检索（例如"找出所有和 Q3 预算相关的邮件"），通过抽象接口扩展即可。

---

## 6. 角色自动检测

### 6.1 流程

```
email-agent setup

    ↓
拉取最近 50 封邮件元数据（只读 sender + subject，不读正文）
    ↓
Claude 分析发件人域名和主题模式 → 推断角色 + 理由
    ↓
Agent 输出推断：
  "根据最近邮件分析，你的角色很可能是【求职者】。
   证据：5 家公司的 HR 邮箱 + 3 封笔试/面试通知。
   对吗？[Y/n]"
    ↓
用户确认 Y → 写入 config.yaml → 锁定角色
```

### 6.2 支持的角色

| 角色 | 分类标签 | 待办触发词 |
|------|----------|-----------|
| worker | work, personal, newsletter, notification | 提交、回复、确认、审批 |
| jobseeker | 面试邀请, 笔试通知, Offer通知, 拒信, 其他 | 面试时间、笔试链接、回复确认、补充材料 |
| professor | 学生自荐, 课题合作, 会议邀请, 审稿邀请, 行政通知 | 附上简历、约面谈、审稿截止、会议注册 |

### 6.3 设计要点

- **隐私优先**: setup 阶段只读元数据，不读正文
- **可解释**: 推断附带证据链
- **人在回路**: 用户确认后才锁定，不做不可逆决策
- **防漂移**: 锁定后角色写入配置文件，运行时不再自动变更

---

## 7. CLI 命令

### 7.1 `email-agent setup`

首次运行，自动检测角色。

### 7.2 `email-agent check`

```bash
email-agent check              # 处理所有未读邮件
email-agent check --dry-run    # 只统计，不处理
email-agent check --verbose    # 显示每封邮件的详细处理过程
```

执行流程：拉取 → 去重 → 全部逐封处理 → 输出汇总 + 跳过报告。

Agent 处理完成后主动查询 `skipped_emails` 表，在终端输出中告知用户哪些邮件无法处理及原因：

```
✅ 处理完成：8/9 封成功

⚠️ 1 封无法处理:
  📧 newsletter@corp.com "=?GBK?B?..."
     → 原因: 邮件编码无法解析（GBK 乱码），正文为空
     → 建议: 在网页端查看原文
```

### 7.3 `email-agent report`

```bash
email-agent report                     # 日报
email-agent report --week              # 周报
email-agent report --from 2026-07-21 --to 2026-07-27
```

从 memory 查询时间范围内的邮件 → Claude 生成报告 → 存储到 reports 表 → 终端输出。

### 7.4 `email-agent scan`

```bash
email-agent scan --week                           # 本周全部邮件（含已读）
email-agent scan --from 2026-07-01 --to 2026-07-27 # 指定范围
email-agent scan --dry-run                        # 只统计，不调 Claude
```

执行流程：

1. IMAP `SEARCH ALL SINCE <from> BEFORE <to>` 拉取全部邮件
2. 每封邮件检查 Message-ID 是否已在 `processed_emails` 中
3. 已处理 → 直接复用 memory 中的分类/优先级/摘要
4. 未处理 → Agent 逐封分类 + 提取待办
5. Claude 综合全部数据生成报告，存储到 `reports` 表

报告内容包含：分类分布、优先级分布、未回复但可能需要关注的邮件列表、发件人 Top 统计。

### 7.5 `email-agent daemon`

```bash
email-agent daemon --interval 300 --report-at 20:00
```

后台持续运行，每 5 分钟执行一次 check，每天 20:00 自动生成日报。

### 7.6 `email-agent help`

```bash
email-agent help
```

输出命令列表、用法说明和使用示例。比 argparse 自带的 `--help` 更友好，包含典型使用场景的完整示例。

---

## 8. Tool 清单

| Tool | 作用 | 关键参数 |
|------|------|----------|
| `fetch_unread_emails` | IMAP 拉取未读 + Message-ID 去重 | — |
| `search_by_date` | 按时间段拉取全部邮件（含已读） | since, before |
| `classify_email` | 分类 + 优先级标记 | uid, category, priority, reason |
| `extract_todos` | 从邮件正文提取待办 | uid, todos[{content, due_date?, source_line}] |
| `get_sender_history` | 查询发件人历史 | sender_email |
| `get_pending_tasks` | 获取未完成待办列表 | — |
| `generate_report` | 生成日报/周报/扫描报告 | type, period_start, period_end |

---

## 9. 错误处理

### 9.1 三级分类

| 级别 | 场景 | 策略 |
|------|------|------|
| 可恢复 | Claude API 超时、IMAP 断连 | 重试 3 次，指数退避 (1s → 2s → 4s) |
| 可跳过 | 邮件编码损坏、正文为空 | 写入 skipped_emails，Agent 主动汇总报告 |
| 致命 | config.yaml 缺失、密码错误 | 立即退出，输出修复指引 |

### 9.2 Skipped Emails 主动报告

Agent 每轮 check 完成后主动查询 `skipped_emails` 表，在输出中告知用户。

区分两种跳过类型：
- **encoding_error（纯技术问题）**: 直接汇总输出，不调 Claude
- **agent_failed（处理异常）**: 让 Claude 重新分析并解释原因

---

## 10. 测试策略

### 10.1 测试金字塔

| 层级 | 测试内容 | Mock 范围 | 数量 |
|------|----------|-----------|------|
| 单元 | Agent loop 逻辑、Tool 函数、Memory CRUD、去重 | Claude API + IMAP | 最多 |
| 集成 | Agent + Mock IMAP + 真实 Claude（分类和提取质量验证） | IMAP 连接 | 中等 |
| E2E | 真实 163 → Claude → SQLite 完整链路 | 不 Mock | 手动 |

### 10.2 单元测试覆盖重点

- Agent stop condition 三种情况
- Tool 执行结果正确传回 Claude
- Message-ID 去重
- 发件人历史查询按时间倒序
- MAX_TURNS 上限生效

### 10.3 集成测试覆盖重点

- 种子邮件集（urgent/正常/垃圾、带待办/不带待办）
- 语义断言：验证分类准确率和待办提取召回率
- 集成测试不在 CI 中跑（消耗 API token）

---

## 11. 面试叙事线

本项目在面试中的核心叙事结构：

1. **痛点**: 每天处理邮件耗时，信息过载
2. **架构**: 自建 Agent 循环，不依赖框架，四层模块（Agent Core / Tools / Memory / Email Adapter）
3. **工具编排**: Agent 自主决策调用哪个 tool，人在回路把控关键操作
4. **记忆系统**: SQLite 存储 + Context 注入，让 Agent 有"发件人画像"能力
5. **角色检测**: setup 阶段自动推断用户角色，有证据链有确认步骤
6. **错误处理**: 三级分类 + 主动报告跳过邮件
7. **效果数据**: 日均处理 X 封，准确率 X%，日均节省 X 分钟

---

## 12. 不做的

- 不自动发送邮件（只读不写，安全第一）
- 不做向量检索（MVP 不需要，做了反而要解释为什么做）
- 不做 Web Dashboard（CLI 聚焦核心能力）
- 不做多 Agent 协作（单 Agent + 多 Tool 已经足够展示深度）
