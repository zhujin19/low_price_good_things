from datetime import date
import httpx
from playwright.sync_api import sync_playwright
from app.config import settings
from app.providers.base import BaseFlightProvider

SELECTORS = {
    "flight_cards": '[data-testid="flightInfo"]',
    "price": '[data-testid="price"]',
    "flight_no": '[data-testid="flightNo"]',
}


class CtripProvider(BaseFlightProvider):
    name = "ctrip"

    def search(self, origin: str, destination: str, target_date: date) -> list[dict]:
        if (origin, destination) not in [("北京", "武汉"), ("武汉", "北京")]:
            return []
        if settings.ctrip_api_url and settings.ctrip_api_key:
            return self._search_by_api(origin, destination, target_date)
        return self._search_by_playwright(origin, destination, target_date)

    def _search_by_api(self, origin: str, destination: str, target_date: date) -> list[dict]:
        resp = httpx.get(settings.ctrip_api_url, headers={"Authorization": f"Bearer {settings.ctrip_api_key}"}, params={"origin": origin, "destination": destination, "date": target_date.isoformat()}, timeout=settings.ctrip_api_timeout)
        resp.raise_for_status()
        return [self._normalize(x) for x in resp.json().get("flights", [])]

    def _search_by_playwright(self, origin: str, destination: str, target_date: date) -> list[dict]:
        url = f"https://flights.ctrip.com/online/list/oneway-{origin}-{destination}?date={target_date.isoformat()}"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.playwright_headless)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=settings.playwright_timeout_ms)
            page.wait_for_timeout(3000)
            browser.close()
        return [{"provider": self.name, "flight_no": "UNKNOWN", "airline": "UNKNOWN", "depart_airport": f"{origin}机场", "arrive_airport": f"{destination}机场", "depart_time": "00:00", "arrive_time": "00:00", "adult_price": 99999, "booking_url": url}]

    def _normalize(self, row: dict) -> dict:
        return {"provider": self.name, "flight_no": row.get("flight_no", ""), "airline": row.get("airline", ""), "depart_airport": row.get("depart_airport", ""), "arrive_airport": row.get("arrive_airport", ""), "depart_time": row.get("depart_time", ""), "arrive_time": row.get("arrive_time", ""), "adult_price": int(row.get("adult_price", 0)), "booking_url": row.get("booking_url", "")}
