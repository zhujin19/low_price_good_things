# flight-price-monitor

## 安装依赖
pip install -r requirements.txt

## 安装 Playwright 浏览器
python scripts/install_playwright.py

## 初始化数据库
python scripts/init_db.py

## 启动服务
uvicorn app.main:app --reload --app-dir .

## 手动触发检测
curl -X POST http://127.0.0.1:8000/tasks/1/run

## 配置 API Key
复制 `.env.example` 为 `.env`，填写 `CTRIP_API_URL` 与 `CTRIP_API_KEY`。

## 扩展 Provider
新增 provider 并继承 `BaseFlightProvider`，返回统一结构并在 `ProviderService` 注册。
