"""高德地图 (Amap) API 封装.

提供 ``GaodeCrawler`` 类，封装 POI 搜索与路径规划接口。
所有密钥均从 ``config.GAODE_API_KEY`` 读取；缺失时返回空结构，
使上层代理能优雅降级。
"""

from __future__ import annotations

import logging
from typing import Any

import requests

import config

logger = logging.getLogger(__name__)

_GAODE_BASE = "https://restapi.amap.com/v3"

# 模式名称到 Gaode 路径规划端点的映射
_MODE_ENDPOINT = {
    "0": "driving",
    "1": "transit/integrated",
    "2": "bicycling",
    "3": "walking",
}

# 用户友好模式名到 Gaode 模式码的映射
_MODE_CODE = {
    "driving": "0",
    "transit": "1",
    "bicycling": "2",
    "walking": "3",
}


def _mode_endpoint_name(mode_code: str) -> str:
    """根据 Gaode 模式码返回对应的端点路径名."""
    return _MODE_ENDPOINT.get(mode_code, "walking")


class GaodeCrawler:
    """高德地图 (Amap) API 客户端.

    Attributes:
        api_key: 从 ``config.GAODE_API_KEY`` 读取的密钥.
    """

    def __init__(self) -> None:
        self.api_key = config.GAODE_API_KEY

    def search_poi(
        self,
        keyword: str,
        city: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """调用高德 Place 接口搜索 POI.

        Args:
            keyword: 搜索关键词，例如 "外滩".
            city: 城市名称，例如 "上海".
            limit: 最多返回的 POI 数量.

        Returns:
            list[dict]: 形如
                ``{"id", "name", "address", "location", "type", "city"}`` 的字典列表.
        """
        if not config.is_key_set(self.api_key):
            logger.warning("GAODE_API_KEY 未配置 — search_poi 返回空列表.")
            return []

        url = f"{_GAODE_BASE}/place/text"
        params = {
            "key": self.api_key,
            "keywords": keyword,
            "city": city,
            "offset": min(limit, 25),
            "page": 1,
            "extensions": "base",
            "output": "json",
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            logger.error("高德 POI 搜索失败: %s", exc)
            return []

        pois: list[dict[str, Any]] = []
        for item in data.get("pois", []) or []:
            pois.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "address": item.get("address"),
                    "location": item.get("location"),  # "lng,lat"
                    "type": item.get("type"),
                    "city": city,
                }
            )
        return pois[:limit]

    def get_route(
        self,
        origin: str,
        destination: str,
        mode: str = "walking",
    ) -> dict[str, Any]:
        """调用高德路径规划接口计算两点之间的路线.

        Args:
            origin: 起点，可为坐标 "lng,lat" 或地点名称.
            destination: 终点，格式同上.
            mode: 出行方式，可选 ``walking`` / ``driving`` / ``transit`` / ``bicycling``.

        Returns:
            dict: 包含 ``distance, duration, steps, mode`` 的字典.
        """
        if not config.is_key_set(self.api_key):
            logger.warning("GAODE_API_KEY 未配置 — get_route 返回空字典.")
            return {}

        mode_code = _MODE_CODE.get(mode, "3")
        endpoint = f"{_GAODE_BASE}/direction/{_mode_endpoint_name(mode_code)}"
        params = {
            "key": self.api_key,
            "origin": origin,
            "destination": destination,
            "output": "json",
        }

        try:
            resp = requests.get(endpoint, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            logger.error("高德路径规划失败: %s", exc)
            return {}

        path = (data.get("route", {}) or {}).get("paths", [{}])[0] or {}
        return {
            "distance": path.get("distance"),
            "duration": path.get("duration"),
            "steps": path.get("steps", []),
            "mode": mode,
        }


# 默认单例
gaode_crawler_instance = GaodeCrawler()
