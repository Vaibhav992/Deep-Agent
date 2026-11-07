"""Accessibility tree builder — structured DOM representation for the agent.

Walks the page DOM and builds a simplified tree of interactive and
content elements. The agent uses this to understand page structure
without needing screenshots.
"""
from playwright.async_api import Page

_INTERACTIVE_ROLES = {
    "button", "link", "textbox", "checkbox", "radio",
    "combobox", "menuitem", "tab", "switch", "slider",
    "searchbox", "spinbutton",
}

_CONTENT_ROLES = {
    "heading", "paragraph", "listitem", "cell", "img",
}


async def build_accessibility_tree(page: Page, max_depth: int = 6) -> list[dict]:
    """Build a simplified accessibility tree from the page.

    Returns a flat list of elements with:
    - index: sequential number for the agent to reference
    - role: ARIA role (button, link, textbox, etc.)
    - name: accessible name / text content
    - tag: HTML tag name
    - selector: CSS selector for targeting
    - interactive: whether the element is clickable/typable
    """
    tree = await page.evaluate("""(maxDepth) => {
        const results = [];
        let idx = 0;

        function walk(el, depth) {
            if (depth > maxDepth) return;
            if (!el || el.nodeType !== 1) return;

            const tag = el.tagName.toLowerCase();
            // Skip invisible elements
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') return;
            if (el.offsetWidth === 0 && el.offsetHeight === 0) return;

            const role = el.getAttribute('role') || el.tagName.toLowerCase();
            const name = el.getAttribute('aria-label')
                || el.getAttribute('title')
                || el.getAttribute('placeholder')
                || el.innerText?.substring(0, 100)?.trim()
                || '';

            const isInteractive = (
                tag === 'a' || tag === 'button' || tag === 'input'
                || tag === 'select' || tag === 'textarea'
                || el.getAttribute('role') === 'button'
                || el.getAttribute('role') === 'link'
                || el.getAttribute('tabindex') !== null
                || el.onclick !== null
            );

            const isContent = (
                tag === 'h1' || tag === 'h2' || tag === 'h3'
                || tag === 'h4' || tag === 'h5' || tag === 'h6'
                || tag === 'p' || tag === 'li' || tag === 'td'
                || tag === 'img'
            );

            if (isInteractive || isContent) {
                const rect = el.getBoundingClientRect();
                let selector = '';
                if (el.id) selector = '#' + el.id;
                else if (el.className && typeof el.className === 'string')
                    selector = tag + '.' + el.className.trim().split(/\\s+/).join('.');
                else selector = tag;

                results.push({
                    index: idx++,
                    role: role,
                    name: name.substring(0, 200),
                    tag: tag,
                    selector: selector,
                    interactive: isInteractive,
                    x: Math.round(rect.x + rect.width / 2),
                    y: Math.round(rect.y + rect.height / 2),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                });
            }

            for (const child of el.children) {
                walk(child, depth + 1);
            }
        }

        walk(document.body, 0);
        return results;
    }""", max_depth)

    return tree


def format_tree_for_agent(tree: list[dict]) -> str:
    """Format the accessibility tree as text for the agent's context."""
    if not tree:
        return "Page appears empty or has no accessible elements."

    lines = []
    for el in tree:
        marker = "*" if el["interactive"] else " "
        name = el["name"][:80] if el["name"] else ""
        lines.append(f"[{el['index']}]{marker} {el['role']}: {name}")

    header = f"Page has {len(tree)} elements ({sum(1 for e in tree if e['interactive'])} interactive)"
    return header + "\n" + "\n".join(lines)
