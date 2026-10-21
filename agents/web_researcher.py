"""网络调研代理 (Web Researcher).

通过 Tavily 与 SerpApi 进行网页搜索, 收集城市与景点信息.
当 ``crewai_tools`` 不可用时退化为无工具状态.
LLM 默认为智谱 GLM (zai/glm-4.7-flash, 免费额度).

测试说明: 当前版本使用 ``_StubSearchTool`` 作为默认工具, 返回受控的虚假
搜索结果, 确保端到端测试无需任何外网或 API Key 即可运行. 真实部署时
可通过环境变量 ``USE_STUB_TOOLS=false`` 切换到 Tavily/SerpApi.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from crewai import Agent
from crewai.tools import BaseTool
from pydantic import Field

from .llm_factory import default_llm

logger = logging.getLogger(__name__)


# =========================================================
#  真实工具 (Tavily / SerpApi) — 默认不启用
# =========================================================
try:  # pragma: no cover - 依赖运行环境
    from crewai_tools import SerpApiGoogleSearchTool, TavilySearchTool  # type: ignore

    _REAL_TOOLS_AVAILABLE = True
    TavilySearchResults = TavilySearchTool  # type: ignore[assignment]
except Exception as exc:  # noqa: BLE001
    logger.warning("crewai_tools 不可用 (%s) — web_researcher 将使用本地工具.", exc)
    SerpApiGoogleSearchTool = None  # type: ignore[assignment]
    TavilySearchResults = None  # type: ignore[assignment]
    TavilySearchTool = None  # type: ignore[assignment]
    _REAL_TOOLS_AVAILABLE = False


# =========================================================
#  测试用 stub (无需 API Key 与网络)
# =========================================================
class _StubSearchTool(BaseTool):
    """离线伪搜索工具: 根据关键词返回受控的景点概览."""

    name: str = "stub_web_search"
    description: str = (
        "接受任意关键词, 返回 3 条预置的网页摘要 (标题、来源、要点). "
        "用于离线测试, 不发起任何网络请求."
    )

    def _run(self, query: str) -> list[dict[str, Any]]:
        """返回桩数据.

        Args:
            query: 用户搜索关键词.

        Returns:
            list[dict]: 固定 3 条结果.
        """
        logger.info("[STUB] web_search query=%r", query)
        return [
            {
                "title": f"{query} · 维基百科摘要",
                "url": "https://example.com/wiki",
                "snippet": (
                    f"{query} 是热门旅游目的地, 历史悠久, 自然与人文景观兼具."
                ),
            },
            {
                "title": f"{query} · 当地旅游局官网",
                "url": "https://example.com/tourism",
                "snippet": "最佳旅行季节为春秋两季, 推荐行程 3-5 天.",
            },
            {
                "title": f"{query} · 旅行攻略精选",
                "url": "https://example.com/tips",
                "snippet": "建议提前预订门票, 旺季需注意人流与天气.",
            },
        ]


def _should_use_stubs() -> bool:
    """默认使用 stub; 设 ``USE_STUB_TOOLS=false`` 启用真实工具.

    Returns:
        bool: True 表示使用 stub.
    """
    return os.getenv("USE_STUB_TOOLS", "true").lower() not in {"false", "0", "no"}


def _collect_tools() -> list[BaseTool]:
    """收集 web_researcher 要使用的工具.

    Returns:
        list[BaseTool]: 工具实例列表.
    """
    tools: list[BaseTool] = [_StubSearchTool()]

    if _should_use_stubs() or not _REAL_TOOLS_AVAILABLE:
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
        Agent: 配备搜索工具的 ``Agent`` 实例.
    """
    tools = _collect_tools()
    logger.info(
        "web_researcher 工具: %s", [t.name for t in tools],
    )
    return Agent(
        role="网络调研员",  # Web Research Specialist
        goal=(
            "为目标城市提供权威的概览资料, 包括代表性景点、最佳季节、签证"
            "与本地注意事项, 并标注来源链接以方便交叉核对."
        ),
        backstory=(
            "你习惯在 30 分钟内梳理一座陌生城市的旅游脉络. 你会先搜索官方"
            "旅游局与维基资料, 再从各大旅游网站采集近期用户评价, 最后把信息"
            "整理成结构化清单交给团队."
        ),
        llm=default_llm(),
        tools=tools,
        verbose=True,
    )