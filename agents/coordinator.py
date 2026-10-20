"""协调者代理 (Coordinator).

负责解析用户请求并向团队其他成员分派任务。
"""

from __future__ import annotations

from crewai import Agent


def create_coordinator_agent() -> Agent:
    """创建协调者代理.

    Returns:
        Agent: 配置完成的 CrewAI ``Agent`` 实例.
    """
    return Agent(
        role="旅行计划协调员",  # Travel Planner Coordinator
        goal="",  # 占位
        backstory="",  # 占位
        allow_delegation=True,
        verbose=True,
    )
