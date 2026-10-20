"""数据可视化代理 (Visualizer)."""

from __future__ import annotations

from crewai import Agent


def create_visualizer_agent() -> Agent:
    """创建数据可视化代理.

    Returns:
        Agent: 负责为 Plotly 准备图表数据的 ``Agent`` 实例.
    """
    return Agent(
        role="数据可视化专家",  # Data Visualization Specialist
        goal="",  # 占位
        backstory="",  # 占位
        verbose=True,
    )
