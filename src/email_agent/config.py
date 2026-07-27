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
