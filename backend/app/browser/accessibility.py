"""Page snapshot for the browser agent.

Walks the whole DOM (including open shadow roots) and returns a flat, numbered
list of visible headings, text blocks and interactive controls in document
order. Coordinates are recorded in page space so off-screen elements can be
scrolled into view before clicking.
"""
from playwright.async_api import Page

MAX_ELEMENTS = 250

_SNAPSHOT_JS = """(maxElements) => {
  const out = [];
  const INTERACTIVE_TAGS = new Set(['a', 'button', 'input', 'select', 'textarea', 'summary']);
  const INTERACTIVE_ROLES = new Set(['button', 'link', 'textbox', 'searchbox', 'checkbox', 'radio',
    'combobox', 'menuitem', 'tab', 'switch', 'option', 'slider', 'spinbutton']);
  const TEXT_TAGS = new Set(['p', 'li', 'td', 'th', 'dd', 'dt', 'blockquote', 'figcaption', 'label', 'pre']);

  function roleOf(el, tag) {
    const explicit = el.getAttribute('role');
    if (explicit) return explicit;
    if (/^h[1-6]$/.test(tag)) return 'heading';
    if (tag === 'a') return 'link';
    if (tag === 'button' || tag === 'summary') return 'button';
    if (tag === 'select') return 'combobox';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'input') {
      const t = (el.getAttribute('type') || 'text').toLowerCase();
      if (t === 'checkbox' || t === 'radio') return t;
      if (t === 'submit' || t === 'button') return 'button';
      if (t === 'search') return 'searchbox';
      return 'textbox';
    }
    if (tag === 'img') return 'img';
    return 'text';
  }

  function nameOf(el, tag) {
    const label = el.getAttribute('aria-label') || el.getAttribute('alt') || el.getAttribute('title');
    if (label) return label;
    if (tag === 'input' || tag === 'textarea') {
      const ph = el.getAttribute('placeholder');
      const val = tag === 'input' && ['submit', 'button'].includes(el.type) ? el.value : '';
      const lbl = el.labels && el.labels[0] ? el.labels[0].innerText : '';
      return [lbl, ph, val].filter(Boolean).join(' · ');
    }
    return (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
  }

  function visible(el) {
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) return null;
    const style = getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none' || Number(style.opacity) === 0) return null;
    return rect;
  }

  function walk(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
    let el = walker.currentNode.nodeType === 1 ? walker.currentNode : walker.nextNode();
    while (el && out.length < maxElements) {
      const tag = el.tagName.toLowerCase();
      if (['script', 'style', 'noscript', 'template', 'svg'].includes(tag)) { el = skipSubtree(walker); continue; }
      const role = roleOf(el, tag);
      const interactive = INTERACTIVE_TAGS.has(tag) || INTERACTIVE_ROLES.has(role)
        || el.hasAttribute('onclick') || el.getAttribute('contenteditable') === 'true';
      const isHeading = role === 'heading';
      const isText = TEXT_TAGS.has(tag) || tag === 'img';
      if (interactive || isHeading || isText) {
        const rect = visible(el);
        if (rect) {
          const name = nameOf(el, tag).substring(0, 160);
          if (name || interactive) {
            out.push({
              index: out.length,
              role: isHeading ? `heading${tag[1] ? ' ' + tag[1] : ''}` : role,
              name,
              tag,
              interactive,
              x: Math.round(rect.x + rect.width / 2),
              y: Math.round(rect.y + rect.height / 2),
              page_x: Math.round(rect.x + rect.width / 2 + scrollX),
              page_y: Math.round(rect.y + rect.height / 2 + scrollY),
              in_viewport: rect.top >= 0 && rect.left >= 0 && rect.bottom <= innerHeight && rect.right <= innerWidth,
            });
          }
        }
        // Text blocks and headings already include their children's text.
        if (!interactive && (isHeading || isText)) { el = skipSubtree(walker); continue; }
      }
      if (el.shadowRoot) walk(el.shadowRoot);
      el = walker.nextNode();
    }
  }

  function skipSubtree(w) {
    const sibling = w.nextSibling();
    if (sibling) return sibling;
    while (w.parentNode()) { const s = w.nextSibling(); if (s) return s; }
    return null;
  }

  walk(document.body);
  return out;
}"""


async def build_accessibility_tree(page: Page, max_elements: int = MAX_ELEMENTS) -> list[dict]:
    return await page.evaluate(_SNAPSHOT_JS, max_elements)


def format_tree_for_agent(tree: list[dict]) -> str:
    if not tree:
        return "The page has no visible content yet. Try browser_wait, then browser_get_page_info."
    interactive = sum(1 for e in tree if e["interactive"])
    lines = [f"Page snapshot: {len(tree)} elements ({interactive} interactive, marked *). "
             f"Elements outside the visible area are marked (off-screen) and can still be clicked."]
    for el in tree:
        marker = "*" if el["interactive"] else " "
        where = "" if el.get("in_viewport") else " (off-screen)"
        lines.append(f"[{el['index']}]{marker} {el['role']}: {el['name'][:120]}{where}")
    if len(tree) >= MAX_ELEMENTS:
        lines.append(f"(snapshot truncated at {MAX_ELEMENTS} elements — scroll or use browser_get_text for more)")
    return "\n".join(lines)
