"""预算分析代理 (Budget Agent).

LLM 默认为智谱 GLM (zai/glm-4.7-flash, 免费额度).
"""

from __future__ import annotations

from crewai import Agent

from .llm_factory import default_llm


def create_budget_agent() -> Agent:
    """创建预算分析代理.

    Returns:
        Agent: 负责分项预算与总额计算的 ``Agent`` 实例.
    """
    return Agent(
        role="预算分析师",  # Budget Analyst
        goal=(
            "按住宿/交通/餐饮/门票/其他分类核算总花费, "
            "给出每类的预估金额、占总预算比例与总额, "
            "并在超出预算时明确指出需要削减的项目."
        ),
        backstory=(
            "你擅长把模糊的'三天两晚, 预算五千'拆解成可执行的账目. "
            "你会按当地真实物价估算, 预留 10% 应急金, "
            "并在发现行程过于奢侈时主动提出更经济的替代方案."
        ),
        llm=default_llm(),
        verbose=True,
    )