"""酒店选择代理 (Hotel Agent).

LLM 默认为智谱 GLM (zai/glm-4.7-flash, 免费额度).
"""

from __future__ import annotations

from crewai import Agent

from .llm_factory import default_llm


def create_hotel_agent() -> Agent:
    """创建酒店选择代理.

    Returns:
        Agent: 负责酒店筛选与推荐的 ``Agent`` 实例.
    """
    return Agent(
        role="酒店选择专家",  # Hotel Selection Specialist
        goal=(
            "在用户预算约束下推荐 3-5 家酒店, 覆盖不同价位档次, "
            "并说明每家酒店的位置优势 (靠近景点/交通枢纽) 与大致每晚价格."
        ),
        backstory=(
            "你做过十年酒店预订与住宿评测, 熟悉各大城市不同区域的生活便利度. "
            "你会优先考虑交通通达性与用户行程的动线合理性, 而不是只看装修风格, "
            "并会坦诚说明淡旺季的价格波动."
        ),
        llm=default_llm(),
        verbose=True,
    )