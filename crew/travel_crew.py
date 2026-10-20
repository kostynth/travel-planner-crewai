"""旅行计划 CrewAI 编排器.

将所有代理串联成一条 9 步的流水线，并对外暴露 ``run`` 入口。
"""

from __future__ import annotations

import logging
from typing import Any

from crewai import Crew, Process, Task

from agents.budget_agent import create_budget_agent
from agents.coordinator import create_coordinator_agent
from agents.hotel_agent import create_hotel_agent
from agents.qa_reviewer import create_qa_reviewer_agent
from agents.report_writer import create_report_writer_agent
from agents.route_agent import create_route_agent
from agents.social_crawler import create_social_crawler_agent
from agents.visualizer import create_visualizer_agent
from agents.web_researcher import create_web_researcher_agent

logger = logging.getLogger(__name__)


class TravelPlannerCrew:
    """旅行计划多代理编排器.

    串联 9 个代理: 解析 → 网络调研 → 社交抓取 → 酒店 → 路线 → 预算
    → 可视化 → 报告 → 质量审核.
    """

    def __init__(self) -> None:
        # 通过工厂函数创建所有代理
        self.coordinator = create_coordinator_agent()
        self.web_researcher = create_web_researcher_agent()
        self.social_crawler = create_social_crawler_agent()
        self.hotel_agent = create_hotel_agent()
        self.route_agent = create_route_agent()
        self.budget_agent = create_budget_agent()
        self.visualizer = create_visualizer_agent()
        self.report_writer = create_report_writer_agent()
        self.qa_reviewer = create_qa_reviewer_agent()

    # ------------------------------------------------------------------
    # 任务编排
    # ------------------------------------------------------------------
    def create_tasks(self, user_request: dict[str, Any]) -> list[Task]:
        """根据用户请求生成 9 个串行任务.

        Args:
            user_request: 形如 ``{"city", "days", "budget", "preferences"}`` 的字典.

        Returns:
            list[Task]: 带有依赖关系的 CrewAI 任务列表.
        """
        # 1. 解析用户请求
        task_parse = Task(
            description=self._format_description("解析用户请求并明确行程目标.", user_request),
            expected_output="结构化的 JSON: city / days / budget / preferences.",
            agent=self.coordinator,
        )

        # 2. 网络调研
        task_web = Task(
            description=self._format_description(
                "搜集城市概览: 景点、季节、签证、注意事项.", user_request
            ),
            expected_output="来源链接列表 + 简要摘要.",
            agent=self.web_researcher,
            context=[task_parse],
        )

        # 3. 社交抓取 + 本地专家
        task_social = Task(
            description=self._format_description(
                "从小红书抓取本地攻略, 通过高德地图获取 POI 与路线.", user_request
            ),
            expected_output="本地推荐清单 + POI 列表.",
            agent=self.social_crawler,
            context=[task_parse],
        )

        # 4. 酒店选择
        task_hotels = Task(
            description=self._format_description(
                "在预算范围内推荐 3-5 家酒店.", user_request
            ),
            expected_output="JSON: 酒店列表及价格区间.",
            agent=self.hotel_agent,
            context=[task_web, task_social],
        )

        # 5. 行程规划
        task_route = Task(
            description=self._format_description(
                "结合酒店与 POI 生成逐日行程表.", user_request
            ),
            expected_output="逐日行程 (含时间与坐标).",
            agent=self.route_agent,
            context=[task_hotels],
        )

        # 6. 预算计算
        task_budget = Task(
            description=self._format_description(
                "按类别 (住宿/交通/餐饮/娱乐) 计算预算.", user_request
            ),
            expected_output="分项预算表 + 总额.",
            agent=self.budget_agent,
            context=[task_route],
        )

        # 7. 可视化数据准备
        task_visualize = Task(
            description=self._format_description(
                "为 Plotly 准备图表数据: 预算分布、行程时间线.", user_request
            ),
            expected_output="Plotly 图表所需的 JSON 数据.",
            agent=self.visualizer,
            context=[task_budget],
        )

        # 8. 最终报告
        task_report = Task(
            description=self._format_description(
                "汇总所有阶段产出, 生成 Markdown 报告.", user_request
            ),
            expected_output="包含所有章节的 Markdown 报告.",
            agent=self.report_writer,
            context=[
                task_parse,
                task_web,
                task_social,
                task_hotels,
                task_route,
                task_budget,
                task_visualize,
            ],
        )

        # 9. 质量审核
        task_qa = Task(
            description=self._format_description(
                "按 5 项标准评审报告质量并提出修改建议.", user_request
            ),
            expected_output="修改建议清单 + 质量评分.",
            agent=self.qa_reviewer,
            context=[task_report],
        )

        return [
            task_parse,
            task_web,
            task_social,
            task_hotels,
            task_route,
            task_budget,
            task_visualize,
            task_report,
            task_qa,
        ]

    # ------------------------------------------------------------------
    # 启动入口
    # ------------------------------------------------------------------
    def run(self, user_request: dict[str, Any]) -> Any:
        """启动整个流水线.

        Args:
            user_request: 形如 ``{"city", "days", "budget", "preferences"}`` 的字典.

        Returns:
            Any: ``Crew.kickoff`` 的执行结果.
        """
        tasks = self.create_tasks(user_request)
        crew = Crew(
            agents=[
                self.coordinator,
                self.web_researcher,
                self.social_crawler,
                self.hotel_agent,
                self.route_agent,
                self.budget_agent,
                self.visualizer,
                self.report_writer,
                self.qa_reviewer,
            ],
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )
        logger.info("启动 TravelPlannerCrew, 请求: %s", user_request)
        return crew.kickoff(inputs=user_request)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    @staticmethod
    def _format_description(base: str, user_request: dict[str, Any]) -> str:
        """将用户请求参数拼接到任务描述中.

        Args:
            base: 任务的中文描述主体.
            user_request: 用户的请求字典.

        Returns:
            str: 拼接后的完整描述.
        """
        lines = [base, "\n\n用户请求参数:"]
        for key, value in user_request.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
