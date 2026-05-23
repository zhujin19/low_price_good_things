from datetime import date, datetime, timezone, timedelta
import os
from pathlib import Path
import re
import shutil
import uuid

import httpx
from playwright.sync_api import sync_playwright

from app.config import settings
from app.providers.base import BaseFlightProvider


CITY_CODES = {
    "北京": "bjs",
    "武汉": "wuh",
    "上海": "sha",
    "广州": "can",
    "深圳": "szx",
    "成都": "ctu",
    "杭州": "hgh",
    "南京": "nkg",
    "重庆": "ckg",
    "西安": "sia",
}

SYSTEM_BROWSER_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

LOW_PRICE_CALENDAR_URL = (
    "https://m.ctrip.com/restapi/soa2/15380/bjjson/"
    "FlightIntlAndInlandLowestPriceSearch"
)


class CtripProvider(BaseFlightProvider):
    name = "ctrip"

    def __init__(self):
        self.last_diagnostics: dict = {}

    def search(self, origin: str, destination: str, target_date: date) -> list[dict]:
        self.last_diagnostics = {}
        if settings.ctrip_api_url and settings.ctrip_api_key:
            return self._search_by_api(origin, destination, target_date)

        if self._storage_state_path():
            detail_rows = self._search_by_playwright(origin, destination, target_date)
            if detail_rows:
                return detail_rows
            detail_diagnostics = self.last_diagnostics
            calendar_rows = self._search_by_low_price_calendar(origin, destination, target_date)
            if calendar_rows:
                self.last_diagnostics = {
                    "mode": "playwright_with_calendar_fallback",
                    "playwright": detail_diagnostics,
                    "fallback": self.last_diagnostics,
                }
                return calendar_rows
            if self.last_diagnostics.get("reason") == "calendar_no_price":
                self.last_diagnostics = {
                    "mode": "playwright_with_calendar_fallback",
                    "playwright": detail_diagnostics,
                    "fallback": self.last_diagnostics,
                }
                return []

        calendar_rows = self._search_by_low_price_calendar(origin, destination, target_date)
        if calendar_rows:
            return calendar_rows
        if self.last_diagnostics.get("reason") == "calendar_no_price":
            return []
        return self._search_by_playwright(origin, destination, target_date)

    def _search_by_api(self, origin: str, destination: str, target_date: date) -> list[dict]:
        resp = httpx.get(
            settings.ctrip_api_url,
            headers={"Authorization": f"Bearer {settings.ctrip_api_key}"},
            params={
                "origin": origin,
                "destination": destination,
                "date": target_date.isoformat(),
            },
            timeout=settings.ctrip_api_timeout,
        )
        resp.raise_for_status()
        return [self._normalize(x) for x in resp.json().get("flights", [])]

    def _search_by_low_price_calendar(
        self,
        origin: str,
        destination: str,
        target_date: date,
    ) -> list[dict]:
        origin_code = self._city_code(origin).upper()
        destination_code = self._city_code(destination).upper()
        transaction_id = uuid.uuid4().hex
        payload = {
            "departNewCityCode": origin_code,
            "arriveNewCityCode": destination_code,
            "startDate": target_date.isoformat(),
            "grade": 15,
            "flag": 0,
            "channelName": "FlightOnline",
            "searchType": 1,
            "passengerList": [
                {"passengercount": 1, "passengertype": "Adult"},
            ],
            "calendarSelections": [
                {"selectionType": 8, "selectionContent": ["15"]},
            ],
        }
        try:
            resp = httpx.post(
                LOW_PRICE_CALENDAR_URL,
                headers={
                    "content-type": "application/json;charset=UTF-8",
                    "referer": "https://flights.ctrip.com/",
                    "transactionid": transaction_id,
                    "user-agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    ),
                },
                json=payload,
                timeout=settings.ctrip_api_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            self.last_diagnostics = {
                "mode": "low_price_calendar",
                "status": "failed",
                "reason": str(exc),
            }
            return []

        price_list = data.get("priceList") or []
        matched = self._find_calendar_price(price_list, target_date)
        if not matched:
            self.last_diagnostics = {
                "mode": "low_price_calendar",
                "status": "no_results",
                "reason": "calendar_no_price",
                "price_items": len(price_list),
            }
            return []

        price = self._calendar_price(matched)
        if price is None or price <= 0:
            self.last_diagnostics = {
                "mode": "low_price_calendar",
                "status": "no_results",
                "reason": "calendar_no_price",
                "target_item": matched,
            }
            return []

        booking_url = self._build_url(origin, destination, target_date)
        self.last_diagnostics = {
            "mode": "low_price_calendar",
            "status": "success",
            "target_date": target_date.isoformat(),
            "price": price,
            "detail": "date-level lowest price; flight time must be confirmed on Ctrip",
        }
        return [
            {
                "provider": self.name,
                "flight_no": "日期最低价",
                "airline": "携程低价日历",
                "depart_airport": origin,
                "arrive_airport": destination,
                "depart_time": "待确认",
                "arrive_time": "待确认",
                "adult_price": price,
                "booking_url": booking_url,
                "price_scope": "date_lowest",
            }
        ]

    def _search_by_playwright(self, origin: str, destination: str, target_date: date) -> list[dict]:
        urls = self._build_urls(origin, destination, target_date)
        launch_options = {
            "headless": settings.playwright_headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        }
        executable_path = settings.playwright_executable_path or self._find_system_browser()
        if executable_path:
            launch_options["executable_path"] = executable_path

        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_options)
            storage_state_path = self._storage_state_path()
            context_options = {
                "viewport": {"width": 1440, "height": 1200},
                "user_agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                "locale": "zh-CN",
                "timezone_id": "Asia/Shanghai",
            }
            if storage_state_path:
                context_options["storage_state"] = str(storage_state_path)
            context = browser.new_context(**context_options)
            context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                """
            )
            page = context.new_page()
            batch_search_status = {}

            def capture_batch_search(response):
                if "search/api/search/batchSearch" not in response.url:
                    return
                try:
                    payload = response.json()
                except Exception:
                    return
                batch_search_status["status"] = payload.get("status")
                batch_search_status["msg"] = payload.get("msg")
                data = payload.get("data") or {}
                batch_search_status["needUserLogin"] = data.get("needUserLogin")
                batch_search_status["lgn"] = data.get("lgn")

            page.on("response", capture_batch_search)
            rows = []
            booking_url = urls[0]
            diagnostics = []
            for url in urls:
                page.goto(url, wait_until="domcontentloaded", timeout=settings.playwright_timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                page.wait_for_timeout(8000)
                item_count = page.locator(".flight-item.domestic").count()
                body_text = self._safe_body_text(page)
                diagnostics.append(
                    {
                        "url": url,
                        "final_url": page.url,
                        "title": page.title(),
                        "flight_items": item_count,
                        "no_flights_text": "未找到符合条件的航班" in body_text,
                        "need_user_login": batch_search_status.get("needUserLogin"),
                    }
                )
                if item_count == 0:
                    continue
                booking_url = page.url
                rows = page.eval_on_selector_all(".flight-item.domestic", self._dom_extract_script())
                if rows:
                    break
            browser.close()

        flights = [self._normalize_dom_row(row, booking_url) for row in rows]
        normalized_rows = [row for row in flights if row is not None]
        if not normalized_rows:
            self.last_diagnostics = {
                "mode": "playwright",
                "headless": settings.playwright_headless,
                "browser": executable_path or "playwright-chromium",
                "storage_state": str(storage_state_path) if storage_state_path else None,
                "batch_search": batch_search_status,
                "pages": diagnostics[-3:],
            }
        return normalized_rows

    def _build_urls(self, origin: str, destination: str, target_date: date) -> list[str]:
        origin_code = self._city_code(origin)
        destination_code = self._city_code(destination)
        date_text = target_date.isoformat()
        return [
            (
                "https://flights.ctrip.com/online/list/"
                f"oneway-{origin_code}-{destination_code}"
                f"?depdate={date_text}&cabin=y_s_c_f&adult=1&child=0&infant=0"
            ),
            f"https://flights.ctrip.com/online/list/oneway-{origin_code}-{destination_code}?_=1&depdate={date_text}",
            f"https://flights.ctrip.com/itinerary/oneway/{origin_code}-{destination_code}?date={date_text}",
        ]

    def _build_url(self, origin: str, destination: str, target_date: date) -> str:
        return self._build_urls(origin, destination, target_date)[0]

    def _dom_extract_script(self) -> str:
        return """
        items => items.map(item => {
          const text = item.innerText || "";
          const query = selector => item.querySelector(selector);
          const timeNodes = Array.from(item.querySelectorAll(".time")).map(x => (x.innerText || "").trim());
          const airportNodes = Array.from(item.querySelectorAll(".airport .name")).map(x => (x.innerText || "").trim());
          const planeNode = query(".plane-No");
          const airlineNode = query(".airline-name span");
          const comfortNode = query("[id^='comfort-']");
          const flightInfoNode = query("[id^='flightInfo-']");
          const priceNode = query(".price .price") || query(".price");
          return {
            text,
            html: item.outerHTML,
            airline: (query(".airline-name")?.innerText || "").trim(),
            flightNoText: (planeNode?.innerText || "").trim(),
            flightNoId: [
              airlineNode?.id || "",
              comfortNode?.id || "",
              flightInfoNode?.id || ""
            ].join(" "),
            departTime: timeNodes[0] || "",
            arriveTime: timeNodes[1] || "",
            departAirport: airportNodes[0] || "",
            arriveAirport: airportNodes[1] || "",
            priceText: (priceNode?.innerText || "").trim()
          };
        })
        """

    def _city_code(self, city: str) -> str:
        code = CITY_CODES.get(city.strip())
        if not code:
            raise ValueError(f"携程暂未配置城市代码: {city}")
        return code

    def _find_system_browser(self) -> str | None:
        if chrome := shutil.which("google-chrome"):
            return chrome
        if chromium := shutil.which("chromium"):
            return chromium
        for path in SYSTEM_BROWSER_CANDIDATES:
            if os.path.exists(path):
                return path
        return None

    def _storage_state_path(self) -> Path | None:
        if not settings.ctrip_storage_state_path:
            return None
        path = Path(settings.ctrip_storage_state_path)
        return path if path.exists() else None

    def _normalize_dom_row(self, row: dict, booking_url: str) -> dict | None:
        price = self._extract_int(row.get("priceText", ""))
        if price is None:
            price = self._extract_int(row.get("text", ""))
        if price is None:
            return None

        flight_no = (
            self._extract_flight_no(row.get("flightNoText", ""))
            or self._extract_flight_no(row.get("flightNoId", ""))
            or self._extract_flight_no(row.get("html", ""))
        )
        airline = row.get("airline") or self._first_line(row.get("text", "")) or "UNKNOWN"
        depart_time = self._normalize_time(row.get("departTime", ""))
        arrive_time = self._normalize_time(row.get("arriveTime", ""))
        if not depart_time:
            depart_time = self._extract_time(row.get("text", ""), index=0)
        if not arrive_time:
            arrive_time = self._extract_time(row.get("text", ""), index=1)

        return {
            "provider": self.name,
            "flight_no": flight_no or "UNKNOWN",
            "airline": airline,
            "depart_airport": row.get("departAirport") or "",
            "arrive_airport": row.get("arriveAirport") or "",
            "depart_time": depart_time,
            "arrive_time": arrive_time,
            "adult_price": price,
            "booking_url": booking_url,
        }

    def _normalize(self, row: dict) -> dict:
        return {
            "provider": self.name,
            "flight_no": row.get("flight_no", ""),
            "airline": row.get("airline", ""),
            "depart_airport": row.get("depart_airport", ""),
            "arrive_airport": row.get("arrive_airport", ""),
            "depart_time": self._normalize_time(row.get("depart_time", "")),
            "arrive_time": self._normalize_time(row.get("arrive_time", "")),
            "adult_price": int(row.get("adult_price", 0)),
            "booking_url": row.get("booking_url", ""),
        }

    def _find_calendar_price(self, price_list: list[dict], target_date: date) -> dict | None:
        for item in price_list:
            if self._parse_ctrip_date(item.get("departDate")) == target_date:
                return item
        return None

    def _parse_ctrip_date(self, value: str | None) -> date | None:
        match = re.search(r"/Date\((\d+)", value or "")
        if not match:
            return None
        timestamp = int(match.group(1)) / 1000
        return datetime.fromtimestamp(
            timestamp,
            tz=timezone(timedelta(hours=8)),
        ).date()

    def _calendar_price(self, item: dict) -> int | None:
        value = item.get("price") or item.get("transportPrice") or item.get("totalPrice")
        if value in (None, ""):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _extract_int(self, value: str) -> int | None:
        match = re.search(r"[¥￥]?\s*(\d+)", value or "")
        return int(match.group(1)) if match else None

    def _extract_flight_no(self, value: str) -> str | None:
        match = re.search(r"([A-Z]{2}\d{3,5})", value or "")
        return match.group(1) if match else None

    def _extract_time(self, value: str, index: int) -> str:
        matches = re.findall(r"\b\d{1,2}:\d{2}\b", value or "")
        if len(matches) <= index:
            return ""
        return self._normalize_time(matches[index])

    def _normalize_time(self, value: str) -> str:
        value = (value or "").strip()
        match = re.search(r"\b(\d{1,2}:\d{2})\b", value)
        if not match:
            return ""
        hour, minute = match.group(1).split(":")
        return f"{int(hour):02d}:{minute}"

    def _first_line(self, value: str) -> str:
        return next((line.strip() for line in (value or "").splitlines() if line.strip()), "")

    def _safe_body_text(self, page) -> str:
        try:
            return page.locator("body").inner_text(timeout=3000) or ""
        except Exception:
            return ""
