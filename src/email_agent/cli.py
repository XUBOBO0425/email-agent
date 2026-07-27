# src/email_agent/cli.py
import argparse
import sys
import time
import logging
from datetime import datetime, timedelta

from email_agent.config import load_config, save_config, validate_config
from email_agent.memory.store import MemoryStore
from email_agent.llm.client import ClaudeClient
from email_agent.llm.deepseek_client import DeepSeekClient
from email_agent.email.imap_ import IMAPAdapter
from email_agent.agent.core import Agent
from email_agent.agent.tools.registry import get_registry

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        prog="email-agent",
        description="智能邮件助手",
    )
    sub = parser.add_subparsers(dest="command")

    check_p = sub.add_parser("check", help="处理所有未读邮件")
    check_p.add_argument("--dry-run", action="store_true")
    check_p.add_argument("--verbose", "-v", action="store_true")

    scan_p = sub.add_parser("scan", help="按时间段筛选邮件并生成报告")
    scan_p.add_argument("--from", dest="from_date")
    scan_p.add_argument("--to", dest="to_date")
    scan_p.add_argument("--week", action="store_true")
    scan_p.add_argument("--dry-run", action="store_true")

    report_p = sub.add_parser("report", help="生成日报或周报")
    report_p.add_argument("--from", dest="from_date")
    report_p.add_argument("--to", dest="to_date")
    report_p.add_argument("--week", action="store_true")

    daemon_p = sub.add_parser("daemon", help="后台持续运行")
    daemon_p.add_argument("--interval", type=int, default=300)
    daemon_p.add_argument("--report-at", default="20:00")

    sub.add_parser("setup", help="首次运行，自动检测角色")
    sub.add_parser("help", help="显示使用说明")

    args = parser.parse_args()

    if args.command is None or args.command == "help":
        _print_help()
        return

    config = load_config()

    if args.command == "setup":
        _cmd_setup(config)
        return

    errors = validate_config(config)
    if errors:
        print("配置错误:")
        for e in errors:
            print(f"  - {e}")
        print("\n提示: 复制 config.yaml.example 为 config.yaml")
        sys.exit(1)

    memory = MemoryStore(config.memory.db_path)
    memory.init()

    llm = _create_llm_client(config)

    _register_tools(memory)

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
    print("Email Agent — 首次设置\n")
    print("正在分析你的邮件，自动检测角色...\n")

    errors = validate_config(config)
    if errors:
        print("请先配置邮箱和API密钥:")
        print("  1. 复制 config.yaml.example 为 config.yaml")
        print("  2. 填入 163 邮箱地址和SMTP授权码")
        print("  3. 填入 Claude API Key")
        return

    memory = MemoryStore(config.memory.db_path)
    memory.init()
    llm = _create_llm_client(config)

    try:
        adapter = IMAPAdapter(
            server=config.email.imap_server,
            port=config.email.imap_port,
            address=config.email.address,
            password=config.email.password,
        )
        adapter.connect()

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

        agent = Agent(llm=llm, registry=get_registry(), memory=memory)
        result = agent.detect_profile("\n".join(metadata_lines))

        print(f"根据最近 {min(len(uids), 50)} 封邮件的分析：\n")
        print(f"   你的角色很可能是【{result.get('profile', 'worker')}】\n")
        if result.get("evidence"):
            print("证据:")
            for e in result["evidence"]:
                print(f"   • {e}")
        print()

        answer = input("   确认？[Y/n] ").strip().lower()
        if answer in ("", "y", "yes"):
            config.profile = result.get("profile", "worker")
            save_config(config)
            print(f"\n角色已保存为: {config.profile}")
            print("   运行 email-agent check 开始处理邮件")
        else:
            print("\n请手动编辑 config.yaml 设置 profile 字段")
            print("可选值: worker, jobseeker, professor")

    except Exception as e:
        print(f"设置失败: {e}")


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

        print("拉取未读邮件...")
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

        print(f"拉取到 {len(uids)} 封未读 | 新邮件: {len(new_emails)} | 已处理: {len(uids) - len(new_emails) - len(skipped_uids)}")

        if skipped_uids:
            print(f" {len(skipped_uids)} 封无法读取")

        if args.dry_run:
            if new_emails:
                est_time = len(new_emails) * 3
                est_cost = len(new_emails) * 0.01
                print(f"\n预计: 处理 {len(new_emails)} 封 | 耗时 ~{est_time}秒 | 费用 ~${est_cost:.2f}")
                print("确认执行: email-agent check (不带 --dry-run)")
            return

        if not new_emails:
            print("所有邮件已处理。")
            return

        print(f"\n开始处理 {len(new_emails)} 封新邮件...\n")

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
    print(f"处理完成: {success}/{total} 封成功", end="")
    if forced:
        print(f" | {forced} 封达上限")
    else:
        print()

    classifications = {}
    todos_total = 0
    for r in results:
        if r.classification:
            pri = r.classification.get("priority", "unknown")
            classifications[pri] = classifications.get(pri, 0) + 1
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

    print(f"扫描邮件: {since} ~ {before}")

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

    print(f"生成{report_type}报告: {since} ~ {before}")
    content = agent.generate_report_content(report_type, since, before)
    from email_agent.memory.models import Report
    memory.save_report(Report(type=report_type, period_start=since, period_end=before, content=content))
    print(f"\n{content}")


def _cmd_daemon(args, config, memory, agent):
    print(f"Email Agent 守护进程启动")
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
            if now.strftime("%H:%M") == args.report_at:
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


def _create_llm_client(config):
    """Create the appropriate LLM client based on config.provider."""
    if config.provider == "deepseek":
        return DeepSeekClient(
            api_key=config.deepseek.api_key,
            model=config.deepseek.model,
            base_url=config.deepseek.base_url,
        )
    else:
        return ClaudeClient(
            api_key=config.claude.api_key,
            model=config.claude.model,
        )


def _register_tools(memory):
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


if __name__ == "__main__":
    main()
