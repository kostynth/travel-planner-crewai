"""外部搜索 API 的封装.

提供 ``SearchTools`` 类，统一调用 Tavily、SerpApi、Bing 三种搜索服务。
所有 API 密钥均从 ``config`` 模块读取；若密钥缺失，
对应方法返回空列表并写日志告警，从而实现优雅降级。
"""

from __future__ import annotations

import logging
from typing import Any

import requests

import config

logger = logging.getLogger(__name__)

# 各服务的端点地址
_TAVILY_URL = "https://api.tavily.com/search"
_SERPAPI_URL = "https://serpapi.com/search.json"
_BING_URL = "https://api.bing.microsoft.com/v7.0/search"


class SearchTools:
    """统一的搜索工具类，封装 Tavily、SerpApi、Bing 三个后端."""

    # ------------------------------------------------------------------
    # Tavily
    # ------------------------------------------------------------------
    def tavily_search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """通过 Tavily Search API 执行搜索.

        Args:
            query: 搜索查询字符串.
            max_results: 返回结果的最大数量.

        Returns:
            list[dict]: 形如 ``{"title", "url", "content", "source"}`` 的字典列表.
        """
        if not config.is_key_set(config.TAVILY_API_KEY):
            logger.warning("TAVILY_API_KEY 未配置 — tavily_search 已跳过.")
            return []

        try:
            payload = {
                "api_key": config.TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "include_answer": False,
            }
            response = requests.post(_TAVILY_URL, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            logger.error("Tavily 请求失败: %s", exc)
            return []
        except ValueError as exc:
            logger.error("Tavily 响应解析失败: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        for item in data.get("results", []) or []:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "source": "tavily",
                }
            )
        return results

    # ------------------------------------------------------------------
    # SerpApi (Google)
    # ------------------------------------------------------------------
    def serpapi_search(self, query: str) -> list[dict[str, Any]]:
        """通过 SerpApi 调用 Google 搜索.

        Args:
            query: 搜索查询字符串.

        Returns:
            list[dict]: 形如 ``{"title", "url", "content", "source"}`` 的字典列表.
        """
        if not config.is_key_set(config.SERPAPI_API_KEY):
            logger.warning("SERPAPI_API_KEY 未配置 — serpapi_search 已跳过.")
            return []

        try:
            params = {
                "q": query,
                "api_key": config.SERPAPI_API_KEY,
                "engine": "google",
                "num": 10,
            }
            response = requests.get(_SERPAPI_URL, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            logger.error("SerpApi 请求失败: %s", exc)
            return []
        except ValueError as exc:
            logger.error("SerpApi 响应解析失败: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        for item in data.get("organic_results", []) or []:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "content": item.get("snippet", ""),
                    "source": "serpapi",
                }
            )
        return results

    # ------------------------------------------------------------------
    # Bing
    # ------------------------------------------------------------------
    def bing_search(self, query: str) -> list[dict[str, Any]]:
        """通过 Bing Web Search API v7 执行搜索.

        Args:
            query: 搜索查询字符串.

        Returns:
            list[dict]: 形如 ``{"title", "url", "content", "source"}`` 的字典列表.
        """
        if not config.is_key_set(config.BING_API_KEY):
            logger.warning("BING_API_KEY 未配置 — bing_search 已跳过.")
            return []

        try:
            headers = {"Ocp-Apim-Subscription-Key": config.BING_API_KEY}
            params = {"q": query, "count": 10, "mkt": "zh-CN"}
            response = requests.get(
                _BING_URL, headers=headers, params=params, timeout=20
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            logger.error("Bing 请求失败: %s", exc)
            return []
        except ValueError as exc:
            logger.error("Bing 响应解析失败: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        for item in (data.get("webPages", {}) or {}).get("value", []) or []:
            results.append(
                {
                    "title": item.get("name", ""),
                    "url": item.get("url", ""),
                    "content": item.get("snippet", ""),
                    "source": "bing",
                }
            )
        return results


# 提供单例实例便于在代理中直接复用
search_tools_instance = SearchTools()
