"""
Page Snapshot — Extract structured page data via JS for LLM consumption.

Produces a compact, token-efficient representation of the visible page
including interactive elements, text content, forms, and navigation.
"""

import json
from typing import Optional

from core.console import console

# ---------------------------------------------------------------------------
# JS snippets executed in isolated context (stealth)
# ---------------------------------------------------------------------------

SNAPSHOT_JS = """
() => {
    const MAX_TEXT = 120;
    const clip = (s) => s && s.length > MAX_TEXT ? s.slice(0, MAX_TEXT) + '…' : s;

    // Gather interactive elements
    const interactives = [];
    const selectors = 'a, button, input, textarea, select, [role="button"], [role="link"], [role="tab"], [contenteditable="true"]';
    document.querySelectorAll(selectors).forEach((el, i) => {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return; // hidden
        const tag = el.tagName.toLowerCase();
        const entry = {
            idx: i,
            tag,
            type: el.type || null,
            role: el.getAttribute('role') || null,
            text: clip(el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || ''),
            name: el.name || el.id || null,
            href: el.href || null,
            selector: buildSelector(el),
            visible: rect.width > 0 && rect.height > 0,
        };
        interactives.push(entry);
    });

    // Page metadata
    const meta = {
        url: location.href,
        title: document.title,
        h1: document.querySelector('h1')?.innerText || null,
        description: document.querySelector('meta[name="description"]')?.content || null,
    };

    // Main text blocks (headings + paragraphs)
    const textBlocks = [];
    document.querySelectorAll('h1,h2,h3,h4,p,li,td,th,label,span[class*="text"],div[class*="content"]').forEach(el => {
        const t = el.innerText?.trim();
        if (t && t.length > 3 && t.length < 500) {
            textBlocks.push({ tag: el.tagName.toLowerCase(), text: clip(t) });
        }
    });
    // dedupe
    const seen = new Set();
    const uniqueText = textBlocks.filter(b => {
        if (seen.has(b.text)) return false;
        seen.add(b.text);
        return true;
    }).slice(0, 60);

    // Forms
    const forms = [];
    document.querySelectorAll('form').forEach(form => {
        const fields = [];
        form.querySelectorAll('input,textarea,select').forEach(f => {
            fields.push({
                tag: f.tagName.toLowerCase(),
                type: f.type,
                name: f.name || f.id,
                placeholder: f.placeholder || null,
                value: f.value || null,
                required: f.required,
            });
        });
        forms.push({
            action: form.action,
            method: form.method,
            fields,
        });
    });

    function buildSelector(el) {
        if (el.id) return '#' + CSS.escape(el.id);
        if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
        if (el.getAttribute('aria-label')) return `[aria-label="${el.getAttribute('aria-label')}"]`;
        // fallback: tag + classes
        let sel = el.tagName.toLowerCase();
        if (el.className && typeof el.className === 'string') {
            const cls = el.className.trim().split(/\\s+/).slice(0, 2).map(c => '.' + CSS.escape(c)).join('');
            sel += cls;
        }
        return sel;
    }

    return { meta, interactives: interactives.slice(0, 80), textBlocks: uniqueText, forms };
}
"""

QUICK_SNAPSHOT_JS = """
() => {
    const els = [];
    document.querySelectorAll('a, button, input, textarea, select, [role="button"], [contenteditable="true"]').forEach((el, i) => {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return;
        els.push({
            i,
            tag: el.tagName.toLowerCase(),
            text: (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '').slice(0, 80),
            selector: el.id ? '#' + el.id : (el.getAttribute('aria-label') ? `[aria-label="${el.getAttribute('aria-label')}"]` : null),
        });
    });
    return { url: location.href, title: document.title, elements: els.slice(0, 50) };
}
"""


# ---------------------------------------------------------------------------
# Snapshot class
# ---------------------------------------------------------------------------

class PageSnapshot:
    """Captures and formats page state for LLM consumption."""

    def __init__(self, page):
        self.page = page

    async def full(self) -> dict:
        """Full structured snapshot — interactive elements, text, forms."""
        try:
            data = await self.page.evaluate(SNAPSHOT_JS)
            console.print(f"[green]✓[/green] Snapshot captured — {len(data.get('interactives', []))} interactive elements")
            return data
        except Exception as e:
            console.print(f"[red]✗[/red] Snapshot failed: {e}")
            return {"error": str(e)}

    async def quick(self) -> dict:
        """Lightweight snapshot — just clickable elements & URL."""
        try:
            return await self.page.evaluate(QUICK_SNAPSHOT_JS)
        except Exception as e:
            return {"error": str(e)}

    async def full_as_text(self) -> str:
        """Full snapshot formatted as compact text for LLM prompts."""
        data = await self.full()
        return self._format_for_llm(data)

    async def quick_as_text(self) -> str:
        """Quick snapshot formatted as text."""
        data = await self.quick()
        lines = [f"URL: {data.get('url')}", f"Title: {data.get('title')}", "", "Interactive Elements:"]
        for el in data.get("elements", []):
            sel = el.get("selector") or f"{el['tag']}[{el['i']}]"
            lines.append(f"  [{el['i']}] <{el['tag']}> \"{el['text']}\"  →  {sel}")
        return "\n".join(lines)

    # ── Formatting ─────────────────────────────────────────────────────────

    @staticmethod
    def _format_for_llm(data: dict) -> str:
        if "error" in data:
            return f"SNAPSHOT ERROR: {data['error']}"

        meta = data.get("meta", {})
        lines = [
            "═══ PAGE SNAPSHOT ═══",
            f"URL:   {meta.get('url')}",
            f"Title: {meta.get('title')}",
        ]
        if meta.get("h1"):
            lines.append(f"H1:    {meta['h1']}")

        # Interactive elements
        interactives = data.get("interactives", [])
        if interactives:
            lines.append(f"\n── Interactive Elements ({len(interactives)}) ──")
            for el in interactives:
                parts = [f"[{el['idx']}]", f"<{el['tag']}>"]
                if el.get("type"):
                    parts.append(f"type={el['type']}")
                if el.get("role"):
                    parts.append(f"role={el['role']}")
                if el.get("text"):
                    parts.append(f'"{el["text"]}"')
                if el.get("selector"):
                    parts.append(f"→ {el['selector']}")
                lines.append("  " + " ".join(parts))

        # Forms
        forms = data.get("forms", [])
        if forms:
            lines.append(f"\n── Forms ({len(forms)}) ──")
            for fi, form in enumerate(forms):
                lines.append(f"  Form #{fi}: action={form.get('action')} method={form.get('method')}")
                for field in form.get("fields", []):
                    lines.append(f"    - <{field['tag']}> name={field.get('name')} type={field.get('type')} placeholder={field.get('placeholder')}")

        # Key text
        text_blocks = data.get("textBlocks", [])
        if text_blocks:
            lines.append(f"\n── Key Page Text ({len(text_blocks)} blocks) ──")
            for block in text_blocks[:30]:
                lines.append(f"  <{block['tag']}> {block['text']}")

        lines.append("═══ END SNAPSHOT ═══")
        return "\n".join(lines)
