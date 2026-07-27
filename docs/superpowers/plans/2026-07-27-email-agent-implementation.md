# Email Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained CLI email agent that processes email via IMAP, uses Claude API for classification/todo extraction/reporting, and stores results in SQLite.

**Architecture:** Four-layer design — Agent Core (perceive→think→act→observe loop), Tools (registry + individual tool modules), Memory (SQLite store + data models), Email Adapter (abstract interface + IMAP implementation). All Claude calls go through a thin LLM client wrapper. CLI uses argparse subcommands.

**Tech Stack:** Python 3.12+, uv, Claude API (claude-sonnet-5), SQLite, IMAP (imaplib), pytest, ruff

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Package metadata, dependencies, build config |
| `config.yaml.example` | Configuration template |
| `src/email_agent/__init__.py` | Package init |
| `src/email_agent/config.py` | Load and validate config from env vars + yaml |
| `src/email_agent/memory/models.py` | Dataclass definitions (ProcessedEmail, Task, etc.) |
| `src/email_agent/memory/store.py` | SQLite CRUD operations |
| `src/email_agent/llm/client.py` | Anthropic SDK wrapper |
| `src/email_agent/prompts/system.py` | System prompt builder (profile-aware) |
| `src/email_agent/prompts/tools.py` | Per-tool prompt fragments |
| `src/email_agent/email/base.py` | Abstract email adapter ABC |
| `src/email_agent/email/imap_.py` | IMAP implementation for 163 |
| `src/email_agent/agent/tools/registry.py` | Tool definition registry |
| `src/email_agent/agent/tools/fetch.py` | fetch_unread_emails tool |
| `src/email_agent/agent/tools/scan_fetch.py` | search_by_date tool |
| `src/email_agent/agent/tools/classify.py` | classify_email tool |
| `src/email_agent/agent/tools/extract_todos.py` | extract_todos tool |
| `src/email_agent/agent/tools/report.py` | generate_report tool |
| `src/email_agent/agent/core.py` | Agent main loop |
| `src/email_agent/cli.py` | CLI entry point |
| `tests/conftest.py` | Shared fixtures |
| `tests/test_models.py` | Data model tests |
| `tests/test_store.py` | Memory store tests |
| `tests/test_agent_core.py` | Agent loop tests |
| `tests/test_email_adapter.py` | Email adapter tests |
| `tests/test_tools/test_classify.py` | Classification tool tests |
| `tests/test_tools/test_extract_todos.py` | Todo extraction tests |
| `README.md` | Project documentation |

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `config.yaml.example`
- Create: `src/email_agent/__init__.py`
- Create: `src/email_agent/agent/__init__.py`
- Create: `src/email_agent/agent/tools/__init__.py`
- Create: `src/email_agent/email/__init__.py`
- Create: `src/email_agent/memory/__init__.py`
- Create: `src/email_agent/llm/__init__.py`
- Create: `src/email_agent/prompts/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_tools/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "email-agent"
version = "0.1.0"
description = "Intelligent email assistant powered by Claude — classify, extract todos, and generate reports."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "anthropic>=0.39.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.6",
]

[project.scripts]
email-agent = "email_agent.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/email_agent"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create config.yaml.example**

```yaml
# Email Agent Configuration
# Copy this file to config.yaml and fill in your values.

# Your role: worker | jobseeker | professor
# Leave empty to auto-detect on first run.
profile: ""

# 163 Email (IMAP/SMTP)
email:
  imap_server: "imap.163.com"
  imap_port: 993
  smtp_server: "smtp.163.com"
  smtp_port: 465
  address: "your-email@163.com"
  password: "your-smtp-auth-code"

# Claude API
claude:
  api_key: "sk-ant-..."
  model: "claude-sonnet-5"

# Agent settings
agent:
  max_turns: 5

# Daemon settings
daemon:
  check_interval: 300
  report_at: "20:00"

# Memory
memory:
  db_path: "data/email_agent.db"
```

- [ ] **Step 3: Create __init__.py files**

All `__init__.py` files are empty (`# Package` comment only).

- [ ] **Step 4: Create directory structure**

Run:
```bash
mkdir -p "g:/Desktop/Email Agent/src/email_agent/agent/tools"
mkdir -p "g:/Desktop/Email Agent/src/email_agent/email"
mkdir -p "g:/Desktop/Email Agent/src/email_agent/memory"
mkdir -p "g:/Desktop/Email Agent/src/email_agent/llm"
mkdir -p "g:/Desktop/Email Agent/src/email_agent/prompts"
mkdir -p "g:/Desktop/Email Agent/tests/test_tools"
mkdir -p "g:/Desktop/Email Agent/data"
```

- [ ] **Step 5: Install dependencies and verify**

```bash
cd "g:/Desktop/Email Agent"
uv pip install -e ".[dev]"
python -c "import email_agent; print('OK')"
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: scaffold project structure"
```

---

### Task 2: Data models

**Files:**
- Create: `src/email_agent/memory/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for models**

```python
# tests/test_models.py
import pytest
from datetime import datetime
from email_agent.memory.models import ProcessedEmail, Task, SkippedEmail, Report, Email


def test_email_dataclass():
    email = Email(
        message_id="<abc@163.com>",
        uid=123,
        sender_email="zhang@company.com",
        sender_name="张三",
        subject="Q3 预算",
        body="请审批",
        received_at=datetime(2026, 7, 27, 10, 0, 0),
    )
    assert email.message_id == "<abc@163.com>"
    assert email.sender_email == "zhang@company.com"


def test_processed_email_from_email():
    email = Email(
        message_id="<abc@163.com>",
        uid=123,
        sender_email="zhang@company.com",
        sender_name="张三",
        subject="Q3 预算",
        body="请审批",
        received_at=datetime(2026, 7, 27, 10, 0, 0),
    )
    processed = ProcessedEmail.from_email(
        email=email,
        category="work",
        priority="urgent",
        summary="Q3预算需审批",
        classification_reason="来自老板，含审批关键词",
    )
    assert processed.message_id == email.message_id
    assert processed.category == "work"
    assert processed.priority == "urgent"


def test_task_model():
    task = Task(
        content="周五前审批Q3预算",
        source_email_id="<abc@163.com>",
        due_date="2026-07-31",
    )
    assert task.status == "pending"
    assert task.due_date == "2026-07-31"


def test_skipped_email():
    skipped = SkippedEmail(
        message_id="<bad@163.com>",
        uid=456,
        sender_email="news@corp.com",
        subject="乱码邮件",
        reason="GBK decode error",
    )
    assert skipped.reason == "GBK decode error"


def test_report_model():
    report = Report(
        type="daily",
        period_start="2026-07-27",
        period_end="2026-07-27",
        content="今日共处理20封邮件...",
    )
    assert report.type == "daily"
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd "g:/Desktop/Email Agent"
pytest tests/test_models.py -v
```
Expected: FAIL (no module)

- [ ] **Step 3: Implement data models**

```python
# src/email_agent/memory/models.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Email:
    """Raw email from IMAP."""
    message_id: str
    uid: int
    sender_email: str
    sender_name: str
    subject: str
    body: str
    received_at: datetime


@dataclass
class ProcessedEmail:
    """Email after agent processing, stored in DB."""
    message_id: str
    uid: int
    sender_email: str
    sender_name: str
    subject: str
    received_at: datetime
    category: str
    priority: str
    summary: str
    classification_reason: str

    @classmethod
    def from_email(cls, email: Email, category: str, priority: str,
                   summary: str, classification_reason: str) -> "ProcessedEmail":
        return cls(
            message_id=email.message_id,
            uid=email.uid,
            sender_email=email.sender_email,
            sender_name=email.sender_name,
            subject=email.subject,
            received_at=email.received_at,
            category=category,
            priority=priority,
            summary=summary,
            classification_reason=classification_reason,
        )


@dataclass
class Task:
    """Extracted todo item."""
    content: str
    source_email_id: str
    due_date: Optional[str] = None
    status: str = "pending"
    id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class SkippedEmail:
    """Email that could not be processed."""
    message_id: str
    uid: int
    sender_email: str
    subject: str
    reason: str
    skipped_at: Optional[str] = None


@dataclass
class Report:
    """Generated email report."""
    type: str
    period_start: str
    period_end: str
    content: str
    id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class ProfileGuess:
    """Agent's role inference result."""
    profile: str
    evidence: list[str]
    confidence: str  # "high" | "medium" | "low"
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/test_models.py -v
```
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add data models"
```

---

### Task 3: Config loader

**Files:**
- Create: `src/email_agent/config.py`

- [ ] **Step 1: Write and implement config.py**

