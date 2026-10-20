"""报告编辑代理 (Report Writer)."""

from __future__ import annotations

from crewai import Agent


def create_report_writer_agent() -> Agent:
    """创建报告编辑代理.

    Returns:
        Agent: 负责汇总所有阶段产出并撰写最终报告的 ``Agent`` 实例.
    """
    return Agent(
        role="旅行报告编辑",  # Travel Report Editor
        goal="",  # 占位
        backstory="",  # 占位
        verbose=True,
    )
