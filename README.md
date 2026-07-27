# Email Agent - 智能邮件助手

基于 Claude API 构建的智能邮件助手，支持邮件分类、待办提取与报告生成。以「自研 Agent 循环」为核心，实现工具编排、上下文记忆、人机协同与角色自动识别。

---

## 快速开始

### 环境要求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip

### 安装

```bash
git clone <repo-url>
cd "Email Agent"

# 使用 uv 创建环境并安装
uv sync
# 如使用 pip:
pip install -e .
```

### 配置

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml`，填入必要信息：

- `email.address` / `email.password` — 你的 163 邮箱地址与 SMTP/IMAP 授权码
- `claude.api_key` — 你的 Claude API Key
- `profile` — 可留空，首次运行 `email-agent setup` 会自动检测

### 首次运行

```bash
email-agent setup
```

该命令会自动连接你的邮箱，分析最近 30 天的邮件元数据（发件人域名与主题），由 Claude 推断你的角色（打工人 / 求职者 / 高校导师），并保存到配置中。

---

## 命令参考

### `setup` — 首次配置与角色检测

自动连接邮箱、拉取最近 30 天邮件元数据，由 Claude 推断用户角色。

```bash
email-agent setup
```

检测到的角色：

| 角色 | 分类标签 |
|------|----------|
| `worker`（打工人） | work, personal, newsletter, notification |
| `jobseeker`（求职者） | 面试邀请, 笔试通知, Offer通知, 拒信, 薪资谈判, 投递确认, 其他 |
| `professor`（高校导师） | 学生自荐, 课题合作, 会议邀请, 审稿邀请, 行政通知, 论文相关, 其他 |

### `check` — 处理未读邮件

拉取所有未读邮件，逐一分类并提取待办事项。

```bash
email-agent check
email-agent check --dry-run     # 预览模式，不实际调用 API
email-agent check --verbose      # 详细输出
```

### `scan` — 按时间段筛选邮件

拉取指定时间段的邮件（含已读），分类后生成时间段报告。

```bash
email-agent scan --from 2026-07-01 --to 2026-07-27
email-agent scan --week          # 本周
email-agent scan --week --dry-run
```

### `report` — 生成报告

基于数据库中已有邮件数据，生成日报或周报。

```bash
email-agent report               # 日报（今天）
email-agent report --week        # 周报（本周）
email-agent report --from 2026-07-01 --to 2026-07-07
```

### `daemon` — 后台守护进程

持续运行，定时检查未读邮件并自动生成日报。

```bash
email-agent daemon --interval 300 --report-at 20:00
```

### `help` — 查看帮助

```bash
email-agent help
```

---

## 架构概览

```
┌──────────────────────────────────────────────┐
│                Agent 核心                     │
│  ┌────────────┐  ┌───────────┐  ┌─────────┐ │
│  │ Agent 循环  │  │ Tool 编排 │  │ 上下文   │ │
│  │ turn-based │  │ registry  │  │ 组装     │ │
│  │ tool-use   │  │ singleton │  │ 发件人   │ │
│  │ 最大轮次   │  │ 动态注册  │  │ 历史     │ │
│  │ 强制终止   │  │           │  │ 待办查询 │ │
│  └────────────┘  └───────────┘  └─────────┘ │
├──────────────────────────────────────────────┤
│                工具层 (Tools)                 │
│  ┌───────────────────┐  ┌─────────────────┐  │
│  │ classify_email    │  │ extract_todos   │  │
│  │ 邮件分类 + 优先级  │  │ 待办提取 + 存储  │  │
│  ├───────────────────┤  ├─────────────────┤  │
│  │ search_by_date    │  │ generate_report │  │
│  │ 按日期拉取 + 缓存  │  │ 日报/周报/扫描   │  │
│  ├───────────────────┤  ├─────────────────┤  │
│  │ fetch_unread      │  │ get_sender_     │  │
│  │ 拉取未读 + 去重   │  │ history         │  │
│  └───────────────────┘  │ 发件人历史查询   │  │
│                         ├─────────────────┤  │
│                         │ get_pending_    │  │
│                         │ tasks           │  │
│                         │ 待办列表查询    │  │
│                         └─────────────────┘  │
├──────────────────────────────────────────────┤
│               记忆层 (Memory)                 │
│  ┌──────────────┐ ┌─────────┐ ┌───────────┐ │
│  │ 已处理邮件   │ │ 待办事项 │ │ 跳过记录  │ │
│  │ processed_   │ │ tasks   │ │ skipped_   │ │
│  │ emails       │ │         │ │ emails     │ │
│  └──────────────┘ └─────────┘ └───────────┘ │
│  SQLite 存储  |  发件人历史索引  |  报告归档 │
├──────────────────────────────────────────────┤
│              邮件适配层 (Email)               │
│  ┌──────────────────────────────────────┐    │
│  │ EmailAdapter (ABC)                   │    │
│  │ ├─ IMAPAdapter                       │    │
│  │ │  ├─ search_unseen / search_by_date │    │
│  │ │  ├─ fetch_header / fetch_full      │    │
│  │ │  └─ MIME 解码 + HTML 转纯文本      │    │
│  │ └─ 可扩展: Graph API / JMAP / POP3   │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

### 核心设计点

**自研 Agent 循环** — 不走 LangChain 等框架，从零实现 turn-based 工具调用循环：Claude 返回 `tool_use` 时，Agent 执行本地工具并将结果回传；返回 `end_turn` 时退出。支持 `max_turns` 上限与强制终止，防止无限循环。

