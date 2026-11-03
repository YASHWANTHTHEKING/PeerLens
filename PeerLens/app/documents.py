import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


@dataclass(frozen=True)
class Page:
    number: int
    heading: str
    text: str


@dataclass(frozen=True)
class Chunk:
    source: str
    page: int
    heading: str
    content: str
    index: int


class _FilingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pages: list[Page] = []
        self.page_number = 1
        self.heading = ""
        self.heading_tag: str | None = None
        self.heading_parts: list[str] = []
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in {"script", "style"}:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading_tag = tag
            self.heading_parts = []
        if tag in {"br", "div", "li", "p", "tr"}:
            self.parts.append("\n")
        elif tag in {"td", "th"}:
            self.parts.append(" | ")
        if tag == "hr" and "page-break-after" in (attributes.get("style") or "").lower():
            self._finish_page()

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag == self.heading_tag:
            text = self._normalize(" ".join(self.heading_parts))
            if text:
                self.heading = text
            self.heading_tag = None
            self.heading_parts = []
            self.parts.append("\n")
        elif tag in {"div", "li", "p", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self.parts.append(data)
        if self.heading_tag:
            self.heading_parts.append(data)

    def _finish_page(self) -> None:
        text = self._normalize(" ".join(self.parts))
        if text:
            self.pages.append(Page(self.page_number, self.heading, text))
        self.parts.clear()
        self.page_number += 1

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


def parse_filing(path: Path) -> list[Page]:
    parser = _FilingParser()
    with path.open(encoding="utf-8", errors="replace") as filing:
        for line in filing:
            parser.feed(line)
    parser.close()
    parser._finish_page()
    return parser.pages


def chunk_pages(
    source: str,
    pages: list[Page],
    max_chars: int = 1800,
    overlap_chars: int = 200,
) -> list[Chunk]:
    if max_chars <= 0 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Chunk size must be positive and overlap smaller than chunk size.")

    chunks: list[Chunk] = []
    for page in pages:
        start = 0
        while start < len(page.text):
            end = min(start + max_chars, len(page.text))
            if end < len(page.text):
                boundary = page.text.rfind(" ", start + max_chars // 2, end)
                if boundary > start:
                    end = boundary
            content = page.text[start:end].strip()
            if content:
                chunks.append(
                    Chunk(
                        source=source,
                        page=page.number,
                        heading=page.heading,
                        content=content,
                        index=len(chunks),
                    )
                )
            if end >= len(page.text):
                break
            start = max(start + 1, end - overlap_chars)
    return chunks
