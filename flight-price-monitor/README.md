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

> 如未接入对应 Provider，可先保留默认值或按实际情况禁用相关任务。

### 5）启动服务

```bash
uvicorn app.main:app --reload --app-dir .
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

请确保你在项目根目录（即包含 `app/` 和 `scripts/` 的目录）执行命令：

```bash
python3 scripts/init_db.py
```

本项目的 `scripts/init_db.py` 已自动处理模块路径；如果你复制了旧脚本，请更新后重试。

## 扩展 Provider 指南

新增 Provider 时请遵循：

1. 在 `app/providers/` 下新增实现并继承 `BaseFlightProvider`
2. 返回统一字段结构，便于后续服务层处理
3. 在 `ProviderService` 中注册新 Provider

## 开发建议

- 新增模型后，记得重新执行 `python3 scripts/init_db.py`
- 建议为 Provider 增加独立日志，便于排查抓取失败问题
- 若页面模板有改动，重启服务以确保模板缓存刷新