```python
# src/email_agent/config.py
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import yaml


@dataclass
class EmailConfig:
    imap_server: str = "imap.163.com"
    imap_port: int = 993
    smtp_server: str = "smtp.163.com"
    smtp_port: int = 465
    address: str = ""
    password: str = ""


@dataclass
class ClaudeConfig:
    api_key: str = ""
    model: str = "claude-sonnet-5"


@dataclass
class AgentConfig:
    max_turns: int = 5


@dataclass
class DaemonConfig:
    check_interval: int = 300
    report_at: str = "20:00"


@dataclass
class MemoryConfig:
    db_path: str = "data/email_agent.db"


@dataclass
class Config:
    profile: str = ""
    email: EmailConfig = field(default_factory=EmailConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)


def load_config(config_path: Optional[str] = None) -> Config:
    """Load config from yaml file, with env var overrides."""
    if config_path is None:
        config_path = _find_config()

    config = Config()

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if "profile" in data and data["profile"]:
            config.profile = data["profile"]

        if "email" in data:
            for key, val in data["email"].items():
                if hasattr(config.email, key):
                    setattr(config.email, key, val)

        if "claude" in data:
            for key, val in data["claude"].items():
                if hasattr(config.claude, key):
                    setattr(config.claude, key, val)

        if "agent" in data:
            for key, val in data["agent"].items():
                if hasattr(config.agent, key):
                    setattr(config.agent, key, val)

        if "daemon" in data:
            for key, val in data["daemon"].items():
                if hasattr(config.daemon, key):
                    setattr(config.daemon, key, val)

        if "memory" in data:
            for key, val in data["memory"].items():
                if hasattr(config.memory, key):
                    setattr(config.memory, key, val)

    # Env var overrides
    if os.environ.get("EMAIL_AGENT_CLAUDE_API_KEY"):
        config.claude.api_key = os.environ["EMAIL_AGENT_CLAUDE_API_KEY"]
    if os.environ.get("EMAIL_AGENT_EMAIL_ADDRESS"):
        config.email.address = os.environ["EMAIL_AGENT_EMAIL_ADDRESS"]
    if os.environ.get("EMAIL_AGENT_EMAIL_PASSWORD"):
        config.email.password = os.environ["EMAIL_AGENT_EMAIL_PASSWORD"]
    if os.environ.get("EMAIL_AGENT_PROFILE"):
        config.profile = os.environ["EMAIL_AGENT_PROFILE"]

    return config


def save_config(config: Config, config_path: Optional[str] = None) -> None:
    """Save config back to yaml file."""
    if config_path is None:
        config_path = _find_config()

    data = {
        "profile": config.profile,
        "email": {
            "imap_server": config.email.imap_server,
            "imap_port": config.email.imap_port,
            "smtp_server": config.email.smtp_server,
            "smtp_port": config.email.smtp_port,
            "address": config.email.address,
            "password": config.email.password,
        },
        "claude": {
            "api_key": config.claude.api_key,
            "model": config.claude.model,
        },
        "agent": {
            "max_turns": config.agent.max_turns,
        },
        "daemon": {
            "check_interval": config.daemon.check_interval,
            "report_at": config.daemon.report_at,
        },
        "memory": {
            "db_path": config.memory.db_path,
        },
    }

    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def validate_config(config: Config) -> list[str]:
    """Validate config, return list of missing required fields."""
    errors = []
    if not config.email.address:
        errors.append("email.address is required")
    if not config.email.password:
        errors.append("email.password is required")
    if not config.claude.api_key:
        errors.append("claude.api_key is required (set in config.yaml or EMAIL_AGENT_CLAUDE_API_KEY)")
    return errors


def _find_config() -> str:
    """Find config.yaml in standard locations."""
    candidates = [
        "config.yaml",
        os.path.expanduser("~/.email-agent/config.yaml"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return "config.yaml"
```

- [ ] **Step 2: Verify config loads**

```bash
cd "g:/Desktop/Email Agent"
python -c "
from email_agent.config import load_config, validate_config
config = load_config('config.yaml.example')
errors = validate_config(config)
print('Errors:', errors)
print('Model:', config.claude.model)
print('Profile:', config.profile or '(not set)')
"
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add config loader with env var override"
```

---

### Task 4: Memory store

**Files:**
- Create: `src/email_agent/memory/store.py`
- Create: `tests/test_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_store.py
import pytest
import os
import tempfile
from datetime import datetime
from email_agent.memory.store import MemoryStore
from email_agent.memory.models import ProcessedEmail, Task, SkippedEmail, Report


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = MemoryStore(path)
    s.init()
    yield s
    s.close()
    os.unlink(path)


def make_email(message_id="<abc@163.com>", sender="zhang@company.com",
               sender_name="张三", received=None):
    return ProcessedEmail(
        message_id=message_id,
        uid=1,
        sender_email=sender,
        sender_name=sender_name,
        subject="Test",
        received_at=received or datetime(2026, 7, 27, 10, 0, 0),
        category="work",
        priority="urgent",
        summary="test summary",
        classification_reason="test reason",
    )


class TestEmailCRUD:
    def test_save_and_exists(self, store):
        email = make_email()
        assert not store.exists(email.message_id)
        store.save_email(email)
        assert store.exists(email.message_id)

    def test_save_duplicate_ignored(self, store):
        email = make_email()
        store.save_email(email)
        store.save_email(email)
        history = store.get_sender_history("zhang@company.com")
        assert len(history) == 1

    def test_get_sender_history_ordered(self, store):
        older = make_email("<older@163.com>", received=datetime(2026, 7, 20))
        newer = make_email("<newer@163.com>", received=datetime(2026, 7, 27))
        store.save_email(older)
        store.save_email(newer)
        history = store.get_sender_history("zhang@company.com")
        assert history[0].message_id == "<newer@163.com>"
        assert history[1].message_id == "<older@163.com>"

    def test_get_sender_history_limit(self, store):
        for i in range(15):
            store.save_email(make_email(f"<id{i}@163.com>"))
        history = store.get_sender_history("zhang@company.com")
        assert len(history) == 10

    def test_get_emails_in_range(self, store):
        in_range = make_email("<in@163.com>", received=datetime(2026, 7, 25))
        out_range = make_email("<out@163.com>", received=datetime(2026, 7, 20))
        store.save_email(in_range)
        store.save_email(out_range)
        results = store.get_emails_in_range("2026-07-24", "2026-07-28")
        assert len(results) == 1
        assert results[0].message_id == "<in@163.com>"


class TestTaskCRUD:
    def test_save_and_get_tasks(self, store):
        task = Task(content="审批预算", source_email_id="<abc@163.com>", due_date="2026-07-31")
        store.save_task(task)
        tasks = store.get_pending_tasks()
        assert len(tasks) == 1
        assert tasks[0].content == "审批预算"

    def test_mark_task_done(self, store):
        task = Task(content="审批预算", source_email_id="<abc@163.com>")
        store.save_task(task)
        tasks = store.get_pending_tasks()
        store.mark_task_done(tasks[0].id)
        assert len(store.get_pending_tasks()) == 0

    def test_get_tasks_by_email(self, store):
        store.save_task(Task(content="任务1", source_email_id="<abc@163.com>"))
        store.save_task(Task(content="任务2", source_email_id="<xyz@163.com>"))
        tasks = store.get_tasks_by_email("<abc@163.com>")
        assert len(tasks) == 1
        assert tasks[0].content == "任务1"


class TestSkippedEmails:
    def test_save_and_get_skipped(self, store):
        skipped = SkippedEmail(
            message_id="<bad@163.com>", uid=1,
            sender_email="n@c.com", subject="Bad",
            reason="decode error",
        )
        store.save_skipped(skipped)
        results = store.get_skipped_emails()
        assert len(results) == 1
        assert results[0].reason == "decode error"


class TestReportCRUD:
    def test_save_and_get_reports(self, store):
        report = Report(
            type="daily",
            period_start="2026-07-27",
            period_end="2026-07-27",
            content="处理了20封邮件",
        )
        store.save_report(report)
        results = store.get_reports("daily", limit=10)
        assert len(results) == 1
        assert "20封" in results[0].content
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_store.py -v
```
Expected: FAIL (no module)

- [ ] **Step 3: Implement MemoryStore**

