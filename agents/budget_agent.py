"""预算分析代理 (Budget Agent)."""

from __future__ import annotations

from crewai import Agent


def create_budget_agent() -> Agent:
    """创建预算分析代理.

    Returns:
        Agent: 负责分项预算与总额计算的 ``Agent`` 实例.
    """
    return Agent(
        role="预算分析师",  # Budget Analyst
        goal="",  # 占位
        backstory="",  # 占位
        verbose=True,
    )
