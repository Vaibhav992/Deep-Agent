"""Browser tools for the browser agent.

Each tool acts on the current run's BrowserSession and reports what it did as a
live `browser_action` event followed by a real screenshot (`browser_frame`).
Elements are referenced by index from the most recent page snapshot.
"""
import time

import structlog
from langchain_core.tools import BaseTool, tool
from playwright.async_api import Page

from app.agent.run_context import current_run, emit
from app.agent.tooling import current_call_id
from app.browser.accessibility import build_accessibility_tree, format_tree_for_agent
from app.browser.human_behavior import human_mouse_move, human_scroll, human_type, random_pause
from app.browser.manager import BrowserSession
from app.config import get_settings
from app.security.url_policy import UrlPolicyError, check_url

logger = structlog.get_logger()


def _session() -> BrowserSession:
    ctx = current_run()
    if ctx.browser is None:
        ctx.browser = BrowserSession(ctx.run_id)
    return ctx.browser


async def _open_page() -> Page:
    session = _session()
    if not session.is_open or session.page is None:
        raise RuntimeError("No page is open yet. Call browser_navigate with a URL first.")
    return session.page


async def _report(action: str, *, target: str | None = None, value: str | None = None,
                  ok: bool = True, error: str | None = None) -> None:
    session = _session()
    page = session.page
    url, title = (page.url, await page.title()) if page else ("", "")
    current_run().browser_actions += 1
    call_id = current_call_id.get()
    emit("browser_action", {
        "call_id": call_id,
        "action": action,
        "target": target,
        "value": value,
        "url": url,
        "title": title,
        "ok": ok,
        "error": error,
        "ts": time.time(),
    })
    if page is not None:
        await session.capture_frame(call_id, force=True)


async def _snapshot(page: Page) -> str:
    session = _session()
    session.element_tree = await build_accessibility_tree(page)
    return format_tree_for_agent(session.element_tree)


def _element(index: int) -> dict:
    tree = _session().element_tree
    if index < 0 or index >= len(tree):
        raise ValueError(f"Element [{index}] does not exist on the current snapshot. Call browser_get_page_info.")
    return tree[index]


async def _scroll_into_view(page: Page, el: dict) -> tuple[float, float]:
    """Return viewport coordinates for `el`, scrolling it into view first if needed."""
    if el.get("in_viewport"):
        return el["x"], el["y"]
    await page.evaluate("([x, y]) => window.scrollTo(x - innerWidth / 2, y - innerHeight / 2)",
                        [el["page_x"], el["page_y"]])
    await random_pause(150, 300)
    pos = await page.evaluate("([x, y]) => [x - scrollX, y - scrollY]", [el["page_x"], el["page_y"]])
    return pos[0], pos[1]


@tool
async def browser_navigate(url: str) -> str:
    """Open a URL in the browser and return a numbered snapshot of the page.

    Args:
        url: Full http(s) URL to open.
    """
    try:
        safe_url = await check_url(url)
    except UrlPolicyError as e:
        await _report("navigate", target=url, ok=False, error=str(e))
        return f"[Blocked] {e}"

    session = _session()
    page = await session.ensure_open()
    try:
        await page.goto(safe_url, wait_until="domcontentloaded", timeout=get_settings().BROWSER_TIMEOUT)
        try:
            await page.wait_for_load_state("networkidle", timeout=5_000)
        except Exception:
            pass
    except Exception as e:
        await _report("navigate", target=safe_url, ok=False, error=str(e)[:200])
        return f"[Error] Could not load {safe_url}: {e}"

    tree = await _snapshot(page)
    await _report("navigate", target=safe_url)
    return f"URL: {page.url}\nTitle: {await page.title()}\n\n{tree}"


@tool
async def browser_click(element_index: int) -> str:
    """Click an element by its [index] from the latest page snapshot.

    Args:
        element_index: The [index] of the element to click.
    """
    page = await _open_page()
    el = _element(element_index)
    x, y = await _scroll_into_view(page, el)
    session = _session()
    await human_mouse_move(page, x, y, *session.last_mouse)
    session.last_mouse = (x, y)
    await page.mouse.click(x, y)
    await random_pause(300, 700)
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=5_000)
    except Exception:
        pass
    tree = await _snapshot(page)
    await _report("click", target=f"{el['role']}: {el['name'][:60]}")
    return f"Clicked [{element_index}] {el['role']}: {el['name'][:80]}\nURL: {page.url}\n\n{tree}"


