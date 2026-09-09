"""Command to manually refresh Markdown preview."""

import sublime_plugin
from ..preview.manager import PreviewManager


class SmpRefreshPreviewCommand(sublime_plugin.TextCommand):
    """Forces an immediate re-render of the Markdown preview."""

    def run(self, edit):
        manager = PreviewManager.get_instance()
        manager.render_view(self.view, force=True)

    def is_enabled(self):
        manager = PreviewManager.get_instance()
        return manager.has_session(self.view.id())


class SmpCopyAllCommand(sublime_plugin.ApplicationCommand):
    """Copies full Markdown document text of the active view to clipboard."""

    def run(self):
        import sublime
        window = sublime.active_window()
        if not window:
            return
        view = window.active_view()
        if view and view.is_valid():
            text = view.substr(sublime.Region(0, view.size()))
            sublime.set_clipboard(text)
            sublime.status_message("Copied full markdown document to clipboard")


class SmpCopyTextCommand(sublime_plugin.ApplicationCommand):
    """Copies given text snippet to clipboard."""

    def run(self, text=""):
        import sublime
        import urllib.parse
        if text:
            raw_text = urllib.parse.unquote(text)
            sublime.set_clipboard(raw_text)
            sublime.status_message("Code snippet copied to clipboard")


class SmpCopyCodeCommand(sublime_plugin.ApplicationCommand):
    """Copies code snippet by ID from SnippetCache to clipboard."""

    def run(self, id=0):
        import sublime
        from ..renderer.highlighter import SnippetCache
        code = SnippetCache.get(int(id))
        if code:
            sublime.set_clipboard(code)
            sublime.status_message("Code block copied to clipboard")
        else:
            sublime.status_message("Code snippet expired or not found")


class SmpCopyTableCommand(sublime_plugin.ApplicationCommand):
    """Copies table content by ID from SnippetCache to clipboard."""

    def run(self, id=0):
        import sublime
        from ..renderer.highlighter import SnippetCache
        content = SnippetCache.get(int(id))
        if content:
            sublime.set_clipboard(content)
            sublime.status_message("Table Markdown copied to clipboard")
        else:
            sublime.status_message("Table content expired or not found")




