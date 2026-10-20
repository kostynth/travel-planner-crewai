# ✈️ Travel Planner CrewAI / 旅行计划师多代理系统

> **RU**: Мультиагентная система на базе [CrewAI](https://github.com/joaomdmoura/crewAI), которая по запросу пользователя (город, дни, бюджет, предпочтения) генерирует полный план путешествия: маршрут по дням, отели, бюджет, рекомендации, источники и оценку качества.
>
> **中文**: 基于 [CrewAI](https://github.com/joaomdmoura/crewAI) 的多智能体系统, 根据用户输入 (城市、天数、预算、偏好) 自动生成完整旅行计划: 每日行程、住宿、预算、本地推荐、参考来源与质量评分.

---

## 📁 Структура проекта / 项目结构

```
travel-planner-crewai/
├── README.md              ← 本文件
├── requirements.txt       ← Python 依赖
├── .gitignore
├── config.py              ← API 密钥 (所有模块统一从这里读取)
├── agents/                ← 9 个代理, 每个独立文件
│   ├── coordinator.py      协调者: 解析用户请求
│   ├── web_researcher.py   网络调研: Tavily / SerpApi
│   ├── social_crawler.py   社交抓取: 小红书 + 高德
│   ├── hotel_agent.py      酒店推荐
│   ├── route_agent.py      行程规划
│   ├── budget_agent.py     预算分析
│   ├── visualizer.py       可视化数据准备
│   ├── report_writer.py    报告编辑
│   └── qa_reviewer.py      质量审核
├── tools/                 ← 底层工具封装
│   ├── search_tools.py     Tavily / SerpApi / Bing
│   ├── xhs_crawler.py      小红书 (XHS)
│   └── gaode_crawler.py    高德地图 (Amap)
├── crew/
│   └── travel_crew.py      ← 流水线编排器
├── frontend/
│   └── app.py              ← Streamlit UI (占位)
├── data/                   ← 本地数据 / 缓存
└── output/                 ← 运行产物
```

### 🔄 Pipeline / 任务流水线

```
parse_request → web_research → social_crawl
        → select_hotels → plan_route → calculate_budget
        → visualize → write_report → review_quality
```

---

## ⚙️ Установка / 安装

**RU**: Требуется Python **3.10+**.
**中文**: 需要 Python **3.10+**.

```bash
# 1. Клонировать проект / 克隆项目
git clone <repo-url>
cd travel-planner-crewai

# 2. Создать venv / 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Установить зависимости / 安装依赖
pip install -r requirements.txt
```

---

## 🔑 Где брать API-ключи / 从哪里获取 API 密钥

**RU**: Все ключи считываются модулями через `import config`. Сам `config.py` сначала читает переменные окружения, а если они не заданы — подставляет заглушку `"вставь_ключ"`. Функция `config.is_key_set(...)` используется для проверки; если ключ отсутствует, агент работает в режиме graceful degradation (без данных, но без падения).

**中文**: 所有模块通过 `import config` 读取密钥。`config.py` 会先尝试读取同名环境变量, 若未设置则回退为占位符 `"вставь_ключ"`。`config.is_key_set(...)` 用于判断密钥是否已配置; 若缺失, 代理进入优雅降级模式 (返回空数据但不抛错)。

Рекомендуется создать `.env` (рекомендуется) или экспортировать ключи / 推荐创建 `.env` 或在终端导出:

```bash
export OPENAI_API_KEY="sk-..."
export TAVILY_API_KEY="tvly-..."
export SERPAPI_API_KEY="..."
export GAODE_API_KEY="..."
export BING_API_KEY="..."
```

> `python-dotenv` уже добавлен в `requirements.txt`, поэтому достаточно положить `.env` рядом с `config.py`.
> `python-dotenv` 已加入 `requirements.txt`, 把 `.env` 放到 `config.py` 同级即可自动加载.

| Сервис / 服务        | Назначение / 用途                          | Консоль / 控制台                            |
|----------------------|--------------------------------------------|----------------------------------------------|
| OpenAI               | LLM для всех агентов / 所有代理的 LLM      | https://platform.openai.com                  |
| Tavily               | Семантический веб-поиск / 语义化网页搜索   | https://app.tavily.com                       |
| SerpApi              | Поиск Google / Google 搜索                | https://serpapi.com                          |
| Bing Search          | Дополнительный веб-поиск / 备用网页搜索    | https://portal.azure.com                     |
| Gaode (Amap) / 高德  | POI и маршруты в Китае / 中国境内 POI 与路径 | https://lbs.amap.com                         |

---

## ▶️ Запуск / 运行

### Python API / Python 调用

```python
from crew import TravelPlannerCrew

crew = TravelPlannerCrew()
result = crew.run(
    user_request={
        "city": "上海",
        "days": 4,
        "budget": 5000,
        "preferences": ["历史文化", "美食", "夜生活"],
    }
)
print(result)
```

### Streamlit UI / Streamlit 前端

```bash
streamlit run frontend/app.py
```

---

## 🛡️ Graceful Degradation / 优雅降级

- Любой метод `SearchTools` без ключа возвращает `[]` и пишет warning в лог.
  任一 `SearchTools` 方法在缺少密钥时返回 `[]` 并写入 warning 日志.
- `crewai_tools` опциональны: если их нет — `web_researcher` создаётся без них.
  `crewai_tools` 为可选依赖, 缺失时 `web_researcher` 将在无工具状态下工作.
- XHS-краулер возвращает mock-данные при отсутствии авторизации.
  XHS 爬虫在无凭据时返回本地 mock 数据.
- Gaode-методы возвращают пустые структуры без ключа.
  高德接口在无密钥时返回空结构.

Это позволяет запускать pipeline даже с минимальной конфигурацией (например, только OpenAI).
即使仅配置了 OpenAI, 流水线仍可运行.

---

## 📝 Roadmap / 路线图

- [ ] Заполнить `goal` и `backstory` для каждого агента / 填入每个代理的 `goal` / `backstory`
- [ ] Реализовать Streamlit-форму и графики Plotly / 实现 Streamlit 表单与 Plotly 图表
- [ ] Подключить реальный XHS-провайдер / 接入真实 XHS 数据源
- [ ] Расширить тесты в `tests/` / 在 `tests/` 中补充单元测试

## 📄 Лицензия / 许可证

MIT
