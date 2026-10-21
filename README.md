# ✈️ Travel Planner CrewAI / 旅行计划师多代理系统

> 基于 [CrewAI](https://github.com/joaomdmoura/crewAI) 的多智能体系统, 根据用户输入 (城市、天数、预算、偏好) 自动生成完整旅行计划: 每日行程、住宿、预算、本地推荐、参考来源与质量评分.

---
<p align="center">
  <img src="assets/magichour_ai_gif-2026-10-21-576x576-cmvidk7vg0174it013taq0j8e(1).gif" alt="Демонстрация работы" width="800" />
</p>

---

## 📁 项目结构

```
travel-planner-crewai/
├── README.md              ← 本文件
├── requirements.txt       ← Python  依赖
├── .gitignore
├── config.py              ← 配置与 API 密钥 (所有模块统一从这里读取)
├── agents/                ← 9 个代理, 每个独立文件
│   ├── coordinator.py      协调者: 解析用户请求
│   ├── web_researcher.py   网络调研: Tavily / SerpApi
│   ├── social_crawler.py   社交抓取: 小红书 + 高德
│   ├── hotel_agent.py      酒店推荐
│   ├── route_agent.py      行程规划
│   ├── budget_agent.py     预算分析
│   ├── visualizer.py       景点图片采集 (icrawler 下载实景照片)
│   ├── report_writer.py    报告编辑
│   └── qa_reviewer.py      质量审核
├── tools/                 ← 底层工具封装
│   ├── search_tools.py     Tavily / SerpApi / Bing
│   ├── xhs_crawler.py      小红书 (XHS)
│   ├── image_crawler.py    景点图片 (icrawler + Bing)
│   └── gaode_crawler.py    高德地图 (Amap)
├── crew/
│   └── travel_crew.py      ← 流水线编排器
├── frontend/
│   └── app.py              ← Streamlit UI (占位)
├── data/                   ← 本地数据 / 缓存
├── runs/                   ← 后台运行日志
└── output/                 ← 运行产物 (报告)
```

### 🔄 任务流水线

```
parse_request → web_research → social_crawl
        → select_hotels → plan_route → calculate_budget
        → visualize → write_report → review_quality
```

---

## ⚙️ 安装

需要 Python **3.10+**。

```bash
# 1. 克隆项目
git clone <repo-url>
cd travel-planner-crewai

# 2. 创建并激活 conda 环境
conda create -n travel-planner python=3.10 -y
conda activate travel-planner

# 3. 安装依赖
pip install -r requirements.txt
```

所有 API 密钥与模型参数都写在 `config.py` (以及同目录的 `.env` 中), 安装时无需单独配置.

---

## 🧠 使用的模型

系统使用智谱 GLM 云端模型, 通过 `litellm` 接入。主模型为 `zai/glm-4.7-flash` (免费额度, 200K 上下文)。当主模型不可用时会自动切换到备用模型 `zai/glm-4-flash-250414`。无需本地 GPU。

| 模型                      | 用途                                               |
|---------------------------|----------------------------------------------------|
| `zai/glm-4.7-flash`       | 主模型, 全部 9 个代理                              |
| `zai/glm-4-flash-250414`  | 备用, 故障时自动切换                               |
| `zai/glm-4.6v-flash`      | 支持图片的备选模型                                 |

所有 LLM 参数 (`LLM_MODEL`, `LLM_BASE_URL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT`, `MAX_ITER`) 在 `config.py` 中定义, 可通过环境变量或 `.env` 覆盖.

所有代理通过 `agents/llm_factory.py` → `default_llm()` 共享同一个 LLM 实例 (带缓存), 模型只初始化一次.

---

## 🔑 API 密钥定义位置

所有模块通过 `import config` 读取密钥。`config.py` 会先读取环境变量, 同目录的 `.env` 会在导入 `config` 时通过 `python-dotenv` 自动加载。`config.is_key_set(...)` 用于判断密钥是否已配置.

| 密钥                  | 用途                                       |
|-----------------------|--------------------------------------------|
| `ZHIPU_API_KEY`       | 主 LLM (智谱)                              |
| `TAVILY_API_KEY`      | 语义化网页搜索                             |
| `SERPAPI_API_KEY`     | Google 搜索                                |
| `BING_API_KEY`        | 备用网页搜索                               |
| `GAODE_API_KEY`       | 中国境内 POI 与路径                        |

---

## 🖼️ 景点图片下载

第 7 号代理 `visualizer` (景点图片采集员) **不绘制图表**, 而是从上游代理产出的景点名称出发, 通过 `icrawler` 调用 Bing 图片搜索下载各景点的实景照片.

```bash
# 快速验证单个景点
python3 agents/test_download_pic.py
```

每个景点保存到独立目录:

```
data/images/
├── 杭州西湖/     000001.jpg 000002.jpg ...
├── 灵隐寺/       000001.jpg ...
└── 西_湖/        000001.jpg ...
```

| 参数                        | 默认值        | 说明                 |
|-----------------------------|---------------|----------------------|
| `IMAGE_ROOT_DIR`            | `data/images` | 图片根目录           |
| `IMAGE_MAX_NUM_PER_PLACE`   | `10`          | 每个景点图片上限     |

特性:
- **无需任何 API Key** — 使用公开的 Bing 图片搜索;
- **按景点名去重**, 空名称直接丢弃;
- **优雅降级**: 单个景点失败不影响其他景点;
- **文件名自动清理非法字符**.

---

## ▶️ 运行

### 1. 环境准备 (只需一次)

```bash
cd travel-planner-crewai
conda activate travel-planner   # Python 3.10 及以上
```

项目根目录下的 `.env` 会被自动加载, 导入 `config` 时通过 `python-dotenv` 读取密钥, **无需手动 export**。

### 2. 运行流水线

```bash
python run_pipeline.py --city 上海 --days 3 --budget 5000 \
  --preferences "美食、历史人文、摄影打卡" --skip-images
```

> 这正是产出 `run14` 日志与 `output/report_上海_3d.md` 报告的命令.

### 全部参数

| 参数              | 作用                                | 默认值                 |
|-------------------|-------------------------------------|------------------------|
| `--city`          | 目标城市                            | `上海`                 |
| `--days`          | 旅行天数                            | `3`                    |
| `--budget`        | 总预算 (元)                         | `5000`                 |
| `--preferences`   | 兴趣偏好 (逗号分隔)                 | `美食、历史人文、摄影打卡` |
| `--skip-images`   | 跳过景点图片下载 (加速)             | 关闭                   |
| `--real-tools`    | 启用真实搜索工具 (Tavily / SerpApi / 高德) | 桩数据          |

### 3. 后台运行并写日志 (推荐)

完整流水线需要 20–40 分钟, 建议放到后台运行.

```bash
cd travel-planner-crewai
nohup python run_pipeline.py --city 杭州 --days 2 --skip-images > runs/run15.log 2>&1 &
echo "pid $!"
```

实时查看进度:

```bash
tail -f runs/run15.log
```

### 4. 检查运行结果

报告保存在:

```
output/report_<城市>_<天数>d.md
```

快速判断流水线是否跑完:

```bash
grep -cE "✅ \[" runs/run15.log            # 已完成的代理数 (应为 9)
grep -E "SANITY|报告已保存" runs/run15.log  # 最终报告
```

### 5. 不跑完整流水线的快速自检

```bash
python test_llm.py                 # 检查模型连通性
python agents/test_download_pic.py # 下载单个景点图片
python tests/test_fallback.py      # 备用模型切换单元测试 (约 45 秒)
```

### 日志里看什么

| 日志                   | 含义                                              |
|------------------------|---------------------------------------------------|
| `切换模型: ... -> ...` | 已切换到备用模型, 出现 1–2 次属正常              |
| `❌`                   | 代理报错                                          |
| `SANITY CHECK`         | 最终校验: 非空报告 / 包含城市名 / 包含天数, 三项都应为 `PASS` |

---

## 📌 待办事项

以下任务是让系统真正可用所必需的后续工作.

- [ ] **完整实现 `search_tools.py`**
      目前 Tavily / SerpApi / Bing 在缺少密钥时返回空结果。需要完善响应解析、重试、超时以及 `title` / `url` / `content` / `source` 字段的归一化.

- [ ] **完整实现 gaode_crawler.py（或改用 JS API）**
      主要计划 —— 接入高德 Place API（城市内 POI 搜索）和 Direction API（两点间路径规划），包括解析步骤（steps）、过滤 POI 类型以及支持批量拉取。
      **备选方案（如果使用 Web Service API 过于麻烦 / 耗时）**：研究如何将 AMap (高德地图) JS API 的交互式小部件直接嵌入到 Web 应用中。
      这可以同时解决两个问题：

            在界面上直接绘制出基于真实道路的路线（而不是一条直线）。

            直接从 JS 对象中提取精确的距离、行驶时间和步骤数（steps），而无需编写复杂的 Python 解析器来发送 HTTP 请求调用 Direction API。

- [ ] **完整实现 `xhs_crawler.py`**
      需要真正从小红书抓取数据:按关键词搜索、提取标签/点赞/图片/作者, 并处理请求频率限制.

- [ ] **补全各代理的详细描述**
      细化 9 个代理的 `goal` 与 `backstory`: 规定输出格式 (如 `coordinator` / `budget_agent` 输出严格 JSON)、明确信息来源、约束与验收标准, 减少各阶段之间的偏差.

- [ ] **跑一次不带桩数据的完整流水线**
      运行 `python run_pipeline.py --real-tools --city 上海 --days 3` 使用真实数据, 确认 9 个代理全部完成, `output/report_上海_3d.md` 内容真实完整, 且 `SANITY CHECK` 三项全部 `PASS`.

- [ ] **设计应用界面**
      基于已完成的 `report_上海_3d.md` 报告结构 (章节划分、预算表格、每日路线、照片画廊) 设计应用界面:按天交互式地图行程、预算图表、下载图片画廊, 以及导出为 PDF / Markdown.
