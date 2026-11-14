"""Per-run browser sessions: BrowserBase (cloud) with a local Playwright fallback.

Every agent run gets its own BrowserSession, so pages, cookies and the element
index never leak between users or concurrent runs. The session is closed when
the browser agent node finishes, fails, or is cancelled.
"""
import asyncio
import base64
import time

import httpx
import structlog
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from app.agent.run_context import emit
from app.browser.stealth import STEALTH_SCRIPT
from app.config import get_settings

logger = structlog.get_logger()

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
VIEWPORT = {"width": 1280, "height": 800}
_FRAME_QUALITY = 60
_MIN_FRAME_INTERVAL_S = 0.4


class BrowserSession:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._pages: list[Page] = []
        self._active_idx = 0
        self._bb_session_id: str | None = None
        self.provider: str | None = None
        self.element_tree: list[dict] = []
        self.last_mouse = (0.0, 0.0)
        self.last_dialog: dict | None = None
        self._last_frame_at = 0.0
        self._lock = asyncio.Lock()
        self._closed = False

    @property
    def page(self) -> Page | None:
        return self._pages[self._active_idx] if self._pages else None

    @property
    def is_open(self) -> bool:
        return self._browser is not None and self._browser.is_connected()

    @property
    def live_url(self) -> str | None:
        if self._bb_session_id:
            return f"https://www.browserbase.com/sessions/{self._bb_session_id}"
        return None

    async def ensure_open(self) -> Page:
        if self._closed:
            raise RuntimeError("This run's browser session has ended.")
        async with self._lock:
            if not self.is_open:
                await self._launch()
        if self._closed:
            # close() ran while we were launching (run cancelled): don't leave the new browser running.
            await self.close()
            raise RuntimeError("This run's browser session has ended.")
        return self.page

    async def _launch(self):
        settings = get_settings()
        self._playwright = await async_playwright().start()
        if settings.BROWSERBASE_API_KEY:
            await self._launch_browserbase(settings)
        else:
            await self._launch_local(settings)
        emit("browser_session", {"status": "open", "provider": self.provider, "live_url": self.live_url})

    async def _launch_browserbase(self, settings):
        body = {"browserSettings": {"viewport": VIEWPORT}}
        if settings.BROWSERBASE_PROJECT_ID:
            body["projectId"] = settings.BROWSERBASE_PROJECT_ID
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.browserbase.com/v1/sessions",
                headers={"x-bb-api-key": settings.BROWSERBASE_API_KEY, "Content-Type": "application/json"},
                json=body,
            )
            resp.raise_for_status()
            self._bb_session_id = resp.json()["id"]

        ws_url = f"wss://connect.browserbase.com?apiKey={settings.BROWSERBASE_API_KEY}&sessionId={self._bb_session_id}"
        self._browser = await self._playwright.chromium.connect_over_cdp(ws_url)
        self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context(
            user_agent=_USER_AGENT, viewport=VIEWPORT
        )
        page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        await page.set_viewport_size(VIEWPORT)
        self._attach(page)
        self._context.on("page", self._attach)
        self.provider = "browserbase"
        logger.info("browser_launched", provider="browserbase", run_id=self.run_id, bb_session=self._bb_session_id)

    async def _launch_local(self, settings):
        self._browser = await self._playwright.chromium.launch(
            headless=settings.BROWSER_HEADLESS,
            args=["--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"],
        )
        self._context = await self._browser.new_context(
            user_agent=_USER_AGENT, viewport=VIEWPORT, locale="en-US",
        )
        await self._context.add_init_script(STEALTH_SCRIPT)
        self._context.on("page", self._attach)
        self._attach(await self._context.new_page())
        self.provider = "local"
        logger.info("browser_launched", provider="local", run_id=self.run_id)

    def _attach(self, page: Page):
        if page in self._pages:
            return
        page.on("dialog", self._on_dialog)
        self._pages.append(page)
        self._active_idx = len(self._pages) - 1

    async def _on_dialog(self, dialog):
        self.last_dialog = {"type": dialog.type, "message": dialog.message}
        await dialog.dismiss()

    async def capture_frame(self, call_id: str | None, force: bool = False) -> None:
        """Screenshot the active page and stream it to the client as a browser_frame."""
        page = self.page
        if page is None:
            return
        now = time.monotonic()
        if not force and now - self._last_frame_at < _MIN_FRAME_INTERVAL_S:
            return
        try:
            data = await page.screenshot(type="jpeg", quality=_FRAME_QUALITY, full_page=False, timeout=10_000)
            title = await page.title()
        except Exception as e:
            logger.warning("browser_frame_failed", error=str(e), run_id=self.run_id)
            return
        self._last_frame_at = now
        emit("browser_frame", {
            "call_id": call_id,
            "url": page.url,
            "title": title,
            "mime": "image/jpeg",
            "data": base64.b64encode(data).decode(),
            "width": VIEWPORT["width"],
            "height": VIEWPORT["height"],
            "ts": time.time(),
        })

    async def close(self):
        self._closed = True
        try:
            if self._browser:
                await self._browser.close()
        except Exception as e:
            logger.warning("browser_close_failed", error=str(e), run_id=self.run_id)
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning("playwright_stop_failed", error=str(e), run_id=self.run_id)
        if self._bb_session_id:
            await self._release_browserbase()
        was_open = self._browser is not None
        self._browser = None
        self._context = None
        self._pages = []
        self._playwright = None
        if was_open:
            emit("browser_session", {"status": "closed"})
            logger.info("browser_closed", run_id=self.run_id)

    async def _release_browserbase(self):
        """Ask BrowserBase to end the session now instead of waiting for its idle timeout."""
        settings = get_settings()
        body = {"status": "REQUEST_RELEASE"}
        if settings.BROWSERBASE_PROJECT_ID:
            body["projectId"] = settings.BROWSERBASE_PROJECT_ID
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.browserbase.com/v1/sessions/{self._bb_session_id}",
                    headers={"x-bb-api-key": settings.BROWSERBASE_API_KEY, "Content-Type": "application/json"},
                    json=body,
                )
        except Exception as e:
            logger.warning("browserbase_release_failed", error=str(e), run_id=self.run_id)
        self._bb_session_id = None
