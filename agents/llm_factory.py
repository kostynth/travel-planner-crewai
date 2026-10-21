"""LLM 工厂 — 包装 :class:`crewai.LLM` 以便在主模型失效时自动改用备用模型.

智谱的免费额度经常在流水线中途耗尽, 表现有三种:

* HTTP 429, ``error.code == 1305`` —— 「该模型当前访问量过大»;
* 请求长时间挂死, 直到客户端超时 (读超时);
* HTTP 200 但 ``content`` 为空 —— 推理模型把 ``max_tokens`` 全部花在
  «思考» 上, CrewAI 随后抛出
  ``Invalid response from LLM call - None or empty``.

这三种情况都会让流水线卡死或中断. 本模块在 :class:`crewai.LLM` 的子类里
拦截它们: 主模型不可用时, 当前请求立刻改用备用模型重试一次
(``glm-4-flash-250414``), 之后所有请求都固定走备用模型, 直到流水线结束.

调用方 (各 ``agents/*``) 无需任何改动.
"""

from __future__ import annotations

import logging
from typing import Any

import config

logger = logging.getLogger(__name__)

# 主模型失效的判定关键词 (智谱错误文案 / 限流语义)
_FAILURE_KEYWORDS = (
    "访问量过大",
    "速率限制",
    "rate limit",
    "too many requests",
    "1305",
    "timeout",
    "timed out",
    "connection",
)


def _is_primary_failure(exc: BaseException) -> bool:
    """判断异常是否表示「主模型当前不可用」.

    Args:
        exc: 捕获到的异常.

    Returns:
        bool: 命中限流/超时/连接类错误时返回 ``True``.
    """
    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(kw.lower() in text for kw in _FAILURE_KEYWORDS)


def _looks_empty(result: Any) -> bool:
    """判断一次成功返回的 LLM 结果是否「实质为空».

    CrewAI 要求返回非空字符串; 推理模型思考耗尽预算时 content 会是
    ``None`` 或 ``""``.

    Args:
        result: :meth:`crewai.LLM.call` 的返回值.

    Returns:
        bool: 结果为空时返回 ``True``.
    """
    if result is None:
        return True
    if isinstance(result, str):
        return not result.strip()
    # 工具调用结果等结构化对象: 只要不是空容器就认为有效
    if isinstance(result, (list, tuple, dict)):
        return not result
    return False


def build_llm() -> Any:
    """构建一个可在主模型失效时自动切换的 ``LLM`` 实例.

    Returns:
        Any: 继承自 ``crewai.LLM`` 的实例.
    """
    from crewai import LLM

    base = config.get_llm()

    class FallbackAwareLLM(LLM):  # type: ignore[misc, valid-type]
        """主模型失效时自动改用备用模型, 并可用 ``_prepare_completion_params`` 定制参数."""

        def _prepare_completion_params(  # type: ignore[override]
            self, *args: Any, **kwargs: Any
        ) -> dict[str, Any]:
            """调用前确定最终使用的模型名, 并可改写其他请求参数.

            Args:
                *args: 位置参数, 原样透传给父类.
                **kwargs: 关键字参数, 原样透传给父类.

            Returns:
                dict[str, Any]: 最终请求参数.

            Note:
                主模型 ``glm-4.7-flash`` 是推理模型 —— 思考内容与正式回答
                共用 ``max_tokens`` 预算, 长任务容易耗尽并返回空 content.
                如需关闭思考模式, 在这里改写:

                    params["thinking"] = {"type": "disabled"}
            """
            params = super()._prepare_completion_params(*args, **kwargs)
            current = config._resolve_model()
            if params.get("model") != current:
                logger.info("切换模型: %s -> %s", params.get("model"), current)
                params["model"] = current
            return params

        def call(self, *args: Any, **kwargs: Any) -> Any:
            """发起请求, 主模型失效时立刻改用备用模型重试.

            Args:
                *args: 位置参数, 原样透传给父类.
                **kwargs: 关键字参数, 原样透传给父类.

            Returns:
                Any: LLM 响应.
            """
            try:
                result = super().call(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                if not _is_primary_failure(exc):
                    raise
                logger.warning("主模型 %s 失败 (%s), 改用备用模型", self.model, exc)
                config.note_overload()
                return self._call_with_fallback(*args, **kwargs)

            if _looks_empty(result):
                logger.warning("主模型 %s 返回空结果, 改用备用模型", self.model)
                config.note_overload()
                return self._call_with_fallback(*args, **kwargs)
            return result

        def _call_with_fallback(self, *args: Any, **kwargs: Any) -> Any:
            """强制用备用模型重发同一个请求.

            Args:
                *args: 位置参数, 原样透传给父类.
                **kwargs: 关键字参数, 原样透传给父类.

            Returns:
                Any: LLM 响应.
            """
            fallback = config.LLM_FALLBACK_MODEL
            if not fallback:
                raise RuntimeError("主模型不可用, 且未配置 LLM_FALLBACK_MODEL.")
            logger.info("使用备用模型: %s", fallback)
            original_model = self.model
            self.model = fallback
            try:
                return super().call(*args, **kwargs)
            finally:
                self.model = original_model

    return _clone(base, FallbackAwareLLM)


def _clone(base: Any, cls: type) -> Any:
    """把已有 LLM 实例的配置拷贝到新类.

    Args:
        base: 原始 ``crewai.LLM`` 实例.
        cls: 目标子类.

    Returns:
        Any: 新建的子类实例.
    """
    data: dict[str, Any] = {}
    for name in cls.model_fields:
        if name == "model":
            continue
        if hasattr(base, name):
            data[name] = getattr(base, name)
    # 透传 base_url / api_key 等显式字段
    for attr in ("base_url", "api_key", "timeout", "stream", "model"):
        if hasattr(base, attr):
            data[attr] = getattr(base, attr)
    data.setdefault("model", config.LLM_MODEL)
    return cls(**data)


def default_llm() -> Any:
    """返回全局默认 LLM 实例 (主模型失效时自动切换到备用模型).

    Returns:
        Any: 支持自动降级的 CrewAI ``LLM`` 实例.
    """
    return build_llm()


__all__ = ["build_llm", "default_llm"]
