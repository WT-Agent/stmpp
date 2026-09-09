"""Command to toggle Markdown preview."""

import sublime_plugin
from ..preview.manager import PreviewManager


class SmpTogglePreviewCommand(sublime_plugin.TextCommand):
    """Toggles Markdown preview state (open if closed, close if open)."""

    def run(self, edit):
        manager = PreviewManager.get_instance()
        manager.toggle_preview(self.view)

    def is_enabled(self):
        manager = PreviewManager.get_instance()
        return manager.is_markdown_view(self.view)
