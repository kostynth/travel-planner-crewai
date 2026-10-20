"""社交媒体与本地专家代理 (Social Crawler).

通过 ``XHSCrawler`` 与 ``GaodeCrawler`` 抓取小红书笔记、
高德 POI 与路线信息。
"""

from __future__ import annotations

from typing import Any

from crewai import Agent
from crewai_tools import BaseTool
from pydantic import Field

from tools.gaode_crawler import gaode_crawler_instance
from tools.xhs_crawler import xhs_crawler_instance


class _XHSSearchTool(BaseTool):
    """小红书关键词搜索工具."""

    name: str = "xhs_search"
    description: str = "按关键词搜索小红书笔记并返回标题、作者、内容."
    limit: int = Field(default=10, description="返回笔记的最大数量.")

    def _run(self, keyword: str, limit: int | None = None) -> list[dict[str, Any]]:
        """执行搜索.

        Args:
            keyword: 搜索关键词.
            limit: 可选，覆盖默认数量上限.

        Returns:
            list[dict]: 小红书笔记结果列表.
        """
        return xhs_crawler_instance.search_notes(
            keyword=keyword, limit=limit or self.limit
        )


class _XHSDetailTool(BaseTool):
    """小红书单篇笔记详情工具."""

    name: str = "xhs_note_detail"
    description: str = "根据笔记 ID 获取小红书笔记的完整内容."

    def _run(self, note_id: str) -> dict[str, Any]:
        """获取笔记详情.

        Args:
            note_id: 小红书笔记 ID.

        Returns:
            dict: 笔记详情字典.
        """
        return xhs_crawler_instance.get_note_detail(note_id=note_id)


class _GaodePOITool(BaseTool):
    """高德 POI 搜索工具."""

    name: str = "gaode_search_poi"
    description: str = "在高德地图中按城市与关键词搜索兴趣点 (POI)."
    limit: int = Field(default=20, description="返回 POI 的最大数量.")

    def _run(
        self,
        keyword: str,
        city: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """搜索 POI.

        Args:
            keyword: 搜索关键词.
            city: 城市名称.
            limit: 可选的数量上限.

        Returns:
            list[dict]: POI 结果列表.
        """
        return gaode_crawler_instance.search_poi(
            keyword=keyword, city=city, limit=limit or self.limit
        )


class _GaodeRouteTool(BaseTool):
    """高德路径规划工具."""

    name: str = "gaode_route"
    description: str = "在高德地图中规划两点之间的出行路线 (步行/驾车/公交/骑行)."

    def _run(
        self,
        origin: str,
        destination: str,
        mode: str = "walking",
    ) -> dict[str, Any]:
        """规划路径.

        Args:
            origin: 起点坐标或名称.
            destination: 终点坐标或名称.
            mode: 出行方式.

        Returns:
            dict: 包含距离、时长与步骤的路径字典.
        """
        return gaode_crawler_instance.get_route(
            origin=origin, destination=destination, mode=mode
        )


def create_social_crawler_agent() -> Agent:
    """创建社交媒体与本地专家代理.

    Returns:
        Agent: 配备 XHS / 高德工具的 ``Agent`` 实例.
    """
    tools = [
        _XHSSearchTool(),
        _XHSDetailTool(),
        _GaodePOITool(),
        _GaodeRouteTool(),
    ]
    return Agent(
        role="社交媒体与本地专家",  # Social Media & Local Expert
        goal="",  # 占位
        backstory="",  # 占位
        tools=tools,
        verbose=True,
    )
