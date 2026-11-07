"""Human behavior simulation for browser automation.

Makes mouse movements and typing look human to avoid bot detection:
- Bezier curve mouse movement with jitter
- Typing with natural delays and occasional typos
- Random pauses and scroll behavior
"""
import asyncio
import math
import random

from playwright.async_api import Page


def _bezier(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
    """Cubic bezier interpolation."""
    return (
        (1 - t) ** 3 * p0
        + 3 * (1 - t) ** 2 * t * p1
        + 3 * (1 - t) * t ** 2 * p2
        + t ** 3 * p3
    )


async def human_mouse_move(
    page: Page,
    target_x: float,
    target_y: float,
    start_x: float = 0,
    start_y: float = 0,
):
    """Move mouse along a bezier curve with jitter."""
    steps = random.randint(15, 30)

    # Random control points for natural curve
    cp1x = start_x + (target_x - start_x) * 0.25 + random.uniform(-50, 50)
    cp1y = start_y + (target_y - start_y) * 0.25 + random.uniform(-50, 50)
    cp2x = start_x + (target_x - start_x) * 0.75 + random.uniform(-30, 30)
    cp2y = start_y + (target_y - start_y) * 0.75 + random.uniform(-30, 30)

    for i in range(steps + 1):
        t = i / steps
        x = _bezier(t, start_x, cp1x, cp2x, target_x) + random.uniform(-1, 1)
        y = _bezier(t, start_y, cp1y, cp2y, target_y) + random.uniform(-1, 1)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.005, 0.02))


_ADJACENT_KEYS = {
    "a": "sq", "b": "vn", "c": "xv", "d": "sf", "e": "wr",
    "f": "dg", "g": "fh", "h": "gj", "i": "uo", "j": "hk",
    "k": "jl", "l": "k;", "m": "n,", "n": "bm", "o": "ip",
    "p": "o[", "q": "wa", "r": "et", "s": "ad", "t": "ry",
    "u": "yi", "v": "cb", "w": "qe", "x": "zc", "y": "tu",
    "z": "x",
}


async def human_type(page: Page, text: str, speed: str = "normal"):
    """Type with human-like timing and occasional typos."""
    speed_map = {"slow": (80, 200), "normal": (30, 80), "fast": (10, 40)}
    min_delay, max_delay = speed_map.get(speed, (30, 80))

    for char in text:
        # ~5% chance of typo on letters
        if random.random() < 0.05 and char.lower() in _ADJACENT_KEYS:
            wrong = random.choice(_ADJACENT_KEYS[char.lower()])
            await page.keyboard.type(wrong)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.keyboard.press("Backspace")

        await page.keyboard.type(char)
        delay = random.uniform(min_delay, max_delay) / 1000
        # Pause longer after punctuation
        if char in ".!?,;:":
            delay += random.uniform(0.1, 0.3)
        await asyncio.sleep(delay)


async def human_scroll(page: Page, direction: str = "down", amount: int = 3):
    """Scroll with variable speed like a human."""
    delta = 120 if direction == "down" else -120
    for _ in range(amount):
        await page.mouse.wheel(0, delta + random.randint(-20, 20))
        await asyncio.sleep(random.uniform(0.05, 0.15))


async def random_pause(min_ms: int = 200, max_ms: int = 800):
    """Random pause to simulate human thinking time."""
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)
