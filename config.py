"""全局配置: LLM 参数与 API 密钥集中存放.

所有配置均可通过同名环境变量覆盖, 否则使用默认值或占位符.
``get_llm()`` 工厂函数统一向所有代理提供同一个 LLM 实例.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 尝试自动加载根目录下的 .env 文件 (若存在)
try:
    from dotenv import load_dotenv

    _ENV_PATH = Path(__file__).parent / ".env"
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH)
except ImportError:  # pragma: no cover - dotenv 为可选依赖
    pass

# =========================================================
#  LLM 配置 (默认使用智谱 GLM 云端 API)
# =========================================================

# --- 提供方: 智谱 GLM (经 litellm 的 zai 路由) ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "zai")

# --- 主模型名 ---
# glm-4.7-flash 是会过载/限额较严的推理模型; 若它挂掉/超时/返回空,
# 会自动切到 LLM_FALLBACK_MODEL 继续走完流水线.
LLM_MODEL = os.getenv("LLM_MODEL", "zai/glm-4.7-flash")

# --- 备用模型 ---
# 触发条件见 ``agents.llm_factory``: 429 / 速率限制 / 主模型彻底超时 /
# 返回空 content (推理模型配额耗尽). 留空则关闭自动切换.
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "zai/glm-4-flash-250414")

# --- 服务地址 ---
# 国内版账号 (bigmodel.cn, 需手机号验证): https://open.bigmodel.cn/api/paas/v4
# 国际版账号 (z.ai, 邮箱注册):          https://api.z.ai/api/paas/v4
# 两端点的 API Key 不互通, 请按注册平台选择.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

# --- 智谱 API Key (控制台 → API Key 管理 创建) ---
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "вставь_ключ")

# --- 采样参数 ---
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.9"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "600"))

# --- 单次回复的最大 token 数 (GLM-4.7-Flash 输出上限 131072) ---
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))

# --- 代理执行轮数上限 ---
MAX_ITER = int(os.getenv("MAX_ITER", "25"))

# --- 是否开启 LLM 流式输出 ---
# 智谱 API 在大上下文下偶尔返回空的流式分片, 导致 CrewAI 报
# "No content received from streaming response" 并重试整个任务.
# 设为 "false" 可关闭流式 (终端输出仍由 Crew 回调打印, 不受影响).
LLM_STREAM = os.getenv("LLM_STREAM", "false").lower() not in {"false", "0", "no"}

# --- 触发速率限制后的冷却时间 (秒) ---
# 智谱免费额度有严格的每分钟请求上限, 长流水线容易撞限.
# 设为 "0" 可关闭重试等待.
LLM_RATE_LIMIT_COOLDOWN = float(os.getenv("LLM_RATE_LIMIT_COOLDOWN", "90"))

# =========================================================
#  景点图片下载配置 (icrawler + Bing 图片搜索)
# =========================================================

# --- 图片保存根目录 ---
IMAGE_ROOT_DIR = os.getenv("IMAGE_ROOT_DIR", "data/images")

# --- 每个景点最多下载的图片数量 ---
IMAGE_MAX_NUM_PER_PLACE = int(os.getenv("IMAGE_MAX_NUM_PER_PLACE", "10"))

# =========================================================
#  外部搜索 / 地图服务 API 密钥
# =========================================================

# --- Tavily: 语义化网页搜索 ---
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "вставь_ключ")

# --- 高德地图 (Amap): 中国境内 POI 与路径规划 ---
GAODE_API_KEY = os.getenv("GAODE_API_KEY", "вставь_ключ")

# --- SerpApi: 备选 Google 搜索 ---
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "вставь_ключ")

# --- Bing Search API: 额外搜索后端 ---
BING_API_KEY = os.getenv("BING_API_KEY", "вставь_ключ")

# --- 占位符标记, 用于 is_key_set 判定 ---
PLACEHOLDER = "вставь_ключ"


def is_key_set(value: str) -> bool:
    """判断 API 密钥是否已配置为真实值 (非空且不等于占位符).

    Args:
        value: 待检查的密钥字符串.

    Returns:
        bool: 密钥可用时返回 ``True``.
    """
    return bool(value) and value != PLACEHOLDER and not value.startswith("вставь_")


# =========================================================
#  LLM 工厂
# =========================================================

_llm_cache: dict[str, Any] = {}

# 当 litellm 报告主模型彻底失败 (含超时) 时翻转该标志,
# 后续 LLM 调用都将走 LLM_FALLBACK_MODEL 直到下次 :func:`reset_fallback`.
_use_fallback: bool = False


def reset_fallback() -> None:
    """重置备用模型状态 (供测试或长任务分段使用)."""
    global _use_fallback
    _use_fallback = False


def note_overload() -> None:
    """标记一次主模型不可用, 之后所有请求改用备用模型.

    由 :mod:`agents.llm_factory` 在捕获到 429 / 超时 / 空响应时调用.
    """
    global _use_fallback
    if not LLM_FALLBACK_MODEL or LLM_FALLBACK_MODEL == LLM_MODEL:
        return
    if not _use_fallback:
        logger.warning("切换到备用模型: %s", LLM_FALLBACK_MODEL)
    _use_fallback = True


def _resolve_model() -> str:
    """决定本次调用使用主模型还是备用模型.

    Returns:
        str: 实际使用的模型名.
    """
    if _use_fallback and LLM_FALLBACK_MODEL and LLM_FALLBACK_MODEL != LLM_MODEL:
        return LLM_FALLBACK_MODEL
    return LLM_MODEL


def get_llm(model: str | None = None, **overrides: Any) -> Any:
    """构建并缓存一个 CrewAI ``LLM`` 实例, 默认指向智谱 GLM.

    延迟导入 ``crewai``, 以便 ``config`` 可被不依赖 CrewAI 的工具模块安全导入.

    Args:
        model: 可选模型名, 覆盖 ``_resolve_model`` 的结果 (调试用).
        **overrides: 其余参数覆盖 (temperature / max_tokens 等).

    Returns:
        Any: CrewAI ``LLM`` 实例.
    """
    from crewai import LLM  # 延迟导入, 避免循环依赖

    if not is_key_set(ZHIPU_API_KEY):
        raise RuntimeError(
            "ZHIPU_API_KEY 未配置 — 请在 .env 中填入智谱控制台生成的 API Key."
        )

    model_name = model or _resolve_model()
    cache_key = f"{model_name}|{sorted(overrides.items())}"
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    params: dict[str, Any] = {
        "model": model_name,
        "base_url": LLM_BASE_URL,
        "api_key": ZHIPU_API_KEY,
        "temperature": LLM_TEMPERATURE,
        "top_p": LLM_TOP_P,
        "timeout": LLM_TIMEOUT,
        "max_tokens": LLM_MAX_TOKENS,
        "stream": LLM_STREAM,
    }
    if LLM_RATE_LIMIT_COOLDOWN > 0:
        # 撞到速率限制后的额外冷却, 避免密集重试再次触发限流
        params["max_retries"] = 8
        params["retry_after"] = LLM_RATE_LIMIT_COOLDOWN
    params.update(overrides)

    llm = LLM(**params)
    _llm_cache[cache_key] = llm
    return llm


def check_llm_available(base_url: str | None = None) -> bool:
    """检测智谱 API 是否可用 (供启动前自检).

    先校验密钥是否已配置, 再向 ``/models`` 端点发一次轻量请求.
    密钥无效或网络不通时返回 ``False``, 并记录原因.

    Args:
        base_url: 可选服务地址, 默认使用 ``LLM_BASE_URL``.

    Returns:
        bool: 服务可达且密钥有效返回 ``True``.
    """
    if not is_key_set(ZHIPU_API_KEY):
        logger.warning("ZHIPU_API_KEY 未配置 — 无法访问智谱 GLM API.")
        return False

    url = f"{(base_url or LLM_BASE_URL).rstrip('/')}/models"
    try:
        import requests

        resp = requests.get(url, headers={"Authorization": f"Bearer {ZHIPU_API_KEY}"}, timeout=5)
        if resp.status_code != 200:
            logger.warning("智谱 API 响应异常: HTTP %s (%s)", resp.status_code, url)
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("智谱 API 不可达 (%s): %s", url, exc)
        return False
