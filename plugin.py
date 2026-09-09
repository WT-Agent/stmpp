"""Sublime Markdown Preview Plugin Entry Point."""

import sublime
import sublime_plugin

from .commands.open_preview import SmpOpenPreviewCommand
from .commands.close_preview import SmpClosePreviewCommand
from .commands.refresh_preview import (
    SmpRefreshPreviewCommand,
    SmpCopyAllCommand,
    SmpCopyTextCommand,
    SmpCopyCodeCommand,
    SmpCopyTableCommand,
)
from .commands.toggle_preview import SmpTogglePreviewCommand
from .commands.export_html import SmpExportHtmlCommand
from .commands.open_toc import SmpOpenTocCommand
from .preview.manager import PreviewManager

__all__ = [
    "SmpOpenPreviewCommand",
    "SmpClosePreviewCommand",
    "SmpRefreshPreviewCommand",
    "SmpCopyAllCommand",
    "SmpCopyTextCommand",
    "SmpCopyCodeCommand",
    "SmpCopyTableCommand",
    "SmpTogglePreviewCommand",
    "SmpExportHtmlCommand",
    "SmpOpenTocCommand",
    "SmpEventListener",
]


class SmpEventListener(sublime_plugin.EventListener):
    """Listens for editor modifications and lifecycle events to trigger preview updates."""

    def on_modified(self, view: sublime.View):
        manager = PreviewManager.get_instance()
        if manager.has_session(view.id()):
            manager.schedule_render(view)

    def on_modified_async(self, view: sublime.View):
        manager = PreviewManager.get_instance()
        if manager.has_session(view.id()):
            manager.schedule_render(view)

    def on_post_save(self, view: sublime.View):
        manager = PreviewManager.get_instance()
        if manager.has_session(view.id()):
            manager.render_view(view, force=True)

    def on_post_save_async(self, view: sublime.View):
        manager = PreviewManager.get_instance()
        if manager.has_session(view.id()):
            manager.render_view(view, force=True)

    def on_activated(self, view: sublime.View):
        manager = PreviewManager.get_instance()
        manager.on_view_activated(view)

    def on_activated_async(self, view: sublime.View):
        manager = PreviewManager.get_instance()
        manager.on_view_activated(view)

    def on_close(self, view: sublime.View):
        manager = PreviewManager.get_instance()
        manager.on_view_closed(view)
