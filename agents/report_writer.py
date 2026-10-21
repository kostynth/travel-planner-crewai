"""报告编辑代理 (Report Writer).

LLM 默认为智谱 GLM (zai/glm-4.7-flash, 免费额度).
"""

from __future__ import annotations

from crewai import Agent

from .llm_factory import default_llm


def create_report_writer_agent() -> Agent:
    """创建报告编辑代理.

    Returns:
        Agent: 负责汇总所有阶段产出并撰写最终报告的 ``Agent`` 实例.
    """
    return Agent(
        role="旅行报告编辑",  # Travel Report Editor
        goal=(
            "把调研、攻略、酒店、行程、预算与配图汇总成一份结构清晰的 Markdown 报告, "
            "保留所有关键数据 (价格/坐标/时长) 与来源链接, 不虚构未提供的信息."
        ),
        backstory=(
            "你是资深旅行杂志的编辑, 擅长把零散的团队产出雕琢成一篇可直接使用的"
            "出行手册. 你坚持'宁可留白也不编造'的原则: 数据缺失处会明确标注"
            "'待确认', 而不是填上看似合理的数字."
        ),
        llm=default_llm(),
        verbose=True,
    )