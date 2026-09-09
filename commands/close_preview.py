"""Command to close Markdown preview."""

import sublime_plugin
from ..preview.manager import PreviewManager


class SmpClosePreviewCommand(sublime_plugin.TextCommand):
    """Closes the Markdown preview for the active view."""

    def run(self, edit):
        manager = PreviewManager.get_instance()
        manager.close_preview(self.view)

    def is_enabled(self):
        manager = PreviewManager.get_instance()
        return manager.has_session(self.view.id())
