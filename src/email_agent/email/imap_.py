import imaplib
import email
import logging
from email.header import decode_header
from datetime import datetime, timedelta
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
        since_fmt = _format_imap_date(since)
        before_fmt = _format_imap_date(before)
        next_day = _next_day(before)
        criteria = f'(SINCE "{since_fmt}" BEFORE "{_format_imap_date(next_day)}")'
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


# Helper functions

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