```python
# src/email_agent/memory/store.py
import sqlite3
import os
from datetime import datetime
from typing import Optional
from email_agent.memory.models import ProcessedEmail, Task, SkippedEmail, Report


class MemoryStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def init(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def close(self):
        if self.conn:
            self.conn.close()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS processed_emails (
                message_id TEXT PRIMARY KEY,
                uid INTEGER,
                sender_email TEXT NOT NULL,
                sender_name TEXT,
                subject TEXT,
                received_at TIMESTAMP,
                category TEXT,
                priority TEXT,
                summary TEXT,
                classification_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source_email_id TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS skipped_emails (
                message_id TEXT PRIMARY KEY,
                uid INTEGER,
                sender_email TEXT,
                subject TEXT,
                reason TEXT,
                skipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                period_start TEXT,
                period_end TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_processed_sender
                ON processed_emails(sender_email, received_at DESC);
        """)
        self.conn.commit()

    # -- Processed Emails --

    def exists(self, message_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM processed_emails WHERE message_id = ?", (message_id,)
        ).fetchone()
        return row is not None

    def save_email(self, email: ProcessedEmail):
        self.conn.execute("""
            INSERT OR IGNORE INTO processed_emails
                (message_id, uid, sender_email, sender_name, subject,
                 received_at, category, priority, summary, classification_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email.message_id, email.uid, email.sender_email, email.sender_name,
            email.subject, email.received_at.isoformat() if isinstance(email.received_at, datetime)
            else email.received_at,
            email.category, email.priority, email.summary, email.classification_reason,
        ))
        self.conn.commit()

    def get_sender_history(self, sender_email: str, limit: int = 10) -> list[ProcessedEmail]:
        rows = self.conn.execute("""
            SELECT * FROM processed_emails
            WHERE sender_email = ?
            ORDER BY received_at DESC
            LIMIT ?
        """, (sender_email, limit)).fetchall()
        return [_row_to_processed_email(r) for r in rows]

    def get_emails_in_range(self, since: str, before: str) -> list[ProcessedEmail]:
        rows = self.conn.execute("""
            SELECT * FROM processed_emails
            WHERE received_at >= ? AND received_at <= ?
            ORDER BY received_at DESC
        """, (since, before)).fetchall()
        return [_row_to_processed_email(r) for r in rows]

    # -- Tasks --

    def save_task(self, task: Task):
        cursor = self.conn.execute("""
            INSERT INTO tasks (content, source_email_id, due_date)
            VALUES (?, ?, ?)
        """, (task.content, task.source_email_id, task.due_date))
        self.conn.commit()
        task.id = cursor.lastrowid

    def get_pending_tasks(self) -> list[Task]:
        rows = self.conn.execute("""
            SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at DESC
        """).fetchall()
        return [_row_to_task(r) for r in rows]

    def get_tasks_by_email(self, message_id: str) -> list[Task]:
        rows = self.conn.execute("""
            SELECT * FROM tasks WHERE source_email_id = ? ORDER BY created_at DESC
        """, (message_id,)).fetchall()
        return [_row_to_task(r) for r in rows]

    def mark_task_done(self, task_id: int):
        self.conn.execute(
            "UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,)
        )
        self.conn.commit()

    # -- Skipped Emails --

    def save_skipped(self, skipped: SkippedEmail):
        self.conn.execute("""
            INSERT OR REPLACE INTO skipped_emails (message_id, uid, sender_email, subject, reason)
            VALUES (?, ?, ?, ?, ?)
        """, (skipped.message_id, skipped.uid, skipped.sender_email, skipped.subject, skipped.reason))
        self.conn.commit()

    def get_skipped_emails(self, since: Optional[str] = None) -> list[SkippedEmail]:
        if since:
            rows = self.conn.execute("""
                SELECT * FROM skipped_emails WHERE skipped_at >= ? ORDER BY skipped_at DESC
            """, (since,)).fetchall()
        else:
            rows = self.conn.execute("""
                SELECT * FROM skipped_emails ORDER BY skipped_at DESC LIMIT 50
            """).fetchall()
        return [_row_to_skipped(r) for r in rows]

    # -- Reports --

    def save_report(self, report: Report):
        cursor = self.conn.execute("""
            INSERT INTO reports (type, period_start, period_end, content)
            VALUES (?, ?, ?, ?)
        """, (report.type, report.period_start, report.period_end, report.content))
        self.conn.commit()
        report.id = cursor.lastrowid

    def get_reports(self, report_type: str, limit: int = 10) -> list[Report]:
        rows = self.conn.execute("""
            SELECT * FROM reports WHERE type = ? ORDER BY created_at DESC LIMIT ?
        """, (report_type, limit)).fetchall()
        return [_row_to_report(r) for r in rows]


def _row_to_processed_email(row) -> ProcessedEmail:
    return ProcessedEmail(
        message_id=row["message_id"], uid=row["uid"],
        sender_email=row["sender_email"], sender_name=row["sender_name"] or "",
        subject=row["subject"] or "",
        received_at=row["received_at"],
        category=row["category"] or "", priority=row["priority"] or "",
        summary=row["summary"] or "", classification_reason=row["classification_reason"] or "",
    )


def _row_to_task(row) -> Task:
    return Task(
        id=row["id"], content=row["content"],
        source_email_id=row["source_email_id"] or "",
        due_date=row["due_date"], status=row["status"],
        created_at=row["created_at"],
    )


def _row_to_skipped(row) -> SkippedEmail:
    return SkippedEmail(
        message_id=row["message_id"], uid=row["uid"],
        sender_email=row["sender_email"] or "",
        subject=row["subject"] or "",
        reason=row["reason"] or "",
        skipped_at=row["skipped_at"],
    )


def _row_to_report(row) -> Report:
    return Report(
        id=row["id"], type=row["type"],
        period_start=row["period_start"], period_end=row["period_end"],
        content=row["content"], created_at=row["created_at"],
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_store.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add memory store with SQLite backend"
```

---

### Task 5: LLM client

**Files:**
- Create: `src/email_agent/llm/client.py`

- [ ] **Step 1: Implement ClaudeClient**

```python
# src/email_agent/llm/client.py
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from anthropic import Anthropic, APIStatusError, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict


@dataclass
class ClaudeResponse:
    text: str
    stop_reason: str
    tool_uses: list[ToolUse] = field(default_factory=list)


class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-5",
                 max_tokens: int = 1024, temperature: float = 0.0):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def send(self, system_prompt: str, messages: list[dict],
             tools: Optional[list[dict]] = None,
             max_retries: int = 3) -> ClaudeResponse:
        """Send a message to Claude, with retry logic."""
        last_error = None
        for attempt in range(max_retries):
            try:
                return self._send_inner(system_prompt, messages, tools)
            except (APITimeoutError, RateLimitError) as e:
                last_error = e
                if attempt == max_retries - 1:
                    break
                wait = 2 ** attempt
                logger.warning("Claude API retry %d/%d after %ds: %s",
                               attempt + 1, max_retries, wait, e)
                time.sleep(wait)
            except APIStatusError as e:
                raise RuntimeError(f"Claude API error (status {e.status_code}): {e.message}") from e

        raise RuntimeError(f"Claude API failed after {max_retries} retries: {last_error}")

    def _send_inner(self, system_prompt: str, messages: list[dict],
                    tools: Optional[list[dict]]) -> ClaudeResponse:
        kwargs = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=messages,
        )
        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)

        tool_uses = []
        text_parts = []
        for block in response.content:
            if block.type == "tool_use":
                tool_uses.append(ToolUse(
                    id=block.id,
                    name=block.name,
                    input=block.input,
                ))
            elif block.type == "text":
                text_parts.append(block.text)

        return ClaudeResponse(
            text="\n".join(text_parts),
            stop_reason=response.stop_reason,
            tool_uses=tool_uses,
        )
```

- [ ] **Step 2: Verify the module imports**

```bash
cd "g:/Desktop/Email Agent"
python -c "from email_agent.llm.client import ClaudeClient, ClaudeResponse, ToolUse; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add Claude LLM client with retry logic"
```

---

### Task 6: Prompts

**Files:**
- Create: `src/email_agent/prompts/system.py`
- Create: `src/email_agent/prompts/tools.py`

- [ ] **Step 1: Implement tool prompt templates**

```python
# src/email_agent/prompts/tools.py

CLASSIFY_TOOL_PROMPT = """Analyze the email and classify it. Determine:
1. **category**: The appropriate category from the available options
2. **priority**: urgent, high, normal, or low
3. **summary**: A one-sentence Chinese summary of the email content
4. **reason**: Why you chose this classification

Priority guidelines:
- urgent: Requires immediate action, contains deadlines within 48 hours, or from key contacts
- high: Important but not urgent, needs attention this week
- normal: Standard correspondence
- low: Newsletters, automated notifications, promotional"""

EXTRACT_TODOS_PROMPT = """Extract actionable tasks from the email. A task is:
- Something the recipient needs to DO (reply, submit, review, confirm, attend)
- Has an explicit or implied deadline
- NOT informational content

For each task found, provide:
- content: The task description in Chinese
- due_date: Explicit deadline if mentioned (format: YYYY-MM-DD), or null
- source_line: The sentence in the email that implies this task"""

REPORT_PROMPT = """Generate a comprehensive email report based on the provided data.

Include these sections:
1. Overview: total count, unread count, date range
2. Priority distribution: counts by priority level
3. Category distribution: counts by category
4. Key items: top urgent/high emails with summaries
5. Pending tasks: all uncompleted tasks with deadlines
6. Top senders: most frequent senders with counts
7. Unreplied but important: emails that may need a response

Write in Chinese. Be concise and actionable."""

PROFILE_DETECTION_PROMPT = """You are analyzing a user's recent email metadata (sender domains and subjects only, no bodies) to guess their primary role.

Roles:
- worker: Corporate employee, emails about projects, meetings, approvals
- jobseeker: Job seeker, emails from HR, recruiters, job platforms
- professor: Academic, emails about research, students, conferences, peer review

Analyze the patterns in sender domains and subject lines. Return:
1. Your best guess for the role
2. Evidence: 2-3 specific observations that support your guess
3. Confidence: high, medium, or low"""
```

- [ ] **Step 2: Implement system prompt builder**

```python
# src/email_agent/prompts/system.py
from email_agent.prompts.tools import (
    CLASSIFY_TOOL_PROMPT,
    EXTRACT_TODOS_PROMPT,
    REPORT_PROMPT,
    PROFILE_DETECTION_PROMPT,
)


PROFILE_LABELS = {
    "worker": {
        "categories": ["work", "personal", "newsletter", "notification"],
        "name": "打工人",
    },
    "jobseeker": {
        "categories": ["面试邀请", "笔试通知", "Offer通知", "拒信", "薪资谈判", "投递确认", "其他"],
        "name": "求职者",
    },
    "professor": {
        "categories": ["学生自荐", "课题合作", "会议邀请", "审稿邀请", "行政通知", "论文相关", "其他"],
        "name": "高校导师",
    },
}


def build_system_prompt(profile: str) -> str:
    """Build the main system prompt for email processing."""
    labels = PROFILE_LABELS.get(profile, PROFILE_LABELS["worker"])
    categories_str = ", ".join(labels["categories"])

    return f"""你是一个智能邮件助手，帮助{labels['name']}高效处理邮件。

## 你的能力
你可以使用以下工具来处理邮件：
- classify_email: 分类邮件并标记优先级
- extract_todos: 从邮件中提取待办事项
- get_sender_history: 查询发件人的历史邮件
- get_pending_tasks: 获取当前未完成的待办列表
- generate_report: 生成邮件报告

## 分类体系
可用的分类标签: {categories_str}
优先级: urgent (紧急), high (重要), normal (普通), low (低优先级)

## 工作流程
1. 仔细阅读邮件内容
2. 如果需要发件人历史或当前待办列表来辅助判断，先调用 get_sender_history 或 get_pending_tasks
3. 调用 classify_email 进行分类
4. 如果邮件包含待办事项，调用 extract_todos 提取

## 规则
- 先理解再分类，不要急于调用工具
- 分类要有明确依据，在 reason 字段中说明
- 待办事项必须是收件人需要执行的行动
- 同一封邮件可以同时分类和提取待办
- 处理完毕后不要继续调用工具
"""


def build_classify_context(email_info: str, sender_history: str,
                           pending_tasks: str) -> str:
    """Build the user message context for email classification."""
    return f"""【当前邮件】
{email_info}

【该发件人历史】
{sender_history}

【当前待办列表】
{pending_tasks}

{CLASSIFY_TOOL_PROMPT}

请分析这封邮件，调用 classify_email 进行分类。如果邮件包含待办事项，也调用 extract_todos。"""


def build_report_context(report_type: str, period_start: str, period_end: str,
                         email_data: str, task_data: str) -> str:
    """Build the user message context for report generation."""
    period_label = "周报" if report_type == "weekly" else "日报"
    return f"""请生成一份邮件{period_label}。

时间范围: {period_start} ~ {period_end}

【邮件数据】
{email_data}

【待办事项】
{task_data}

{REPORT_PROMPT}"""


def build_profile_detection_context(metadata: str) -> str:
    """Build the user message context for profile detection."""
    return f"""以下是用户最近收到的邮件元数据（发件人域名和主题）：

{metadata}

{PROFILE_DETECTION_PROMPT}"""
```

