import subprocess
import sys


if sys.platform.startswith("linux"):
    subprocess.call([sys.executable, "-m", "playwright", "install-deps", "chromium"])
subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
print("Playwright chromium installed")
