"""Command to open Markdown Table of Contents / Outline navigation."""

import re
import sublime
import sublime_plugin
from ..preview.manager import PreviewManager


class SmpOpenTocCommand(sublime_plugin.WindowCommand):
    """Displays a Quick Panel outline of Markdown headings to quickly jump to sections."""

    def run(self):
        view = self.window.active_view()
        if not view:
            return

        manager = PreviewManager.get_instance()
        if not manager.is_markdown_view(view):
            sublime.status_message("Active view is not a Markdown document")
            return

        lines = view.substr(sublime.Region(0, view.size())).splitlines()
        headings = []
        heading_lines = []

        for idx, line in enumerate(lines):
            stripped = line.strip()
            m = re.match(r"^(#{1,6})\s+(.*?)(?:\s+#+)?$", stripped)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                prefix = "  " * (level - 1) + f"H{level}: "
                headings.append(f"{prefix}{title}")
                heading_lines.append(idx)

        if not headings:
            sublime.status_message("No headings found in current Markdown document")
            return

        def on_select(index):
            if index < 0 or index >= len(heading_lines):
                return
            target_line = heading_lines[index]
            pt = view.text_point(target_line, 0)
            view.sel().clear()
            view.sel().add(sublime.Region(pt, pt))
            view.show_at_center(pt)
            self.window.focus_view(view)

        self.window.show_quick_panel(headings, on_select)

    def is_enabled(self):
        view = self.window.active_view()
        if not view:
            return False
        manager = PreviewManager.get_instance()
        return manager.is_markdown_view(view)
