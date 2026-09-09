"""Comprehensive test suite for Markdown preview renderer."""

import unittest
import os
import sys
import time

# Ensure stmpp is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.dirname(current_dir)
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from renderer.path_resolver import PathResolver
from renderer.sanitizer import HtmlSanitizer
from renderer.highlighter import SyntaxHighlighter, MiniHtmlFormatter
from renderer.engine import MarkdownEngine


class TestPathResolver(unittest.TestCase):
    def setUp(self):
        self.base_dir = r"C:\project\docs"
        self.resolver = PathResolver(base_dir=self.base_dir, allow_remote=False)
        self.resolver_remote = PathResolver(base_dir=self.base_dir, allow_remote=True)

    def test_relative_image_path(self):
        res = self.resolver.resolve_image_src("./images/arch.png")
        self.assertTrue(res.startswith("file:///"))
        self.assertIn("project/docs/images/arch.png", res.replace("\\", "/"))

    def test_parent_relative_path(self):
        res = self.resolver.resolve_image_src("../assets/logo.png")
        self.assertTrue(res.startswith("file:///"))
        self.assertIn("project/assets/logo.png", res.replace("\\", "/"))

    def test_remote_blocking(self):
        res = self.resolver.resolve_image_src("https://example.com/pic.png")
        self.assertEqual(res, "")

    def test_remote_allowed(self):
        res = self.resolver_remote.resolve_image_src("https://example.com/pic.png")
        self.assertEqual(res, "https://example.com/pic.png")


class TestSanitizer(unittest.TestCase):
    def setUp(self):
        self.sanitizer = HtmlSanitizer(allow_html=True)
        self.sanitizer_strict = HtmlSanitizer(allow_html=False)

    def test_script_tag_stripped(self):
        raw = 'Hello <script>alert("xss")</script> World'
        cleaned = self.sanitizer.sanitize(raw)
        self.assertNotIn("<script>", cleaned)
        self.assertNotIn("alert", cleaned)
        self.assertIn("Hello", cleaned)
        self.assertIn("World", cleaned)

    def test_event_handler_stripped(self):
        raw = '<img src="a.png" onerror="alert(1)" />'
        cleaned = self.sanitizer.sanitize(raw)
        self.assertNotIn("onerror", cleaned)

    def test_strict_mode(self):
        raw = "<div>Hello</div>"
        cleaned = self.sanitizer_strict.sanitize(raw)
        self.assertIn("&lt;div&gt;", cleaned)


class TestHighlighter(unittest.TestCase):
    def test_python_highlight(self):
        code = 'def hello():\n    # greeting\n    return "world"'
        hl = MiniHtmlFormatter.highlight(code, "python")
        self.assertIn('class="hl-keyword">def</span>', hl)
        self.assertIn('class="hl-keyword">return</span>', hl)
        self.assertIn('class="hl-comment"># greeting</span>', hl)
        self.assertIn('class="hl-string">&quot;world&quot;</span>', hl)

    def test_javascript_highlight(self):
        code = 'const x = 123;\n// comment\nreturn x;'
        hl = MiniHtmlFormatter.highlight(code, "javascript")
        self.assertIn('class="hl-keyword">const</span>', hl)
        self.assertIn('class="hl-number">123</span>', hl)
        self.assertIn('class="hl-comment">// comment</span>', hl)


class TestMarkdownEngine(unittest.TestCase):
    def setUp(self):
        self.engine = MarkdownEngine(
            options={"toc": True, "allow_html": True, "code_line_numbers": False},
            base_dir=r"C:\test\docs"
        )

    def test_headings_and_toc(self):
        md = "# Heading 1\n\n## Sub Heading\n\nContent here."
        html_out = self.engine.render(md)
        self.assertIn('<h1 id="heading-1" data-line="1">Heading 1</h1>', html_out)
        self.assertIn('<h2 id="sub-heading" data-line="3">Sub Heading</h2>', html_out)
        self.assertIn('class="top-menu-bar"', html_out)
        self.assertIn('smp_open_toc', html_out)
        self.assertIn('<div class="toc-container">', html_out)
        self.assertIn('href="#heading-1"', html_out)
        self.assertIn('href="#sub-heading"', html_out)

    def test_toc_position_top(self):
        engine_top = MarkdownEngine(options={"toc": True, "toc_position": "top"})
        md = "# Heading 1\n\n## Sub Heading\n\nContent here."
        html_out = engine_top.render(md)
        self.assertNotIn('class="top-menu-bar"', html_out)
        self.assertIn('<div class="toc-container">', html_out)

    def test_gfm_table(self):
        # 2 columns table renders as <table>
        md = "| Name | Role |\n|---|---|\n| Alice | Admin |\n| Bob | User |"
        html_out = self.engine.render(md)
        self.assertIn("<table><tr>", html_out)
        self.assertIn("[Copy Table]", html_out)
        self.assertIn("<th>Name</th>", html_out)
        self.assertIn("<td>Alice</td>", html_out)

    def test_gfm_wide_table_cards(self):
        # >3 columns table renders as cards by default for minihtml
        md = "| Col1 | Col2 | Col3 | Col4 |\n|---|---|---|---|\n| V1 | V2 | V3 | V4 |"
        html_out = self.engine.render(md)
        self.assertIn('class="table-cards"', html_out)
        self.assertIn('[Copy Table]', html_out)
        self.assertIn('class="table-card"', html_out)
        self.assertIn('class="card-label">Col1:</span>', html_out)

    def test_task_list(self):
        md = "- [x] Done item\n- [ ] Pending item"
        html_out = self.engine.render(md)
        self.assertIn('class="task-list-item"><span style="color: #2ea44f; font-weight: bold;">[x]</span>', html_out)
        self.assertIn('class="task-list-item"><span style="color: #888888;">[ ]</span>', html_out)

    def test_fenced_code_block(self):
        md = "```python\nprint('hello')\n```"
        html_out = self.engine.render(md)
        self.assertIn('<div class="code-container">', html_out)
        self.assertIn('[Copy Code]', html_out)
        self.assertIn('<code class="language-python">', html_out)

    def test_inlines(self):
        md = "**Bold** and *Italic* and ~~Deleted~~ and `code`"
        html_out = self.engine.render(md)
        self.assertIn("<strong>Bold</strong>", html_out)
        self.assertIn("<em>Italic</em>", html_out)
        self.assertIn('<span style="text-decoration: line-through;">Deleted</span>', html_out)
        self.assertIn("<code>code</code>", html_out)

    def test_rendering_performance_100kb(self):
        chunk = "# Title\n\nParagraph with **bold** text and `inline code`.\n\n- [x] Item 1\n- [ ] Item 2\n\n"
        # Repeat to produce ~100KB of markdown
        large_md = chunk * 1500
        start = time.perf_counter()
        html_out = self.engine.render(large_md)
        duration_ms = (time.perf_counter() - start) * 1000
        self.assertTrue(len(html_out) > 50000)
        print(f"\n[Perf Benchmark] 100KB Markdown Render Duration: {duration_ms:.2f}ms")
        # Ensure under 200ms
        self.assertLess(duration_ms, 200)


if __name__ == "__main__":
    unittest.main()
