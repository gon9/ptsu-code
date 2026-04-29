"""Session Memory のデフォルトテンプレート。

Claude Code の DEFAULT_SESSION_MEMORY_TEMPLATE に準拠した 10 セクション構成。
italic _descriptions_ はテンプレート指示であり、LLM が編集してはならない部分。
"""

DEFAULT_TEMPLATE: str = """# Session Title
_A short and distinctive 5-10 word descriptive title for the session. Super info dense, no filler_

# Current State
_What is actively being worked on right now? Pending tasks not yet completed. Immediate next steps._

# Task specification
_What did the user ask to build? Any design decisions or other explanatory context_

# Files and Functions
_What are the important files? In short, what do they contain and why are they relevant?_

# Workflow
_What bash commands are usually run and in what order? How to interpret their output if not obvious?_

# Errors & Corrections
_Errors encountered and how they were fixed. What did the user correct? What approaches failed and should not be tried again?_

# Codebase and System Documentation
_What are the important system components? How do they work/fit together?_

# Learnings
_What has worked well? What has not? What to avoid? Do not duplicate items from other sections_

# Key results
_If the user asked a specific output such as an answer to a question, a table, or other document, repeat the exact result here_

# Worklog
_Step by step, what was attempted, done? Very terse summary for each step_
"""

REQUIRED_SECTIONS: tuple[str, ...] = (
    "# Session Title",
    "# Current State",
    "# Task specification",
    "# Files and Functions",
    "# Workflow",
    "# Errors & Corrections",
    "# Codebase and System Documentation",
    "# Learnings",
    "# Key results",
    "# Worklog",
)


def is_empty(content: str) -> bool:
    """メモリ内容がテンプレートのみかどうかを判定する。

    Args:
        content: チェック対象の文字列

    Returns:
        テンプレートと一致していれば True（実際の内容がなければ True）
    """
    return content.strip() == DEFAULT_TEMPLATE.strip()


def has_required_sections(content: str) -> bool:
    """メモリ内容に必要なセクションが全て含まれているか確認する。

    Args:
        content: チェック対象の文字列

    Returns:
        全セクションが含まれていれば True
    """
    return all(section in content for section in REQUIRED_SECTIONS)
