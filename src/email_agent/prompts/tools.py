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