@tool
async def browser_type(element_index: int, text: str, press_enter: bool = False) -> str:
    """Type text into an input by its [index], replacing what is there.

    Args:
        element_index: The [index] of the input or textarea.
        text: Text to type.
        press_enter: Press Enter afterwards (for example to submit a search).
    """
    page = await _open_page()
    el = _element(element_index)
    x, y = await _scroll_into_view(page, el)
    await page.mouse.click(x, y)
    await page.keyboard.press("Control+a")
    await page.keyboard.press("Backspace")
    await human_type(page, text, speed="fast")
    if press_enter:
        await page.keyboard.press("Enter")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=8_000)
        except Exception:
            pass
    tree = await _snapshot(page)
    await _report("type", target=f"{el['role']}: {el['name'][:60]}", value=text[:80])
    return f"Typed into [{element_index}] {el['name'][:60]}{' and pressed Enter' if press_enter else ''}.\nURL: {page.url}\n\n{tree}"


@tool
async def browser_get_text() -> str:
    """Return the readable text of the current page (up to 8000 characters)."""
    page = await _open_page()
    text = await page.evaluate("""() => {
        const root = document.querySelector('main, article, [role=main]') || document.body;
        const clone = root.cloneNode(true);
        clone.querySelectorAll('script, style, noscript, svg').forEach(el => el.remove());
        return (clone.innerText || '').replace(/\\n{3,}/g, '\\n\\n').trim().substring(0, 8000);
    }""")
    await _report("extract", target="page text")
    return f"URL: {page.url}\nTitle: {await page.title()}\n\n{text or '(no visible text)'}"


@tool
async def browser_scroll(direction: str = "down", amount: int = 3) -> str:
    """Scroll the page and return the refreshed snapshot.

    Args:
        direction: 'up' or 'down'.
        amount: Scroll ticks, 1-10.
    """
    page = await _open_page()
    direction = "up" if direction == "up" else "down"
    amount = max(1, min(10, amount))
    await human_scroll(page, direction, amount)
    await random_pause(200, 400)
    tree = await _snapshot(page)
    await _report("scroll", target=direction)
    return f"Scrolled {direction}.\n\n{tree}"


@tool
async def browser_go_back() -> str:
    """Go back to the previous page."""
    page = await _open_page()
    await page.go_back(wait_until="domcontentloaded", timeout=get_settings().BROWSER_TIMEOUT)
    tree = await _snapshot(page)
    await _report("back")
    return f"URL: {page.url}\n\n{tree}"


@tool
async def browser_wait(seconds: int = 2) -> str:
    """Wait for the page to finish updating, then return the refreshed snapshot.

    Args:
        seconds: 1-10 seconds.
    """
    page = await _open_page()
    seconds = max(1, min(10, seconds))
    await page.wait_for_timeout(seconds * 1000)
    tree = await _snapshot(page)
    await _report("wait", target=f"{seconds}s")
    return f"URL: {page.url}\n\n{tree}"


@tool
async def browser_get_page_info() -> str:
    """Return a fresh numbered snapshot of the current page's headings, text and controls."""
    page = await _open_page()
    tree = await _snapshot(page)
    await _report("inspect", target="page structure")
    return f"URL: {page.url}\nTitle: {await page.title()}\n\n{tree}"


@tool
async def browser_get_links() -> str:
    """List the visible links on the current page (up to 60)."""
    page = await _open_page()
    links = await page.evaluate("""() => Array.from(document.querySelectorAll('a[href]'))
        .filter(a => a.offsetParent !== null)
        .map(a => ({text: (a.innerText || a.getAttribute('aria-label') || '').trim().substring(0, 100), href: a.href}))
        .filter(l => l.text && l.href.startsWith('http'))
        .slice(0, 60)""")
    await _report("extract", target="links")
    if not links:
        return "No visible links on this page."
    return "\n".join(f"- [{l['text']}]({l['href']})" for l in links)


def get_browser_tools() -> list[BaseTool]:
    return [
        browser_navigate,
        browser_click,
        browser_type,
        browser_get_text,
        browser_scroll,
        browser_go_back,
        browser_wait,
        browser_get_page_info,
        browser_get_links,
    ]
