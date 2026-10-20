"""所有 CrewAI 代理的工厂函数集合.

每个子模块导出一个 ``create_*_agent() -> Agent`` 工厂函数。
"""

from .budget_agent import create_budget_agent
from .coordinator import create_coordinator_agent
from .hotel_agent import create_hotel_agent
from .qa_reviewer import create_qa_reviewer_agent
from .report_writer import create_report_writer_agent
from .route_agent import create_route_agent
from .social_crawler import create_social_crawler_agent
from .visualizer import create_visualizer_agent
from .web_researcher import create_web_researcher_agent

__all__ = [
    "create_coordinator_agent",
    "create_web_researcher_agent",
    "create_social_crawler_agent",
    "create_hotel_agent",
    "create_route_agent",
    "create_budget_agent",
    "create_visualizer_agent",
    "create_report_writer_agent",
    "create_qa_reviewer_agent",
]
