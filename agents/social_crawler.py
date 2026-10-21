"""社交媒体与本地专家代理 (Social Crawler).

通过 ``XHSCrawler`` 与 ``GaodeCrawler`` 抓取小红书笔记、
高德 POI 与路线信息.
LLM 默认为智谱 GLM (zai/glm-4.7-flash, 免费额度).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from crewai import Agent
from crewai.tools import BaseTool
from pydantic import Field

from tools.gaode_crawler import gaode_crawler_instance
from tools.xhs_crawler import xhs_crawler_instance

from .llm_factory import default_llm

logger = logging.getLogger(__name__)


def _use_stubs() -> bool:
    """默认使用 stub; 设 ``USE_STUB_TOOLS=false`` 启用真实抓取.

    Returns:
        bool: True 表示使用 stub 工具.
    """
    return os.getenv("USE_STUB_TOOLS", "true").lower() not in {"false", "0", "no"}


class _StubNotesTool(BaseTool):
    """离线桩: 返回预置的"本地攻略"笔记."""

    name: str = "stub_xhs_notes"
    description: str = "按关键词返回 4 条预置的本地攻略笔记 (无需网络)."

    limit: int = Field(default=4, description="返回笔记数量上限.")

    def _run(self, keyword: str, limit: int | None = None) -> list[dict[str, Any]]:
        """返回桩数据.

        Args:
            keyword: 搜索关键词.
            limit: 可选数量上限.

        Returns:
            list[dict]: 笔记列表.
        """
        n = limit or self.limit
        logger.info("[STUB] xhs_notes keyword=%r limit=%d", keyword, n)
        templates = [
            ("本地人私藏的 {k} 路线", "避开人潮的小众路线, 全天不踩雷."),
            ("{k} 必吃清单", "老字号早餐、排队网红店与本地小馆各 2 家."),
            ("{k} 拍照机位整理", "黄金时刻的光线与机位, 附参数建议."),
            ("{k} 避坑提醒", "门票、预约与交通的实用提示, 帮你少走弯路."),
        ]
        return [
            {
                "id": f"stub-{i}",
                "title": tpl.format(k=keyword),
                "author": f"本地博主{i}",
                "content": content.format(k=keyword),
            }
            for i, (tpl, content) in enumerate(templates[:n], start=1)
        ]


class _StubPOITool(BaseTool):
    """离线桩: 返回预置的 POI 列表 (含伪坐标)."""

    name: str = "stub_gaode_poi"
    description: str = "在城市中按关键词返回预置 POI 列表 (含地址与坐标, 离线)."

    limit: int = Field(default=8, description="返回 POI 数量上限.")

    def _run(
        self,
        keyword: str,
        city: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """返回桩数据.

        Args:
            keyword: 搜索关键词.
            city: 城市名称.
            limit: 可选数量上限.

        Returns:
            list[dict]: POI 列表.
        """
        n = limit or self.limit
        logger.info("[STUB] gaode_poi city=%r keyword=%r", city, keyword)
        base_lng, base_lat = 121.4737, 31.2304  # 上海市中心, 仅作演示
        kinds = ["博物馆", "历史街区", "公园", "古镇", "地标建筑", "文创园", "夜市", "山顶"]
        results = []
        for i in range(n):
            kind = kinds[i % len(kinds)]
            results.append(
                {
                    "id": f"stub-poi-{i}",
                    "name": f"{city}{keyword}·{kind}{i + 1}",
                    "address": f"{city}市示意路{i + 1}号",
                    "location": f"{base_lng + i * 0.01:.5f},{base_lat + i * 0.008:.5f}",
                    "type": kind,
                    "city": city,
                    "rating": round(4.0 + (i % 10) / 10, 1),
                }
            )
        return results


class _StubRouteTool(BaseTool):
    """离线桩: 返回伪路线信息."""

    name: str = "stub_gaode_route"
    description: str = "返回两点之间的示意距离与时长 (离线桩, 坐标为伪值)."

    def _run(
        self,
        origin: str,
        destination: str,
        mode: str = "walking",
    ) -> dict[str, Any]:
        """返回桩数据.

        Args:
            origin: 起点.
            destination: 终点.
            mode: 出行方式.

        Returns:
            dict: 路线信息.
        """
        logger.info("[STUB] gaode_route %s -> %s (%s)", origin, destination, mode)
        speed = {"walking": 4.5, "bicycling": 15.0, "driving": 30.0, "transit": 20.0}
        km = 3.2
        return {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "distance_km": km,
            "duration_min": round(km / speed.get(mode, 4.5) * 60),
            "note": "[STUB] 桩数据, 距离与时长为固定估算值.",
        }


class _XHSSearchTool(BaseTool):
    """小红书关键词搜索工具."""

    name: str = "xhs_search"
    description: str = "按关键词搜索小红书笔记并返回标题、作者、内容."
    limit: int = Field(default=10, description="返回笔记的最大数量.")

    def _run(self, keyword: str, limit: int | None = None) -> list[dict[str, Any]]:
        """执行搜索.

        Args:
            keyword: 搜索关键词.
            limit: 可选, 覆盖默认数量上限.

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
    if _use_stubs():
        tools: list[BaseTool] = [_StubNotesTool(), _StubPOITool(), _StubRouteTool()]
    else:
        tools = [
            _XHSSearchTool(),
            _XHSDetailTool(),
            _GaodePOITool(),
            _GaodeRouteTool(),
        ]

    logger.info("social_crawler 工具: %s", [t.name for t in tools])

    return Agent(
        role="社交媒体与本地专家",  # Social Media & Local Expert
        goal=(
            "从本地人的真实分享中提炼出小众但可靠的玩法, 并结合地图 POI 数据"
            "确认景点位置与相互距离, 为后续行程规划提供带坐标的候选清单."
        ),
        backstory=(
            "你长期混迹小红书与本地生活社区, 深知'网红推荐'与'本地口碑'的差别. "
            "你会主动比对多位博主的笔记, 剔除明显的广告内容, 再用地图工具核实"
            "这些地点的实际位置与通勤距离."
        ),
        llm=default_llm(),
        tools=tools,
        verbose=True,
    )