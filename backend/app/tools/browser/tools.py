"""Browser tools — LangChain tools for browser automation.

Each tool operates on the BrowserManager singleton's active page.
The agent references elements by index from the accessibility tree.
"""
import base64

import structlog
from langchain_core.tools import tool, BaseTool
from playwright.async_api import Page

from app.browser.manager import BrowserManager
from app.browser.human_behavior import human_mouse_move, human_type, human_scroll, random_pause
from app.browser.accessibility import build_accessibility_tree, format_tree_for_agent
from app.config import get_settings

logger = structlog.get_logger()

_cached_tree: list[dict] = []


def _get_page() -> Page:
    bm = BrowserManager.get_instance()
    if not bm.is_launched or bm.page is None:
        raise RuntimeError("Browser not launched. Use browser_navigate first.")
    return bm.page


@tool
async def browser_navigate(url: str) -> str:
    """Navigate the browser to a URL and return the page structure.

    Use this to open a website. After navigation, you'll get the
    accessibility tree showing all interactive elements on the page.

    Args:
        url: The full URL to navigate to.

    Returns:
        The page's accessibility tree showing clickable elements.
    """
    global _cached_tree
    bm = BrowserManager.get_instance()

    if not bm.is_launched:
        await bm.launch(user_id="agent")

    page = bm.page
    settings = get_settings()

    await page.goto(url, wait_until="domcontentloaded", timeout=settings.BROWSER_TIMEOUT)
    await random_pause(500, 1500)

    _cached_tree = await build_accessibility_tree(page)
    tree_text = format_tree_for_agent(_cached_tree)

    logger.info("browser_navigated", url=url, elements=len(_cached_tree))
    return f"Navigated to: {page.url}\n\n{tree_text}"


@tool
async def browser_click(element_index: int) -> str:
    """Click an element on the page by its index number.

    Use the index from the accessibility tree (shown after navigation
    or get_page_info). Elements marked with * are interactive.

    Args:
        element_index: The [index] number of the element to click.

    Returns:
        Result of the click and updated page structure.
    """
    global _cached_tree
    page = _get_page()

    if element_index < 0 or element_index >= len(_cached_tree):
        return f"[Error] Invalid element index {element_index}. Use get_page_info to see available elements."

    el = _cached_tree[element_index]

    # Move mouse naturally, then click
    bm = BrowserManager.get_instance()
    await human_mouse_move(page, el["x"], el["y"], bm._last_mouse_x, bm._last_mouse_y)
    bm._last_mouse_x = el["x"]
    bm._last_mouse_y = el["y"]

    await page.mouse.click(el["x"], el["y"])
    await random_pause(300, 800)

    # Refresh tree after click (page may have changed)
    _cached_tree = await build_accessibility_tree(page)
    tree_text = format_tree_for_agent(_cached_tree)

    logger.info("browser_clicked", element=el["name"][:50], role=el["role"])
    return f"Clicked: [{el['role']}] {el['name'][:80]}\n\nCurrent page: {page.url}\n\n{tree_text}"


@tool
async def browser_type(element_index: int, text: str) -> str:
    """Type text into an input field.

    First clicks the element to focus it, then types with human-like timing.

    Args:
        element_index: The [index] of the input/textarea to type into.
        text: The text to type.

    Returns:
        Confirmation of what was typed.
    """
    page = _get_page()

    if element_index < 0 or element_index >= len(_cached_tree):
        return f"[Error] Invalid element index {element_index}."

    el = _cached_tree[element_index]

    # Click to focus
    await page.mouse.click(el["x"], el["y"])
    await random_pause(100, 300)

    # Clear existing content
    await page.keyboard.press("Control+a")
    await page.keyboard.press("Backspace")

    # Type with human-like behavior
    await human_type(page, text)

    logger.info("browser_typed", element=el["name"][:50], text_len=len(text))
    return f"Typed '{text}' into [{el['role']}] {el['name'][:80]}"


@tool
async def browser_screenshot() -> str:
    """Take a screenshot of the current page.

    Returns a base64-encoded PNG screenshot. Use this when you need
    to visually inspect the page or verify an action worked.

    Returns:
        Base64-encoded screenshot data.
    """
    page = _get_page()
    screenshot_bytes = await page.screenshot(type="png", full_page=False)
    b64 = base64.b64encode(screenshot_bytes).decode()
    logger.info("browser_screenshot", url=page.url)
    return f"Screenshot captured ({len(screenshot_bytes)} bytes). URL: {page.url}"


