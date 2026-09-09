"""Layout manager for Sublime Markdown Preview."""

import sublime
from typing import Optional, Dict, Any


class LayoutManager:
    """Manages window layouts, splitting views and restoring original column configurations."""

    @staticmethod
    def get_2col_layout(split_ratio: float = 0.5) -> Dict[str, Any]:
        """Generate a 2-column layout dictionary with custom split ratio."""
        ratio = max(0.1, min(0.9, split_ratio))
        return {
            "cols": [0.0, ratio, 1.0],
            "rows": [0.0, 1.0],
            "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
        }

    @staticmethod
    def split_to_side(window: sublime.Window, split_ratio: float = 0.5) -> Optional[Dict[str, Any]]:
        """Split window into 2 columns if only 1 group exists, returning original layout if changed."""
        if not window:
            return None

        current_layout = window.layout()
        if window.num_groups() == 1:
            two_col = LayoutManager.get_2col_layout(split_ratio)
            window.set_layout(two_col)
            return current_layout

        return None

    @staticmethod
    def restore_layout(window: sublime.Window, original_layout: Optional[Dict[str, Any]] = None):
        """Restore previous layout if group 1 is now empty."""
        if not window:
            return

        if window.num_groups() > 1:
            sheets_in_group_1 = window.sheets_in_group(1) if hasattr(window, "sheets_in_group") else []
            views_in_group_1 = window.views_in_group(1) if hasattr(window, "views_in_group") else []

            if not sheets_in_group_1 and not views_in_group_1:
                if original_layout:
                    window.set_layout(original_layout)
                else:
                    window.set_layout({
                        "cols": [0.0, 1.0],
                        "rows": [0.0, 1.0],
                        "cells": [[0, 0, 1, 1]]
                    })
