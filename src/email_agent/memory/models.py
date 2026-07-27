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
