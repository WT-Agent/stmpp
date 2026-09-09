"""HTML sanitizer for Markdown documents."""

import re
import html


class HtmlSanitizer:
    """Sanitizes raw HTML to prevent XSS and unsafe script execution in minihtml."""

    # Disallowed tags that must be stripped or escaped
    DANGEROUS_TAGS_PATTERN = re.compile(
        r"<\s*(script|iframe|object|embed|applet|meta|link|base)[^>]*>.*?</\s*\1\s*>|"
        r"<\s*(script|iframe|object|embed|applet|meta|link|base)[^>]*/>|"
        r"<\s*(script|iframe|object|embed|applet|meta|link|base)[^>]*>",
        re.IGNORECASE | re.DOTALL,
    )

    # Event handlers like onload, onclick, onerror
    EVENT_HANDLER_PATTERN = re.compile(
        r"\s+on[a-z]+\s*=\s*(?:'[^']*'|\"[^\"]*\"|[^\s>]+)",
        re.IGNORECASE,
    )

    # Javascript: URIs
    JS_URI_PATTERN = re.compile(
        r"\bhref\s*=\s*(?:'javascript:[^']*'|\"javascript:[^\"]*\")",
        re.IGNORECASE,
    )

    def __init__(self, allow_html=True):
        self.allow_html = allow_html

    def sanitize(self, raw_html: str) -> str:
        """Sanitize raw HTML according to configuration."""
        if not raw_html:
            return ""

        if not self.allow_html:
            return html.escape(raw_html)

        # Strip dangerous tags
        cleaned = self.DANGEROUS_TAGS_PATTERN.sub("", raw_html)

        # Strip inline event handlers
        cleaned = self.EVENT_HANDLER_PATTERN.sub("", cleaned)

        # Strip javascript: URIs
        cleaned = self.JS_URI_PATTERN.sub('href="#"', cleaned)

        return cleaned