- [ ] **Step 3: Verify imports**

```bash
cd "g:/Desktop/Email Agent"
python -c "
from email_agent.prompts.system import build_system_prompt, PROFILE_LABELS
print(build_system_prompt('jobseeker')[:200])
print('OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add prompt system with profile-aware templates"
```

---

### Task 7: Email adapter

**Files:**
- Create: `src/email_agent/email/base.py`
- Create: `src/email_agent/email/imap_.py`
- Create: `tests/test_email_adapter.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create conftest.py with shared fixtures**

```python
# tests/conftest.py
import pytest
from datetime import datetime
from email_agent.memory.models import Email, ProcessedEmail, Task


@pytest.fixture
def sample_email():
    return Email(
        message_id="<test123@163.com>",
        uid=1,
        sender_email="zhang@company.com",
        sender_name="张三",
        subject="Q3 预算审批需要你的反馈",
        body="请在本周五之前审批Q3预算方案，详见附件。",
        received_at=datetime(2026, 7, 27, 10, 0, 0),
    )


@pytest.fixture
def sample_emails():
    return [
        Email(
            message_id=f"<test{i}@163.com>",
            uid=i,
            sender_email=f"sender{i}@company.com",
            sender_name=f"发件人{i}",
            subject=f"测试邮件{i}",
            body=f"这是第{i}封测试邮件的内容。",
            received_at=datetime(2026, 7, 27, 10, i, 0),
        )
        for i in range(5)
    ]
```

- [ ] **Step 2: Write failing IMAP adapter test**

```python
# tests/test_email_adapter.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from email_agent.email.base import EmailAdapter
from email_agent.email.imap_ import IMAPAdapter


class TestIMAPAdapter:
    def test_adapter_is_abstract(self):
        with pytest.raises(TypeError):
            EmailAdapter()

    def test_imap_is_concrete(self):
        adapter = IMAPAdapter(
            server="imap.163.com",
            port=993,
            address="test@163.com",
            password="test",
        )
        assert isinstance(adapter, EmailAdapter)

    @patch("imaplib.IMAP4_SSL")
    def test_connect(self, mock_imap):
        adapter = IMAPAdapter("imap.163.com", 993, "test@163.com", "test")
        adapter.connect()
        mock_imap.assert_called_once_with("imap.163.com", 993)
        mock_imap.return_value.login.assert_called_once_with("test@163.com", "test")

    @patch("imaplib.IMAP4_SSL")
    def test_search_unseen(self, mock_imap):
        mock_conn = mock_imap.return_value
        mock_conn.search.return_value = ("OK", [b"1 2 3 4 5"])
        adapter = IMAPAdapter("imap.163.com", 993, "test@163.com", "test")
        adapter._conn = mock_conn
        uids = adapter.search_unseen()
        assert uids == ["1", "2", "3", "4", "5"]

    @patch("imaplib.IMAP4_SSL")
    def test_search_unseen_empty(self, mock_imap):
        mock_conn = mock_imap.return_value
        mock_conn.search.return_value = ("OK", [b""])
        adapter = IMAPAdapter("imap.163.com", 993, "test@163.com", "test")
        adapter._conn = mock_conn
        uids = adapter.search_unseen()
        assert uids == []

    @patch("imaplib.IMAP4_SSL")
    def test_search_by_date(self, mock_imap):
        mock_conn = mock_imap.return_value
        mock_conn.search.return_value = ("OK", [b"10 11 12"])
        adapter = IMAPAdapter("imap.163.com", 993, "test@163.com", "test")
        adapter._conn = mock_conn
        uids = adapter.search_by_date("2026-07-01", "2026-07-27")
        assert uids == ["10", "11", "12"]

    @patch("imaplib.IMAP4_SSL")
    def test_fetch_header(self, mock_imap):
        mock_conn = mock_imap.return_value
        mock_conn.fetch.return_value = (
            "OK",
            [(b"1 (UID 1)", b"Message-ID: <abc@163.com>\r\nSubject: =?UTF-8?B?5rWL6K+V?=")]
        )
        adapter = IMAPAdapter("imap.163.com", 993, "test@163.com", "test")
        adapter._conn = mock_conn
        msg_id = adapter.fetch_header("1", "Message-ID")
        assert msg_id == "<abc@163.com>"

    @patch("imaplib.IMAP4_SSL")
    def test_fetch_header_not_found(self, mock_imap):
        mock_conn = mock_imap.return_value
        mock_conn.fetch.return_value = (
            "OK",
            [(b"1 (UID 1)", b"Subject: Test")]
        )
        adapter = IMAPAdapter("imap.163.com", 993, "test@163.com", "test")
        adapter._conn = mock_conn
        result = adapter.fetch_header("1", "Message-ID")
        assert result is None
```

- [ ] **Step 3: Run tests to verify failure**

```bash
pytest tests/test_email_adapter.py -v
```
Expected: FAIL

- [ ] **Step 4: Implement abstract base**

```python
# src/email_agent/email/base.py
from abc import ABC, abstractmethod
from email_agent.memory.models import Email


class EmailAdapter(ABC):
    """Abstract interface for email protocol adapters."""

    @abstractmethod
    def connect(self):
        """Establish connection to the email server."""
        ...

    @abstractmethod
    def disconnect(self):
        """Close the connection."""
        ...

    @abstractmethod
    def search_unseen(self) -> list[str]:
        """Return UIDs of all unseen (unread) emails."""
        ...

    @abstractmethod
    def search_by_date(self, since: str, before: str) -> list[str]:
        """Return UIDs of all emails within date range (inclusive)."""
        ...

    @abstractmethod
    def fetch_header(self, uid: str, header_name: str) -> str | None:
        """Fetch a specific header value for a given UID."""
        ...

    @abstractmethod
    def fetch_full(self, uid: str) -> Email:
        """Fetch the complete email (headers + body) for a given UID."""
        ...
```

- [ ] **Step 5: Implement IMAP adapter**

```python
# src/email_agent/email/imap_.py
import imaplib
import email
import logging
from email.header import decode_header
from datetime import datetime
from email_agent.email.base import EmailAdapter
from email_agent.memory.models import Email as EmailModel

logger = logging.getLogger(__name__)


class IMAPAdapter(EmailAdapter):
    def __init__(self, server: str, port: int, address: str, password: str):
        self.server = server
        self.port = port
        self.address = address
        self.password = password
        self._conn: imaplib.IMAP4_SSL | None = None

    def connect(self):
        self._conn = imaplib.IMAP4_SSL(self.server, self.port)
        self._conn.login(self.address, self.password)
        self._conn.select("INBOX")

    def disconnect(self):
        if self._conn:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    def search_unseen(self) -> list[str]:
        status, data = self._conn.search(None, "UNSEEN")
        if status != "OK":
            return []
        return _parse_uid_list(data)

    def search_by_date(self, since: str, before: str) -> list[str]:
        # IMAP date format: DD-Mon-YYYY, e.g. 01-Jul-2026
        since_fmt = _format_imap_date(since)
        before_fmt = _format_imap_date(before)
        criteria = f'(SINCE "{since_fmt}" BEFORE "{_next_day(before)}")'
        status, data = self._conn.search(None, criteria)
        if status != "OK":
            return []
        return _parse_uid_list(data)

    def fetch_header(self, uid: str, header_name: str) -> str | None:
        try:
            status, data = self._conn.fetch(uid, f"(BODY.PEEK[HEADER.FIELDS ({header_name})])")
            if status != "OK":
                return None
            raw = data[0][1]
            if not raw:
                return None
            msg = email.message_from_bytes(raw)
            value = msg.get(header_name)
            if value:
                decoded_parts = decode_header(value)
                return "".join(
                    part.decode(charset or "utf-8") if isinstance(part, bytes) else part
                    for part, charset in decoded_parts
                )
            return None
        except Exception as e:
            logger.warning("Failed to fetch header %s for UID %s: %s", header_name, uid, e)
            return None

    def fetch_full(self, uid: str) -> EmailModel:
        status, data = self._conn.fetch(uid, "(RFC822)")
        if status != "OK":
            raise RuntimeError(f"Failed to fetch email UID {uid}")

        raw = data[0][1]
        msg = email.message_from_bytes(raw)

        message_id = msg.get("Message-ID", f"<unknown-{uid}>")
        message_id = _decode_header_value(message_id)

        sender_name, sender_email_addr = _parse_address(msg.get("From", ""))
        subject = _decode_header_value(msg.get("Subject", "(无主题)"))
        received_at = _parse_date(msg.get("Date"))

        body = _extract_body(msg)

        return EmailModel(
            message_id=message_id,
            uid=int(uid),
            sender_email=sender_email_addr,
            sender_name=sender_name,
            subject=subject,
            body=body,
            received_at=received_at,
        )


# -- Helper functions --

def _parse_uid_list(data: list) -> list[str]:
    if not data or not data[0]:
        return []
    raw = data[0]
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    uids = raw.strip().split()
    return [u for u in uids if u]


