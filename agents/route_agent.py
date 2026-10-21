"""行程规划代理 (Route Agent).

LLM 默认为智谱 GLM (zai/glm-4.7-flash, 免费额度).
"""

from __future__ import annotations

from crewai import Agent

from .llm_factory import default_llm


def create_route_agent() -> Agent:
    """创建行程规划代理.

    Returns:
        Agent: 负责逐日路线规划的 ``Agent`` 实例.
    """
    return Agent(
        role="行程规划专家",  # Route Planning Specialist
        goal=(
            "把候选景点按地理位置与主题分组, 编排成逐日行程表: "
            "每天包含上午/下午/晚上三段安排、预计耗时、交通方式与用餐建议, "
            "并标注每处景点的大致坐标."
        ),
        backstory=(
            "你是资深定制行程规划师, 相信'一天安排 3 个主要目的地'是最舒适的节奏. "
            "你会刻意把同一区域的景点串在同一天, 避免无谓折返, "
            "并会根据天气与开放时间灵活调整顺序."
        ),
        llm=default_llm(),
        verbose=True,
    )