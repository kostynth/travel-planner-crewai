"""旅行计划 CrewAI 编排器.

将所有代理串联成一条 9 步的流水线, 并对外暴露 ``run`` 入口.
所有代理使用智谱 GLM 模型 (zai/glm-4.7-flash), 详见 ``config.py``.
"""

from __future__ import annotations

import logging
from typing import Any

from crewai import Crew, Process, Task

import config
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
    → 景点图片下载 → 报告 → 质量审核.
    """

    def __init__(self, verbose: bool = True) -> None:
        """初始化编排器.

        Args:
            verbose: 是否输出详细日志.
        """
        # 通过工厂函数创建所有代理 (默认使用智谱 GLM 模型)
        # get_llm() 若未配置 ZHIPU_API_KEY 会立即抛出 RuntimeError
        self.verbose = verbose
        # 最近一次运行中「旅行报告编辑」任务的产出 (见 run()).
        self.last_report: str = ""
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

        # 7. 下载景点图片
        task_visualize = Task(
            description=self._format_description(
                "根据行程中出现的景点名称, 使用图片下载工具抓取每个景点的实景照片. "
                "只下载图片, 不绘制任何图表. "
                "最后汇总: 每个景点下载了多少张、图片保存在哪个目录.",
                user_request,
            ),
            expected_output="景点图片下载汇总: 各景点图片数量与保存路径.",
            agent=self.visualizer,
            context=[task_route, task_social],
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
    def run(
        self,
        user_request: dict[str, Any],
        stream: bool = True,
        on_token: "Callable[[str], None] | None" = None,
    ) -> Any:
        """启动整个流水线.

        Args:
            user_request: 形如 ``{"city", "days", "budget", "preferences"}`` 的字典.
            stream: 是否流式打印各代理的中间产出 (便于终端观察).
            on_token: 每收到一块流式输出时调用的回调 (用于实时打印到终端).

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
            verbose=self.verbose,
            max_iter=config.MAX_ITER,
            llm=config.get_llm(),
            # Crew 级流式会强制 litellm 使用 SSE, 智谱在大上下文下偶发空分片,
            # 因此实际开关由 config.LLM_STREAM 控制.
            stream=stream and config.LLM_STREAM,
            task_callback=self._on_task_done,
            step_callback=self._on_step,
        )
        logger.info("启动 TravelPlannerCrew, 请求: %s", user_request)

        output = crew.kickoff(inputs=user_request)

        # Crew 会复制传入的 tasks, 因此只有 crew.tasks 上的 .output 才有值.
        # 这里把「旅行报告编辑」任务的产出单独取出来 — kickoff() 返回的是
        # 最后一个任务 (质量审核) 的产出, 并不是真正的旅行报告.
        self.last_report = self._extract_report(crew)

        if stream and hasattr(output, "__iter__") and on_token is not None:
            for chunk in output:
                content = getattr(chunk, "content", "")
                if content:
                    on_token(content)
            return getattr(output, "result", output)
        return output

    @staticmethod
    def _extract_report(crew: Any) -> str:
        """从 Crew 的任务列表里取出「旅行报告编辑」任务的产出.

        Args:
            crew: 已执行完成的 ``Crew`` 实例.

        Returns:
            str: 报告正文; 找不到时返回空字符串.
        """
        for task in getattr(crew, "tasks", None) or []:
            role = getattr(getattr(task, "agent", None), "role", "")
            if role != "旅行报告编辑":
                continue
            output = getattr(task, "output", None)
            if output is None:
                continue
            for attr in ("raw", "output", "final_output"):
                value = getattr(output, attr, None)
                if isinstance(value, str) and value.strip():
                    return value
            if isinstance(output, str):
                return output
        return ""

    # ------------------------------------------------------------------
    # 终端回调: 把代理产出实时打印出来
    # ------------------------------------------------------------------
    @staticmethod
    def _on_step(_result: Any = None, **_: Any) -> None:
        """Crew 每执行一步时回调.

        ``crewai>=1.15`` вызывает ``step_callback(formatted_answer)`` с одним
        позиционным аргументом, который может быть как строкой (результат
        инструмента), так и объектом ``AgentFinish`` / ``ToolUsage``. Дополнительные
        именованные аргументы неизвестны наперёд, поэтому принимаем любые.

        Args:
            _result: Строка либо объект с полем ``text`` / ``output``.
            **_ : Дополнительные именованные аргументы, игнорируем.
        """
        if isinstance(_result, str):
            snippet = _result
        else:
            snippet = ""
            for attr in ("text", "output", "result", "content"):
                value = getattr(_result, attr, None)
                if isinstance(value, str) and value.strip():
                    snippet = value
                    break
        snippet = snippet.strip()
        if snippet:
            head = snippet if len(snippet) <= 120 else snippet[:120] + "…"
            logger.info("→ [step] %s", head)

    @staticmethod
    def _on_task_done(task_output: Any = None, **_: Any) -> None:
        """Crew 完成一个任务时回调.

        ``crewai>=1.15`` вызывает ``task_callback(task_output)`` (один
        позиционный аргумент).

        Args:
            task_output: 任务产出对象或字符串.
            **_ : 其余参数, 忽略.
        """
        agent_role = getattr(task_output, "agent", "?")
        description = getattr(task_output, "description", "")
        text = str(getattr(task_output, "raw", "") or task_output or "")
        logger.info(
            "✅ [%s] 完成%s — 产出 %d 字符",
            agent_role,
            f" ({description[:40]}...)" if description else "",
            len(text),
        )

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
