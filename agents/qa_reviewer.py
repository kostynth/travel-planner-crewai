"""质量评审代理 (QA Reviewer).

LLM 默认为智谱 GLM (zai/glm-4.7-flash, 免费额度).
"""

from __future__ import annotations

from crewai import Agent

from .llm_factory import default_llm


def create_qa_reviewer_agent() -> Agent:
    """创建质量评审代理.

    Returns:
        Agent: 负责评估报告质量并提出修改建议的 ``Agent`` 实例.
    """
    return Agent(
        role="质量保证审稿人",  # Quality Assurance Reviewer
        goal=(
            "按信息完整性、预算一致性、行程可行性、时效性与数据可信度五项标准"
            "评审报告, 指出具体缺陷位置, 给出 1-10 分评分与可执行的修改清单."
        ),
        backstory=(
            "你是严谨的质量审核员, 见过太多因为'预算对不上''景点当天闭馆'"
            "而导致行程报废的报告. 你会逐条比对报告中的数字, "
            "任何前后矛盾的地方都会明确标出并要求修正."
        ),
        llm=default_llm(),
        verbose=True,
    )