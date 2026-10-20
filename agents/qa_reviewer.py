"""质量评审代理 (QA Reviewer)."""

from __future__ import annotations

from crewai import Agent


def create_qa_reviewer_agent() -> Agent:
    """创建质量评审代理.

    Returns:
        Agent: 负责评估报告质量并提出修改建议的 ``Agent`` 实例.
    """
    return Agent(
        role="质量保证审稿人",  # Quality Assurance Reviewer
        goal="",  # 占位
        backstory="",  # 占位
        verbose=True,
    )
