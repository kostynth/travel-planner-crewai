"""酒店选择代理 (Hotel Agent)."""

from __future__ import annotations

from crewai import Agent


def create_hotel_agent() -> Agent:
    """创建酒店选择代理.

    Returns:
        Agent: 负责酒店筛选与推荐的 ``Agent`` 实例.
    """
    return Agent(
        role="酒店选择专家",  # Hotel Selection Specialist
        goal="",  # 占位
        backstory="",  # 占位
        verbose=True,
    )
