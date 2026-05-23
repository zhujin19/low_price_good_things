from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

from app.config import settings  # noqa: E402
from app.providers.ctrip_provider import CtripProvider  # noqa: E402


DEFAULT_STATE_PATH = PROJECT_ROOT / "storage" / "ctrip.storage-state.json"
LOGIN_URL = "https://passport.ctrip.com/user/login"
VERIFY_URL = "https://flights.ctrip.com/online/list/oneway-bjs-wuh?depdate=2026-06-05"


def main():
    state_path = Path(settings.ctrip_storage_state_path or DEFAULT_STATE_PATH)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    provider = CtripProvider()
    executable_path = settings.playwright_executable_path or provider._find_system_browser()
    launch_options = {
        "headless": False,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ],
    }
    if executable_path:
        launch_options["executable_path"] = executable_path

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_options)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1200},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        page = context.new_page()
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=settings.playwright_timeout_ms)
        print("已打开携程登录页。请在浏览器中完成登录。")
        print("登录完成后，回到终端按 Enter；脚本会访问机票页并保存 storage state。")
        input()
        page.goto(VERIFY_URL, wait_until="domcontentloaded", timeout=settings.playwright_timeout_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        page.wait_for_timeout(3000)
        context.storage_state(path=str(state_path))
        browser.close()

    print(f"携程登录态已保存到: {state_path}")
    print("请确认 .env 中 CTRIP_STORAGE_STATE_PATH 指向该文件，然后重启服务。")


if __name__ == "__main__":
    main()
