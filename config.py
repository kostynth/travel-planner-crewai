"""全局配置: API 密钥集中存放, 其他模块统一从这里读取.

所有密钥均可通过同名环境变量覆盖, 否则使用占位符 ``"вставь_ключ"``;
模块函数 ``is_key_set`` 用于判断密钥是否真正配置.
"""

import os

# --- LLM 提供方 (OpenAI 兼容) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "вставь_ключ")

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
