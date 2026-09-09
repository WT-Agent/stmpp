"""Scroll synchronization between Markdown editor and Preview sheet."""

import sublime
from typing import List, Optional


class ScrollSynchronizer:
    """Computes matching anchors and sync points between source Markdown and HTML preview."""

    @staticmethod
    def get_current_line(view: sublime.View) -> int:
        """Get the current top visible line or cursor line in the view (1-indexed)."""
        if not view:
            return 1

        try:
            visible_region = view.visible_region()
            top_pt = visible_region.begin()
            row, _ = view.rowcol(top_pt)
            return row + 1
        except Exception:
            return 1

    @staticmethod
    def find_nearest_heading_anchor(lines: List[str], target_line: int) -> Optional[str]:
        """Find the nearest heading anchor at or above target_line."""
        nearest_anchor = None
        for i in range(min(target_line - 1, len(lines) - 1), -1, -1):
            line = lines[i].strip()
            if line.startswith("#"):
                clean_title = line.lstrip("#").strip()
                import re
                slug = re.sub(r"[^\w\s-]", "", clean_title.lower()).strip()
                slug = re.sub(r"[-\s]+", "-", slug)
                if slug:
                    return slug
        return nearest_anchor
