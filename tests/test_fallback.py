"""Проверка автоматического переключения на резервную модель.

Запускается без сети: litellm.completion подменяется заглушкой, которая
имитирует разные режимы отказа основной модели.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import litellm  # noqa: E402

import config  # noqa: E402
from agents.llm_factory import default_llm  # noqa: E402

PRIMARY = config.LLM_MODEL
FALLBACK = config.LLM_FALLBACK_MODEL


class _Msg:
    def __init__(self, content: str | None) -> None:
        self.content = content
        self.role = "assistant"
        self.tool_calls = None


class _Choice:
    def __init__(self, content: str | None, finish_reason: str) -> None:
        self.message = _Msg(content)
        self.finish_reason = finish_reason
        self.index = 0


class _Resp:
    def __init__(self, content: str | None, finish_reason: str) -> None:
        self.choices = [_Choice(content, finish_reason)]
        self.model_extra = {}


def _make_error() -> Exception:
    """Создать исключение, похожее на 429 от 智谱."""
    err = litellm.exceptions.RateLimitError(
        message="该模型当前访问量过大，请您稍后再试",
        llm_provider="zai",
        model=PRIMARY,
        response=None,
    )
    err.status_code = 429
    return err


def scenario(name: str, behaviour: str) -> bool:
    """Проверить один сценарий отказа основной модели.

    Args:
        name: Название сценария.
        behaviour: Что делает заглушка: "429" / "empty" / "ok".

    Returns:
        bool: Сценарий прошёл успешно.
    """
    config.reset_fallback()
    config._llm_cache.clear()
    used_models: list[str] = []

    def fake_completion(**kwargs):
        model = kwargs.get("model", "")
        used_models.append(model)
        if model == FALLBACK:
            return _Resp("来自备用模型的回答", "stop")
        if behaviour == "429":
            raise _make_error()
        if behaviour == "empty":
            return _Resp(None, "length")
        return _Resp("来自主模型的回答", "stop")

    original = litellm.completion
    litellm.completion = fake_completion  # type: ignore[assignment]
    try:
        llm = default_llm()
        result = llm.call("测试")
    except Exception as exc:  # noqa: BLE001
        print(f"[{name}] EXCEPTION: {type(exc).__name__}: {exc}")
        return False
    finally:
        litellm.completion = original  # type: ignore[assignment]

    text = str(result)
    if behaviour == "ok":
        # 主模型正常时不应切换
        ok = used_models == [PRIMARY] and "主模型" in text
    else:
        ok = (
            FALLBACK in used_models
            and "备用模型" in text
            and config._resolve_model() == FALLBACK
        )
    status = "OK " if ok else "FAIL"
    print(f"[{status}] {name}: models={used_models} result={text[:40]!r}")
    return ok


def main() -> int:
    """Прогнать все сценарии.

    Returns:
        int: 0 — все сценарии прошли, 1 — есть провалы.
    """
    results = [
        scenario("主模型 429 限流", "429"),
        scenario("主模型返回空 content", "empty"),
        scenario("主模型正常 (不应切换)", "ok"),
    ]
    if all(results):
        print("\n全部通过 ✅")
        return 0
    print("\n有失败用例 ❌")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
