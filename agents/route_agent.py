"""行程规划代理 (Route Agent)."""

from __future__ import annotations

from crewai import Agent


def create_route_agent() -> Agent:
    """创建行程规划代理.

    Returns:
        Agent: 负责逐日路线规划的 ``Agent`` 实例.
    """
    return Agent(
        role="行程规划专家",  # Route Planning Specialist
        goal="",  # 占位
        backstory="",  # 占位
        verbose=True,
    )
