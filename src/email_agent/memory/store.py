import sqlite3
import os
from datetime import datetime
from email_agent.memory.models import ProcessedEmail, Task, SkippedEmail, Report


def _row_to_processed_email(row) -> ProcessedEmail:
    return ProcessedEmail(
        message_id=row["message_id"],
        uid=row["uid"],
        sender_email=row["sender_email"],
        sender_name=row["sender_name"],
        subject=row["subject"],
        body=row["body"],
        received_at=datetime.fromisoformat(row["received_at"]),
        category=row["category"],
        priority=row["priority"],
        summary=row["summary"],
        classification_reason=row["classification_reason"],
    )


def _row_to_task(row) -> Task:
    return Task(
        id=row["id"],
        content=row["content"],
        source_email_id=row["source_email_id"],
        due_date=row["due_date"],
        status=row["status"],
        created_at=row["created_at"],
    )


def _row_to_skipped(row) -> SkippedEmail:
    return SkippedEmail(
        message_id=row["message_id"],
        uid=row["uid"],
        sender_email=row["sender_email"],
        subject=row["subject"],
        reason=row["reason"],
        skipped_at=row["skipped_at"],
    )


def _row_to_report(row) -> Report:
    return Report(
        id=row["id"],
        type=row["type"],
        period_start=row["period_start"],
        period_end=row["period_end"],
        content=row["content"],
        created_at=row["created_at"],
    )


class MemoryStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    def init(self):
        dirname = os.path.dirname(self.db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS processed_emails (
                message_id TEXT PRIMARY KEY,
                uid INTEGER NOT NULL,
                sender_email TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                received_at TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                summary TEXT NOT NULL,
                classification_reason TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_processed_sender
                ON processed_emails(sender_email, received_at DESC);

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source_email_id TEXT NOT NULL,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS skipped_emails (
                message_id TEXT PRIMARY KEY,
                uid INTEGER NOT NULL,
                sender_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                reason TEXT NOT NULL,
                skipped_at TEXT
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT
            );
        """)
        self.conn.commit()

    # ── ProcessedEmail ──────────────────────────────────────────────

    def exists(self, message_id: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM processed_emails WHERE message_id = ?", (message_id,)
        )
        return cur.fetchone() is not None

    def save_email(self, email: ProcessedEmail):
        self.conn.execute(
            """INSERT OR IGNORE INTO processed_emails
               (message_id, uid, sender_email, sender_name, subject, body,
                received_at, category, priority, summary, classification_reason)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                email.message_id,
                email.uid,
                email.sender_email,
                email.sender_name,
                email.subject,
                email.body,
                email.received_at.isoformat(),
                email.category,
                email.priority,
                email.summary,
                email.classification_reason,
            ),
        )
        self.conn.commit()

    def get_sender_history(self, sender_email: str, limit: int = 10) -> list[ProcessedEmail]:
        cur = self.conn.execute(
            """SELECT * FROM processed_emails
               WHERE sender_email = ?
               ORDER BY received_at DESC
               LIMIT ?""",
            (sender_email, limit),
        )
        return [_row_to_processed_email(row) for row in cur.fetchall()]

    def get_emails_in_range(self, since: str, before: str) -> list[ProcessedEmail]:
        cur = self.conn.execute(
            """SELECT * FROM processed_emails
               WHERE received_at >= ? AND received_at <= ?
               ORDER BY received_at DESC""",
            (since, before),
        )
        return [_row_to_processed_email(row) for row in cur.fetchall()]

    # ── Task ─────────────────────────────────────────────────────────

    def save_task(self, task: Task):
        cur = self.conn.execute(
            """INSERT INTO tasks (content, source_email_id, due_date, status, created_at)
               VALUES (?,?,?,?,?)""",
            (task.content, task.source_email_id, task.due_date, task.status, task.created_at),
        )
        task.id = cur.lastrowid
        self.conn.commit()

    def get_pending_tasks(self) -> list[Task]:
        cur = self.conn.execute(
            "SELECT * FROM tasks WHERE status = 'pending' ORDER BY id"
        )
        return [_row_to_task(row) for row in cur.fetchall()]

    def get_tasks_by_email(self, message_id: str) -> list[Task]:
        cur = self.conn.execute(
            "SELECT * FROM tasks WHERE source_email_id = ? ORDER BY id",
            (message_id,),
        )
        return [_row_to_task(row) for row in cur.fetchall()]

    def mark_task_done(self, task_id: int):
        self.conn.execute(
            "UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,)
        )
        self.conn.commit()

    # ── SkippedEmail ─────────────────────────────────────────────────

    def save_skipped(self, skipped: SkippedEmail):
        self.conn.execute(
            """INSERT OR REPLACE INTO skipped_emails
               (message_id, uid, sender_email, subject, reason, skipped_at)
               VALUES (?,?,?,?,?,?)""",
            (
                skipped.message_id,
                skipped.uid,
                skipped.sender_email,
                skipped.subject,
                skipped.reason,
                skipped.skipped_at,
            ),
        )
        self.conn.commit()

    def get_skipped_emails(self, since: str | None = None) -> list[SkippedEmail]:
        if since is not None:
            cur = self.conn.execute(
                "SELECT * FROM skipped_emails WHERE skipped_at >= ? ORDER BY skipped_at DESC",
                (since,),
            )
        else:
            cur = self.conn.execute(
                "SELECT * FROM skipped_emails ORDER BY skipped_at DESC"
            )
        return [_row_to_skipped(row) for row in cur.fetchall()]

    # ── Report ───────────────────────────────────────────────────────

    def save_report(self, report: Report):
        cur = self.conn.execute(
            """INSERT INTO reports (type, period_start, period_end, content, created_at)
               VALUES (?,?,?,?,?)""",
            (report.type, report.period_start, report.period_end, report.content, report.created_at),
        )
        report.id = cur.lastrowid
        self.conn.commit()

    def get_reports(self, type: str, limit: int = 10) -> list[Report]:
        cur = self.conn.execute(
            "SELECT * FROM reports WHERE type = ? ORDER BY id DESC LIMIT ?",
            (type, limit),
        )
        return [_row_to_report(row) for row in cur.fetchall()]
