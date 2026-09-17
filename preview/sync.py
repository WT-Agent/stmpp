"""Scroll synchronization between Markdown editor and Preview sheet."""

from typing import List, Optional, Any

try:
    import sublime
except ImportError:
    sublime = None


class ScrollSynchronizer:
    """Computes matching anchors and sync points between source Markdown and HTML preview."""

    @staticmethod
    def get_current_line(view: Any) -> int:
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

    @staticmethod
    def calculate_scroll_ratio(view: Any) -> float:
        """Calculate the vertical scroll ratio (0.0 ~ 1.0) of an editor view."""
        if not view:
            return 0.0

        try:
            view_pos = view.viewport_position()
            view_y = view_pos[1] if isinstance(view_pos, (tuple, list)) else getattr(view_pos, "y", 0.0)

            view_extent = view.layout_extent()
            view_h = view_extent[1] if isinstance(view_extent, (tuple, list)) else getattr(view_extent, "y", 1.0)

            view_vp = view.viewport_extent()
            vp_h = view_vp[1] if isinstance(view_vp, (tuple, list)) else getattr(view_vp, "y", 1.0)

            max_scroll = max(1.0, float(view_h) - float(vp_h))
            return max(0.0, min(1.0, float(view_y) / max_scroll))
        except Exception:
            return 0.0

    @staticmethod
    def calculate_target_sheet_y(sheet: Any, ratio: float) -> float:
        """Calculate the target vertical layout offset in an HtmlSheet for a given ratio."""
        if not sheet or not hasattr(sheet, "layout_extent") or not hasattr(sheet, "viewport_extent"):
            return 0.0

        try:
            sheet_layout = sheet.layout_extent()
            sheet_h = getattr(sheet_layout, "y", None)
            if sheet_h is None:
                sheet_h = sheet_layout[1] if isinstance(sheet_layout, (tuple, list)) else 0.0

            sheet_vp = sheet.viewport_extent()
            vp_h = getattr(sheet_vp, "y", None)
            if vp_h is None:
                vp_h = sheet_vp[1] if isinstance(sheet_vp, (tuple, list)) else 0.0

            max_sheet_scroll = max(0.0, float(sheet_h) - float(vp_h))
            return float(ratio) * max_sheet_scroll
        except Exception:
            return 0.0

    @classmethod
    def sync_editor_to_preview(cls, view: Any, sheet: Any, animate: bool = False):
        """Synchronize preview sheet viewport to match the source editor's scroll position."""
        if not view or not sheet:
            return

        if not hasattr(sheet, "set_viewport_position"):
            return

        try:
            ratio = cls.calculate_scroll_ratio(view)
            target_y = cls.calculate_target_sheet_y(sheet, ratio)

            if sublime and hasattr(sublime, "Vector"):
                target_pos = sublime.Vector(0.0, target_y)
            else:
                target_pos = (0.0, target_y)

            sheet.set_viewport_position(target_pos, animate=animate)
        except Exception:
            pass
