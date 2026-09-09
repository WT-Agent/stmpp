"""Command to export Markdown preview to a standalone HTML file."""

import os
import sublime
import sublime_plugin
from ..preview.manager import PreviewManager
from ..renderer.engine import MarkdownEngine


class SmpExportHtmlCommand(sublime_plugin.TextCommand):
    """Exports the rendered Markdown view as a standalone HTML file."""

    def run(self, edit):
        manager = PreviewManager.get_instance()
        if not manager.is_markdown_view(self.view):
            return

        file_name = self.view.file_name()
        if not file_name:
            sublime.error_message("Please save the file before exporting HTML.")
            return

        base_dir = os.path.dirname(file_name)
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        default_out = os.path.join(base_dir, f"{base_name}.html")

        content = self.view.substr(sublime.Region(0, self.view.size()))
        settings = manager._load_settings()
        css = manager._prepare_css(self.view, settings)

        engine = MarkdownEngine(options=settings, base_dir=base_dir)
        html_out = engine.render(content, custom_css=css)

        try:
            with open(default_out, "w", encoding="utf-8") as f:
                f.write(html_out)
            sublime.status_message(f"Exported HTML to {os.path.basename(default_out)}")
        except Exception as e:
            sublime.error_message(f"Failed to export HTML: {e}")

    def is_enabled(self):
        manager = PreviewManager.get_instance()
        return manager.is_markdown_view(self.view)
