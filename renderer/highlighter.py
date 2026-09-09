"""Lightweight syntax highlighter for minihtml code blocks."""

import html
import re

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, TextLexer
    from pygments.formatters import HtmlFormatter
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False


class SnippetCache:
    """Thread-safe in-memory cache for code snippets referenced by subl: URLs."""
    _snippets = {}
    _counter = 0

    @classmethod
    def store(cls, code: str) -> int:
        cls._counter += 1
        cls._snippets[cls._counter] = code
        if len(cls._snippets) > 500:
            oldest = sorted(cls._snippets.keys())[:200]
            for k in oldest:
                cls._snippets.pop(k, None)
        return cls._counter

    @classmethod
    def get(cls, snippet_id: int) -> str:
        return cls._snippets.get(snippet_id, "")


class MiniHtmlFormatter:
    """Fallback regex-based syntax highlighter for common programming languages."""

    KEYWORDS = {
        "python": {
            "def", "class", "if", "elif", "else", "for", "while", "return", "import",
            "from", "as", "try", "except", "finally", "raise", "with", "yield", "async",
            "await", "lambda", "pass", "break", "continue", "in", "is", "not", "and", "or",
            "True", "False", "None"
        },
        "javascript": {
            "function", "const", "let", "var", "return", "if", "else", "for", "while",
            "do", "switch", "case", "default", "break", "continue", "try", "catch",
            "finally", "throw", "new", "class", "extends", "import", "export", "from",
            "as", "async", "await", "yield", "this", "super", "typeof", "instanceof",
            "true", "false", "null", "undefined"
        },
        "json": {
            "true", "false", "null"
        },
        "go": {
            "func", "package", "import", "type", "struct", "interface", "return", "if",
            "else", "for", "range", "switch", "case", "default", "select", "chan",
            "go", "defer", "var", "const", "true", "false", "nil"
        },
        "rust": {
            "fn", "let", "mut", "pub", "struct", "enum", "impl", "trait", "match",
            "if", "else", "for", "while", "loop", "return", "use", "mod", "crate",
            "self", "Self", "where", "as", "async", "await", "true", "false"
        },
        "c": {
            "int", "char", "float", "double", "void", "struct", "union", "enum",
            "typedef", "sizeof", "static", "extern", "const", "return", "if", "else",
            "for", "while", "do", "switch", "case", "default", "break", "continue"
        },
        "bash": {
            "if", "then", "else", "elif", "fi", "case", "esac", "for", "while",
            "until", "do", "done", "in", "function", "return", "exit", "local", "echo"
        },
        "sql": {
            "SELECT", "FROM", "WHERE", "INSERT", "INTO", "UPDATE", "DELETE", "JOIN",
            "LEFT", "RIGHT", "INNER", "OUTER", "ON", "GROUP", "BY", "ORDER", "HAVING",
            "LIMIT", "OFFSET", "CREATE", "TABLE", "DROP", "ALTER", "AND", "OR", "NOT",
            "NULL", "AS", "SET", "VALUES"
        }
    }

    # Alias mapping
    ALIASES = {
        "py": "python",
        "js": "javascript",
        "ts": "javascript",
        "typescript": "javascript",
        "sh": "bash",
        "shell": "bash",
        "zsh": "bash",
        "golang": "go",
        "rs": "rust",
        "cpp": "c",
        "c++": "c",
        "h": "c",
        "hpp": "c"
    }

    @classmethod
    def highlight(cls, code: str, lang: str) -> str:
        lang = cls.ALIASES.get(lang.lower(), lang.lower())
        keywords = cls.KEYWORDS.get(lang, set())

        lines = code.splitlines()
        highlighted_lines = []

        for line in lines:
            highlighted_lines.append(cls._highlight_line(line, keywords, lang))

        return "\n".join(highlighted_lines)

    @classmethod
    def _highlight_line(cls, line: str, keywords: set, lang: str) -> str:
        # Check single line comment
        comment_prefix = "#" if lang in ("python", "bash", "sh", "yaml", "dockerfile") else "--" if lang == "sql" else "//"
        comment_idx = -1
        in_str = None
        for i, char in enumerate(line):
            if char in ('"', "'"):
                if in_str == char and (i == 0 or line[i-1] != '\\'):
                    in_str = None
                elif in_str is None:
                    in_str = char
            elif in_str is None and line.startswith(comment_prefix, i):
                comment_idx = i
                break

        if comment_idx != -1:
            code_part = line[:comment_idx]
            comment_part = line[comment_idx:]
            return cls._highlight_code(code_part, keywords) + f'<span class="hl-comment">{html.escape(comment_part)}</span>'
        else:
            return cls._highlight_code(line, keywords)

    @classmethod
    def _highlight_code(cls, text: str, keywords: set) -> str:
        token_pattern = re.compile(
            r'(?P<str>"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\')|'
            r'(?P<num>\b\d+(?:\.\d+)?\b)|'
            r'(?P<ident>\b[a-zA-Z_][a-zA-Z0-9_]*\b)|'
            r'(?P<other>[^\w\s"\'\\]+)'
        )

        out = []
        last_end = 0

        for match in token_pattern.finditer(text):
            start, end = match.span()
            if start > last_end:
                out.append(html.escape(text[last_end:start]))

            val = match.group()
            group_name = match.lastgroup

            if group_name == "str":
                out.append(f'<span class="hl-string">{html.escape(val)}</span>')
            elif group_name == "num":
                out.append(f'<span class="hl-number">{html.escape(val)}</span>')
            elif group_name == "ident":
                upper_val = val.upper()
                if val in keywords or upper_val in keywords:
                    out.append(f'<span class="hl-keyword">{html.escape(val)}</span>')
                else:
                    out.append(html.escape(val))
            else:
                out.append(html.escape(val))

            last_end = end

        if last_end < len(text):
            out.append(html.escape(text[last_end:]))

        return "".join(out)


class SyntaxHighlighter:
    """Formats fenced code blocks with appropriate syntax styles."""

    def __init__(self, show_line_numbers=False):
        self.show_line_numbers = show_line_numbers

    def highlight_block(self, code: str, lang: str = "") -> str:
        lang_clean = lang.strip().lower()
        lang_display = lang_clean if lang_clean else "text"

        if not lang_clean:
            highlighted = html.escape(code)
        elif HAS_PYGMENTS:
            try:
                lexer = get_lexer_by_name(lang_clean, stripall=False)
                formatter = HtmlFormatter(nowrap=True, classprefix="hl-")
                highlighted = highlight(code, lexer, formatter)
            except Exception:
                highlighted = MiniHtmlFormatter.highlight(code, lang_clean)
        else:
            highlighted = MiniHtmlFormatter.highlight(code, lang_clean)

        # Register snippet in cache and use clean snippet ID
        snippet_id = SnippetCache.store(code)
        copy_href = f"subl:smp_copy_code {{&quot;id&quot;: {snippet_id}}}"

        return (
            f'<div class="code-container">'
            f'<div class="code-header">'
            f'<span class="code-lang">{html.escape(lang_display)}</span>'
            f'<a class="code-copy-btn" href="{copy_href}">[Copy Code]</a>'
            f'</div>'
            f'<pre><code class="language-{html.escape(lang_display)}">{highlighted}</code></pre>'
            f'</div>'
        )
