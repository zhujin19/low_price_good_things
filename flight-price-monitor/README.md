# flight-price-monitor

一个基于 FastAPI + SQLAlchemy + Playwright 的机票价格监控系统。可配置多条监控任务，按设定时间自动抓取价格，并在达到阈值时触发告警。

## 功能特性

- 多平台 Provider 抽象（携程、飞猪、美团、国航、南航、东航等）
- 定时执行航班价格抓取
- 价格历史记录与任务管理
- 告警记录与可视化页面
- 支持手动触发单条任务检测

## 项目结构

```text
flight-price-monitor/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置读取
│   ├── database.py             # 数据库引擎与 Session
│   ├── models/                 # 数据模型
│   ├── providers/              # 各平台抓取实现
│   ├── scheduler/jobs.py       # 定时任务注册
│   ├── services/               # 业务逻辑
│   └── templates/              # 页面模板
├── scripts/
│   ├── init_db.py              # 初始化数据库表
│   └── install_playwright.py   # 安装 Playwright 浏览器
├── requirements.txt
└── README.md
```

## 环境要求

- Python 3.10+
- 建议使用 `venv` 或 `conda` 创建独立环境

## 快速开始

> 以下命令默认在 `flight-price-monitor` 目录下执行。

### 1）安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2）安装 Playwright 浏览器

```bash
python3 scripts/install_playwright.py
```

Ubuntu 上建议同时安装 Chrome/Chromium 依赖：

```bash
python3 -m playwright install-deps chromium
python3 -m playwright install chromium
```

### 3）初始化数据库

```bash
python3 scripts/init_db.py
```

如果看到 `DB initialized`，说明数据库表已创建成功。

### 4）配置环境变量

复制并编辑环境文件：

```bash
cp .env.example .env
```

至少需要关注以下配置：

- `CTRIP_API_URL`
- `CTRIP_API_KEY`
- `CTRIP_STORAGE_STATE_PATH`

> 如未接入外部 Provider，可先保留 `CTRIP_API_URL` / `CTRIP_API_KEY` 为空。需要抓取携程航班明细时，建议配置 `CTRIP_STORAGE_STATE_PATH`。

### 5）启动服务

```bash
uvicorn app.main:app --reload --app-dir .
```

也可以使用项目内置入口启动，适合 Ubuntu 上通过 `nohup`、systemd 或 supervisor 执行：

```bash
python3 /path/to/flight-price-monitor/run.py --host 0.0.0.0 --port 8000
```

如果希望安装成命令行工具：

```bash
pip install -e .
flight-price-monitor --host 0.0.0.0 --port 8000
```

启动后访问：

- Web 页面：`http://127.0.0.1:8000/`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`

## 常用操作

### 手动触发某条任务检测

```bash
curl -X POST http://127.0.0.1:8000/tasks/1/run
```

### 常见问题

#### `ModuleNotFoundError: No module named 'app'`

这个错误通常是 Ubuntu 服务脚本、`nohup` 或 supervisor 没有在项目根目录执行，导致 Python 找不到 `app/` 包。推荐改用内置入口，它会自动把项目根目录加入 `uvicorn` 的模块搜索路径：

```bash
python3 /path/to/flight-price-monitor/run.py --host 0.0.0.0 --port 8000
```

如果继续直接使用 `uvicorn`，请确保在项目根目录（即包含 `app/` 和 `scripts/` 的目录）执行，并显式指定 `--app-dir`：

```bash
cd /path/to/flight-price-monitor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir .
```

初始化数据库也请使用项目路径下的脚本：

```bash
python3 scripts/init_db.py
```

本项目现在会固定读取项目根目录下的 `.env`，默认 SQLite 数据库也固定为项目根目录下的 `flight_monitor.db`，避免服务工作目录不同导致本地和 Ubuntu 行为不一致。

#### Ubuntu 执行成功但结果为空

携程页面在无头浏览器下可能返回空航班列表或要求登录，表现为日志里 `returned 0 flights`。本项目已对无头模式增加浏览器特征兼容，并把 0 条结果标记为 `no_results`，日志会包含页面标题、最终 URL、是否出现“未找到符合条件的航班”、以及 `needUserLogin` 等诊断信息。

当前版本支持两层携程抓取：

1. 如配置了 `CTRIP_STORAGE_STATE_PATH` 且文件存在，会优先使用 Playwright 登录态打开携程机票页，抓取航班明细。
2. 如果未配置登录态，或明细抓取没有返回航班，会回退调用携程低价日历接口抓取目标日期的日期级最低价。

低价日历数据可以用于跑通低价监控和阈值告警，但不包含具体航班号与起飞时间；命中后结果会标记为“日期最低价 / 待确认”，用户需要打开携程链接确认具体航班。如果你接入了自己的 `CTRIP_API_URL` 和 `CTRIP_API_KEY`，系统仍会优先使用外部接口返回的航班明细数据。

#### 保存携程登录态

本项目不保存携程账号密码，只保存 Playwright storage state 文件。该文件包含登录 Cookie，必须只保存在本机或可信服务器，不要提交到 Git。

可以在 Web 页面进入 `设置`，点击 `获取登录态`。系统会打开携程登录窗口，完成登录后会自动保存登录态。保存后点击 `健康检查`，页面会显示 Cookie 是否有效。

也可以在终端手动执行：

```bash
python3 scripts/save_ctrip_storage_state.py
```

脚本会打开携程登录页。完成登录后回到终端按 Enter，脚本会把登录态保存到 `.env` 中 `CTRIP_STORAGE_STATE_PATH` 指向的位置，默认是：

```text
storage/ctrip.storage-state.json
```

保存后重启服务，再手动触发任务：

```bash
curl -X POST http://127.0.0.1:8000/tasks/1/run
```

如果日志中仍出现 `needUserLogin: true`，说明登录态已失效或未覆盖携程机票域名，请重新运行脚本。

如果 Ubuntu 仍然持续返回 0，可以改用虚拟显示器运行有头浏览器：

```bash
sudo apt-get update
sudo apt-get install -y xvfb
PLAYWRIGHT_HEADLESS=false xvfb-run -a python3 /path/to/flight-price-monitor/run.py --host 0.0.0.0 --port 8000
```

## 扩展 Provider 指南

新增 Provider 时请遵循：

1. 在 `app/providers/` 下新增实现并继承 `BaseFlightProvider`
2. 返回统一字段结构，便于后续服务层处理
3. 在 `ProviderService` 中注册新 Provider

## 开发建议

- 新增模型后，记得重新执行 `python3 scripts/init_db.py`
- 建议为 Provider 增加独立日志，便于排查抓取失败问题
- 若页面模板有改动，重启服务以确保模板缓存刷新