def _format_imap_date(date_str: str) -> str:
    """Convert YYYY-MM-DD to DD-Mon-YYYY."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d.day:02d}-{months[d.month - 1]}-{d.year}"


def _next_day(date_str: str) -> str:
    """Get the next day after date_str, since IMAP BEFORE is exclusive."""
    from datetime import timedelta
    d = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _decode_header_value(raw: str | None) -> str:
    if not raw:
        return ""
    decoded_parts = decode_header(raw)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def _parse_address(from_header: str) -> tuple[str, str]:
    """Parse 'Name <email>' into (name, email)."""
    if not from_header:
        return "", ""
    name, addr = email.utils.parseaddr(from_header)
    name = _decode_header_value(name) if name else ""
    return name, addr


def _parse_date(date_header: str | None) -> datetime:
    if not date_header:
        return datetime.now()
    try:
        parsed = email.utils.parsedate_to_datetime(date_header)
        return parsed
    except Exception:
        return datetime.now()


def _extract_body(msg: email.message.Message) -> str:
    """Extract text body from email message."""
    body_parts = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_parts.append(payload.decode(charset, errors="replace"))
                except Exception:
                    continue
            elif content_type == "text/html" and not body_parts:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_parts.append(_strip_html(payload.decode(charset, errors="replace")))
                except Exception:
                    continue
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload:
                body_parts.append(payload.decode(charset, errors="replace"))
        except Exception:
            pass

    return "\n".join(body_parts).strip()


def _strip_html(html: str) -> str:
    """Crude HTML tag stripper."""
    import re
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_email_adapter.py -v
```
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add email adapter with IMAP implementation"
```

---

### Task 8: Tool registry

**Files:**
- Create: `src/email_agent/agent/tools/registry.py`

- [ ] **Step 1: Implement ToolRegistry**

```python
# src/email_agent/agent/tools/registry.py
from typing import Callable, Any


class ToolRegistry:
    """Registry of tools the agent can use. Each tool has a name,
    an Anthropic-format tool definition, and a handler function."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, definition: dict, handler: Callable):
        self._tools[name] = {
            "definition": definition,
            "handler": handler,
        }

    def get_definitions(self) -> list[dict]:
        """Return tool definitions in Anthropic API format."""
        return [t["definition"] for t in self._tools.values()]

    def execute(self, name: str, input: dict) -> str:
        """Execute a tool by name and return its result as a string."""
        if name not in self._tools:
            return f"Error: unknown tool '{name}'"
        try:
            result = self._tools[name]["handler"](**input)
            return str(result) if not isinstance(result, str) else result
        except Exception as e:
            return f"Error executing {name}: {e}"


# Singleton
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    return _registry
```

- [ ] **Step 2: Verify import**

```bash
cd "g:/Desktop/Email Agent"
python -c "from email_agent.agent.tools.registry import get_registry; r = get_registry(); print('OK:', len(r.get_definitions()))"
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add tool registry"
```

---

### Task 9: fetch_unread_emails tool

**Files:**
- Create: `src/email_agent/agent/tools/fetch.py`

- [ ] **Step 1: Implement fetch tool and register it**

```python
# src/email_agent/agent/tools/fetch.py
import logging
from email_agent.agent.tools.registry import get_registry

logger = logging.getLogger(__name__)

FETCH_DEFINITION = {
    "name": "fetch_unread_emails",
    "description": "从IMAP服务器拉取所有未读邮件，自动基于Message-ID去重。返回新邮件的发件人、主题和正文摘要。",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}


def register(adapter, memory):
    """Register the fetch tool with given adapter and memory store."""

    def handler() -> str:
        try:
            uids = adapter.search_unseen()
            if not uids:
                return "没有未读邮件。"

            new_emails = []
            for uid in uids:
                try:
                    msg_id = adapter.fetch_header(uid, "Message-ID")
                    if msg_id and memory.exists(msg_id):
                        continue
                    email = adapter.fetch_full(uid)
                    new_emails.append({
                        "uid": uid,
                        "message_id": email.message_id,
                        "sender": f"{email.sender_name} <{email.sender_email}>",
                        "subject": email.subject,
                        "body_preview": email.body[:300],
                        "received_at": email.received_at.isoformat(),
                    })
                except Exception as e:
                    logger.warning("跳过邮件 UID %s: %s", uid, e)

            if not new_emails:
                return "所有未读邮件都已处理过。"

            return _format_fetch_result(new_emails)
        except Exception as e:
            return f"拉取邮件失败: {e}"

    get_registry().register("fetch_unread_emails", FETCH_DEFINITION, handler)


def _format_fetch_result(emails: list[dict]) -> str:
    lines = [f"拉取到 {len(emails)} 封新邮件:\n"]
    for i, em in enumerate(emails, 1):
        lines.append(
            f"{i}. [{em['uid']}] {em['sender']}\n"
            f"   主题: {em['subject']}\n"
            f"   时间: {em['received_at']}\n"
            f"   预览: {em['body_preview']}...\n"
        )
    return "\n".join(lines)
```

- [ ] **Step 2: Verify import and registration**

```bash
cd "g:/Desktop/Email Agent"
python -c "from email_agent.agent.tools import fetch; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add fetch_unread_emails tool"
```

---

### Task 10: classify_email tool

**Files:**
- Create: `src/email_agent/agent/tools/classify.py`

- [ ] **Step 1: Implement classify tool**

```python
# src/email_agent/agent/tools/classify.py
from email_agent.agent.tools.registry import get_registry

CLASSIFY_DEFINITION = {
    "name": "classify_email",
    "description": "对邮件进行分类并标记优先级。调用后结果会自动保存。",
    "input_schema": {
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": "邮件的Message-ID",
            },
            "category": {
                "type": "string",
                "description": "分类标签",
            },
            "priority": {
                "type": "string",
                "enum": ["urgent", "high", "normal", "low"],
                "description": "优先级",
            },
            "summary": {
                "type": "string",
                "description": "一句话中文摘要",
            },
            "reason": {
                "type": "string",
                "description": "分类依据",
            },
        },
        "required": ["message_id", "category", "priority", "summary", "reason"],
    },
}


def register(memory):
    """Register classify tool with given memory store."""

    def handler(message_id: str, category: str, priority: str,
                summary: str, reason: str) -> str:
        # Store in memory — this will be combined with the raw email data
        # by the agent core after all tools have run.
        return (
            f"已分类: {category} | 优先级: {priority}\n"
            f"摘要: {summary}\n"
            f"依据: {reason}"
        )

    get_registry().register("classify_email", CLASSIFY_DEFINITION, handler)
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: add classify_email tool"
```

---

### Task 11: extract_todos tool

**Files:**
- Create: `src/email_agent/agent/tools/extract_todos.py`

- [ ] **Step 1: Implement extract_todos tool**

```python
# src/email_agent/agent/tools/extract_todos.py
import json
from email_agent.agent.tools.registry import get_registry

EXTRACT_DEFINITION = {
    "name": "extract_todos",
    "description": "从邮件中提取待办事项。每个待办包含内容和可选的截止日期。",
    "input_schema": {
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": "邮件的Message-ID",
            },
            "todos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "待办内容（中文）",
                        },
                        "due_date": {
                            "type": "string",
                            "description": "截止日期 YYYY-MM-DD，无则填null",
                        },
                        "source_line": {
                            "type": "string",
                            "description": "邮件中暗示此任务的原文",
                        },
                    },
                    "required": ["content", "due_date", "source_line"],
                },
                "description": "提取的待办事项列表",
            },
        },
        "required": ["message_id", "todos"],
    },
}


def register(memory):
    """Register extract_todos tool."""

    def handler(message_id: str, todos: list[dict]) -> str:
        from email_agent.memory.models import Task

        count = 0
        for todo in todos:
            task = Task(
                content=todo["content"],
                source_email_id=message_id,
                due_date=todo.get("due_date") if todo.get("due_date") and todo["due_date"] != "null" else None,
            )
            memory.save_task(task)
            count += 1

        return f"已从邮件提取 {count} 个待办事项"

    get_registry().register("extract_todos", EXTRACT_DEFINITION, handler)
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: add extract_todos tool"
```

---

### Task 12: search_by_date and query tools

**Files:**
- Create: `src/email_agent/agent/tools/scan_fetch.py`

- [ ] **Step 1: Implement search_by_date and query tools**

```python
# src/email_agent/agent/tools/scan_fetch.py
import logging
from email_agent.agent.tools.registry import get_registry

logger = logging.getLogger(__name__)

SEARCH_BY_DATE_DEFINITION = {
    "name": "search_by_date",
    "description": "按时间段拉取所有邮件（含已读）。对已存在于数据库的邮件复用已有分类。",
    "input_schema": {
        "type": "object",
        "properties": {
            "since": {
                "type": "string",
                "description": "起始日期 YYYY-MM-DD",
            },
            "before": {
                "type": "string",
                "description": "结束日期 YYYY-MM-DD",
            },
        },
        "required": ["since", "before"],
    },
}

GET_SENDER_HISTORY_DEFINITION = {
    "name": "get_sender_history",
    "description": "查询某发件人的历史邮件统计和最近邮件摘要。",
    "input_schema": {
        "type": "object",
        "properties": {
            "sender_email": {
                "type": "string",
                "description": "发件人邮箱地址",
            },
        },
        "required": ["sender_email"],
    },
}

GET_PENDING_TASKS_DEFINITION = {
    "name": "get_pending_tasks",
    "description": "获取当前所有未完成的待办事项列表。",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}


