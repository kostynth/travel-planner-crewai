"""协调者代理 (Coordinator).

负责解析用户请求并向团队其他成员分派任务.
LLM 默认为智谱 GLM (zai/glm-4.7-flash, 免费额度).
"""

from __future__ import annotations

from crewai import Agent

from .llm_factory import default_llm


def create_coordinator_agent() -> Agent:
    """创建协调者代理.

    Returns:
        Agent: 配置完成的 CrewAI ``Agent`` 实例.
    """
    return Agent(
        role="旅行计划协调员",  # Travel Planner Coordinator
        goal=(
            "将用户的口语化出行需求解析为结构化的行程要素 "
            "(城市、天数、预算、景点类别偏好), 并把控整条流水线的进度与质量."
        ),
        backstory=(
            "你是经验丰富的旅行规划项目经理, 擅长与客户沟通并把模糊的愿望"
            "翻译成可执行的任务清单. 你会向下游研究员、酒店专员、路线规划师等"
            "同事分发需求, 并在他们交付后进行汇总与审阅."
        ),
        llm=default_llm(),
        allow_delegation=True,
        verbose=True,
    )