@tool
async def browser_get_text() -> str:
    """Extract the visible text content from the current page.

    Returns the main text content, stripping navigation and UI elements.
    Useful for reading articles, documentation, or any text-heavy page.

    Returns:
        The page's main text content.
    """
    page = _get_page()
    text = await page.evaluate("""() => {
        const main = document.querySelector('article')
            || document.querySelector('main')
            || document.querySelector('[role=main]')
            || document.body;

        // Remove noise
        const clone = main.cloneNode(true);
        clone.querySelectorAll('script, style, nav, header, footer, aside').forEach(el => el.remove());

        return clone.innerText.trim().substring(0, 8000);
    }""")

    logger.info("browser_get_text", url=page.url, text_len=len(text))
    return f"**Page:** {page.url}\n\n{text}"


@tool
async def browser_scroll(direction: str = "down", amount: int = 3) -> str:
    """Scroll the page up or down.

    Args:
        direction: 'up' or 'down' (default: 'down').
        amount: Number of scroll ticks (1-10, default: 3).

    Returns:
        Confirmation and updated element count.
    """
    global _cached_tree
    page = _get_page()
    amount = max(1, min(10, amount))

    await human_scroll(page, direction, amount)
    await random_pause(200, 500)

    _cached_tree = await build_accessibility_tree(page)

    return f"Scrolled {direction} by {amount}. Page has {len(_cached_tree)} visible elements."


@tool
async def browser_wait(seconds: int = 2) -> str:
    """Wait for the page to load or update.

    Use after clicking something that triggers a page load or
    AJAX request. Max wait: 10 seconds.

    Args:
        seconds: Seconds to wait (1-10, default: 2).

    Returns:
        Confirmation and current URL.
    """
    global _cached_tree
    page = _get_page()
    seconds = max(1, min(10, seconds))

    await page.wait_for_timeout(seconds * 1000)
    _cached_tree = await build_accessibility_tree(page)

    return f"Waited {seconds}s. Current URL: {page.url}. {len(_cached_tree)} elements visible."


@tool
async def browser_get_page_info() -> str:
    """Get the current page's accessibility tree (element list).

    Refreshes the tree and returns all interactive and content elements.
    Use this after actions to see the updated page state.

    Returns:
        The current page structure with numbered elements.
    """
    global _cached_tree
    page = _get_page()
    _cached_tree = await build_accessibility_tree(page)
    tree_text = format_tree_for_agent(_cached_tree)

    return f"URL: {page.url}\n\n{tree_text}"


@tool
async def browser_fill_form(fields: list[dict]) -> str:
    """Fill multiple form fields at once.

    Each field should have 'index' (element index) and 'value' (text to enter).
    For select elements, pass the option text as 'value'.

    Args:
        fields: List of {'index': int, 'value': str} dictionaries.

    Returns:
        Summary of fields filled.
    """
    page = _get_page()
    results = []

    for field in fields:
        idx = field.get("index", -1)
        value = field.get("value", "")

        if idx < 0 or idx >= len(_cached_tree):
            results.append(f"[{idx}] Error: invalid index")
            continue

        el = _cached_tree[idx]
        try:
            await page.mouse.click(el["x"], el["y"])
            await random_pause(50, 150)

            if el["tag"] == "select":
                await page.select_option(el["selector"], label=value)
            else:
                await page.keyboard.press("Control+a")
                await page.keyboard.press("Backspace")
                await human_type(page, value, speed="fast")

            results.append(f"[{idx}] {el['name'][:40]}: filled with '{value}'")
        except Exception as e:
            results.append(f"[{idx}] Error: {e}")

    return "Form fill results:\n" + "\n".join(results)


@tool
async def browser_get_links() -> str:
    """Get all links on the current page with their URLs.

    Returns:
        List of links with text and href.
    """
    page = _get_page()
    links = await page.evaluate("""() => {
        return Array.from(document.querySelectorAll('a[href]'))
            .filter(a => a.offsetParent !== null)
            .slice(0, 50)
            .map(a => ({
                text: (a.innerText || a.getAttribute('aria-label') || '').trim().substring(0, 100),
                href: a.href,
            }))
            .filter(l => l.text && l.href);
    }""")

    if not links:
        return "No visible links found on the page."

    lines = [f"- [{l['text']}]({l['href']})" for l in links]
    return f"Found {len(links)} links:\n" + "\n".join(lines)


def get_browser_tools() -> list[BaseTool]:
    """Return all browser automation tools."""
    return [
        browser_navigate,
        browser_click,
        browser_type,
        browser_screenshot,
        browser_get_text,
        browser_scroll,
        browser_wait,
        browser_get_page_info,
        browser_fill_form,
        browser_get_links,
    ]
