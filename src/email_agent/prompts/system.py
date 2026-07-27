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