def register(adapter, memory):
    """Register search_by_date and query tools."""

    def search_by_date_handler(since: str, before: str) -> str:
        try:
            uids = adapter.search_by_date(since, before)
            if not uids:
                return f"{since} ~ {before} 期间没有邮件。"

            emails_info = []
            new_count = 0
            cached_count = 0

            for uid in uids[:100]:  # cap at 100 for performance
                msg_id = adapter.fetch_header(uid, "Message-ID")
                subject = adapter.fetch_header(uid, "Subject") or "(无主题)"

                if msg_id and memory.exists(msg_id):
                    cached_count += 1
                    emails_info.append(f"[已缓存] {subject}")
                else:
                    new_count += 1
                    emails_info.append(f"[待处理] {subject}")
                    # Don't fetch full body yet — let agent decide

            return (
                f"{since} ~ {before}: 共 {len(uids)} 封 ({len(emails_info)} 显示)\n"
                f"已缓存: {cached_count}, 待处理: {new_count}\n\n" +
                "\n".join(emails_info)
            )
        except Exception as e:
            return f"搜索失败: {e}"

    def get_sender_history_handler(sender_email: str) -> str:
        history = memory.get_sender_history(sender_email)
        if not history:
            return f"未找到 {sender_email} 的历史邮件。"

        urgent_count = sum(1 for e in history if e.priority == "urgent")
        high_count = sum(1 for e in history if e.priority == "high")
        categories = set(e.category for e in history)

        lines = [
            f"【{sender_email} 历史】",
            f"近 {len(history)} 封邮件: urgent: {urgent_count}, high: {high_count}",
            f"涉及分类: {', '.join(categories)}",
            "",
            "最近邮件:",
        ]
        for e in history[:5]:
            lines.append(f"  [{e.priority}] {e.subject} ({e.received_at})")
        return "\n".join(lines)

    def get_pending_tasks_handler() -> str:
        tasks = memory.get_pending_tasks()
        if not tasks:
            return "当前没有待办事项。"

        lines = [f"当前 {len(tasks)} 个待办:"]
        for t in tasks:
            due = f" | 截止: {t.due_date}" if t.due_date else ""
            lines.append(f"  - {t.content}{due}")
        return "\n".join(lines)

    get_registry().register("search_by_date", SEARCH_BY_DATE_DEFINITION,
                            search_by_date_handler)
    get_registry().register("get_sender_history", GET_SENDER_HISTORY_DEFINITION,
                            get_sender_history_handler)
    get_registry().register("get_pending_tasks", GET_PENDING_TASKS_DEFINITION,
                            get_pending_tasks_handler)
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: add search_by_date and query tools"
```

---

### Task 13: generate_report tool

**Files:**
- Create: `src/email_agent/agent/tools/report.py`

- [ ] **Step 1: Implement report tool**

```python
# src/email_agent/agent/tools/report.py
from email_agent.agent.tools.registry import get_registry

REPORT_DEFINITION = {
    "name": "generate_report",
    "description": "生成邮件报告（日报、周报或时间段报告）。生成的报告会自动保存到数据库。",
    "input_schema": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["daily", "weekly", "scan"],
                "description": "报告类型",
            },
            "period_start": {
                "type": "string",
                "description": "起始日期 YYYY-MM-DD",
            },
            "period_end": {
                "type": "string",
                "description": "结束日期 YYYY-MM-DD",
            },
            "content": {
                "type": "string",
                "description": "报告正文（Markdown格式，中文）",
            },
        },
        "required": ["type", "period_start", "period_end", "content"],
    },
}


def register(memory):
    """Register generate_report tool."""

    def handler(type: str, period_start: str, period_end: str, content: str) -> str:
        from email_agent.memory.models import Report

        report = Report(
            type=type,
            period_start=period_start,
            period_end=period_end,
            content=content,
        )
        memory.save_report(report)
        return f"报告已保存 ({type}, {period_start} ~ {period_end})"

    get_registry().register("generate_report", REPORT_DEFINITION, handler)
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: add generate_report tool"
```

---

### Task 14: Agent core loop

**Files:**
- Create: `src/email_agent/agent/core.py`
- Create: `tests/test_agent_core.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_agent_core.py
import pytest
from unittest.mock import MagicMock
from datetime import datetime
from email_agent.agent.core import Agent, ProcessResult
from email_agent.agent.tools.registry import ToolRegistry, get_registry
from email_agent.llm.client import ClaudeResponse, ToolUse
from email_agent.memory.models import Email


class MockLLM:
    """Controllable LLM for testing agent logic."""
    def __init__(self):
        self.responses = []
        self.calls = []

    def add_response(self, response: ClaudeResponse):
        self.responses.append(response)

    def send(self, system_prompt, messages, tools=None, max_retries=3):
        self.calls.append({"system": system_prompt, "messages": messages, "tools": tools})
        if self.responses:
            return self.responses.pop(0)
        return ClaudeResponse(text="done", stop_reason="end_turn")


@pytest.fixture
def mock_llm():
    return MockLLM()


@pytest.fixture
def sample_email():
    return Email(
        message_id="<test@163.com>",
        uid=1,
        sender_email="boss@company.com",
        sender_name="老板",
        subject="紧急会议",
        body="今天下午3点开会讨论Q3预算。",
        received_at=datetime(2026, 7, 27, 10, 0, 0),
    )


@pytest.fixture
def agent(mock_llm):
    registry = ToolRegistry()
    executed = {}

    registry.register("test_tool", {
        "name": "test_tool",
        "description": "A test tool",
        "input_schema": {"type": "object", "properties": {"arg": {"type": "string"}}, "required": ["arg"]},
    }, lambda arg: executed.update({"arg": arg}) or f"executed: {arg}")

    memory = MagicMock()
    memory.get_sender_history.return_value = []
    memory.get_pending_tasks.return_value = []

    return Agent(llm=mock_llm, registry=registry, memory=memory, max_turns=3)


class TestAgentLoop:
    def test_stops_on_text_response(self, agent, mock_llm, sample_email):
        """Agent should stop when Claude returns text without tool calls."""
        mock_llm.add_response(ClaudeResponse(
            text="已完成处理", stop_reason="end_turn", tool_uses=[]
        ))
        result = agent.process_email(sample_email)
        assert result.turns_used == 1
        assert result.force_stopped is False

    def test_executes_tool_and_continues(self, agent, mock_llm, sample_email):
        """Agent should execute tool call and send result back to Claude."""
        mock_llm.add_response(ClaudeResponse(
            text="",
            stop_reason="tool_use",
            tool_uses=[ToolUse(id="call_1", name="test_tool", input={"arg": "value1"})],
        ))
        mock_llm.add_response(ClaudeResponse(
            text="处理完成", stop_reason="end_turn", tool_uses=[]
        ))
        result = agent.process_email(sample_email)
        assert result.turns_used == 2
        assert len(result.tool_results) == 1

    def test_force_stop_at_max_turns(self, agent, mock_llm, sample_email):
        """Agent should force stop when max_turns is reached."""
        for _ in range(5):
            mock_llm.add_response(ClaudeResponse(
                text="",
                stop_reason="tool_use",
                tool_uses=[ToolUse(id="call_1", name="test_tool", input={"arg": "x"})],
            ))
        result = agent.process_email(sample_email)
        assert result.force_stopped is True
        assert result.turns_used == 3  # max_turns

    def test_unknown_tool_handled(self, agent, mock_llm, sample_email):
        """Agent should handle unknown tool gracefully."""
        mock_llm.add_response(ClaudeResponse(
            text="",
            stop_reason="tool_use",
            tool_uses=[ToolUse(id="call_1", name="nonexistent", input={})],
        ))
        mock_llm.add_response(ClaudeResponse(
            text="done", stop_reason="end_turn", tool_uses=[]
        ))
        result = agent.process_email(sample_email)
        assert result.turns_used == 2
        assert "unknown" in str(result.tool_results[0]).lower()

    def test_context_includes_sender_history(self, agent, mock_llm, sample_email):
        """Agent should include sender history in the context sent to Claude."""
        mock_llm.add_response(ClaudeResponse(
            text="done", stop_reason="end_turn", tool_uses=[]
        ))
        agent.process_email(sample_email)
        call = mock_llm.calls[0]
        messages_text = str(call["messages"])
        assert sample_email.subject in messages_text
        assert sample_email.sender_email in messages_text
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_agent_core.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement Agent core**

