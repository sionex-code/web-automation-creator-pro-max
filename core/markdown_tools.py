"""
Helpers for turning local Markdown files into LinkedIn-ready article content.
"""

import re
from html.parser import HTMLParser
from pathlib import Path

import markdown


class _HTMLTextExtractor(HTMLParser):
    """Collect plain text from HTML for lightweight previews."""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str):
        if data:
            self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


def _strip_front_matter(text: str) -> str:
    """Remove optional YAML front matter from a markdown file."""
    if not text.startswith("---"):
        return text

    lines = text.splitlines()
    if not lines:
        return text

    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1:]).lstrip()

    return text


def _detect_title(lines: list[str], path: Path) -> tuple[str, int | None]:
    """Choose a title from the markdown heading or first content line."""
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip(), index

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped:
            cleaned = re.sub(r"^[#>*\-\d\.\)\s]+", "", stripped).strip()
            if cleaned:
                return cleaned, index

    fallback = path.stem.replace("-", " ").replace("_", " ").strip().title()
    return fallback or "Untitled Article", None


def parse_markdown_article(path: str) -> dict:
    """Read a markdown file and return title, markdown body, html body, and preview."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {path}")

    raw = file_path.read_text(encoding="utf-8")
    normalized = _strip_front_matter(raw.replace("\r\n", "\n").replace("\r", "\n")).strip()
    lines = normalized.splitlines()

    title, title_index = _detect_title(lines, file_path)

    body_lines = list(lines)
    if title_index is not None and lines[title_index].strip().startswith("# "):
        body_lines = lines[:title_index] + lines[title_index + 1:]

    body_markdown = "\n".join(body_lines).strip()
    body_html = markdown.markdown(
        body_markdown,
        extensions=["extra", "sane_lists", "nl2br"],
        output_format="html5",
    )

    extractor = _HTMLTextExtractor()
    extractor.feed(body_html)
    preview_text = re.sub(r"\s+", " ", extractor.text()).strip()

    return {
        "path": str(file_path),
        "title": title,
        "body_markdown": body_markdown,
        "body_html": body_html,
        "preview_text": preview_text,
        "word_count": len(preview_text.split()),
    }
