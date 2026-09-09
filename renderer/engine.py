"""Markdown parsing and HTML rendering engine for Sublime Markdown Preview."""

import re
import html
from typing import List, Dict, Tuple, Optional
from .path_resolver import PathResolver
from .highlighter import SyntaxHighlighter
from .sanitizer import HtmlSanitizer


class HeadingItem:
    def __init__(self, level: int, title: str, anchor: str, line_no: int):
        self.level = level
        self.title = title
        self.anchor = anchor
        self.line_no = line_no


class MarkdownEngine:
    """Parses GFM Markdown and renders minihtml-compatible HTML documents."""

    FRONT_MATTER_PATTERN = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*?)(?:\s+#+)?$")
    HR_PATTERN = re.compile(r"^ {0,3}([-*_])(?:\s*\1){2,}\s*$")
    BLOCKQUOTE_PATTERN = re.compile(r"^ {0,3}>\s?(.*)$")
    TASK_LIST_PATTERN = re.compile(r"^ {0,3}[-*+]\s+\[([ xX])\]\s+(.*)$")
    UNORDERED_LIST_PATTERN = re.compile(r"^ {0,3}[-*+]\s+(.*)$")
    ORDERED_LIST_PATTERN = re.compile(r"^ {0,3}\d+\.\s+(.*)$")

    def __init__(self, options: Optional[Dict] = None, base_dir: str = ""):
        self.options = options or {}
        self.base_dir = base_dir
        self.path_resolver = PathResolver(
            base_dir=base_dir,
            allow_remote=self.options.get("allow_remote_resources", False),
        )
        self.highlighter = SyntaxHighlighter(
            show_line_numbers=self.options.get("code_line_numbers", False)
        )
        self.sanitizer = HtmlSanitizer(
            allow_html=self.options.get("allow_html", True)
        )
        self.headings = []

    def render(self, markdown_text: str, custom_css: str = "") -> str:
        """Render markdown text into a complete HTML document."""
        self.headings = []

        # 1. Strip YAML front matter
        body_text = self._strip_front_matter(markdown_text)

        # 2. Parse block elements
        html_blocks = self._parse_blocks(body_text)

        # 3. Build Table of Contents if enabled
        toc_html = ""
        if self.options.get("toc", True) and len(self.headings) > 1:
            toc_html = self._build_toc_html()

        # 4. Assemble final document
        content_body = toc_html + "\n".join(html_blocks)
        return self._wrap_document(content_body, custom_css)

    def _strip_front_matter(self, text: str) -> str:
        return self.FRONT_MATTER_PATTERN.sub("", text)

    def _parse_blocks(self, text: str) -> List[str]:
        lines = text.splitlines()
        blocks = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            # Empty lines
            if not stripped:
                i += 1
                continue

            # Fenced code blocks ```
            if stripped.startswith("```") or stripped.startswith("~~~"):
                fence = stripped[:3]
                lang = stripped[3:].strip()
                code_lines = []
                i += 1
                while i < n and not lines[i].strip().startswith(fence):
                    code_lines.append(lines[i])
                    i += 1
                if i < n:
                    i += 1  # consume closing fence
                highlighted = self.highlighter.highlight_block("\n".join(code_lines), lang)
                blocks.append(highlighted)
                continue

            # Horizontal Rule
            if self.HR_PATTERN.match(line):
                blocks.append("<hr>")
                i += 1
                continue

            # Headings
            h_match = self.HEADING_PATTERN.match(line)
            if h_match:
                level = len(h_match.group(1))
                title_raw = h_match.group(2).strip()
                anchor = self._slugify(title_raw)
                self.headings.append(HeadingItem(level, title_raw, anchor, i + 1))
                rendered_title = self._parse_inlines(title_raw)
                blocks.append(f'<h{level} id="{anchor}" data-line="{i + 1}">{rendered_title}</h{level}>')
                i += 1
                continue

            # Tables: check current line contains '|' and next line is table separator
            if "|" in line and i + 1 < n and self._is_table_separator(lines[i + 1]):
                table_html, new_i = self._parse_table(lines, i)
                blocks.append(table_html)
                i = new_i
                continue

            # Blockquotes
            if line.lstrip().startswith(">"):
                quote_lines = []
                while i < n and (lines[i].lstrip().startswith(">") or (lines[i].strip() and not self._is_block_starter(lines[i]))):
                    q_line = lines[i].lstrip()
                    if q_line.startswith(">"):
                        quote_lines.append(q_line[1:].lstrip())
                    else:
                        quote_lines.append(lines[i])
                    i += 1
                quote_content = "\n".join(self._parse_blocks("\n".join(quote_lines)))
                blocks.append(f"<blockquote>{quote_content}</blockquote>")
                continue

            # Task list or Unordered list
            if self.TASK_LIST_PATTERN.match(line) or self.UNORDERED_LIST_PATTERN.match(line):
                list_html, new_i = self._parse_list(lines, i, is_ordered=False)
                blocks.append(list_html)
                i = new_i
                continue

            # Ordered list
            if self.ORDERED_LIST_PATTERN.match(line):
                list_html, new_i = self._parse_list(lines, i, is_ordered=True)
                blocks.append(list_html)
                i = new_i
                continue

            # Paragraph (consume until empty line or new block)
            p_lines = []
            while i < n and lines[i].strip() and not self._is_block_starter(lines[i]):
                p_lines.append(lines[i].strip())
                i += 1
            if p_lines:
                p_text = " ".join(p_lines)
                blocks.append(f"<p>{self._parse_inlines(p_text)}</p>")

        return blocks

    def _is_block_starter(self, line: str) -> bool:
        s = line.strip()
        if not s:
            return True
        if s.startswith("```") or s.startswith("~~~"):
            return True
        if self.HR_PATTERN.match(line):
            return True
        if self.HEADING_PATTERN.match(line):
            return True
        if s.startswith(">"):
            return True
        if self.TASK_LIST_PATTERN.match(line) or self.UNORDERED_LIST_PATTERN.match(line) or self.ORDERED_LIST_PATTERN.match(line):
            return True
        return False

    def _is_table_separator(self, line: str) -> bool:
        s = line.strip()
        if not (s.startswith("|") or "|" in s):
            return False
        parts = [p.strip() for p in s.strip("|").split("|")]
        if not parts:
            return False
        for p in parts:
            if not re.match(r"^:?-+:?$", p):
                return False
        return True

    def _parse_table(self, lines: List[str], start_idx: int) -> Tuple[str, int]:
        header_line = lines[start_idx]
        sep_line = lines[start_idx + 1]

        headers = [h.strip() for h in header_line.strip("|").split("|")]
        aligns = []
        for s in [p.strip() for p in sep_line.strip("|").split("|")]:
            if s.startswith(":") and s.endswith(":"):
                aligns.append(' style="text-align: center;"')
            elif s.endswith(":"):
                aligns.append(' style="text-align: right;"')
            elif s.startswith(":"):
                aligns.append(' style="text-align: left;"')
            else:
                aligns.append("")

        table_mode = self.options.get("table_mode", "auto")
        # minihtml doesn't implement <table> column constraints.
        # If columns > 3 or table_mode == 'cards', render as readable structured cards.
        render_cards = (table_mode == "cards") or (table_mode == "auto" and len(headers) > 3)

        i = start_idx + 2
        n = len(lines)
        rows_data = []
        while i < n and "|" in lines[i] and lines[i].strip():
            row_cells = [c.strip() for c in lines[i].strip("|").split("|")]
            rows_data.append(row_cells)
            i += 1

        if render_cards:
            out = ['<div class="table-cards">']
            for row in rows_data:
                out.append('<div class="table-card">')
                for idx, cell in enumerate(row):
                    header_label = headers[idx] if idx < len(headers) else f"Column {idx + 1}"
                    rendered_cell = self._parse_inlines(cell)
                    out.append(
                        f'<div class="card-row">'
                        f'<span class="card-label">{self._parse_inlines(header_label)}:</span> '
                        f'<span class="card-value">{rendered_cell}</span>'
                        f'</div>'
                    )
                out.append('</div>')
            out.append('</div>')
            return "".join(out), i

        out = ["<table><tr>"]
        for idx, h in enumerate(headers):
            style = aligns[idx] if idx < len(aligns) else ""
            out.append(f"<th{style}>{self._parse_inlines(h)}</th>")
        out.append("</tr>")

        for row_cells in rows_data:
            out.append("<tr>")
            for idx, c in enumerate(row_cells):
                style = aligns[idx] if idx < len(aligns) else ""
                out.append(f"<td{style}>{self._parse_inlines(c)}</td>")
            out.append("</tr>")

        out.append("</table>")
        return "".join(out), i

    def _parse_list(self, lines: List[str], start_idx: int, is_ordered: bool) -> Tuple[str, int]:
        tag = "ol" if is_ordered else "ul"
        out = [f"<{tag}>"]
        i = start_idx
        n = len(lines)

        while i < n:
            line = lines[i]
            if not line.strip():
                # End of list or paragraph break in list
                break

            task_m = self.TASK_LIST_PATTERN.match(line)
            if task_m:
                checked = task_m.group(1).lower() == "x"
                item_text = task_m.group(2)
                chk_box = '<span style="color: #2ea44f; font-weight: bold;">[x]</span>' if checked else '<span style="color: #888888;">[ ]</span>'
                out.append(f'<li class="task-list-item">{chk_box} {self._parse_inlines(item_text)}</li>')
                i += 1
                continue

            if is_ordered:
                ord_m = self.ORDERED_LIST_PATTERN.match(line)
                if ord_m:
                    out.append(f"<li>{self._parse_inlines(ord_m.group(1))}</li>")
                    i += 1
                else:
                    break
            else:
                unord_m = self.UNORDERED_LIST_PATTERN.match(line)
                if unord_m:
                    out.append(f"<li>{self._parse_inlines(unord_m.group(1))}</li>")
                    i += 1
                else:
                    break

        out.append(f"</{tag}>")
        return "".join(out), i

    def _parse_inlines(self, text: str) -> str:
        """Parse inline markdown elements."""
        if not text:
            return ""

        # Sanitize raw HTML
        res = self.sanitizer.sanitize(text)

        # Escape naked & that is not part of a valid HTML/XML entity
        res = re.sub(r"&(?!(?:[a-zA-Z0-9]+|#[0-9]+|#x[0-9a-fA-F]+);)", "&amp;", res)

        # Escape naked < that is not an HTML tag
        res = re.sub(r"<(?![a-zA-Z/!])", "&lt;", res)

        # Escape isolated > (e.g. ' > ' in priorities)
        res = re.sub(r"(?<=\s)>(?=\s)", "&gt;", res)

        # Inline code: `code`
        res = re.sub(r"`([^`]+)`", lambda m: f"<code>{html.escape(m.group(1))}</code>", res)

        # Images: ![alt](url "title")
        def replace_img(match):
            alt = html.escape(match.group(1))
            raw_src = match.group(2)
            resolved_src = self.path_resolver.resolve_image_src(raw_src)
            if not resolved_src:
                return f'<span>[Image unavailable: {alt}]</span>'
            return f'<img src="{html.escape(resolved_src)}" alt="{alt}" />'

        res = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)", replace_img, res)

        # Links: [text](href "title")
        def replace_link(match):
            txt = match.group(1)
            raw_href = match.group(2)
            resolved_href = self.path_resolver.resolve_link_href(raw_href)
            return f'<a href="{html.escape(resolved_href)}">{txt}</a>'

        res = re.sub(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)", replace_link, res)

        # Bold + Italic: ***text*** or ___text___
        res = re.sub(r"(\*\*\*|___)(.*?)\1", r"<strong><em>\2</em></strong>", res)

        # Bold: **text** or __text__
        res = re.sub(r"(\*\*|__)(.*?)\1", r"<strong>\2</strong>", res)

        # Italic: *text* or _text_
        res = re.sub(r"(\*|_)(.*?)\1", r"<em>\2</em>", res)

        # Strikethrough: ~~text~~
        res = re.sub(r"~~(.*?)~~", r'<span style="text-decoration: line-through;">\1</span>', res)

        return res

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug or "section"

    def _build_toc_html(self) -> str:
        items = []
        for h in self.headings:
            indent = (h.level - 1) * 16
            items.append(
                f'<li style="margin-left: {indent}px;">'
                f'<a href="#{h.anchor}">{html.escape(h.title)}</a>'
                f'</li>'
            )
        return (
            '<div class="toc-container">'
            '<div class="toc-title">Table of Contents</div>'
            f'<ul class="toc-list">{"".join(items)}</ul>'
            '</div>'
        )

    def _wrap_document(self, content_body: str, custom_css: str) -> str:
        return (
            "<style>\n"
            f"{custom_css}\n"
            "</style>\n"
            '<body id="sublime-markdown-preview">\n'
            f"{content_body}\n"
            "</body>"
        )
