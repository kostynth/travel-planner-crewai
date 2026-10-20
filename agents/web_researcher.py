"""网络调研代理 (Web Researcher).

通过 Tavily 与 SerpApi 进行网页搜索，收集城市与景点信息。
当 ``crewai_tools`` 不可用时退化为无工具状态。
"""

from __future__ import annotations

import logging

from crewai import Agent

logger = logging.getLogger(__name__)

# 尝试导入 crewai_tools；失败时进入优雅降级
try:  # pragma: no cover - 依赖运行环境
    from crewai_tools import SerpApiGoogleSearchTool, TavilySearchResults  # type: ignore

    _TOOLS_AVAILABLE = True
except Exception as exc:  # noqa: BLE001
    logger.warning("crewai_tools 不可用 (%s) — web_researcher 将无工具运行.", exc)
    SerpApiGoogleSearchTool = None  # type: ignore[assignment]
    TavilySearchResults = None  # type: ignore[assignment]
    _TOOLS_AVAILABLE = False


def _collect_tools() -> list:
    """收集可用的搜索工具，跳过初始化失败的对象.

    Returns:
        list: 成功初始化的工具列表.
    """
    tools: list = []
    if not _TOOLS_AVAILABLE:
        return tools

    for factory in (TavilySearchResults, SerpApiGoogleSearchTool):
        if factory is None:
            continue
        try:
            tools.append(factory())
        except Exception as exc:  # noqa: BLE001
            logger.warning("工具初始化失败: %s", exc)
    return tools


def create_web_researcher_agent() -> Agent:
    """创建网络调研代理.

    Returns:
        Agent: 配备 Tavily / SerpApi 工具的 ``Agent`` 实例.
    """
    tools = _collect_tools()
    return Agent(
        role="",  # 占位
        goal="",  # 占位
        backstory="",  # 占位
        tools=tools,
        verbose=True,
    )
