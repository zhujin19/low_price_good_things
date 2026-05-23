import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.paths import PROJECT_ROOT
from app.providers.ctrip_provider import CtripProvider


DEFAULT_STATE_PATH = PROJECT_ROOT / "storage" / "ctrip.storage-state.json"
_capture_process: subprocess.Popen | None = None
_last_health: dict | None = None


def storage_state_path() -> Path:
    return Path(settings.ctrip_storage_state_path or DEFAULT_STATE_PATH)


def storage_state_summary() -> dict:
    path = storage_state_path()
    summary = {
        "path": str(path),
        "exists": path.exists(),
        "cookie_count": 0,
        "ctrip_cookie_count": 0,
        "mtime": None,
        "size": None,
    }
    if not path.exists():
        return summary

    stat = path.stat()
    summary["mtime"] = datetime.fromtimestamp(stat.st_mtime)
    summary["size"] = stat.st_size
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        summary["read_error"] = "登录态文件无法读取或不是有效 JSON"
        return summary

    cookies = data.get("cookies") or []
    summary["cookie_count"] = len(cookies)
    summary["ctrip_cookie_count"] = len(
        [
            cookie
            for cookie in cookies
            if "ctrip.com" in (cookie.get("domain") or "")
            or "trip.com" in (cookie.get("domain") or "")
        ]
    )
    return summary


def capture_status() -> dict:
    global _capture_process
    if _capture_process is None:
        return {"running": False, "returncode": None}
    returncode = _capture_process.poll()
    if returncode is not None:
        status = {"running": False, "returncode": returncode}
        _capture_process = None
        return status
    return {"running": True, "returncode": None}


def start_capture() -> dict:
    global _capture_process
    status = capture_status()
    if status["running"]:
        return status

    script = PROJECT_ROOT / "scripts" / "save_ctrip_storage_state.py"
    _capture_process = subprocess.Popen(
        [
            sys.executable,
            str(script),
            "--auto",
            "--timeout",
            "180",
        ],
        cwd=str(PROJECT_ROOT),
        start_new_session=True,
    )
    return {"running": True, "returncode": None}


def check_health() -> dict:
    global _last_health
    _last_health = CtripProvider().check_login_health()
    return _last_health


def last_health() -> dict | None:
    return _last_health
