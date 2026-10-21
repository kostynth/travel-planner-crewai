"""景点图片代理 (Visualizer).

接收上游代理产出的景点名称, 通过 ``icrawler`` (Bing 图片搜索)
下载各景点的实景照片, 供最终报告使用. 不负责绘制统计图表.

LLM 默认为智谱 GLM (zai/glm-4.7-flash, 免费额度).
"""

from __future__ import annotations

from typing import Any

from crewai import Agent
from crewai.tools import BaseTool
from pydantic import Field

import config
from tools.image_crawler import image_crawler_instance

from .llm_factory import default_llm


class _DownloadPlaceImagesTool(BaseTool):
    """下载单个景点图片的工具."""

    name: str = "download_place_images"
    description: str = (
        "根据景点名称下载实景照片 (如 '杭州西湖'、'外滩'), "
        "返回保存目录与图片数量."
    )
    max_num: int = Field(default=10, description="最多下载的图片数量.")

    def _run(self, place_name: str, max_num: int | None = None) -> dict[str, Any]:
        """下载单个景点图片.

        Args:
            place_name: 景点名称.
            max_num: 可选, 覆盖默认数量上限.

        Returns:
            dict: 含保存目录与图片数量的结果.
        """
        return image_crawler_instance.download_place_images(
            place_name=place_name,
            max_num=max_num or self.max_num or config.IMAGE_MAX_NUM_PER_PLACE,
        )


class _DownloadPlacesImagesTool(BaseTool):
    """批量下载多个景点图片的工具."""

    name: str = "download_places_images"
    description: str = (
        "批量下载多个景点的图片. 输入为景点名称列表, "
        "返回每个景点的结果与整体汇总."
    )
    max_num_per_place: int = Field(
        default=10, description="每个景点最多下载的图片数量."
    )

    def _run(
        self,
        place_names: list[str],
        max_num_per_place: int | None = None,
    ) -> dict[str, Any]:
        """批量下载景点图片.

        Args:
            place_names: 景点名称列表.
            max_num_per_place: 可选, 每个景点的图片数量上限.

        Returns:
            dict: 含逐景点结果与整体汇总的字典.
        """
        results = image_crawler_instance.download_places(
            place_names=place_names,
            max_num_per_place=(
                max_num_per_place
                or self.max_num_per_place
                or config.IMAGE_MAX_NUM_PER_PLACE
            ),
        )
        return {
            "results": results,
            "summary": image_crawler_instance.summarize(results),
        }


def create_visualizer_agent() -> Agent:
    """创建景点图片下载代理.

    Returns:
        Agent: 配备图片下载工具的 ``Agent`` 实例.
    """
    return Agent(
        role="景点图片采集员",  # Landmark Image Collector
        goal=(
            "根据行程中确定的景点名称, 下载每个景点的实景照片, "
            "并汇报图片保存位置与数量, 使最终报告图文并茂."
        ),
        backstory=(
            "你负责为旅行报告收集配图. 你会拿到上游代理整理好的景点清单, "
            "逐一使用图片下载工具抓取真实照片. "
            "你只负责下载图片, 不做数据分析与图表绘制."
        ),
        llm=default_llm(),
        tools=[
            _DownloadPlaceImagesTool(),
            _DownloadPlacesImagesTool(),
        ],
        verbose=True,
    )