"""小红书 (XHS) 数据抓取封装.

提供 ``XHSCrawler`` 类，用于按关键词搜索笔记以及获取单篇笔记详情。
当未提供合法的 cookie 时，方法返回空结果（仅本地 mock 数据），
以保证上层代理在缺失凭据时不会崩溃。
"""

from __future__ import annotations

import logging
from typing import Any

import config

logger = logging.getLogger(__name__)


class XHSCrawler:
    """小红书 (XHS) 笔记抓取器.

    Attributes:
        cookie: 登录态 cookie；为空时进入 mock 模式.
        base_url: XHS 内部 API 基础地址.
    """

    def __init__(self, cookie: str | None = None) -> None:
        self.cookie = cookie
        self.base_url = "https://www.xiaohongshu.com/api/sns/web/v1"

    def search_notes(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        """按关键词搜索小红书笔记.

        Args:
            keyword: 搜索关键词，例如 "上海 三天 行程".
            limit: 最多返回的笔记数量.

        Returns:
            list[dict]: 形如 ``{"id", "title", "author", "content"}`` 的字典列表.
        """
        if not self._has_credentials():
            logger.warning("XHS cookie 未配置 — search_notes 返回 mock 数据.")
            return self._mock_results(keyword, limit)

        # 真实实现需构造 x-s / x-t 签名头，此处保留占位逻辑
        logger.info("XHS search: keyword=%s, limit=%d", keyword, limit)
        return self._mock_results(keyword, limit)

    def get_note_detail(self, note_id: str) -> dict[str, Any]:
        """根据笔记 ID 获取单篇笔记的详细信息.

        Args:
            note_id: 小红书笔记 ID.

        Returns:
            dict: 包含 ``id, title, content, author, likes, comments`` 的字典；
                  若未配置 cookie 则返回空字典.
        """
        if not self._has_credentials():
            logger.warning("XHS cookie 未配置 — get_note_detail 返回空字典.")
            return {}

        logger.info("XHS get_note_detail: %s", note_id)
        return {
            "id": note_id,
            "title": "示例笔记",
            "content": "请替换 XHS cookie 并实现真实请求逻辑.",
            "author": "unknown",
            "likes": 0,
            "comments": 0,
        }

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------
    def _has_credentials(self) -> bool:
        """判断是否拥有合法凭据."""
        if not self.cookie:
            return False
        return config.is_key_set(self.cookie)

    @staticmethod
    def _mock_results(keyword: str, limit: int) -> list[dict[str, Any]]:
        """生成用于本地开发的 mock 结果."""
        return [
            {
                "id": f"mock-{i}",
                "title": f"{keyword} — 示例标题 {i}",
                "author": "示例作者",
                "content": f"关于 {keyword} 的示例内容, 用于本地开发.",
            }
            for i in range(limit)
        ]


# 默认单例（无 cookie，仅 mock 模式）
xhs_crawler_instance = XHSCrawler()
