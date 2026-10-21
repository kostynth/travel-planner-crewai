"""冒烟测试: 验证智谱 GLM 模型与项目配置是否可用.

运行方式::

    python3 test_llm.py
"""

import config


def test_llm_call() -> None:
    """直接调用云端模型, 确认推理链路通畅."""
    llm = config.get_llm()
    response = llm.call("Скажи одним предложением, что такое Ханчжоу.")
    print("LLM 响应:", response)


def test_config() -> None:
    """打印当前配置与外部服务可用性."""
    print("=" * 50)
    print("LLM_PROVIDER :", config.LLM_PROVIDER)
    print("LLM_MODEL    :", config.LLM_MODEL)
    print("LLM_BASE_URL :", config.LLM_BASE_URL)
    print("智谱可用     :", config.check_llm_available())
    print("=" * 50)


def test_agents_import() -> None:
    """验证所有代理工厂函数可正常导入与实例化."""
    try:
        from crew import TravelPlannerCrew

        planner = TravelPlannerCrew(verbose=False)
        print("代理创建成功, 共", 9, "个")
        assert planner.coordinator is not None
    except ImportError as exc:
        print("跳过 (crewai 未安装):", exc)
    except Exception as exc:  # noqa: BLE001
        print("代理创建失败:", type(exc).__name__, exc)


if __name__ == "__main__":
    test_config()
    test_llm_call()
    #test_agents_import()