**工具编排** — 所有工具通过 `ToolRegistry` 单例管理，提供 Anthropic 格式的 tool definition 与 handler 函数。工具在 CLI 启动时按需注册（`classify_email`、`extract_todos`、`generate_report` 为常驻工具；`fetch_unread_emails`、`search_by_date` 等 IMAP 工具需要 adapter 实例，按命令动态注册）。

**记忆系统** — 基于 SQLite 的四表设计（`processed_emails`、`tasks`、`skipped_emails`、`reports`），持久化所有处理结果。Agent 在分类每封邮件前自动查询发件人历史与当前待办，作为上下文注入 system prompt 旁的 user message 中，实现「记忆增强推理」。

**人机协同 (Human-in-the-Loop)** — `setup` 命令的角色检测结果需用户确认后才写入配置；`check --dry-run` 预估耗时和 API 费用后不执行，由用户决定是否真正调用。

**角色自动检测** — 拉取用户最近邮件的发件人域名与主题（不含正文，保护隐私），由 Claude 分析邮件模式推断角色（打工人/求职者/高校导师），每种角色对应不同的分类标签体系。

---

## 技术栈

| 层次 | 技术 |
|------|------|
| 语言 | Python 3.12+ |
| LLM | Claude (via `anthropic` SDK)，默认 model: `claude-sonnet-5` |
| 邮件协议 | IMAP4_SSL（163 邮箱），MIME 解码，HTML 转纯文本 |
| 存储 | SQLite3（`processed_emails`、`tasks`、`skipped_emails`、`reports` 四表） |
| 配置 | YAML + 环境变量覆盖 |
| CLI | `argparse`（`email-agent` console script，6 个子命令） |
| 包管理 | `uv` + `hatchling` |
| 测试 | `pytest` + `pytest-asyncio` |
| 代码检查 | `ruff`（E, F, I, N rules） |

---

## 配置

配置文件 `config.yaml`（或 `~/.email-agent/config.yaml`）：

```yaml
# 角色: worker | jobseeker | professor（留空则首次运行自动检测）
profile: ""

# 163 邮箱 IMAP/SMTP
email:
  imap_server: "imap.163.com"
  imap_port: 993
  smtp_server: "smtp.163.com"
  smtp_port: 465
  address: "your-email@163.com"
  password: "your-smtp-auth-code"    # SMTP 授权码，非登录密码

# Claude API
claude:
  api_key: "sk-ant-..."
  model: "claude-sonnet-5"           # 可选，见 anthropic SDK 支持的模型

# Agent 设置
agent:
  max_turns: 5                       # 每封邮件最大 tool-use 轮次

# 守护进程
daemon:
  check_interval: 300                # 检查间隔（秒）
  report_at: "20:00"                 # 日报生成时间

# 数据库
memory:
  db_path: "data/email_agent.db"
```

### 环境变量覆盖

所有敏感字段支持环境变量覆盖（优先级高于 YAML 文件）：

```bash
export EMAIL_AGENT_CLAUDE_API_KEY="sk-ant-..."
export EMAIL_AGENT_EMAIL_ADDRESS="your-email@163.com"
export EMAIL_AGENT_EMAIL_PASSWORD="your-auth-code"
export EMAIL_AGENT_PROFILE="worker"
```

---

## 开发

### 项目结构

```
Email Agent/
├── src/email_agent/
│   ├── agent/
│   │   ├── core.py              # Agent 主循环
│   │   └── tools/
│   │       ├── registry.py      # 工具注册中心（单例）
│   │       ├── classify.py      # 邮件分类工具
│   │       ├── extract_todos.py # 待办提取工具
│   │       ├── report.py        # 报告生成工具
│   │       ├── fetch.py         # 未读拉取工具
│   │       └── scan_fetch.py    # 日期搜索 + 查询工具
│   ├── email/
│   │   ├── base.py              # EmailAdapter 抽象接口
│   │   └── imap_.py             # IMAP 实现
│   ├── memory/
│   │   ├── models.py            # 数据模型 (Email, ProcessedEmail, Task, etc.)
│   │   └── store.py             # SQLite MemoryStore
│   ├── llm/
│   │   └── client.py            # Claude API 客户端（含重试逻辑）
│   ├── prompts/
│   │   ├── system.py            # 系统提示词构建器
│   │   └── tools.py             # 工具提示词模板
│   ├── config.py                # 配置加载与校验
│   └── cli.py                   # CLI 入口（6 个子命令）
├── tests/
│   ├── test_agent_core.py       # Agent 循环测试
│   ├── test_models.py           # 数据模型测试
│   ├── test_store.py            # 存储层测试
│   ├── test_email_adapter.py    # 邮件适配器测试
│   └── test_tools/              # 工具测试（预留）
├── pyproject.toml
├── config.yaml.example
└── README.md
```

### 运行测试

```bash
# 全部测试
uv run pytest tests/ -v

# 仅运行指定文件
uv run pytest tests/test_agent_core.py -v

# 带覆盖率（需安装 pytest-cov）
uv run pytest tests/ -v --cov=email_agent
```

### 代码检查

```bash
uv run ruff check src/
uv run ruff check src/ --fix     # 自动修复
```

### 运行

```bash
# 使用 uv run 直接执行
uv run email-agent help

# 或激活虚拟环境后
email-agent check --dry-run
```
