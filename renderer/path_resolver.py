"""Path and resource resolver for Markdown documents."""

import os
import urllib.parse


class PathResolver:
    """Resolves relative links and images relative to the source Markdown document."""

    def __init__(self, base_dir=None, allow_remote=False):
        self.base_dir = base_dir or ""
        self.allow_remote = allow_remote

    def resolve_image_src(self, src: str) -> str:
        """Resolve an image source to an absolute file URI or remote URL."""
        if not src:
            return ""

        src = src.strip()

        # Handle remote URLs
        if src.startswith(("http://", "https://", "ftp://")):
            if self.allow_remote:
                return src
            return ""

        # Handle data URIs
        if src.startswith("data:image/"):
            return src

        # Handle file:// URIs
        if src.startswith("file://"):
            return src

        # Clean URL query/hash if any for local path check
        url_parts = urllib.parse.urlsplit(src)
        clean_path = url_parts.path

        # Unquote URL path in case it was percent-encoded
        clean_path = urllib.parse.unquote(clean_path)

        # Convert forward slashes to system separator for local path lookup
        clean_path = os.path.normpath(clean_path)

        if os.path.isabs(clean_path):
            abs_path = clean_path
        else:
            if not self.base_dir:
                return src
            abs_path = os.path.normpath(os.path.join(self.base_dir, clean_path))

        # Convert to file:/// URI
        norm_abs = abs_path.replace("\\", "/")
        if not norm_abs.startswith("/"):
            norm_abs = "/" + norm_abs

        return f"file://{norm_abs}"

    def resolve_link_href(self, href: str) -> str:
        """Resolve a link href, preserving internal anchors and external links."""
        if not href:
            return "#"

        href = href.strip()

        # Internal document anchor
        if href.startswith("#"):
            return href

        # Remote link or existing file URI
        if href.startswith(("http://", "https://", "mailto:", "ftp://", "file://")):
            return href

        # Internal relative markdown link
        if not self.base_dir:
            return href

        url_parts = urllib.parse.urlsplit(href)
        clean_path = urllib.parse.unquote(url_parts.path)
        clean_path = os.path.normpath(clean_path)

        if not os.path.isabs(clean_path):
            clean_path = os.path.normpath(os.path.join(self.base_dir, clean_path))

        norm_abs = clean_path.replace("\\", "/")
        if not norm_abs.startswith("/"):
            norm_abs = "/" + norm_abs

        res = f"file://{norm_abs}"
        if url_parts.fragment:
            res += f"#{url_parts.fragment}"
        return res
