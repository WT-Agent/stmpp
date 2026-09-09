"""Command to open Markdown preview."""

import sublime_plugin
from ..preview.manager import PreviewManager


class SmpOpenPreviewCommand(sublime_plugin.TextCommand):
    """Opens a Markdown preview for the active view."""

    def run(self, edit, mode="side"):
        manager = PreviewManager.get_instance()
        manager.open_preview(self.view, mode=mode)

    def is_enabled(self):
        manager = PreviewManager.get_instance()
        return manager.is_markdown_view(self.view)
