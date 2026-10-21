"""景点图片爬虫封装 (基于 icrawler + Bing 图片搜索).

提供 ``ImageCrawler`` 类, 接收代理产出的景点名称, 通过
``icrawler.builtin.BingImageCrawler`` 下载实景照片到 ``data/images/<地点>/``.

设计要点:
- 不依赖任何 API Key, 直接使用 Bing 图片搜索的公开结果;
- 每个景点使用独立子目录, 避免文件名互相覆盖;
- 任何单点失败都不抛出, 由上层汇总为失败列表, 保证优雅降级.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from icrawler.builtin import BingImageCrawler

import config

logger = logging.getLogger(__name__)


def _sanitize(name: str) -> str:
    """将景点名称转换为安全的目录名.

    移除文件系统非法字符, 折叠空白, 限制长度.

    Args:
        name: 原始景点名称.

    Returns:
        str: 可安全用作目录名的字符串.
    """
    cleaned = re.sub(r'[\\/:*?"<>|\n\r\t]', "", name).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return (cleaned or "unknown")[:60]


class ImageCrawler:
    """景点图片下载客户端.

    Attributes:
        root_dir: 图片保存根目录.
    """

    def __init__(self, root_dir: str | Path | None = None) -> None:
        """初始化爬虫.

        Args:
            root_dir: 可选图片根目录, 默认使用 ``config.IMAGE_ROOT_DIR``.
        """
        self.root_dir = Path(root_dir or config.IMAGE_ROOT_DIR)

    def download_place_images(
        self,
        place_name: str,
        max_num: int = 10,
    ) -> dict[str, Any]:
        """下载单个景点的一批图片.

        Args:
            place_name: 景点名称 (如 ``杭州西湖``).
            max_num: 最多下载图片数量.

        Returns:
            dict: 含 ``place`` / ``saved_dir`` / ``count`` / ``files`` /
            ``success`` 字段的结果字典.
        """
        safe_name = _sanitize(place_name)
        target_dir = self.root_dir / safe_name
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            crawler = BingImageCrawler(
                storage={"root_dir": str(target_dir)},
                feeder_threads=1,
                parser_threads=1,
                downloader_threads=4,
            )
            crawler.crawl(keyword=place_name, max_num=max_num)
        except Exception as exc:  # noqa: BLE001
            logger.warning("景点 %r 图片下载失败: %s", place_name, exc)
            return {
                "place": place_name,
                "saved_dir": str(target_dir),
                "count": 0,
                "files": [],
                "success": False,
                "error": str(exc),
            }

        files = sorted(
            p.name for p in target_dir.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        )
        return {
            "place": place_name,
            "saved_dir": str(target_dir),
            "count": len(files),
            "files": files,
            "success": bool(files),
        }

    def download_places(
        self,
        place_names: list[str],
        max_num_per_place: int = 10,
    ) -> list[dict[str, Any]]:
        """批量下载多个景点的图片.

        Args:
            place_names: 景点名称列表.
            max_num_per_place: 每个景点下载的图片数量上限.

        Returns:
            list[dict]: 每个景点的结果字典列表.
        """
        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        for name in place_names:
            clean = (name or "").strip()
            if not clean:
                continue
            # 依据清洗后的目录名去重, 避免同名景点重复下载
            key = _sanitize(clean)
            if key in seen:
                continue
            seen.add(key)

            logger.info("下载景点图片: %s", clean)
            results.append(self.download_place_images(clean, max_num_per_place))

        return results

    def summarize(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """汇总批量下载结果.

        Args:
            results: ``download_places`` 的返回值.

        Returns:
            dict: 包含成功/失败数量与总数的结果.
        """
        ok = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        return {
            "total_places": len(results),
            "success_places": len(ok),
            "failed_places": len(failed),
            "total_images": sum(r.get("count", 0) for r in results),
            "successful": [r["place"] for r in ok],
            "failed": [r["place"] for r in failed],
        }


# 单例实例, 供所有代理共享
image_crawler_instance = ImageCrawler()