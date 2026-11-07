"""BrowserManager — singleton Playwright browser with crash recovery."""
import asyncio
import random

import structlog
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Frame,
    Playwright,
)

from app.config import get_settings
from app.browser.stealth import STEALTH_SCRIPT

logger = structlog.get_logger()

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
]


class BrowserManager:
    """Singleton Playwright browser manager with anti-detection and crash recovery."""

    _instance: "BrowserManager | None" = None

    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._pages: list[Page] = []
        self._active_page_idx: int = 0
        self._active_frame: Frame | None = None
        self._last_mouse_x: float = 0
        self._last_mouse_y: float = 0
        self._last_dialog: dict | None = None
        self._health_task: asyncio.Task | None = None
        self._current_user_id: str | None = None

    @classmethod
    def get_instance(cls) -> "BrowserManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def page(self) -> Page | None:
        if not self._pages:
            return None
        return self._pages[self._active_page_idx]

    @property
    def is_launched(self) -> bool:
        return self._browser is not None and self._browser.is_connected()

    async def launch(self, user_id: str, storage_state: dict | None = None):
        """Launch browser with stealth and optional session restore."""
        settings = get_settings()
        self._current_user_id = user_id

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.BROWSER_HEADLESS,
            slow_mo=settings.BROWSER_SLOW_MO,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        context_opts = {
            "user_agent": random.choice(_USER_AGENTS),
            "viewport": random.choice(_VIEWPORTS),
            "locale": "en-US",
            "timezone_id": "America/New_York",
        }
        if storage_state:
            context_opts["storage_state"] = storage_state

        self._context = await self._browser.new_context(**context_opts)
        await self._context.add_init_script(STEALTH_SCRIPT)

        self._context.on("page", self._on_new_page)

        page = await self._context.new_page()
        page.on("dialog", self._on_dialog)
        self._pages = [page]
        self._active_page_idx = 0

        self._health_task = asyncio.create_task(self._health_loop())
        logger.info("browser_launched", user_id=user_id)

    def _on_new_page(self, page: Page):
        page.on("dialog", self._on_dialog)
        self._pages.append(page)

    async def _on_dialog(self, dialog):
        self._last_dialog = {
            "type": dialog.type,
            "message": dialog.message,
            "default_value": dialog.default_value,
        }
        await dialog.dismiss()

    async def _health_loop(self):
        """Periodic crash recovery check."""
        while True:
            await asyncio.sleep(30)
            try:
                if self._browser and not self._browser.is_connected():
                    logger.warning("browser_disconnected")
                    await self.launch(self._current_user_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("browser_health_check_failed", error=str(e))

    async def get_storage_state(self) -> dict | None:
        """Export cookies/localStorage for session persistence."""
        if self._context:
            return await self._context.storage_state()
        return None

    async def new_tab(self, url: str | None = None) -> Page:
        """Open a new tab, optionally navigating to a URL."""
        if not self._context:
            raise RuntimeError("Browser not launched")
        page = await self._context.new_page()
        if url:
            await page.goto(url, wait_until="domcontentloaded", timeout=get_settings().BROWSER_TIMEOUT)
        self._pages.append(page)
        self._active_page_idx = len(self._pages) - 1
        return page

    async def close_tab(self, idx: int | None = None):
        """Close a tab by index (default: active tab)."""
        idx = idx if idx is not None else self._active_page_idx
        if 0 <= idx < len(self._pages):
            await self._pages[idx].close()
            self._pages.pop(idx)
            self._active_page_idx = max(0, min(self._active_page_idx, len(self._pages) - 1))

    async def switch_tab(self, idx: int):
        if 0 <= idx < len(self._pages):
            self._active_page_idx = idx
            await self._pages[idx].bring_to_front()

    async def close(self):
        """Graceful shutdown."""
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._browser = None
        self._context = None
        self._pages = []
        logger.info("browser_closed")

    @classmethod
    async def shutdown(cls):
        """Class-level shutdown for app lifecycle."""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