```python
# src/email_agent/agent/core.py
import logging
from dataclasses import dataclass, field
from email_agent.memory.models import Email, ProcessedEmail, SkippedEmail
from email_agent.prompts.system import build_system_prompt, build_classify_context
from email_agent.agent.tools.registry import ToolRegistry
from email_agent.llm.client import ClaudeClient, ClaudeResponse, ToolUse

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    email_id: str
    tool_results: list[str] = field(default_factory=list)
    turns_used: int = 0
    force_stopped: bool = False
    classification: dict | None = None


class Agent:
    def __init__(self, llm: ClaudeClient, registry: ToolRegistry,
                 memory, profile: str = "worker", max_turns: int = 5):
        self.llm = llm
        self.registry = registry
        self.memory = memory
        self.profile = profile
        self.max_turns = max_turns

    def process_email(self, email: Email) -> ProcessResult:
        """Process a single email through the agent loop."""
        result = ProcessResult(email_id=email.message_id)

        # Build initial context
        sender_history = self._format_sender_history(email.sender_email)
        pending_tasks = self._format_pending_tasks()

        email_info = (
            f"UID: {email.uid}\n"
            f"Message-ID: {email.message_id}\n"
            f"发件人: {email.sender_name} <{email.sender_email}>\n"
            f"主题: {email.subject}\n"
            f"时间: {email.received_at}\n"
            f"正文:\n{email.body}"
        )

        context = build_classify_context(email_info, sender_history, pending_tasks)
        system_prompt = build_system_prompt(self.profile)

        messages = [{"role": "user", "content": context}]

        for turn in range(self.max_turns):
            response = self.llm.send(
                system_prompt=system_prompt,
                messages=messages,
                tools=self.registry.get_definitions(),
            )

            if response.stop_reason != "tool_use":
                result.turns_used = turn + 1
                break

            # Execute tool calls
            tool_results_text = []
            for tool_use in response.tool_uses:
                tool_result = self.registry.execute(tool_use.name, tool_use.input)
                result.tool_results.append(tool_result)
                tool_results_text.append(
                    f"[{tool_use.name}] {tool_result}"
                )

                # Track classification results
                if tool_use.name == "classify_email":
                    result.classification = tool_use.input

            # Append tool results to conversation
            tool_result_content = []
            for i, tu in enumerate(response.tool_uses):
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result.tool_results[i],
                })

            messages.append({"role": "assistant", "content": [
                *[{"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input}
                  for tu in response.tool_uses],
            ]})
            messages.append({"role": "user", "content": tool_result_content})

        else:
            result.force_stopped = True
            result.turns_used = self.max_turns
            logger.warning("Email %s 达到 %d 轮上限，强制终止",
                           email.message_id, self.max_turns)

        return result

    def process_emails(self, emails: list[Email]) -> list[ProcessResult]:
        """Process multiple emails sequentially."""
        results = []
        skipped = []
        for email in emails:
            try:
                result = self.process_email(email)
                results.append(result)
            except Exception as e:
                logger.warning("跳过邮件 %s: %s", email.message_id, e)
                skipped.append(SkippedEmail(
                    message_id=email.message_id,
                    uid=email.uid,
                    sender_email=email.sender_email,
                    subject=email.subject,
                    reason=f"agent_failed: {e}",
                ))
                self.memory.save_skipped(skipped[-1])
        return results

    def generate_report_content(self, report_type: str, period_start: str,
                                period_end: str) -> str:
        """Generate a report using Claude."""
        from email_agent.prompts.system import build_report_context

        emails = self.memory.get_emails_in_range(period_start, period_end)
        tasks = self.memory.get_pending_tasks()

        email_data = self._format_email_list(emails)
        task_data = self._format_task_list(tasks)

        context = build_report_context(report_type, period_start, period_end,
                                       email_data, task_data)
        system_prompt = build_system_prompt(self.profile)

        response = self.llm.send(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": context}],
            tools=[],  # no tools for report generation
        )
        return response.text

    def detect_profile(self, metadata: str) -> dict:
        """Detect user profile from email metadata."""
        from email_agent.prompts.system import build_profile_detection_context

        context = build_profile_detection_context(metadata)
        response = self.llm.send(
            system_prompt="你是一个分析用户邮件模式的助手。返回JSON格式的分析结果。",
            messages=[{"role": "user", "content": context}],
            tools=[],
            max_tokens=512,
        )
        # Parse Claude's text response as best-effort JSON
        import json
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {
                "profile": "worker",
                "evidence": ["无法解析Claude的响应，使用默认角色"],
                "confidence": "low",
            }

    def _format_sender_history(self, sender_email: str) -> str:
        history = self.memory.get_sender_history(sender_email)
        if not history:
            return "（无历史记录）"

        urgent = sum(1 for e in history if e.priority == "urgent")
        high = sum(1 for e in history if e.priority == "high")
        lines = [
            f"近 7 天发了 {len(history)} 封邮件:",
            f"  urgent: {urgent} | high: {high}",
            "",
            "最近邮件:",
        ]
        for e in history[:10]:
            lines.append(f"  [{e.priority}] {e.subject} ({e.received_at})")
        return "\n".join(lines)

    def _format_pending_tasks(self) -> str:
        tasks = self.memory.get_pending_tasks()
        if not tasks:
            return "（无待办）"
        lines = [f"当前 {len(tasks)} 个待办:"]
        for t in tasks:
            due = f" | 截止: {t.due_date}" if t.due_date else ""
            lines.append(f"  - {t.content}{due}")
        return "\n".join(lines)

    def _format_email_list(self, emails: list) -> str:
        if not emails:
            return "（无邮件数据）"
        lines = []
        for e in emails:
            lines.append(
                f"[{e.priority}] {e.sender_name} <{e.sender_email}>\n"
                f"  主题: {e.subject}\n"
                f"  分类: {e.category} | 时间: {e.received_at}\n"
                f"  摘要: {e.summary}"
            )
        return "\n\n".join(lines)

    def _format_task_list(self, tasks: list) -> str:
        if not tasks:
            return "（无待办事项）"
        lines = []
        for t in tasks:
            due = f" | 截止: {t.due_date}" if t.due_date else ""
            lines.append(f"- [{t.status}] {t.content}{due}")
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_agent_core.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add agent core loop"
```

---

### Task 15: CLI

**Files:**
- Create: `src/email_agent/cli.py`

- [ ] **Step 1: Implement CLI**

