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
