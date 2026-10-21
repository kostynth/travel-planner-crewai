"""端到端冒烟测试: 跑通完整的 9 步多代理流水线.

特点:
- 使用真实的智谱 GLM 模型, 验证 LLM 交互链路;
- 默认使用 stub 工具 (无需 Tavily/XHS/高德 的 API Key 或网络);
- 所有步骤实时打印到终端, 便于观察代理间协作;
- 每完成一步立即落盘, 便于中断后检查进度.

用法::

    python3 run_pipeline.py                     # 上海 3 天
    python3 run_pipeline.py --city 杭州 --days 2
    python3 run_pipeline.py --real-tools        # 启用真实搜索工具

环境变量:
    ``USE_STUB_TOOLS=false`` 或 ``--real-tools`` 切换到真实工具.
    ``ZHIPU_API_KEY`` 必需 (见 .env).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

# 让本文件可在项目根目录直接执行
sys.path.insert(0, str(Path(__file__).parent))

# 必须在 import config 之前设置, 供 agents 读取
os.environ.setdefault("USE_STUB_TOOLS", "true")

import config  # noqa: E402
from crew import TravelPlannerCrew  # noqa: E402

# 让 crewai / litellm / 工具的日志实时出现在终端
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stdout,
)
# 这几个库的信息日志非常密集且价值不高, 降级为 WARNING
for noisy in ("urllib3", "httpx", "httpcore", "LiteLLM", "litellm", "CrewAI"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# ------------------------------------------------------------------
# 终端输出工具
# ------------------------------------------------------------------
_STEP_NO = 0


def _ts() -> str:
    """当前时间戳.

    Returns:
        str: ``HH:MM:SS`` 格式的时间.
    """
    return datetime.now().strftime("%H:%M:%S")


def banner(text: str, char: str = "=") -> None:
    """打印分节标题.

    Args:
        text: 标题文本.
        char: 分隔符字符.
    """
    print(f"\n{char * 78}\n{text}\n{char * 78}", flush=True)


def step(text: str) -> None:
    """打印带序号的步骤标题.

    Args:
        text: 步骤描述.
    """
    global _STEP_NO
    _STEP_NO += 1
    print(f"\n[{_ts()}] ── STEP {_STEP_NO}: {text} ", end="", flush=True)
    print("─" * max(0, 60 - len(text)), flush=True)


def info(msg: str) -> None:
    """打印信息行.

    Args:
        msg: 消息内容.
    """
    print(f"[{_ts()}] {msg}", flush=True)


def ok(msg: str) -> None:
    """打印成功行.

    Args:
        msg: 消息内容.
    """
    print(f"[{_ts()}] ✅ {msg}", flush=True)


def fail(msg: str) -> None:
    """打印错误行 (走 stderr).

    Args:
        msg: 消息内容.
    """
    print(f"[{_ts()}] ❌ {msg}", file=sys.stderr, flush=True)


def dump(title: str, content: str, limit: int = 1200) -> None:
    """打印代理产出 (过长时截断).

    Args:
        title: 产出标题.
        content: 文本内容.
        limit: 最大显示字符数.
    """
    text = (content or "").strip()
    if not text:
        info(f"── {title}: (空)")
        return
    truncated = len(text) > limit
    body = text[:limit] + ("\n  … 已截断" if truncated else "")
    print(f"\n[{_ts()}] ══ {title} ══\n{body}\n", flush=True)


# ------------------------------------------------------------------
# 配置检查
# ------------------------------------------------------------------
def preflight(skip_key_check: bool = False) -> bool:
    """检查密钥与模型可用性.

    Args:
        skip_key_check: True 时跳过密钥检查 (mock 模式).

    Returns:
        bool: 检查通过返回 True.
    """
    banner("PRE-FLIGHT 检查 / 预检查")
    info(f"LLM_MODEL    : {config.LLM_MODEL}")
    info(f"LLM_BASE_URL : {config.LLM_BASE_URL}")
    info(f"USE_STUB_TOOLS: {os.environ.get('USE_STUB_TOOLS')}")

    if skip_key_check:
        info("ZHIPU_API_KEY: mock 模式, 跳过检查 ✅")
        return True

    if not config.is_key_set(config.ZHIPU_API_KEY):
        fail("ZHIPU_API_KEY 未配置 — 请在 .env 中填入智谱 API Key, 或使用 --mock-llm.")
        return False

    info("ZHIPU_API_KEY: 已配置 ✅")
    return True


# ------------------------------------------------------------------
# 主流程
# ------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """解析命令行参数.

    Returns:
        argparse.Namespace: 解析结果.
    """
    parser = argparse.ArgumentParser(description="运行完整的旅行规划流水线")
    parser.add_argument("--city", default="上海", help="目标城市 (默认: 上海)")
    parser.add_argument("--days", type=int, default=3, help="旅行天数 (默认: 3)")
    parser.add_argument("--budget", type=int, default=5000, help="总预算 (默认: 5000)")
    parser.add_argument(
        "--preferences",
        default="美食、历史人文、摄影打卡",
        help="兴趣偏好 (默认: 美食、历史人文、摄影打卡)",
    )
    parser.add_argument(
        "--real-tools",
        action="store_true",
        help="使用真实搜索工具 (需配置 Tavily/SerpApi/XHS/高德 Key)",
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="跳过景点图片下载步骤 (加快测试)",
    )
    parser.add_argument(
        "--mock-llm",
        action="store_true",
        help="用桩数据替代真实 LLM 调用 (无需 API Key, 仅验证编排逻辑)",
    )
    return parser.parse_args()


def _install_mock() -> None:
    """安装桩 LLM (延迟导入, 避免无谓开销)."""
    from mock_llm import install_mock_llm

    install_mock_llm()


def save_report(result: str, city: str, days: int) -> Path:
    """把最终报告保存到 output 目录.

    Args:
        result: 报告文本.
        city: 城市名 (用于文件名).
        days: 天数 (用于文件名).

    Returns:
        Path: 保存的文件路径.
    """
    out_dir = Path(config.__file__).parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"report_{city}_{days}d.md"
    path.write_text(result, encoding="utf-8")
    return path


def main() -> int:
    """执行完整流水线.

    Returns:
        int: 0 表示成功, 1 表示失败.
    """
    args = parse_args()

    if args.real_tools:
        os.environ["USE_STUB_TOOLS"] = "false"
    elif "USE_STUB_TOOLS" not in os.environ:
        os.environ["USE_STUB_TOOLS"] = "true"

    if args.mock_llm:
        banner("MOCK MODE / 桩模式")
        info("将使用固定桩数据替代 LLM 调用 — 输出不具备真实参考价值.")
        _install_mock()

    if not preflight(skip_key_check=args.mock_llm):
        return 1

    user_request = {
        "city": args.city,
        "days": args.days,
        "budget": args.budget,
        "preferences": args.preferences,
    }

    banner("USER REQUEST / 用户请求")
    for k, v in user_request.items():
        info(f"{k:12} = {v}")

    banner("CREW 启动 / 启动 9 个代理")
    t0 = time.time()
    try:
        crew = TravelPlannerCrew(verbose=True)
    except Exception as exc:  # noqa: BLE001
        fail(f"代理初始化失败: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return 1

    ok(f"9 个代理就绪, 用时 {time.time() - t0:.1f}s")

    # 打印各代理的身份, 便于确认描述已生效
    banner("AGENTS / 代理清单")
    for name in (
        "coordinator", "web_researcher", "social_crawler", "hotel_agent",
        "route_agent", "budget_agent", "visualizer", "report_writer", "qa_reviewer",
    ):
        agent = getattr(crew, name)
        print(f"  • {name:16} role={agent.role}", flush=True)

    tasks = crew.create_tasks(user_request)

    banner("TASKS / 任务依赖")
    for i, t in enumerate(tasks, start=1):
        ctx = t.context
        try:
            ctx_len = len(ctx) if ctx else 0
        except TypeError:
            ctx_len = 0
        print(f"  {i}. agent={t.agent.role:<20} ctx={ctx_len}", flush=True)

    if args.skip_images:
        info("\n注意: --skip-images 仅跳过实际下载, 任务仍在流水线中.")

    banner("KICKOFF / 开始执行 (输出实时打印)")
    t0 = time.time()

    # 把每个 token 放入 stderr (蓝色前缀), 让 stdout 的最终报告摘要在视觉上分开
    import sys as _sys

    sys.stderr.reconfigure(encoding="utf-8")

    # 简单密码锁避免多个生产者同时写
    _lock = threading.Lock()
    _buf: list[str] = []

    def emit(chunk: str) -> None:
        """接收流式 token, 实时打印到 stderr.

        Args:
            chunk: 一个增量片段, 可能跨行.
        """
        chunk = (chunk or "").replace("\r", "\n")
        with _lock:
            # 使用累积+逐行 flush, 避免单独的小分片反复换行
            lines = ("" .join(_buf) + chunk).split("\n")
            _buf.clear()
            for line in lines[:-1]:
                _sys.stderr.write(f"\x1b[2;36m│ {line}\x1b[0m\n")
            _buf.append(lines[-1])
        _sys.stderr.flush()

    try:
        result = crew.run(user_request, stream=True, on_token=emit)
    except Exception as exc:  # noqa: BLE001
        fail(f"流水线执行失败: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return 1
    finally:
        with _lock:
            if _buf and _buf[0]:
                _sys.stderr.write(f"\x1b[2;36m│ {_buf[0]}\x1b[0m\n")
                _buf.clear()

    elapsed = time.time() - t0

    banner("RESULT / 最终报告")
    def _extract(result: Any) -> str:
        """从 CrewAI 返回值中提取最终文本.

        Args:
            result: run() 任意返回值.

        Returns:
            str: 最终文本.
        """
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        for attr in ("raw", "output", "final_output"):
            if hasattr(result, attr):
                value = getattr(result, attr)
                if isinstance(value, str) and value:
                    return value
        # Последний fallback
        return str(result)

    final = _extract(result)

    # crew.kickoff() 返回的是「最后一个任务」(质量审核) 的产出, 而真正的
    # 旅行报告来自第 8 个任务 (旅行报告编辑). 优先取报告任务的输出.
    report_output = getattr(crew, "last_report", "") or ""

    if report_output and len(report_output) > 100:
        # 报告任务的产出才是真正的旅行报告, 始终优先于 kickoff 的返回值
        final = report_output

    dump("最终产出", final, limit=4000)

    path = save_report(final, args.city, args.days)
    ok(f"报告已保存: {path}")
    ok(f"总用时 {elapsed:.1f}s, 报告长度 {len(final)} 字符")

    # 简单断言: 报告应包含关键章节
    banner("SANITY CHECK / 结果校验")
    checks = {
        "非空报告": len(final) > 100,
        "包含城市名": args.city in final,
        "包含天数": str(args.days) in final,
    }
    for name, passed in checks.items():
        (ok if passed else fail)(f"{name}: {'PASS' if passed else 'FAIL'}")

    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())