```python
# src/email_agent/cli.py
import argparse
import sys
import time
import logging
from datetime import datetime, timedelta

from email_agent.config import load_config, save_config, validate_config
from email_agent.memory.store import MemoryStore
from email_agent.llm.client import ClaudeClient
from email_agent.email.imap_ import IMAPAdapter
from email_agent.agent.core import Agent
from email_agent.agent.tools.registry import get_registry

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        prog="email-agent",
        description="智能邮件助手 — 基于 Claude 的邮件分类、待办提取和报告生成",
    )
    sub = parser.add_subparsers(dest="command")

    # check
    check_p = sub.add_parser("check", help="处理所有未读邮件")
    check_p.add_argument("--dry-run", action="store_true", help="只统计不处理")
    check_p.add_argument("--verbose", "-v", action="store_true", help="显示详细处理过程")

    # scan
    scan_p = sub.add_parser("scan", help="按时间段筛选邮件并生成报告")
    scan_p.add_argument("--from", dest="from_date", help="起始日期 YYYY-MM-DD")
    scan_p.add_argument("--to", dest="to_date", help="结束日期 YYYY-MM-DD")
    scan_p.add_argument("--week", action="store_true", help="本周")
    scan_p.add_argument("--dry-run", action="store_true", help="只统计不生成报告")

    # report
    report_p = sub.add_parser("report", help="生成日报或周报")
    report_p.add_argument("--from", dest="from_date", help="起始日期 YYYY-MM-DD")
    report_p.add_argument("--to", dest="to_date", help="结束日期 YYYY-MM-DD")
    report_p.add_argument("--week", action="store_true", help="周报")

    # daemon
    daemon_p = sub.add_parser("daemon", help="后台持续运行")
    daemon_p.add_argument("--interval", type=int, default=300, help="检查间隔（秒）")
    daemon_p.add_argument("--report-at", default="20:00", help="每日报告时间")

    # setup
    sub.add_parser("setup", help="首次运行，自动检测角色")

    # help
    sub.add_parser("help", help="显示使用说明")

    args = parser.parse_args()

    if args.command is None or args.command == "help":
        _print_help()
        return

    # Load config
    config = load_config()

    if args.command == "setup":
        _cmd_setup(config)
        return

    # Validate config for commands that need it
    errors = validate_config(config)
    if errors:
        print("❌ 配置错误:")
        for e in errors:
            print(f"  - {e}")
        print("\n提示: 复制 config.yaml.example 为 config.yaml 并填入你的信息")
        sys.exit(1)

    # Initialize components
    memory = MemoryStore(config.memory.db_path)
    memory.init()

    llm = ClaudeClient(
        api_key=config.claude.api_key,
        model=config.claude.model,
    )

    # Register tools
    _register_tools(memory, config)

    agent = Agent(
        llm=llm,
        registry=get_registry(),
        memory=memory,
        profile=config.profile or "worker",
        max_turns=config.agent.max_turns,
    )

    if args.command == "check":
        _cmd_check(args, config, memory, agent)
    elif args.command == "scan":
        _cmd_scan(args, config, memory, agent)
    elif args.command == "report":
        _cmd_report(args, config, memory, agent)
    elif args.command == "daemon":
        _cmd_daemon(args, config, memory, agent)


def _cmd_setup(config):
    print("🔍 Email Agent — 首次设置\n")
    print("正在分析你的邮件，自动检测角色...\n")

    # Load config to get credentials
    errors = validate_config(config)
    if errors:
        print("⚠️ 请先配置邮箱和API密钥:")
        print("  1. 复制 config.yaml.example 为 config.yaml")
        print("  2. 填入你的 163 邮箱地址和SMTP授权码")
        print("  3. 填入你的 Claude API Key")
        return

    memory = MemoryStore(config.memory.db_path)
    memory.init()
    llm = ClaudeClient(api_key=config.claude.api_key, model=config.claude.model)

    try:
        adapter = IMAPAdapter(
            server=config.email.imap_server,
            port=config.email.imap_port,
            address=config.email.address,
            password=config.email.password,
        )
        adapter.connect()

        # Fetch metadata only (sender + subject, no body)
        uids = adapter.search_by_date(
            (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
        )

        if not uids:
            print("未找到最近30天的邮件。请确认邮箱配置正确。")
            return

        metadata_lines = []
        for uid in uids[:50]:
            sender = adapter.fetch_header(uid, "From") or "unknown"
            subject = adapter.fetch_header(uid, "Subject") or "(无主题)"
            metadata_lines.append(f"发件人: {sender} | 主题: {subject}")

        adapter.disconnect()

        # Use agent to detect profile
        agent = Agent(llm=llm, registry=get_registry(), memory=memory)
        result = agent.detect_profile("\n".join(metadata_lines))

        print(f"📊 根据最近 {min(len(uids), 50)} 封邮件的分析：\n")
        print(f"   你的角色很可能是【{result.get('profile', 'worker')}】\n")
        if result.get("evidence"):
            print("📋 证据:")
            for e in result["evidence"]:
                print(f"   • {e}")
        print()

        answer = input("   确认？[Y/n] ").strip().lower()
        if answer in ("", "y", "yes"):
            config.profile = result.get("profile", "worker")
            save_config(config)
            print(f"\n✅ 角色已保存为: {config.profile}")
            print("   运行 email-agent check 开始处理邮件")
        else:
            print("\n请手动编辑 config.yaml 设置 profile 字段")
            print("可选值: worker, jobseeker, professor")

    except Exception as e:
        print(f"❌ 设置失败: {e}")


def _cmd_check(args, config, memory, agent):
    adapter = None
    try:
        adapter = IMAPAdapter(
            server=config.email.imap_server,
            port=config.email.imap_port,
            address=config.email.address,
            password=config.email.password,
        )
        adapter.connect()

        print("📬 拉取未读邮件...")
        uids = adapter.search_unseen()

        if not uids:
            print("没有未读邮件。")
            return

        new_emails = []
        skipped_uids = []
        for uid in uids:
            try:
                msg_id = adapter.fetch_header(uid, "Message-ID")
                if msg_id and memory.exists(msg_id):
                    continue
                email = adapter.fetch_full(uid)
                new_emails.append(email)
            except Exception as e:
                logger.warning("跳过 UID %s: %s", uid, e)
                skipped_uids.append((uid, str(e)))

        print(f"📬 拉取到 {len(uids)} 封未读 | 新邮件: {len(new_emails)} | 已处理: {len(uids) - len(new_emails) - len(skipped_uids)}")

        if skipped_uids:
            print(f"⚠️  {len(skipped_uids)} 封无法读取")

        if args.dry_run:
            if new_emails:
                est_time = len(new_emails) * 3  # ~3s per email
                est_cost = len(new_emails) * 0.01  # ~$0.01 per email
                print(f"\n预计: 处理 {len(new_emails)} 封 | 耗时 ~{est_time}秒 | 费用 ~${est_cost:.2f}")
                print("确认执行: email-agent check (不带 --dry-run)")
            return

        if not new_emails:
            print("所有邮件已处理。")
            return

        print(f"\n🆕 开始处理 {len(new_emails)} 封新邮件...\n")

        results = agent.process_emails(new_emails)

        _print_check_summary(results, skipped_uids)

    except Exception as e:
        logger.error("Check failed: %s", e)
        raise
    finally:
        if adapter:
            adapter.disconnect()


def _print_check_summary(results, skipped_uids):
    total = len(results) + len(skipped_uids)
    success = sum(1 for r in results if not r.force_stopped)
    forced = sum(1 for r in results if r.force_stopped)

    print(f"\n{'='*50}")
    print(f"✅ 处理完成: {success}/{total} 封成功", end="")
    if forced:
        print(f" | ⚠️ {forced} 封达上限")
    else:
        print()

    # Classification summary
    classifications = {}
    todos_total = 0
    for r in results:
        if r.classification:
            pri = r.classification.get("priority", "unknown")
            classifications[pri] = classifications.get(pri, 0) + 1
        # Count extract_todos results
        for tr in r.tool_results:
            if "已从邮件提取" in str(tr):
                import re
                match = re.search(r"(\d+)", str(tr))
                if match:
                    todos_total += int(match.group(1))

    if classifications:
        parts = []
        for pri in ["urgent", "high", "normal", "low"]:
            if pri in classifications:
                emoji = {"urgent": "🔴", "high": "🟡", "normal": "🟢", "low": "⚪"}.get(pri, "")
                parts.append(f"{emoji}{pri}:{classifications[pri]}")
        print(f"  {' | '.join(parts)}")
        if todos_total:
            print(f"  📋 提取 {todos_total} 个待办事项")

    if skipped_uids:
        print(f"\n⚠️ {len(skipped_uids)} 封无法处理:")
        for uid, reason in skipped_uids:
            print(f"  📧 UID {uid} → {reason}")

    print(f"  ⏱️ 共处理 {total} 封")


def _cmd_scan(args, config, memory, agent):
    if args.week:
        today = datetime.now()
        since = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        before = today.strftime("%Y-%m-%d")
    elif args.from_date and args.to_date:
        since = args.from_date
        before = args.to_date
    else:
        print("请指定 --from 和 --to，或使用 --week")
        return

    print(f"📊 扫描邮件: {since} ~ {before}")

    adapter = IMAPAdapter(
        server=config.email.imap_server,
        port=config.email.imap_port,
        address=config.email.address,
        password=config.email.password,
    )
    adapter.connect()
    from email_agent.agent.tools.scan_fetch import register as register_scan_fetch
    register_scan_fetch(adapter, memory)
    uids = adapter.search_by_date(since, before)
    print(f"找到 {len(uids)} 封邮件")

    if args.dry_run:
        adapter.disconnect()
        return

    # Process uncached emails
    new_emails = []
    for uid in uids[:100]:
        msg_id = adapter.fetch_header(uid, "Message-ID")
        if msg_id and not memory.exists(msg_id):
            email = adapter.fetch_full(uid)
            new_emails.append(email)

    if new_emails:
        print(f"处理 {len(new_emails)} 封新邮件...")
        agent.process_emails(new_emails)

    adapter.disconnect()

    # Generate report
    print("生成报告...")
    report_content = agent.generate_report_content("scan", since, before)
    from email_agent.memory.models import Report
    memory.save_report(Report(type="scan", period_start=since, period_end=before, content=report_content))
    print(f"\n{report_content}")


def _cmd_report(args, config, memory, agent):
    today = datetime.now().strftime("%Y-%m-%d")

    if args.week:
        since = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
        before = today
        report_type = "weekly"
    elif args.from_date and args.to_date:
        since = args.from_date
        before = args.to_date
        report_type = "daily"
    else:
        since = today
        before = today
        report_type = "daily"

    print(f"📊 生成{report_type}报告: {since} ~ {before}")
    content = agent.generate_report_content(report_type, since, before)
    from email_agent.memory.models import Report
    memory.save_report(Report(type=report_type, period_start=since, period_end=before, content=content))
    print(f"\n{content}")


def _cmd_daemon(args, config, memory, agent):
    print(f"🤖 Email Agent 守护进程启动")
    print(f"   检查间隔: {args.interval}s")
    print(f"   日报时间: {args.report_at}")
    print(f"   Ctrl+C 退出\n")

    try:
        while True:
            try:
                _cmd_check(argparse.Namespace(dry_run=False, verbose=False),
                           config, memory, agent)
            except Exception as e:
                logger.error("Check error: %s", e)

            now = datetime.now()
            report_time = args.report_at
            if now.strftime("%H:%M") == report_time:
                try:
                    _cmd_report(
                        argparse.Namespace(from_date=None, to_date=None, week=False),
                        config, memory, agent,
                    )
                except Exception as e:
                    logger.error("Report error: %s", e)

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n👋 已退出")


def _register_tools(memory, config):
    """Register all tools with the registry."""
    # Lazy import tools to register them
    from email_agent.agent.tools import classify, extract_todos, report

    classify.register(memory)
    extract_todos.register(memory)
    report.register(memory)


def _print_help():
    print("""
╔══════════════════════════════════════════════╗
║           Email Agent — 智能邮件助手          ║
╚══════════════════════════════════════════════╝

用法:
  email-agent <命令> [参数]

命令:
  setup       首次运行，自动检测你的角色并配置
  check       处理所有未读邮件（分类 + 提取待办）
  scan        筛选指定时间段的邮件，生成报告
  report      生成日报或周报
  daemon      后台持续运行，定时处理邮件
  help        显示此帮助

示例:
  # 第一次使用
  email-agent setup

  # 日常检查邮件
  email-agent check
  email-agent check --dry-run    # 预览模式
  email-agent check --verbose    # 详细输出

  # 回顾过去一个月的邮件
  email-agent scan --from 2026-07-01 --to 2026-07-27
  email-agent scan --week

  # 生成报告
  email-agent report              # 日报
  email-agent report --week       # 周报

  # 让它自己跑（每5分钟检查一次）
  email-agent daemon --interval 300

配置:
  1. 复制 config.yaml.example 为 config.yaml
  2. 填入你的 163 邮箱地址和 SMTP 授权码
  3. 填入你的 Claude API Key
  4. (可选) 设置 profile: worker/jobseeker/professor
  5. 运行 email-agent setup 自动检测角色
""")
```

- [ ] **Step 2: Verify CLI runs**

```bash
cd "g:/Desktop/Email Agent"
python -m email_agent.cli help
python -m email_agent.cli --help
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add CLI with all commands"
```

---

### Task 16: Integration and README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

Write `README.md` covering:
- Project description (one paragraph)
- Quick start (clone, install, configure, run setup)
- Command reference
- Architecture overview (the four-layer diagram)
- Tech stack
- License

- [ ] **Step 2: Verify full install**

```bash
cd "g:/Desktop/Email Agent"
uv pip install -e ".[dev]"
python -c "import email_agent; from email_agent.cli import main; print('Full import OK')"
ruff check src/
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "docs: add README and finalize integration"
```

---

### Task 17: Integration tests

**Files:**
- Create: `tests/test_tools/test_classify.py`
- Create: `tests/test_tools/test_extract_todos.py`

- [ ] **Step 1: Write tool integration tests**

```python
# tests/test_tools/test_classify.py
"""Integration tests for classify_email tool using seed emails.
These require a real Claude API key and incur costs. Run manually."""
import pytest
from email_agent.agent.tools.registry import ToolRegistry, get_registry
from email_agent.agent.tools.classify import register as register_classify


@pytest.fixture
def registry():
    return ToolRegistry()


@pytest.mark.integration
class TestClassifyIntegration:
    """Seed email tests. Run with: pytest -m integration"""

    def test_urgent_from_boss(self, registry):
        """Email from boss with deadline → urgent"""
        # This test requires a real Claude API key in the environment
        # and will incur API costs (~$0.01)
        pass  # Run manually with real API

    def test_newsletter_is_low(self, registry):
        """Newsletter → low priority"""
        pass

    def test_extract_interview_todo(self, registry):
        """Interview invitation → extract date and action"""
        pass
```

- [ ] **Step 2: Mark integration tests**

```toml
# Add to pyproject.toml [tool.pytest.ini_options]
markers = [
    "integration: tests that call real Claude API (slow, costs money)",
]
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "test: add integration test scaffolding"
```
